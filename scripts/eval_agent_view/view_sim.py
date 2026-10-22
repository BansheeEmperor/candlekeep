#!/usr/bin/env python3
"""Display-policy simulator: what an agent would see under a different way of showing results.

Exploratory, not part of the registered protocol. A search returns ranked results, each with
an Arcane Recall window; the server then decides how much of each window to show. This
simulator replays round 2's searches (state B′'s Layer 1 windows, which equal C′'s) and
scores any display policy on them, without running Candlekeep.

    view_sim.py build                                   build the cache (windows, documents, gold data, features)
    view_sim.py eval FILE.py:FUNC [--split dev] [--cap 4000] [--suites ...] [--paths ...] [--out OUT.json]

A policy is a Python function

    policy(query: dict, results: list[dict], cap: int) -> list[dict]

query    {"query", "path"}: the query text and the query_type (all the server knows; no benchmark labels)
results  ranked results, each:
           rank          0-based rank
           source        document file name
           score         search score (RRF for hybrid/explore, cross-encoder logit for precise)
           text          the full Arcane Recall window (what Candlekeep returned)
           prefix_len    length of the Bardic prefix at the start of `text` ("Document: … Description: …\\n\\n")
           match_offset  where the best-matching chunk starts in `text` (B′ starts its view here)
           n_matches     matched chunks inside the window (may be None)
           title         the document title
           segments      list of {start, end, kind, emb, lex, ce} over `text`:
                           kind  prefix | heading | para | sentence | list | table | code
                           emb   cosine of the segment and the query (bge-small, the server's embedder)
                           lex   share of the query's content words found in the segment
                           ce    cross-encoder logit of (query, segment) (ms-marco-MiniLM-L-6-v2); costly at query time
           doc_text      the document body (frontmatter removed); None if unavailable
           doc_span      (start, end) of the window body inside doc_text, or None if it could not be aligned
cap      the character budget for the whole search output (displayed text, below)

It returns the results to show, in display order:

    {"rank": r, "pieces": [(start, end), ...], "space": "window" | "doc", "title": bool}

`pieces` are character ranges of `text` (space "window") or of `doc_text` (space "doc").
Consecutive pieces that touch are merged; a gap between pieces costs a marker "\\n[…]\\n".
`title` adds a line "Document: <title>\\n\\n". Displayed text = title lines + pieces + gap markers,
summed over the shown results; it must stay within `cap`. Output beyond the cap is cut (and
counted as a violation). Per-result headers (score, source, fences: about 50 characters each)
are not counted against the cap; they are reported as `overhead`.

Metrics (per suite and path, over the chosen split of queries):
  facts_share   mean share of the reference answer's facts shown (CEN and CEN-G; fixture
                tests/fixtures/cen_answer_spans.json; matching as in answer_spans.py)
  facts_all     queries whose every fact is shown        facts_q  queries with facts
  goldtext      mean count of gold-document shingles shown (protocol §7: 150 characters, step 25)
  gold_share    mean share of the gold documents' shingles shown
  srcvis        share of queries with a gold document among the shown results
  support_all   MH: share of queries where every supporting document has a shingle shown
  chars         mean displayed characters per search (also p95, max); adv_chars: on adversarial queries
  violations    searches over the cap

Splits: queries with an odd number (CEN-001, LEG-003, …) are `dev`, even ones `heldout`.
Tune on dev only.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pickle
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import answer_spans as AS  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
RES = REPO / "tests" / "results" / "agent_view_eval_r2"
CACHE = Path.home() / ".cache" / "candlekeep-eval" / "view_sim"
EVAL_HOME = Path.home() / ".cache" / "candlekeep-eval" / "r2"
SUITES = ("CEN", "CEN-G", "MH", "CD-LEG", "CD-MED", "CD-NAR", "CD-API", "CD-ALT", "BEIR-SF", "BEIR-NF")
CORPUS_DIRS = {
    "CEN": [EVAL_HOME / "staging" / "I01"], "MH": [EVAL_HOME / "staging" / "I01"],
    "CEN-G": [EVAL_HOME / "staging" / "I02"],
    "CD-LEG": [REPO / "tests/fixtures/cross_domain/legal_docs"],
    "CD-MED": [REPO / "tests/fixtures/cross_domain/medical_docs"],
    "CD-NAR": [REPO / "tests/fixtures/cross_domain/narrative_docs"],
    "CD-API": [REPO / "tests/fixtures/cross_domain/api_ref_docs"],
    "CD-ALT": [REPO / "tests/fixtures/cross_domain/alternating_docs"],
    "BEIR-SF": [EVAL_HOME / "staging" / "I08"], "BEIR-NF": [EVAL_HOME / "staging" / "I09"],
}
FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
GAP = "\n[…]\n"
HEADER = 50
STOP = set("a an and are as at be by can do does for from has have how i in is it its of on or that the this to "
           "was what when where which who why will with you your vs versus about into than then there these those "
           "should would could my we our".split())


# ── text helpers ─────────────────────────────────────────────────────

def protocol_norm(s: str) -> str:
    """Protocol §7 GoldText normalisation: markdown escapes removed, whitespace collapsed, lower case."""
    s = re.sub(r"\\([_*\[\]()#.\-`|<>])", r"\1", s)       # verify.py's _ESC_RE
    return re.sub(r"\s+", " ", s).lower().strip()


def shingles(text: str) -> list[str]:
    t = protocol_norm(text)
    if not t:
        return []
    return [t] if len(t) < 150 else sorted({t[i:i + 150] for i in range(0, len(t) - 149, 25)})


def words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9][a-z0-9\-\.]*[a-z0-9]|[a-z0-9]", s.lower()) if w not in STOP and len(w) > 1}


def lexical(query_words: set[str], seg: str) -> float:
    if not query_words:
        return 0.0
    sw = words(seg)
    hit = sum(1 for w in query_words if w in sw or (len(w) >= 5 and any(x.startswith(w[:5]) for x in sw)))
    return hit / len(query_words)


def segment(text: str, prefix_len: int) -> list[tuple[int, int, str]]:
    """Segments of a window: prefix, headings, paragraphs (long ones split into sentences),
    list items, table blocks and fenced code blocks, as (start, end, kind)."""
    out = []
    if prefix_len:
        out.append((0, prefix_len, "prefix"))
    i, n = prefix_len, len(text)
    while i < n:
        while i < n and text[i] in "\n ":
            i += 1
        if i >= n:
            break
        if text.startswith("```", i):
            j = text.find("\n```", i + 3)
            j = n if j < 0 else min(n, j + 4)
            out.append((i, j, "code"))
            i = j
            continue
        j = text.find("\n\n", i)
        j = n if j < 0 else j
        block = text[i:j]
        first = block.lstrip()
        if first.startswith("#"):
            nl = block.find("\n")
            if nl < 0:
                out.append((i, j, "heading"))
                i = j
                continue
            out.append((i, i + nl, "heading"))
            i = i + nl + 1
            continue
        if first.startswith("|"):
            out.append((i, j, "table"))
        elif re.match(r"(\s*([-*+]|\d+[.)])\s)", block):
            k = i
            for line in re.split(r"(?<=\n)", block):
                if line.strip():
                    out.append((k, k + len(line.rstrip("\n")), "list"))
                k += len(line)
        elif len(block) > 400:
            k = i
            for sent in re.split(r"(?<=[.!?])\s+", block):
                pos = text.find(sent, k)
                if pos < 0:
                    continue
                out.append((pos, pos + len(sent), "sentence"))
                k = pos + len(sent)
        else:
            out.append((i, j, "para"))
        i = j
    return [(a, b, k) for a, b, k in out if b > a]


def doc_index(suite: str) -> dict[str, Path]:
    idx = {}
    for d in CORPUS_DIRS[suite]:
        for p in d.rglob("*"):
            if p.is_file():
                idx.setdefault(p.name, p)
    return idx


def read_doc(path: Path) -> tuple[str, str | None]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    m = FRONTMATTER.match(raw)
    title = None
    if m:
        t = re.search(r"^title:\s*(.+)$", m.group(1), re.M)
        title = t.group(1).strip().strip("'\"") if t else None
    return (FRONTMATTER.sub("", raw, count=1), title)


def align(window_body: str, doc: str):
    """(start, end) of window_body inside doc, by whitespace-free matching of its ends; None if not found."""
    def squeeze(s):
        keep = [i for i, ch in enumerate(s) if not ch.isspace()]
        return "".join(s[i] for i in keep), keep
    dn, dmap = squeeze(doc)
    wn, _ = squeeze(window_body)
    if not wn:
        return None
    head, tail = wn[:200], wn[-200:]
    a = dn.find(head)
    if a < 0:
        return None
    b = dn.find(tail, a)
    if b < 0:
        return None
    return (dmap[a], dmap[b + len(tail) - 1] + 1)


# ── build ────────────────────────────────────────────────────────────

def cmd_build(suites) -> int:
    import os
    os.environ.setdefault("CANDLEKEEP_DEVICE", "mps")
    os.environ.setdefault("CHROMA_URL", "http://127.0.0.1:65530")
    os.environ.setdefault("CANDLEKEEP_DATA_DIR", str(CACHE / "ck_data"))   # Settings creates it; keep it out of real data
    import numpy as np
    from candlekeep.config import Settings
    from candlekeep.database.embeddings import EmbeddingManager
    from candlekeep.model_lock import call_in_slices
    from candlekeep.rag.reranker import _get_cross_encoder
    em = EmbeddingManager(Settings.from_env())
    ce = _get_cross_encoder("cross-encoder/ms-marco-MiniLM-L-6-v2", os.environ["CANDLEKEEP_DEVICE"])
    CACHE.mkdir(parents=True, exist_ok=True)
    spans = json.loads(AS.FIXTURE.read_text(encoding="utf-8"))["items"]
    cen_by_text = {v["question"]: k for k, v in spans.items()}
    emb_cache: dict[str, np.ndarray] = {}

    def embed(texts):
        todo = [t for t in dict.fromkeys(texts) if t not in emb_cache]
        for i in range(0, len(todo), 256):
            vecs = np.asarray(em.embed(todo[i:i + 256]))
            vecs = vecs / np.linalg.norm(vecs, axis=1, keepdims=True).clip(1e-12)
            emb_cache.update(zip(todo[i:i + 256], vecs))
        return [emb_cache[t] for t in texts]

    for suite in suites:
        l1 = json.loads((RES / "L1" / f"B_{suite}.json").read_text(encoding="utf-8"))
        idx = doc_index(suite)
        docs = {}

        def doc(name):
            if name not in docs:
                p = idx.get(name)
                docs[name] = read_doc(p) if p else (None, None)
            return docs[name]

        queries = {q["qid"]: q for q in l1["queries"]}
        out = {"suite": suite, "queries": {}, "runs": {}, "gold": {}}
        for qid, q in queries.items():
            gold = q.get("gold_sources") or []
            supp = q.get("supporting") or []
            cen = cen_by_text.get(q["query"]) if suite in ("CEN", "CEN-G") else None
            out["queries"][qid] = {"qid": qid, "query": q["query"], "category": q.get("category"),
                                   "gold": gold, "supporting": supp, "cen_qid": cen}
            for g in set(gold) | set(supp):
                if g not in out["gold"]:
                    body, _ = doc(g)
                    out["gold"][g] = shingles(body) if body else None
        pairs, seg_rows = [], []
        for row in l1["rows"]:
            q = queries[row["qid"]]
            qwords = words(q["query"])
            res = []
            for rank, r in enumerate(row["results"]):
                text = r["text"] or ""
                m = re.match(r"Document: [^\n]*\n\n", text)
                prefix_len = m.end() if m else 0
                body, title = doc(r["source"])
                segs = segment(text, prefix_len)
                item = {"rank": rank, "source": r["source"], "score": r["score"], "text": text, "prefix_len": prefix_len,
                        "match_offset": r.get("match_offset") or 0, "n_matches": r.get("n_matches"), "title": title,
                        "doc_text": body, "doc_span": align(text[prefix_len:], body) if body else None,
                        "segments": [{"start": a, "end": b, "kind": k, "lex": lexical(qwords, text[a:b])} for a, b, k in segs]}
                for s in item["segments"]:
                    pairs.append((q["query"], text[s["start"]:s["end"]]))
                    seg_rows.append(s)
                res.append(item)
            out["runs"].setdefault(row["path"], {})[row["qid"]] = res
        # Features: embedding cosine and cross-encoder logits, batched.
        qtexts = [q["query"] for q in queries.values()]
        qvec = dict(zip(qtexts, embed(qtexts)))
        svec = embed([p[1] for p in pairs])
        for s, (qt, _), v in zip(seg_rows, pairs, svec):
            s["emb"] = float(np.dot(qvec[qt], v))
        uniq = list(dict.fromkeys(pairs))
        scores = {}
        for i in range(0, len(uniq), 512):
            batch = uniq[i:i + 512]
            vals = call_in_slices(ce.predict, batch, getattr(ce, "device", "mps"))
            scores.update(zip(batch, (float(x) for x in vals)))
        for s, p in zip(seg_rows, pairs):
            s["ce"] = scores[p]
        with open(CACHE / f"{suite}.pkl", "wb") as f:
            pickle.dump(out, f, protocol=pickle.HIGHEST_PROTOCOL)
        n_res = sum(len(v) for runs in out["runs"].values() for v in runs.values())
        aligned = sum(1 for runs in out["runs"].values() for v in runs.values() for r in v if r["doc_span"])
        print(f"{suite}: {len(queries)} queries, paths {sorted(out['runs'])}, {n_res} results "
              f"({aligned} aligned to their document), {len(seg_rows)} segments", flush=True)
    return 0


# ── eval ─────────────────────────────────────────────────────────────

def qnum(qid: str) -> int:
    m = re.search(r"(\d+)$", qid)
    return int(m.group(1)) if m else 0


def in_split(qid: str, split: str) -> bool:
    return split == "all" or (split == "dev") == (qnum(qid) % 2 == 1)


def render(display: dict, res: list[dict]) -> tuple[str, str]:
    r = res[display["rank"]]
    src = r["text"] if display.get("space", "window") == "window" else (r["doc_text"] or "")
    pieces = []
    for a, b in display.get("pieces", []):
        a, b = max(0, int(a)), min(len(src), int(b))
        if b <= a:
            continue
        if pieces and a <= pieces[-1][1] and a >= pieces[-1][0]:
            pieces[-1] = (pieces[-1][0], max(pieces[-1][1], b))
        else:
            pieces.append((a, b))
    body = GAP.join(src[a:b] for a, b in pieces)
    title = f"Document: {r['title'] or r['source']}\n\n" if display.get("title") else ""
    return r["source"], title + body


def load_policy(spec: str):
    path, _, func = spec.rpartition(":")
    mod_spec = importlib.util.spec_from_file_location(f"policy_{hashlib.md5(path.encode()).hexdigest()[:8]}", path)
    mod = importlib.util.module_from_spec(mod_spec)
    mod_spec.loader.exec_module(mod)
    return getattr(mod, func)


def evaluate(policy, suites, paths, split, cap, per_query: bool = False) -> dict:
    spans = json.loads(AS.FIXTURE.read_text(encoding="utf-8"))["items"]
    report = {}
    for suite in suites:
        with open(CACHE / f"{suite}.pkl", "rb") as f:
            data = pickle.load(f)
        for path in paths:
            runs = data["runs"].get(path)
            if not runs:
                continue
            agg = {k: [] for k in ("facts_share", "goldtext", "gold_share", "srcvis", "support_all", "chars",
                                   "adv_chars", "n_shown")}
            facts_all = facts_q = violations = 0
            pq = {}
            for qid, res in runs.items():
                if not in_split(qid, split):
                    continue
                qd = data["queries"][qid]
                query = {"query": qd["query"], "path": path}     # only what the server knows at display time
                displays = policy(query, res, cap) or []
                parts, sources = [], []
                for d in displays:
                    src, txt = render(d, res)
                    parts.append(txt)
                    sources.append(src)
                total = sum(len(p) for p in parts)
                if total > cap:
                    violations += 1
                    cut, kept = cap, []
                    for p in parts:
                        kept.append(p[:max(0, cut)])
                        cut -= len(p)
                    parts = kept
                out = "\n\n".join(parts)
                agg["chars"].append(min(total, cap))
                agg["n_shown"].append(len(parts))
                rec = pq[qid] = {"chars": min(total, cap)}
                if qd["category"] == "adversarial" or not qd["gold"]:
                    agg["adv_chars"].append(min(total, cap))
                    continue
                on = protocol_norm(out)
                gs = sorted({s for g in qd["gold"] for s in (data["gold"].get(g) or [])})
                hit = sum(1 for s in gs if s in on)
                agg["goldtext"].append(hit)          # 0 when the gold document is not in the corpus, as verify.py
                rec["goldtext"] = hit
                if gs:
                    agg["gold_share"].append(hit / len(gs))
                agg["srcvis"].append(1.0 if any(s in qd["gold"] for s in sources) else 0.0)
                rec["srcvis"] = agg["srcvis"][-1]
                if qd["supporting"]:
                    agg["support_all"].append(1.0 if all(any(s in on for s in (data["gold"].get(g) or [])[:10**6])
                                                         for g in qd["supporting"]) else 0.0)
                cen = qd.get("cen_qid")
                if cen and spans.get(cen, {}).get("facts"):
                    nn = AS.norm(out)
                    facts = spans[cen]["facts"]
                    shown = sum(1 for fct in facts if any(AS.present(x, nn) for x in fct["quotes"]))
                    agg["facts_share"].append(shown / len(facts))
                    rec["facts"], rec["facts_all"] = shown / len(facts), shown == len(facts)
                    facts_q += 1
                    facts_all += shown == len(facts)
            mean = lambda xs: statistics.mean(xs) if xs else None  # noqa: E731
            ch = sorted(agg["chars"])
            report[f"{suite}/{path}"] = {
                "queries": len(agg["chars"]), "facts_q": facts_q, "facts_share": mean(agg["facts_share"]),
                "facts_all": facts_all if facts_q else None, "goldtext": mean(agg["goldtext"]),
                "gold_share": mean(agg["gold_share"]), "srcvis": mean(agg["srcvis"]),
                "support_all": mean(agg["support_all"]), "chars": mean(agg["chars"]),
                "chars_p95": ch[int(0.95 * (len(ch) - 1))] if ch else None, "chars_max": ch[-1] if ch else None,
                "adv_chars": mean(agg["adv_chars"]), "n_shown": mean(agg["n_shown"]),
                "overhead": (mean(agg["n_shown"]) or 0) * HEADER, "violations": violations,
                **({"per_query": pq} if per_query else {})}
    return report


def print_report(report: dict) -> None:
    def f(x, nd=2, pct=False):
        if x is None:
            return "-"
        return f"{x:.0%}" if pct else f"{x:.{nd}f}"
    print(f"{'suite/path':18} {'q':>4} {'facts':>6} {'all':>4} {'goldtext':>9} {'gold%':>6} {'srcvis':>7} "
          f"{'supp':>5} {'chars':>7} {'p95':>6} {'max':>6} {'adv':>6} {'n':>4} {'viol':>4}")
    for k, m in report.items():
        print(f"{k:18} {m['queries']:>4} {f(m['facts_share'], pct=True):>6} "
              f"{(m['facts_all'] if m['facts_all'] is not None else '-'):>4} {f(m['goldtext'], 1):>9} "
              f"{f(m['gold_share'], pct=True):>6} {f(m['srcvis'], pct=True):>7} {f(m['support_all'], pct=True):>5} "
              f"{f(m['chars'], 0):>7} {f(m['chars_p95'], 0):>6} {f(m['chars_max'], 0):>6} {f(m['adv_chars'], 0):>6} "
              f"{f(m['n_shown'], 1):>4} {m['violations']:>4}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--suites", nargs="*", default=list(SUITES))
    e = sub.add_parser("eval")
    e.add_argument("policy", help="FILE.py:FUNCTION")
    e.add_argument("--split", choices=("dev", "heldout", "all"), default="dev")
    e.add_argument("--cap", type=int, default=4000)
    e.add_argument("--suites", nargs="*", default=list(SUITES))
    e.add_argument("--paths", nargs="*", default=["hybrid", "precise", "explore"])
    e.add_argument("--out", type=Path)
    e.add_argument("--per-query", action="store_true", help="add per-query values to --out")
    args = ap.parse_args()
    if args.cmd == "build":
        return cmd_build(args.suites)
    rep = evaluate(load_policy(args.policy), args.suites, args.paths, args.split, args.cap, args.per_query)
    print_report(rep)
    if args.out:
        args.out.write_text(json.dumps({"policy": args.policy, "split": args.split, "cap": args.cap, "report": rep},
                                       indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
