#!/usr/bin/env python3
"""Plain-text renderings of the judge pack parts (protocol section 8, as amended in
section 16).

    render_pack.py --pack J1      writes judges/pack_J1_part<k>.txt for every part
    render_pack.py --check        re-parses every .txt and compares it with its .json

The judges read their part through a file viewer that truncates lines over 2,000
characters, and a JSON part keeps each tool output on one line of up to ~8,000.
The text rendering holds exactly the same items, with each field's line breaks
written out:

    <<<ITEM J0001>>>
    <<<QUESTION>>>
    ...
    <<<REFERENCE_ANSWER>>>
    ...
    <<<TOOL_OUTPUT>>>
    ...
    <<<END_ITEM J0001>>>

--check parses the markers back and requires the items to equal the JSON part's,
field for field, so the rendering is lossless.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

FIELDS = (("question", "QUESTION"), ("reference_answer", "REFERENCE_ANSWER"), ("tool_output", "TOOL_OUTPUT"))
MARK = "<<<"


def judges_dir() -> Path:
    return C.CONFIG.results_root / "judges"


def render(items: list, title: str) -> str:
    out = [f"{MARK}PACK {title}: {len(items)} items>>>\n"]
    for item in items:
        for name, _ in FIELDS:
            if MARK in item[name]:
                raise SystemExit(f"{item['id']}: {name} contains {MARK!r}; pick another marker")
        out.append(f"{MARK}ITEM {item['id']}>>>\n")
        for name, label in FIELDS:
            out.append(f"{MARK}{label}>>>\n{item[name]}\n")
        out.append(f"{MARK}END_ITEM {item['id']}>>>\n\n")
    return "".join(out)


def parse(text: str) -> list:
    """Inverse of render (without the header line)."""
    items = []
    body = text.split("\n", 1)[1]
    while body:
        if body == "":
            break
        head, body = body.split("\n", 1)
        if not (head.startswith(f"{MARK}ITEM ") and head.endswith(">>>")):
            raise ValueError(f"expected an item marker, got {head[:80]!r}")
        item = {"id": head[len(f"{MARK}ITEM "):-3]}
        for i, (name, label) in enumerate(FIELDS):
            start = f"{MARK}{label}>>>\n"
            if not body.startswith(start):
                raise ValueError(f"{item['id']}: expected {start!r}")
            body = body[len(start):]
            end = (f"\n{MARK}{FIELDS[i + 1][1]}>>>\n" if i + 1 < len(FIELDS)
                   else f"\n{MARK}END_ITEM {item['id']}>>>\n\n")
            cut = body.index(end)
            item[name] = body[:cut]
            body = body[cut + 1:]
        closing = f"{MARK}END_ITEM {item['id']}>>>\n\n"
        if not body.startswith(closing):
            raise ValueError(f"{item['id']}: expected {closing!r}")
        body = body[len(closing):]
        items.append(item)
    return items


def parts_of(pack: str) -> list[Path]:
    return sorted(judges_dir().glob(f"pack_{pack}_part*.json"), key=lambda p: int(p.stem.rsplit("part", 1)[1]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pack", action="append", default=[], help="pack to render (repeatable)")
    ap.add_argument("--check", action="store_true", help="verify every .txt against its .json")
    C.add_hidden_args(ap)
    args = ap.parse_args()
    C.apply_overrides(args)
    for pack in args.pack:
        for p in parts_of(pack):
            items = C.load_json(p)
            out = p.with_suffix(".txt")
            out.write_text(render(items, f"{pack} {p.stem.rsplit('_', 1)[1]}"), encoding="utf-8")
            print(f"{out.name}: {len(items)} items, {out.read_text(encoding='utf-8').count(chr(10))} lines, "
                  f"SHA-256 {C.sha256_file(out)}")
    if args.check:
        bad = 0
        for txt in sorted(judges_dir().glob("pack_*_part*.txt")):
            want = C.load_json(txt.with_suffix(".json"))
            got = parse(txt.read_text(encoding="utf-8"))
            ok = got == [{k: it[k] for k in ("id", "question", "reference_answer", "tool_output")} for it in want]
            bad += not ok
            print(f"{txt.name}: {'identical to' if ok else 'DIFFERS FROM'} {txt.with_suffix('.json').name}")
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
