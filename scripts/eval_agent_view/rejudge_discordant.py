#!/usr/bin/env python3
"""Informational re-judging of C-11's discordant queries (protocol section 16).

    rejudge_discordant.py build      writes judges/pack_J1D_part{1,2}.json (+ .txt), keymap_J1D.json (+ .sha256)
    rejudge_discordant.py analyse    after judges/out_J1D_part<k>_<judge>.json exist: majority verdicts and C-11 sensitivity

Discordant queries are the CEN-A queries whose J1 verdicts differ between B and C on
"full" (B full and C not, or the reverse). Their B and C items are re-issued under new
ids D#### in two parts, so that no part holds both states of one query:
part 1 = B items of the first half of the queries (sorted by qid) + C items of the
second half, part 2 = the complement. Each part is judged by two new judges. The
J1 verdict and the two new verdicts give each item three verdicts; an item counts
as full when at least two of the three say full. Nothing here replaces the
pre-registered C-11 verdicts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from math import comb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
import render_pack  # noqa: E402

SEED = C.SEED


def jdir() -> Path:
    return C.CONFIG.results_root / "judges"


def j1_items() -> tuple[dict, dict, dict]:
    d = jdir()
    pack = {i["id"]: i for i in C.load_json(d / "pack_J1.json")}
    keymap = C.load_json(d / "keymap_J1.json")
    verdict = {}
    for f in sorted(d.glob("out_J1_part*.json")):
        for e in C.load_json(f):
            verdict[e["id"]] = str(e["verdict"]).strip().lower()
    return pack, keymap, verdict


def discordant() -> tuple[list, dict]:
    pack, keymap, verdict = j1_items()
    by_q: dict = {}
    for jid, key in keymap.items():
        qid, state = key.split("|")
        by_q.setdefault(qid, {})[state] = jid
    out = []
    for qid in sorted(by_q):
        b, c = by_q[qid].get("B"), by_q[qid].get("C")
        if b and c and (verdict[b] == "full") != (verdict[c] == "full"):
            out.append(qid)
    return out, by_q


def build() -> None:
    pack, _, _ = j1_items()
    qids, by_q = discordant()
    half = (len(qids) + 1) // 2
    first, second = qids[:half], qids[half:]
    parts = [[by_q[q]["B"] for q in first] + [by_q[q]["C"] for q in second],
             [by_q[q]["C"] for q in first] + [by_q[q]["B"] for q in second]]
    rng = random.Random(SEED)
    keymap, n = {}, 0
    for k, ids in enumerate(parts, 1):
        rng.shuffle(ids)
        items = []
        for jid in ids:
            n += 1
            did = f"D{n:04d}"
            keymap[did] = jid
            items.append({**pack[jid], "id": did})
        C.write_json_atomic(jdir() / f"pack_J1D_part{k}.json", items)
        out = jdir() / f"pack_J1D_part{k}.txt"
        out.write_text(render_pack.render(items, f"J1D part{k}"), encoding="utf-8")
        assert render_pack.parse(out.read_text(encoding="utf-8")) == items
    kp = jdir() / "keymap_J1D.json"
    C.write_json_atomic(kp, dict(sorted(keymap.items())))
    digest = hashlib.sha256(kp.read_bytes()).hexdigest()
    (jdir() / "keymap_J1D.json.sha256").write_text(f"{digest}  keymap_J1D.json\n", encoding="utf-8")
    print(f"J1D: {len(qids)} discordant queries {qids}; parts {[len(p) for p in parts]}; keymap SHA-256 {digest}")


def mcnemar(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def analyse() -> None:
    _, keymap1, verdict1 = j1_items()
    keyd = C.load_json(jdir() / "keymap_J1D.json")
    new: dict = {}
    files = sorted(jdir().glob("out_J1D_part*_*.json"))
    for f in files:
        for e in C.load_json(f):
            new.setdefault(keyd[e["id"]], []).append(str(e["verdict"]).strip().lower())
    qids, by_q = discordant()
    rows, b, c = [], 0, 0
    for q in qids:
        cell = {}
        for st in ("B", "C"):
            jid = by_q[q][st]
            votes = [verdict1[jid]] + new.get(jid, [])
            cell[st] = {"votes": votes, "full": sum(v == "full" for v in votes) >= 2}
        b += cell["B"]["full"] and not cell["C"]["full"]
        c += cell["C"]["full"] and not cell["B"]["full"]
        rows.append({"qid": q, **cell})
    p = mcnemar(b, c)
    summary = C.load_json(C.CONFIG.results_root / "summary.json")
    p08 = summary["criteria"]["C-08"]["mcnemar"]["p"]
    p09 = summary["criteria"]["C-09"]["mcnemar"]["p"]
    ps = sorted([("C-08", p08), ("C-09", p09), ("C-11", p)], key=lambda x: x[1])
    holm, running = {}, 0.0
    for i, (name, pv) in enumerate(ps):
        running = max(running, min(1.0, (len(ps) - i) * pv))
        holm[name] = running
    res = {"discordant_queries": qids, "judge_files": [f.name for f in files], "rows": rows,
           "majority_b": b, "majority_c": c, "mcnemar_p": p, "holm_p_C11": holm["C-11"],
           "note": "informational (section 16); C-11's registered verdicts are unchanged"}
    C.write_json_atomic(jdir() / "results_J1D.json", res)
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=1))
    for r in rows:
        print(r["qid"], "B", r["B"]["votes"], "C", r["C"]["votes"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["build", "analyse"])
    args = ap.parse_args()
    build() if args.cmd == "build" else analyse()
    return 0


if __name__ == "__main__":
    sys.exit(main())
