#!/usr/bin/env python3
"""Answer visibility: is the correct answer in Candlekeep's result, and is it shown to the agent?

Exploratory measure, not part of the registered protocol. It splits what an agent can
see into two stages, for the CEN-A queries (the 76 CEN queries with a reference answer):

  in result   the answer's facts are inside the windows the search returns (Layer 1
              `text` of the top results, before any display budget);
  shown       the facts are inside the tool output the agent reads (Layer 2 raw output).

A fact is a statement the reference answer needs, tied to verbatim quotes of the gold
document that state it. The facts and quotes come from blind annotators (they see the
question, the reference answer and the gold document, never a search output), checked
by independent verifiers, then validated here: every kept quote must occur verbatim in
the gold document.

    answer_spans.py tasks   --out DIR            annotation batches (batch_<k>.txt / .json)
    answer_spans.py check   --raw DIR            validate annotations, write the fixture
    answer_spans.py measure [--round FILE]       measure every CEN / CEN-G run of the results root

Matching. Text is normalised (markdown backslash escapes removed, `*`, `_` and backticks
removed, lower case, all whitespace removed). A quote is present in a text when every
consecutive 40-character piece of it (the last piece merged when under 20) occurs in the
text. Pieces are shorter than the chunk overlap of both corpora (100 and 50 characters),
so a quote that crosses a chunk boundary is still found in state A, whose windows repeat
each chunk's prefix and overlap. A fact is present when any of its quotes is.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

FIXTURE = C.REPO / "tests" / "fixtures" / "cen_answer_spans.json"
FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)   # DocumentProcessor.FRONTMATTER_PATTERN
PIECE, MIN_TAIL, MIN_QUOTE = 40, 20, 20
PATHS = ("hybrid", "precise", "explore")
MARK = "<<<"


def norm(s: str) -> str:
    s = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|>~])", r"\1", s)
    return re.sub(r"[\s*_`]+", "", s).lower()


def pieces(quote: str) -> list[str]:
    q = norm(quote)
    out = [q[i:i + PIECE] for i in range(0, len(q), PIECE)]
    if len(out) > 1 and len(out[-1]) < MIN_TAIL:
        out[-2:] = [out[-2] + out[-1]]
    return out


def present(quote: str, text_norm: str) -> bool:
    ps = pieces(quote)
    return bool(ps) and all(p in text_norm for p in ps)


def cen_a() -> list[dict]:
    """The CEN-A queries: non-adversarial CEN queries with a non-empty reference answer."""
    suite = json.loads((C.REPO / "tests/fixtures/eval_suite_with_answers.json").read_text(encoding="utf-8"))
    qs = suite["queries"] if isinstance(suite, dict) else suite
    out = []
    for i, q in enumerate(qs, 1):
        ref = (q.get("reference_answer") or "").strip()
        if q.get("category") == "adversarial" or not ref or not q.get("expected_sources"):
            continue
        out.append({"qid": f"CEN-{i:03d}", "question": q["query"], "reference_answer": ref,
                    "gold_source": q["expected_sources"][0]})
    return out


def doc_body(rel: str) -> str:
    return FRONTMATTER.sub("", (C.REPO / rel).read_text(encoding="utf-8"), count=1)


# ── tasks ────────────────────────────────────────────────────────────

def cmd_tasks(out: Path, n_batches: int) -> int:
    items = cen_a()
    out.mkdir(parents=True, exist_ok=True)
    size = -(-len(items) // n_batches)
    for k in range(n_batches):
        batch = items[k * size:(k + 1) * size]
        lines = [f"{MARK}BATCH {k + 1}: {len(batch)} items>>>"]
        for it in batch:
            body = doc_body(it["gold_source"])
            for name, text in (("question", it["question"]), ("reference_answer", it["reference_answer"]), ("document", body)):
                if MARK in text:
                    raise SystemExit(f"{it['qid']}: {name} contains {MARK!r}")
            lines += [f"{MARK}ITEM {it['qid']}>>>", f"{MARK}QUESTION>>>", it["question"],
                      f"{MARK}REFERENCE_ANSWER>>>", it["reference_answer"],
                      f"{MARK}DOCUMENT {it['gold_source']}>>>", body.rstrip("\n"), f"{MARK}END_ITEM {it['qid']}>>>", ""]
        txt = out / f"batch_{k + 1}.txt"
        txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
        (out / f"batch_{k + 1}.json").write_text(json.dumps([it["qid"] for it in batch]) + "\n", encoding="utf-8")
        print(f"{txt}: {len(batch)} items, {txt.read_text(encoding='utf-8').count(chr(10))} lines")
    return 0


# ── check ────────────────────────────────────────────────────────────

def cmd_check(raw: Path) -> int:
    """raw/annotation_<k>.json and raw/verification_<k>.json (the workflow's structured outputs)."""
    items = {it["qid"]: it for it in cen_a()}
    ann = {}
    for f in sorted(raw.glob("annotation_*.json")):
        for it in json.loads(f.read_text(encoding="utf-8"))["items"]:
            ann[it["qid"]] = it
    ver = {}
    for f in sorted(raw.glob("verification_*.json")):
        for it in json.loads(f.read_text(encoding="utf-8"))["items"]:
            ver[it["qid"]] = it
    missing = sorted(set(items) - set(ann))
    if missing:
        raise SystemExit(f"no annotation for {missing}")
    fixture, stats = {}, {"facts": 0, "kept": 0, "dropped_by_verifier": 0, "not_in_document": 0,
                          "added_by_verifier": 0, "quotes": 0, "quotes_not_verbatim": 0, "facts_without_valid_quote": 0}
    for qid, it in items.items():
        body_n = norm(doc_body(it["gold_source"]))
        checks = {c["id"]: c for c in (ver.get(qid) or {}).get("checks", [])}
        facts, absent, dropped = [], [], []
        candidates = [dict(f, source="annotator") for f in ann[qid]["facts"]]
        candidates += [{"id": f"V{i}", "fact": m["fact"], "in_document": bool(m.get("quotes")),
                        "quotes": m.get("quotes") or [], "source": "verifier"}
                       for i, m in enumerate((ver.get(qid) or {}).get("missing", []), 1)]
        for f in candidates:
            stats["facts"] += 1
            if f["source"] == "annotator" and qid in ver and not checks.get(f["id"], {}).get("keep", False):
                stats["dropped_by_verifier"] += 1
                dropped.append({"fact": f["fact"], "reason": checks.get(f["id"], {}).get("reason", "not checked")})
                continue
            if f["source"] == "verifier":
                stats["added_by_verifier"] += 1
            if not f.get("in_document") or not f.get("quotes"):
                stats["not_in_document"] += 1
                absent.append(f["fact"])
                continue
            good = []
            for q in f["quotes"]:
                stats["quotes"] += 1
                if len(norm(q)) >= MIN_QUOTE and norm(q) in body_n:
                    good.append(q)
                else:
                    stats["quotes_not_verbatim"] += 1
            if not good:
                stats["facts_without_valid_quote"] += 1
                dropped.append({"fact": f["fact"], "reason": "no quote occurs verbatim in the document"})
                continue
            stats["kept"] += 1
            facts.append({"id": f["id"], "fact": f["fact"], "quotes": good, "source": f["source"]})
        fixture[qid] = {"question": it["question"], "gold_source": it["gold_source"], "facts": facts,
                        "facts_not_in_document": absent, "dropped": dropped}
    doc = {"version": 1, "description": "Facts of each CEN-A reference answer, with verbatim quotes of the gold "
                                        "document that state them (scripts/eval_agent_view/answer_spans.py).",
           "matching": f"normalised text; every {PIECE}-character piece of a quote must occur", "stats": stats,
           "items": fixture}
    FIXTURE.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {FIXTURE}: {json.dumps(stats)}")
    no_fact = [q for q, v in fixture.items() if not v["facts"]]
    if no_fact:
        print(f"queries without a document-supported fact (left out of the measure): {no_fact}")
    return 0


# ── measure ──────────────────────────────────────────────────────────

def _rows(path: Path) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    return {(r["qid"], r["path"]): r for r in d["rows"]}, d.get("queries")


def _qid_map(queries) -> dict:
    """CEN-G file qid -> CEN qid, by query text."""
    by_text = {it["question"]: it["qid"] for it in cen_a()}
    return {q["qid"]: by_text[q["query"]] for q in queries or [] if q.get("query") in by_text}


def _verdicts() -> dict:
    """{(state, CEN qid): J1 verdict} from the results root's judges, when present."""
    d = C.CONFIG.results_root / "judges"
    km = d / "keymap_J1.json"
    if not km.exists():
        return {}
    keymap = json.loads(km.read_text(encoding="utf-8"))
    out = {}
    for f in d.glob("out_J1_part*.json"):
        for e in json.loads(f.read_text(encoding="utf-8")):
            qid, st = keymap[e["id"]].split("|")
            out[(st, qid)] = str(e["verdict"]).lower()
    return out


def _measure_run(spans: dict, l1: dict, l2: dict, qmap: dict) -> dict:
    out = {}
    for p in PATHS:
        per_q = {}
        for (fqid, path), r2 in l2.items():
            qid = qmap.get(fqid, fqid)
            if path != p or qid not in spans or not spans[qid]["facts"]:
                continue
            r1 = l1.get((fqid, p))
            win = norm(" ".join(x.get("text") or "" for x in (r1 or {}).get("results", [])))
            shown = norm(r2.get("raw_output") or "")
            facts = spans[qid]["facts"]
            in_res = [any(present(q, win) for q in f["quotes"]) for f in facts]
            in_out = [any(present(q, shown) for q in f["quotes"]) for f in facts]
            per_q[qid] = {"facts": len(facts), "in_result": sum(in_res), "shown": sum(in_out),
                          "shown_not_in_result": sum(1 for a, b in zip(in_res, in_out) if b and not a)}
        if not per_q:
            continue
        n = len(per_q)
        out[p] = {
            "queries": n,
            "facts": sum(v["facts"] for v in per_q.values()),
            "fact_share_in_result": statistics.mean(v["in_result"] / v["facts"] for v in per_q.values()),
            "fact_share_shown": statistics.mean(v["shown"] / v["facts"] for v in per_q.values()),
            "all_facts_in_result": sum(v["in_result"] == v["facts"] for v in per_q.values()),
            "all_facts_shown": sum(v["shown"] == v["facts"] for v in per_q.values()),
            "no_fact_in_result": sum(v["in_result"] == 0 for v in per_q.values()),
            "no_fact_shown": sum(v["shown"] == 0 for v in per_q.values()),
            "per_query": per_q,
        }
    return out


def cmd_measure() -> int:
    spans = json.loads(FIXTURE.read_text(encoding="utf-8"))["items"]
    root = C.CONFIG.results_root
    runs = []
    for suite in ("CEN", "CEN-G"):
        for st in ("A", "B", "C"):
            runs.append((f"{st}_{suite}", st, suite, f"{st}_{suite}"))
    runs += [("B_CEN_rerun", "B", "CEN", "B_CEN_rerun"), ("C_CEN_killswitch", "C", "CEN", "C_CEN")]
    runs += [(p.stem, p.stem.split("_")[1], p.stem.rsplit("_", 1)[1], f"{p.stem.split('_')[1]}_{p.stem.rsplit('_', 1)[1]}")
             for p in sorted((root / "L2").glob("info_*_CEN*.json"))]
    result, verdicts = {}, _verdicts()
    for name, st, suite, l1_name in runs:
        l2p, l1p = root / "L2" / f"{name}.json", root / "L1" / f"{l1_name}.json"
        if not (l2p.exists() and l1p.exists()):
            continue
        l2, queries = _rows(l2p)
        l1, _ = _rows(l1p)
        qmap = _qid_map(queries) if suite == "CEN-G" else {}
        result[name] = {"state": st, "suite": suite, "layer1": l1p.name, **_measure_run(spans, l1, l2, qmap)}
    # How the judges' verdicts line up with "all facts shown" (CEN hybrid, J1).
    agreement = {}
    for st in ("A", "B", "C"):
        pq = (result.get(f"{st}_CEN") or {}).get("hybrid", {}).get("per_query", {})
        tab: dict = {}
        for qid, v in pq.items():
            vd = verdicts.get((st, qid))
            if vd:
                key = f"{vd}|{'all shown' if v['shown'] == v['facts'] else 'some shown' if v['shown'] else 'none shown'}"
                tab[key] = tab.get(key, 0) + 1
        if tab:
            agreement[st] = dict(sorted(tab.items()))
    out_dir = root / "answer_visibility"
    out_dir.mkdir(parents=True, exist_ok=True)
    C.write_json_atomic(out_dir / "answer_visibility.json", {
        "fixture": str(FIXTURE), "fixture_sha256": C.sha256_file(FIXTURE), "generated_at": C.now_iso(),
        "matching": f"normalised; every {PIECE}-char piece of a quote present", "runs": result,
        "judge_vs_shown_CEN_hybrid": agreement})
    print(f"{'run':24} {'path':8} {'q':>3} {'facts in result':>16} {'facts shown':>12} {'shown/in result':>16} "
          f"{'all in result':>14} {'all shown':>10}")
    for name, r in result.items():
        for p in PATHS:
            m = r.get(p)
            if not m:
                continue
            ratio = m["fact_share_shown"] / m["fact_share_in_result"] if m["fact_share_in_result"] else float("nan")
            print(f"{name:24} {p:8} {m['queries']:>3} {m['fact_share_in_result']:>15.0%} {m['fact_share_shown']:>12.0%} "
                  f"{ratio:>16.0%} {m['all_facts_in_result']:>14} {m['all_facts_shown']:>10}")
    for st, tab in agreement.items():
        print(f"J1 verdict vs facts shown, {st} CEN hybrid: {tab}")
    print(f"wrote {out_dir / 'answer_visibility.json'}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tasks")
    t.add_argument("--out", required=True, type=Path)
    t.add_argument("--batches", type=int, default=4)
    c = sub.add_parser("check")
    c.add_argument("--raw", required=True, type=Path)
    m = sub.add_parser("measure")
    C.add_hidden_args(m)
    args = ap.parse_args()
    if args.cmd == "tasks":
        return cmd_tasks(args.out, args.batches)
    if args.cmd == "check":
        return cmd_check(args.raw)
    C.apply_overrides(args)
    return cmd_measure()


if __name__ == "__main__":
    sys.exit(main())
