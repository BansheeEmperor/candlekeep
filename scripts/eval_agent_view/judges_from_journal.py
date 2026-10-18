#!/usr/bin/env python3
"""Write judges/out_<P>_part<k>.json from a judge workflow's journal (protocol
section 8, as amended in section 16).

    judges_from_journal.py --journal <workflow transcript dir>/journal.jsonl

Each judge agent of the workflow is labelled `judge:<P>:part<k>` (a retry adds
`:attempt<n>`) and returns `{"items": [{id, verdict, evidence, note}, ...]}` as
structured output, which the journal records verbatim. For every part, the first
attempt whose ids are exactly the part's ids is written, unchanged, as the JSON array
that `judge_pack.py unblind` reads. Nothing is edited, merged or re-ordered here.
judges/journal_extract.json records which agent produced each file.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

LABEL = re.compile(r"^judge:(?P<pack>[A-Z0-9]+):part(?P<part>\d+)(?::attempt(?P<attempt>\d+))?$")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--journal", required=True, type=Path)
    ap.add_argument("--force", action="store_true", help="overwrite existing out_*.json files")
    args = ap.parse_args()
    d = C.CONFIG.results_root / "judges"
    labels, results, order = {}, {}, {}
    for line in args.journal.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec.get("type") == "started" and rec.get("label"):
            labels[rec["agentId"]] = rec["label"]
            order[rec["agentId"]] = len(order)      # start order (a resumed run re-starts unfinished agents)
        elif rec.get("type") == "result":
            results[rec["agentId"]] = rec.get("result")
    attempts: dict = {}
    for agent_id, label in labels.items():
        m = LABEL.match(label)
        if m:
            key = (m["pack"], int(m["part"]))
            attempts.setdefault(key, []).append((int(m["attempt"] or 1), order[agent_id], agent_id, label))
    written, problems = [], []
    for (pack, part), tries in sorted(attempts.items()):
        want = [item["id"] for item in C.load_json(d / f"pack_{pack}_part{part}.json")]
        chosen = None
        for n, (attempt, _, agent_id, label) in enumerate(sorted(tries), 1):
            res = results.get(agent_id)
            if res is None:
                problems.append(f"{label} ({agent_id}), agent {n} of {len(tries)}: no result (stopped without output)")
                continue
            items = res.get("items") if isinstance(res, dict) else None
            ids = [i.get("id") for i in items] if isinstance(items, list) else None
            if ids is not None and sorted(ids) == sorted(want) and len(set(ids)) == len(ids):
                chosen = (n, agent_id, label, items)
                break
            problems.append(f"{label} ({agent_id}), agent {n} of {len(tries)}: result rejected "
                            f"(ids {'missing' if ids is None else len(ids)})")
        if chosen is None:
            problems.append(f"{pack} part {part}: no attempt returned exactly the part's {len(want)} ids")
            continue
        out = d / f"out_{pack}_part{part}.json"
        if out.exists() and not args.force:
            raise SystemExit(f"{out} exists; use --force to overwrite")
        C.write_json_atomic(out, chosen[3])
        written.append({"file": out.name, "pack": pack, "part": part, "agent_number": chosen[0],
                        "agents_started": len(tries), "agent_id": chosen[1],
                        "label": chosen[2], "n_items": len(chosen[3]), "sha256": C.sha256_file(out)})
        print(f"{out.name}: {len(chosen[3])} items from {chosen[2]} ({chosen[1]})")
    C.write_json_atomic(d / "journal_extract.json", {
        "journal": str(args.journal), "journal_sha256": C.sha256_file(args.journal), "extracted_at": C.now_iso(),
        "files": written, "problems": problems})
    for p in problems:
        print("problem:", p)
    return 1 if any(p.endswith("ids") for p in problems) else 0


if __name__ == "__main__":
    sys.exit(main())
