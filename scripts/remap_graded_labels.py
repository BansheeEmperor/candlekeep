#!/usr/bin/env python3
"""Re-point the Centurion Set's graded labels at the current chunking.

The graded labels ("graded_relevance" in tests/fixtures/eval_suite_100.json) are
keyed "source:chunk_index". They were made on 2026-02-26 (51f939f) with the
processor of that time, at chunk overlap 50. Two later changes moved chunk indices
of some documents:

* 69172ef (2026-03-17) added setext-header splitting to the chunker;
* the 2026-10-19 fixture repair fixed frontmatter that did not parse and a
  metadata block written as a ```yaml fence. The processor used to keep such a
  block in the body, so it formed the document's first chunk(s); now it is
  metadata, and every later chunk index moves.

For each labelled key, the script rebuilds the labelled chunk's text exactly as
the labelling-time processor produced it (its source is loaded from git at
51f939f, applied to the documents as they were at 51f939f). It then finds the
current processor's chunk (overlap 50) of the current document that holds that
text, and moves the key there. A label whose text has no counterpart is dropped,
e.g. a chunk that held only the raw frontmatter, which is now the Bardic
Knowledge prefix of every chunk. If two old keys land on one new chunk, the
higher grade is kept.

    python scripts/remap_graded_labels.py            # print the remap
    python scripts/remap_graded_labels.py --write    # also update eval_suite_100.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
from candlekeep.config import Settings  # noqa: E402
from candlekeep.rag.processor import DocumentProcessor  # noqa: E402

LABEL_COMMIT = "51f939f"
SUITE = REPO / "tests" / "fixtures" / "eval_suite_100.json"
OVERLAP = 50            # the annotation chunking
SHINGLE, STEP = 30, 5   # containment test for chunks whose text changed
MIN_CONTAINMENT = 0.6


def git_show(path: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), "show", f"{LABEL_COMMIT}:{path}"],
                          capture_output=True, text=True, check=True).stdout


def labelling_time_chunker():
    """The processor class as it was at LABEL_COMMIT, with overlap 50."""
    ns: dict = {}
    exec(compile(git_show("src/candlekeep/rag/processor.py"), f"{LABEL_COMMIT}:processor.py", "exec"), ns)
    old = object.__new__(ns["DocumentProcessor"])
    old.settings = types.SimpleNamespace(chunk_size=512, chunk_overlap=OVERLAP, bardic_knowledge=True)
    return lambda text: old._chunk_text(old._parse_frontmatter(text)[1])


def current_chunker():
    settings = Settings.from_env()
    settings.chunk_overlap = OVERLAP
    new = DocumentProcessor(settings)
    return lambda text: new._chunk_text(new._parse_frontmatter(text)[1])


def shingles(text: str) -> set:
    t = " ".join(text.split())
    return {t[i:i + SHINGLE] for i in range(0, max(1, len(t) - SHINGLE + 1), STEP)}


def match(old_text: str, candidates: list[str]) -> tuple[int | None, str]:
    for i, c in enumerate(candidates):
        if c == old_text:
            return i, "exact"
    want = shingles(old_text)
    best, score = None, 0.0
    for i, c in enumerate(candidates):
        s = len(want & shingles(c)) / len(want)
        if s > score:
            best, score = i, s
    if best is not None and score >= MIN_CONTAINMENT:
        return best, f"containment {score:.2f}"
    return None, f"no counterpart (best containment {score:.2f})"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="update eval_suite_100.json")
    args = ap.parse_args()
    old_chunks, new_chunks = labelling_time_chunker(), current_chunker()
    suite = json.loads(SUITE.read_text(encoding="utf-8"))
    if suite["metadata"].get("version") != "1.2":
        # The keys must still be labelling-time indices; a remapped suite is 1.3.
        raise SystemExit(f"{SUITE} is version {suite['metadata'].get('version')}, not 1.2: already remapped")
    cache: dict = {}

    def chunks_of(source: str):
        if source not in cache:
            cache[source] = (old_chunks(git_show(source)), new_chunks((REPO / source).read_text(encoding="utf-8")))
        return cache[source]

    moved, dropped, kept = [], [], 0
    for q in suite["queries"]:
        labels = q.get("graded_relevance")
        if not labels:
            continue
        out: dict = {}
        for key, grade in labels.items():
            source, idx = key.rsplit(":", 1)
            old, new = chunks_of(source)
            i = int(idx)
            if i < len(old) and i < len(new) and old[i] == new[i]:
                new_key, how = key, "unchanged"
            elif i >= len(old):
                new_key, how = None, "index beyond the labelling-time chunks"
            else:
                j, how = match(old[i], new)
                new_key = f"{source}:{j}" if j is not None else None
            if new_key is None:
                dropped.append({"query": q["query"], "key": key, "grade": grade, "why": how})
                continue
            if new_key != key:
                moved.append({"query": q["query"], "from": key, "to": new_key, "grade": grade, "how": how})
            else:
                kept += 1
            out[new_key] = max(grade, out.get(new_key, grade))
        q["graded_relevance"] = out
    print(json.dumps({"kept": kept, "moved": moved, "dropped": dropped}, indent=1, ensure_ascii=False))
    print(f"kept {kept}, moved {len(moved)}, dropped {len(dropped)}", file=sys.stderr)
    if args.write:
        suite["metadata"]["version"] = "1.3"
        suite["metadata"]["graded_relevance"]["remap"] = {
            "date": "2026-10-19",
            "script": "scripts/remap_graded_labels.py",
            "reason": "keys re-pointed from the labelling-time chunking to the current chunker and the repaired fixtures",
            "kept": kept, "moved": len(moved), "dropped": len(dropped),
        }
        SUITE.write_text(json.dumps(suite, indent=2), encoding="utf-8")   # the file's own format
        print(f"wrote {SUITE}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
