"""Rank-weighted display policies for view_sim.py: how to split the character cap across ranked results.

Axis: allocation across ranks. Placement inside each window is kept deliberately simple so the
effect of the allocation shows: one contiguous piece per result, starting `lead` characters
before the match point (lead 0 = B′'s start), shifted back when the window ends before the
piece is full. Every shown result gets a title line (as B′ does when its view starts mid-window);
title lines count against the cap.

Allocation schemes (weights over the first `n` results, then water-filling):

  equal          w = 1
  geometric      w = ratio ** rank
  linear         w = n - rank
  zipf           w = 1 / (rank + 1) ** alpha
  fixed          w = a fixed split (default 3000/1500/1000/500/500), scaled to the cap
  softmax        w = exp((score - top score) / T); T is per score scale (RRF or cross-encoder logit)
  waterfall      rank 1 gets up to `ceiling` characters (or its whole window), then rank 2, ...

`floor` gives every shown result a minimum before the weighted split. With `redistribute`, a
result whose window is shorter than its share passes the rest on to the others (water-filling);
without it the rest is unused. A result whose body share falls below `min_body` is dropped and
the cap is re-split over fewer results.

Probes (measured, not recommended unless named below): `by_doc` (weight by the document's rank
among distinct sources), `len_pow` (favour long windows), `backfill=False` (B′'s no-shift-back
ablation) and `head_ranks` (an interaction probe with a placement outside this axis: the top
result's share split between its window's first characters and the match piece).

The named policies at the bottom are the ones reported; each is `view_sim.py eval
rank_alloc.py:<name>`. Dev-split results and the reasoning are in the axis report.

Cost class: ranks, the query path, window lengths, match offsets, titles and (softmax only)
scores: all "cheap". Standard library only, deterministic, and it reads nothing but its arguments.
"""
from __future__ import annotations

import math

RRF_PATHS = ("hybrid", "explore")      # precise scores are cross-encoder logits


def title_cost(r: dict) -> int:
    """Characters of the title line view_sim.render adds for this result."""
    return len(f"Document: {r['title'] or r['source']}\n\n")


def body_len(r: dict) -> int:
    return max(0, len(r["text"]) - (r["prefix_len"] or 0))


# ── allocation ───────────────────────────────────────────────────────

def waterfill(weights: list[float], caps: list[float], total: float) -> list[float]:
    """Split `total` in proportion to `weights`, no item above its cap; what a capped item cannot
    use goes to the others in proportion to their weights."""
    n = len(weights)
    alloc = [0.0] * n
    active = [i for i in range(n) if weights[i] > 0 and caps[i] > 0]
    rem = float(total)
    while active and rem > 1e-9:
        w_sum = sum(weights[i] for i in active)
        full = [i for i in active if caps[i] - alloc[i] <= rem * weights[i] / w_sum]
        if not full:
            for i in active:
                alloc[i] += rem * weights[i] / w_sum
            break
        for i in full:
            rem -= caps[i] - alloc[i]
            alloc[i] = caps[i]
        active = [i for i in active if i not in full]
    return alloc


def split(weights, needs, total, floor=0, redistribute=True, ceiling=None, waterfall=False):
    """Body characters per result. `needs` = the most each result can use (its window body)."""
    n = len(weights)
    caps = [min(nd, ceiling) if ceiling else nd for nd in needs]
    base = [min(floor, c) for c in caps]
    if sum(base) > total:                       # floors alone do not fit: equal split of what there is
        base = waterfill([1.0] * n, caps, total)
        return [int(x) for x in base]
    rest = total - sum(base)
    room = [c - b for c, b in zip(caps, base)]
    if waterfall:
        extra = []
        for rm in room:
            give = min(rm, rest)
            extra.append(give)
            rest -= give
    elif redistribute:
        extra = waterfill(weights, room, rest)
    else:
        w_sum = sum(weights) or 1.0
        extra = [min(rm, rest * w / w_sum) for rm, w in zip(room, weights)]
    return [int(b + e) for b, e in zip(base, extra)]


def doc_ranks(results: list[dict]) -> list[int]:
    """Rank of each result's document among the distinct sources, in order of first appearance."""
    seen: dict[str, int] = {}
    return [seen.setdefault(r["source"], len(seen)) for r in results]


def weights_for(scheme: str, results: list[dict], path: str, ratio=0.6, alpha=1.0, temp=None,
                fixed=(3000, 1500, 1000, 500, 500), by_doc=False) -> list[float]:
    """Weights per result. With `by_doc`, a result is weighted by its document's rank among the
    distinct sources, so a lower-ranked window of the top document weighs like the top result."""
    n = len(results)
    ks = doc_ranks(results) if by_doc else list(range(n))
    if scheme == "equal" or scheme == "waterfall":
        return [1.0] * n
    if scheme == "geometric":
        return [ratio ** k for k in ks]
    if scheme == "linear":
        return [float(n - k) for k in ks]
    if scheme == "zipf":
        return [1.0 / (k + 1) ** alpha for k in ks]
    if scheme == "fixed":
        f = list(fixed) + [fixed[-1]] * max(0, n - len(fixed))
        return [float(f[k]) for k in ks]
    if scheme == "softmax":
        t = temp[path in RRF_PATHS and "rrf" or "ce"] if isinstance(temp, dict) else temp
        top = max(r["score"] for r in results)
        return [math.exp((r["score"] - top) / t) for r in results]
    if scheme == "scoreprop":                    # RRF: share of the score; logits: sigmoid (relevance probability)
        if path in RRF_PATHS:
            return [max(r["score"], 0.0) for r in results]
        return [1.0 / (1.0 + math.exp(-r["score"])) for r in results]
    raise ValueError(scheme)


# ── placement ────────────────────────────────────────────────────────

def place(r: dict, b: int, lead=0, lead_frac=None) -> tuple[int, int]:
    """One piece of `b` body characters: from `lead` before the match point (lead_frac: that share
    of b, capped by lead when both are given), shifted back when the window ends first."""
    p, n_txt = r["prefix_len"] or 0, len(r["text"])
    if b >= n_txt - p:
        return (p, n_txt)
    m = min(max(r["match_offset"] or p, p), n_txt)
    ld = lead
    if lead_frac is not None:
        ld = int(lead_frac * b) if not lead else min(lead, int(lead_frac * b))
    start = max(p, m - ld)
    end = start + b
    if end > n_txt:
        end = n_txt
        start = max(p, n_txt - b)
    return (start, end)


GAP_LEN = len("\n[…]\n")


def place_with_head(r: dict, b: int, head: int, lead=0, lead_frac=None) -> list[tuple[int, int]]:
    """Interaction probe (not this axis's placement): the first `head` body characters, a gap
    marker, then the rest of the share placed as `place` does. Falls back to one piece when the
    head would touch the match piece or the share is too small."""
    p, n_txt = r["prefix_len"] or 0, len(r["text"])
    if head <= 0 or b - head - GAP_LEN < 200 or b >= n_txt - p:
        return [place(r, b, lead=lead, lead_frac=lead_frac)]
    s, e = place(r, b - head - GAP_LEN, lead=lead, lead_frac=lead_frac)
    if s <= p + head:                                   # the match piece reaches into the head: one piece from the start
        return [(p, min(n_txt, p + b))]
    return [(p, p + head), (s, e)]


# ── policy factory ───────────────────────────────────────────────────

def make(scheme="equal", n=None, floor=0, redistribute=True, ceiling=None, min_body=150, lead=0,
         lead_frac=None, ratio=0.6, alpha=1.0, temp=None, fixed=(3000, 1500, 1000, 500, 500), n_by_path=None,
         by_doc=False, head_ranks=0, head_frac=0.3, head_max=1200, len_pow=0.0, backfill=True):
    """A display policy: weights by `scheme` over the first `n` results (all when None), split of the
    cap minus title lines, results under `min_body` dropped (and the cap re-split).

    backfill=False (ablation): a piece never moves back before its start point, so a result can use
    only the text from `lead` before its match to the window end (B′'s behaviour)."""
    if not backfill and (lead_frac is not None or head_ranks):
        raise ValueError("backfill=False supports a fixed lead only")

    def start_of(r):
        p = r["prefix_len"] or 0
        return max(p, min(max(r["match_offset"] or p, p), len(r["text"])) - lead)

    def policy(query, results, cap):
        nn = (n_by_path or {}).get(query["path"], n)
        rs = list(results[:nn] if nn else results)
        while rs:
            titles = [title_cost(r) for r in rs]
            total = cap - sum(titles)
            if total <= 0:
                rs = rs[:-1]
                continue
            w = weights_for(scheme, rs, query["path"], ratio=ratio, alpha=alpha, temp=temp, fixed=fixed,
                            by_doc=by_doc)
            if len_pow:                                  # probe: favour long windows (more matched neighbours)
                w = [wi * max(1, body_len(r)) ** len_pow for wi, r in zip(w, rs)]
            needs = [body_len(r) if backfill else len(r["text"]) - start_of(r) for r in rs]
            alloc = split(w, needs, total, floor=floor, redistribute=redistribute, ceiling=ceiling,
                          waterfall=(scheme == "waterfall"))
            small = [i for i, a in enumerate(alloc) if a < min(min_body, needs[i])]
            if small and len(rs) > 1:
                rs = [r for i, r in enumerate(rs) if i != max(small)]   # drop the lowest-ranked small one
                continue
            out = []
            for i, (r, a) in enumerate(zip(rs, alloc)):
                if a <= 0:
                    continue
                if not backfill:
                    s0 = start_of(r)
                    pieces = [(s0, min(len(r["text"]), s0 + a))]
                elif i < head_ranks:
                    pieces = place_with_head(r, a, min(head_max, int(head_frac * a)), lead=lead, lead_frac=lead_frac)
                else:
                    pieces = [place(r, a, lead=lead, lead_frac=lead_frac)]
                out.append({"rank": r["rank"], "pieces": pieces, "title": True})
            return out
        return []
    return policy


# ── named policies (reported) ────────────────────────────────────────
# All cheap: they use ranks, the query path, window lengths, match offsets and titles only.

_equal5 = make("equal", n=5)
_bprime_scaled = make("equal", backfill=False, redistribute=False)
_zipf2_floor300 = make("zipf", alpha=2.0, floor=300, n=5)
_zipf2_floor300_lead = make("zipf", alpha=2.0, floor=300, n=5, lead_frac=0.5)
_waterfall_floor500 = make("waterfall", floor=500, n=5)
_waterfall_floor300_lead = make("waterfall", floor=300, n=5, lead_frac=0.5)
_HEAD = dict(head_ranks=1, head_frac=0.4, head_max=1500)
_zipf2_floor300_lead_head = make("zipf", alpha=2.0, floor=300, n=5, lead_frac=0.5, **_HEAD)
_waterfall_floor300_lead_head = make("waterfall", floor=300, n=5, lead_frac=0.5, **_HEAD)


def equal5(query, results, cap):
    """Baseline: the cap (minus title lines) split equally over the top 5 results; a window shorter
    than its share passes the rest on; each piece starts at the match point (shifted back when the
    window ends first)."""
    return _equal5(query, results, cap)


def bprime_scaled(query, results, cap):
    """Weak baseline: B′'s rule with its 1,000 scaled to cap / n results (title included), from the
    match point, no redistribution and no shifting back."""
    return _bprime_scaled(query, results, cap)


def zipf2_floor300(query, results, cap):
    """Top 5 results; 300 characters each, the rest of the cap split 1 : 1/4 : 1/9 : 1/16 : 1/25 by
    rank (water-filled); each piece starts at the match point."""
    return _zipf2_floor300(query, results, cap)


def zipf2_floor300_lead(query, results, cap):
    """zipf2_floor300 with each piece starting half its length before the match point."""
    return _zipf2_floor300_lead(query, results, cap)


def waterfall_floor500(query, results, cap):
    """Top 5 results; 500 characters each, the rest to rank 1 up to its whole window, then rank 2, ..."""
    return _waterfall_floor500(query, results, cap)


def pathaware(query, results, cap):
    """hybrid and explore: zipf2_floor300_lead. precise (cross-encoder reranked, where the top result
    holds nearly all the answer): 300 characters per result and the rest to the top result first
    (waterfall), pieces starting half their length before the match point."""
    pol = _waterfall_floor300_lead if query["path"] == "precise" else _zipf2_floor300_lead
    return pol(query, results, cap)


def pathaware_head(query, results, cap):
    """Interaction probe with a placement outside this axis: pathaware, plus the top result's share
    split into its window's first 40% (at most 1,500 characters) and the match piece."""
    pol = _waterfall_floor300_lead_head if query["path"] == "precise" else _zipf2_floor300_lead_head
    return pol(query, results, cap)
