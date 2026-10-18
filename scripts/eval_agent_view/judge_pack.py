#!/usr/bin/env python3
"""Blind judge packs for Layer 3 (protocol section 8, as amended in section 16).

    judge_pack.py build --pack J1     hybrid path, states A/B/C x 76 CEN-A queries = 228 items
    judge_pack.py build --pack J1R    a 20% sample of J1 (round(0.2 x 228) = 46), re-issued under new ids
    judge_pack.py build --pack J2     precise path, states B/C x 76 = 152 items (optional pack)
    judge_pack.py unblind --pack P    join judges/out_<P>_part*.json with the key map

CEN-A is the 78 non-adversarial CEN queries minus those whose reference answer is
empty in the fixture (CEN-014 and CEN-038, protocol section 16); the excluded qids
are recorded in the manifest. Each item is {id, question, reference_answer,
tool_output}: the CEN-A question, its reference answer (eval_suite_with_answers.json,
same index as eval_suite_100.json) and the raw `search` output from
L2/<STATE>_CEN.json. No state, path or source label is included. Items are shuffled
with random.Random(seed) and numbered J0001.. (J1), K0001.. (J2); J1R draws
round(0.2 * 228) sorted J1 ids with random.Random(seed).sample and numbers them
R0001... unblind splits each evidence string on " ... " and checks every part
verbatim against the item's tool output (the rule verify.py applies).

Files (under tests/results/agent_view_eval/judges/):
    pack_<P>.json                 all items, no keys
    pack_<P>_part<k>.json         balanced parts of at most 26 items, one per judge
    keymap_<P>.json (+ .sha256)   id -> "qid|STATE" (J1R: R id -> J id)
    manifest_<P>.json             inputs, seed, counts, key-map hash (no keys)
    results_<P>.json              written by unblind

Seeds: protocol section 4 fixes seed 20261018 for every shuffled or sampled step,
so every pack defaults to it. --seed overrides it (log a deviation if used).
"""
from __future__ import annotations

import argparse
import hashlib
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

PACKS = {
    "J1": {"path": "hybrid", "states": ["A", "B", "C"], "prefix": "J"},
    "J2": {"path": "precise", "states": ["B", "C"], "prefix": "K"},
}
REJUDGE = {"J1R": {"source": "J1", "prefix": "R"}}
PART_MAX = 26
VERDICTS = ("full", "partial", "none")
# Protocol section 16: CEN-014 and CEN-038 have empty reference answers and are not
# judged, so CEN-A has 76 queries (J1 = 228 items, J1R = 46, J2 = 152).
CEN_A_N = 76
CEN_A_EXCLUDED = ("CEN-014", "CEN-038")
EVIDENCE_SEPARATOR = " ... "


def judges_dir() -> Path:
    d = C.CONFIG.results_root / "judges"
    d.mkdir(parents=True, exist_ok=True)
    return d


def keymap_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def balanced_parts(items: list, cap: int = PART_MAX) -> list[list]:
    """Split into ceil(n / cap) consecutive parts whose sizes differ by at most one."""
    if not items:
        return []
    k = -(-len(items) // cap)
    base, extra = divmod(len(items), k)
    parts, start = [], 0
    for i in range(k):
        size = base + (1 if i < extra else 0)
        parts.append(items[start:start + size])
        start += size
    return parts


def write_pack(name: str, pack: list, keymap: dict, manifest: dict, force: bool) -> None:
    d = judges_dir()
    targets = [d / f"pack_{name}.json", d / f"keymap_{name}.json", d / f"keymap_{name}.json.sha256",
               d / f"manifest_{name}.json"]
    existing = [p for p in targets + sorted(d.glob(f"pack_{name}_part*.json")) if p.exists()]
    if existing and not force:
        raise SystemExit(f"{name} already built ({existing[0]}); use --force to rebuild")
    for p in d.glob(f"pack_{name}_part*.json"):
        p.unlink()
    C.write_json_atomic(d / f"pack_{name}.json", pack)
    C.write_json_atomic(d / f"keymap_{name}.json", dict(sorted(keymap.items())))
    digest = keymap_sha(d / f"keymap_{name}.json")
    (d / f"keymap_{name}.json.sha256").write_text(f"{digest}  keymap_{name}.json\n", encoding="utf-8")
    parts = balanced_parts(pack)
    for k, part in enumerate(parts, 1):
        C.write_json_atomic(d / f"pack_{name}_part{k}.json", part)
    manifest.update({"pack": name, "n_items": len(pack), "parts": [len(p) for p in parts],
                     "keymap_sha256": digest, "built_at": C.now_iso(),
                     "harness_sha256": C.harness_hashes("judge_pack.py")})
    C.write_json_atomic(d / f"manifest_{name}.json", manifest)
    print(f"{name}: {len(pack)} items in {len(parts)} parts {[len(p) for p in parts]}")
    print(f"keymap_{name}.json SHA-256: {digest}")


def build_main(name: str, seed: int, force: bool) -> None:
    spec = PACKS[name]
    answers = C._query_list(C.load_json(C.CEN_ANSWERS))
    docs, items, excluded, inputs = {}, [], [], {}
    try:  # every input must come from the CEN corpus's current ingest
        _, identity = C.current_ingest(C.CORPORA[C.SUITES["CEN"].corpus])
    except C.IngestError as e:
        raise SystemExit(f"cannot build {name}: {e}")
    for state in spec["states"]:
        path = C.layer_path("L2", state, "CEN")
        doc = C.load_json(path)
        meta = doc["meta"]
        if meta.get("state") != state or meta.get("suite") != "CEN" or meta.get("tag"):
            raise SystemExit(f"{path}: unexpected meta state={meta.get('state')} suite={meta.get('suite')} "
                             f"tag={meta.get('tag')}")
        why = C.identity_mismatch(meta, identity)
        if why:
            raise SystemExit(f"{path} was not computed on the current ingest of the CEN corpus ({why})")
        if meta.get("invalid"):
            raise SystemExit(f"{path} is marked invalid: {meta['invalid']}")
        docs[state] = doc
        inputs[state] = {"file": str(path), "sha256": C.sha256_file(path), "ingest_uuid": meta.get("ingest_uuid"),
                         "git_sha": meta.get("git_sha"), "src_tree_sha": meta.get("src_tree_sha")}
    queries = docs[spec["states"][0]]["queries"]
    for state, doc in docs.items():
        if [q["qid"] for q in doc["queries"]] != [q["qid"] for q in queries]:
            raise SystemExit(f"L2/{state}_CEN.json has a different query list")
    if len(answers) != len(queries):
        raise SystemExit("eval_suite_with_answers.json and the CEN queries differ in length")
    for state in spec["states"]:
        rows = {r["qid"]: r for r in docs[state]["rows"] if r["path"] == spec["path"]}
        for i, q in enumerate(queries):
            if C.is_adversarial(q):
                continue
            if answers[i]["query"] != q["query"]:
                raise SystemExit(f"{q['qid']}: answers file has a different query at index {i}")
            reference = answers[i].get("reference_answer") or ""
            if not reference.strip():  # no ground truth to judge against (protocol section 16)
                if state == spec["states"][0]:
                    excluded.append(q["qid"])
                continue
            row = rows.get(q["qid"])
            if row is None or row.get("error") is not None:
                raise SystemExit(f"L2/{state}_CEN.json {q['qid']} {spec['path']}: missing row or tool error")
            items.append({"key": f"{q['qid']}|{state}", "question": q["query"], "reference_answer": reference,
                          "tool_output": row["raw_output"]})
    per_state = len(items) // len(spec["states"])
    if tuple(excluded) != CEN_A_EXCLUDED or per_state != CEN_A_N:
        raise SystemExit(f"{name}: the fixtures give {per_state} CEN-A queries (excluded for an empty reference "
                         f"answer: {excluded}); protocol section 16 fixes {CEN_A_N} (excluded {list(CEN_A_EXCLUDED)})")
    random.Random(seed).shuffle(items)
    pack, keymap = [], {}
    for n, item in enumerate(items, 1):
        item_id = f"{spec['prefix']}{n:04d}"
        keymap[item_id] = item["key"]
        pack.append({"id": item_id, "question": item["question"], "reference_answer": item["reference_answer"],
                     "tool_output": item["tool_output"]})
    manifest = {"path": spec["path"], "states": spec["states"], "seed": seed, "inputs": inputs,
                "answers": str(C.CEN_ANSWERS), "queries_per_state": per_state,
                "excluded_qids": excluded,
                "excluded_reason": "non-adversarial CEN queries with an empty reference answer in the fixture "
                                   "(protocol section 16)"}
    print(f"{name}: {per_state} CEN-A queries per state; excluded (empty reference answer): {excluded}")
    write_pack(name, pack, keymap, manifest, force)


def build_rejudge(name: str, seed: int, fraction: float, force: bool) -> None:
    spec = REJUDGE[name]
    d = judges_dir()
    source = spec["source"]
    keymap_path = d / f"keymap_{source}.json"
    recorded = (d / f"keymap_{source}.json.sha256").read_text(encoding="utf-8").split()[0]
    if keymap_sha(keymap_path) != recorded:
        raise SystemExit(f"{keymap_path} does not match its recorded SHA-256")
    source_pack = {item["id"]: item for item in C.load_json(d / f"pack_{source}.json")}
    ids = sorted(C.load_json(keymap_path))
    expected = CEN_A_N * len(PACKS[source]["states"])
    if len(ids) != expected or set(ids) != set(source_pack):
        raise SystemExit(f"{source} has {len(ids)} key-map ids and {len(source_pack)} pack items; "
                         f"protocol section 16 fixes {expected}")
    k = round(fraction * len(ids))           # round(0.2 x 228) = 46
    sample = random.Random(seed).sample(ids, k)
    pack, keymap = [], {}
    for n, source_id in enumerate(sample, 1):
        item_id = f"{spec['prefix']}{n:04d}"
        keymap[item_id] = source_id
        pack.append({**source_pack[source_id], "id": item_id})
    manifest = {"source_pack": source, "source_keymap_sha256": recorded, "source_items": len(ids),
                "fraction": fraction, "seed": seed}
    write_pack(name, pack, keymap, manifest, force)


def evidence_parts(evidence) -> list[str]:
    """The quoted passages of a judge's evidence: a string or a list of strings (an
    object counts as its quote/text/snippet/evidence field), each split on " ... ",
    the separator between non-adjacent quotes; blank parts are dropped."""
    if evidence is None:
        return []
    parts = []
    for entry in evidence if isinstance(evidence, list) else [evidence]:
        if isinstance(entry, dict):
            entry = next((entry[k] for k in ("quote", "text", "snippet", "evidence") if k in entry), None) or ""
        parts += [p for p in str(entry).split(EVIDENCE_SEPARATOR) if p.strip()]
    return parts


def part_in_output(part: str, output: str) -> bool:
    """A part occurs verbatim in the tool output, apart from surrounding whitespace,
    quote marks and a leading or trailing ellipsis the judge put around it."""
    if part in output or part.strip() in output:
        return True
    text = part.strip().strip("\"'“”").strip()
    text = re.sub(r"^(\.\.\.|…)\s*", "", text)
    text = re.sub(r"\s*(\.\.\.|…)$", "", text)
    return bool(text) and text in output


def unblind(name: str) -> int:
    d = judges_dir()
    pack = {item["id"]: item for item in C.load_json(d / f"pack_{name}.json")}
    keymap_path = d / f"keymap_{name}.json"
    keymap = C.load_json(keymap_path)
    recorded = (d / f"keymap_{name}.json.sha256").read_text(encoding="utf-8").split()[0]
    sha_ok = keymap_sha(keymap_path) == recorded
    resolve = keymap
    source_keymap = None
    if name in REJUDGE:
        source_keymap = C.load_json(d / f"keymap_{REJUDGE[name]['source']}.json")
        resolve = {rid: source_keymap[jid] for rid, jid in keymap.items()}
    out_files = sorted(d.glob(f"out_{name}_part*.json"))
    judged, problems = {}, []
    # The L2 files the pack was built from must be unchanged (J1R: those of J1).
    manifest_path = d / f"manifest_{REJUDGE[name]['source'] if name in REJUDGE else name}.json"
    inputs = C.load_json(manifest_path).get("inputs", {}) if manifest_path.is_file() else None
    if inputs is None:
        problems.append(f"{manifest_path.name} missing: cannot check the pack's input files")
    for state, info in (inputs or {}).items():
        f = Path(info["file"])
        if not f.is_file() or C.sha256_file(f) != info["sha256"]:
            problems.append(f"input {f} of state {state} changed or is missing since the pack was built")
    for f in out_files:
        entries = C.load_json(f)
        if not isinstance(entries, list):
            problems.append(f"{f.name}: not a JSON array")
            continue
        for e in entries:
            item_id = e.get("id")
            if item_id not in pack:
                problems.append(f"{f.name}: unknown id {item_id!r}")
                continue
            if item_id in judged:
                problems.append(f"{f.name}: {item_id} judged more than once")
                continue
            verdict = str(e.get("verdict", "")).strip().lower()
            if verdict not in VERDICTS:
                problems.append(f"{f.name}: {item_id} has verdict {e.get('verdict')!r}")
            evidence = e.get("evidence")
            parts = evidence_parts(evidence)          # split on " ... " before the verbatim check
            output = pack[item_id]["tool_output"]
            not_found = [p for p in parts if not part_in_output(p, output)]
            judged[item_id] = {"verdict": verdict, "evidence": evidence, "note": e.get("note"),
                               "evidence_parts": len(parts), "evidence_verbatim": not not_found,
                               "evidence_not_found": not_found, "out_file": f.name}
    missing = sorted(set(pack) - set(judged))
    results = []
    for item_id in sorted(pack):
        key = resolve[item_id]
        qid, state = key.split("|")
        row = {"id": item_id, "key": key, "state": state, "qid": qid}
        if source_keymap is not None:
            row["source_id"] = keymap[item_id]
        row.update(judged.get(item_id, {"verdict": None, "evidence": None, "note": None, "evidence_parts": None,
                                        "evidence_verbatim": None, "evidence_not_found": None, "out_file": None}))
        results.append(row)
    counts: dict = {}
    for r in results:
        if r["verdict"] in VERDICTS:
            counts.setdefault(r["state"], {v: 0 for v in VERDICTS})[r["verdict"]] += 1
    report = {
        "pack": name, "unblinded_at": C.now_iso(), "keymap_sha256": keymap_sha(keymap_path),
        "keymap_sha256_recorded": recorded, "keymap_sha256_ok": sha_ok,
        "out_files": [f.name for f in out_files], "n_items": len(pack), "n_judged": len(judged),
        "missing": missing, "problems": problems,
        "evidence_not_verbatim": [r["id"] for r in results if r["evidence_verbatim"] is False],
        "counts_by_state": counts, "items": results,
    }
    C.write_json_atomic(d / f"results_{name}.json", report)
    print(f"wrote {d / f'results_{name}.json'}: {len(judged)}/{len(pack)} judged, {len(missing)} missing, "
          f"{len(problems)} problems, key map SHA-256 ok: {sha_ok}")
    for state, c in sorted(counts.items()):
        print(f"  {state}: {c}")
    return 0 if sha_ok and not missing and not problems else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--pack", required=True, choices=sorted([*PACKS, *REJUDGE]))
    b.add_argument("--seed", type=int, default=C.SEED, help=f"default {C.SEED} (protocol section 4)")
    b.add_argument("--fraction", type=float, default=0.2, help="J1R share of J1 items (default 0.2)")
    b.add_argument("--force", action="store_true", help="rebuild an existing pack")
    C.add_hidden_args(b)
    u = sub.add_parser("unblind")
    u.add_argument("--pack", required=True, choices=sorted([*PACKS, *REJUDGE]))
    C.add_hidden_args(u)
    args = ap.parse_args()
    C.apply_overrides(args)
    if args.cmd == "build":
        if args.pack in REJUDGE:
            build_rejudge(args.pack, args.seed, args.fraction, args.force)
        else:
            build_main(args.pack, args.seed, args.force)
        return 0
    return unblind(args.pack)


if __name__ == "__main__":
    sys.exit(main())
