#!/usr/bin/env python3
"""Check that the server's display (src/candlekeep/rag/display.py) makes exactly the choices of
the simulator policy it was ported from (view_policies/combined/combined.py:doc_select), on every
cached search of view_sim.py (all suites, paths and queries).

    display_parity.py            prints the number of searches compared and every difference
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "view_policies" / "combined"))
import combined  # noqa: E402
import view_sim  # noqa: E402
from candlekeep.rag import display  # noqa: E402


def as_items(res):
    """view_sim's result dicts as display.items_of builds them from SearchResults."""
    return [{"rank": r["rank"], "doc": r["source"], "source": r["source"], "score": r["score"], "text": r["text"],
             "prefix_len": r["prefix_len"], "match_offset": r["match_offset"] or 0, "title": r["title"],
             "doc_text": r["doc_text"], "doc_span": tuple(r["doc_span"]) if r["doc_span"] else None} for r in res]


def main() -> int:
    cap, compared, diffs = 4000, 0, []
    for suite in view_sim.SUITES:
        with open(view_sim.CACHE / f"{suite}.pkl", "rb") as f:
            data = pickle.load(f)
        for path, runs in data["runs"].items():
            for qid, res in runs.items():
                q = data["queries"][qid]["query"]
                want = combined.doc_select({"query": q, "path": path}, res, cap)
                items = as_items(res)
                got = display.select(q, items, cap)
                norm = lambda ds: [(d["rank"], [tuple(p) for p in d["pieces"]], d.get("space", "window"), bool(d["title"]))
                                   for d in ds]
                compared += 1
                if norm(want) != norm(got):
                    diffs.append((suite, path, qid))
                    continue
                text = display.render(items, got)
                shown = sum(len(view_sim.render(d, res)[1]) for d in want)
                body = sum(len(b.split("```\n", 1)[1].rsplit("\n```", 1)[0]) for b in text.split("**Score: ")[1:])
                if body != shown or shown > cap:
                    diffs.append((suite, path, qid, "length", shown, body))
    print(f"{compared} searches compared, {len(diffs)} differences")
    for d in diffs[:20]:
        print("  ", d)
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
