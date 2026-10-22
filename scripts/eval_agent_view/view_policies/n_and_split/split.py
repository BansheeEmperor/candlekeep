"""Axis "n and split": how many results to show, and dividing the character cap equally among them.

Cost class of every policy here: cheap. They read ranks, scores, offsets (match_offset,
prefix_len), window lengths and titles only: no embeddings, no cross-encoder call, no document
fetch beyond the window.

Mechanics shared by the policies in this file:

  selection   the top n results (n = min(n, len(results))); optionally an adaptive cut that drops
              results whose score falls far below the top score: `rel` for RRF scores (hybrid,
              explore: keep s_i >= rel * s_0) and `gap` for cross-encoder logits (precise: keep
              s_i >= s_0 - gap).
  allocation  max-min fair ("water-filling") equal split of the cap: every shown result gets
              cap / k; a result whose usable text is shorter than its share keeps only what it
              can use, and the remainder is split equally among the others, repeated until stable.
              redistribute=False loses a short window's leftover; "top" gives it to the
              highest-ranked results first.
  anchor      where a result's view starts inside its Arcane Recall window:
                match   at match_offset (B'), never before it.
                back    at match_offset; when the text after the match is shorter than the
                        allocation, the view extends backwards before the match, down to the end
                        of the Bardic prefix (one contiguous range, no gap marker).
                body    at the window start, after the Bardic prefix ("Document: … Description:
                        …"): the window's first chunk, which Arcane Recall placed at most two
                        chunks before the window's first matched chunk. A view that reaches the
                        window end extends backwards like `back` (it cannot, as it starts at lo).
                both    a window that fits is shown whole; a longer one shows its opening (as
                        `body`) and its matched chunk, two pieces with a gap marker, `opening` of
                        the room to the opening (the match piece gives back what the window's end
                        cannot fill). A match inside the opening piece makes it `body`.
                start   at the window start, Bardic prefix included (reference.py's window_start).
              Every anchor but `start` puts B''s title line ("Document: <title>") first, as B'
              does, instead of the ~200-character Bardic prefix.
  tiers       tiered_policy: the top n_full results split the cap equally; the next results, up to
              n_max, get a teaser of at most `teaser` characters (title line included); a second
              water-filling hands what the full results cannot use to whoever can still use it.

Title lines and gap markers count against the cap, as in view_sim.render.
"""
from __future__ import annotations

GAP = "\n[…]\n"


def _title_cost(r) -> int:
    return len(f"Document: {r['title']}\n\n") if r.get("title") else 0


def select(query, results, n, rel=None, gap=None):
    """Top n results, then the adaptive score cut (relative for RRF, absolute logit gap for precise)."""
    res = list(results[:max(0, n)])
    if not res:
        return res
    s0 = res[0]["score"]
    if query.get("path") == "precise":
        if gap is not None:
            res = [r for r in res if r["score"] >= s0 - gap]
    elif rel is not None and s0 > 0:
        res = [r for r in res if r["score"] >= rel * s0]
    return res


def _range(r, anchor: str):
    """(lo, a0, hi): the usable range [lo, hi] of the window and where the view starts (a0)."""
    L, mo, pl = len(r["text"]), r["match_offset"] or 0, r["prefix_len"] or 0
    pl = min(pl, L)
    mo = min(max(mo, pl), L)
    if anchor == "start":
        return 0, 0, L
    if anchor == "match":
        return mo, mo, L
    if anchor == "back":
        return pl, mo, L
    if anchor in ("body", "both"):
        return pl, pl, L
    raise ValueError(anchor)


def _demand(r, anchor: str) -> int:
    """Characters this result can usefully take under the anchor (title line included)."""
    lo, _, hi = _range(r, anchor)
    title = _title_cost(r) if (anchor != "start" and lo > 0) else 0
    return (hi - lo) + title


def waterfill(demands, total, weights=None):
    """Max-min fair split of `total` (optionally weighted): nobody gets more than its demand,
    and whatever a small demand leaves is shared among the rest in proportion to the weights."""
    k = len(demands)
    w = list(weights) if weights else [1.0] * k
    alloc = [0] * k
    open_ = set(range(k))
    left = total
    while open_ and left > 0:
        wsum = sum(w[i] for i in open_)
        share = {i: left * w[i] / wsum for i in open_}
        capped = [i for i in open_ if demands[i] <= share[i]]
        if not capped:
            for i in open_:
                alloc[i] = int(share[i])
            break
        for i in capped:
            alloc[i] = demands[i]
            left -= demands[i]
            open_.discard(i)
    return alloc


def fixed_split(demands, total, weights=None):
    """No redistribution: share i is total * w_i / sum(w), capped at the demand; leftovers are lost."""
    k = len(demands)
    w = list(weights) if weights else [1.0] * k
    return [min(d, int(total * wi / sum(w))) for d, wi in zip(demands, w)]


def topfirst_split(demands, total, weights=None):
    """Equal shares capped at the demand; the leftover pool goes to the results in rank order
    (rank 0 first, up to its demand), instead of being shared equally."""
    alloc = fixed_split(demands, total, weights)
    left = total - sum(alloc)
    for i, d in enumerate(demands):
        if left <= 0:
            break
        extra = min(left, d - alloc[i])
        alloc[i] += extra
        left -= extra
    return alloc


def view(r, budget: int, anchor: str, opening: float = 0.8):
    """One result's display within `budget` characters (title line included)."""
    if budget <= 0:
        return None
    lo, a0, hi = _range(r, anchor)
    if anchor == "start":
        return {"rank": r["rank"], "pieces": [(0, min(hi, budget))], "title": False}
    title = bool(lo > 0 and r.get("title"))
    room = budget - (_title_cost(r) if title else 0)
    if room <= 0:
        return None
    if anchor == "both" and hi - lo > room:
        mo = min(max(r["match_offset"] or 0, lo), hi)
        r2 = room - len(GAP)
        first = int(r2 * opening)
        if mo > lo + first and r2 > 0:
            second = min(hi - mo, r2 - first)
            first = r2 - second        # a short tail after the match gives its room back
            if mo - lo > first:
                return {"rank": r["rank"], "pieces": [(lo, lo + first), (mo, mo + second)], "title": title}
            # the two pieces would touch: one range from the opening
    a, b = a0, min(hi, a0 + room)
    if b - a < room:                   # the text after the anchor is short: extend backwards
        a = max(lo, b - room)
    return {"rank": r["rank"], "pieces": [(a, b)], "title": title}


def split_policy(query, results, cap, n=5, anchor="body", rel=None, gap=None, weights=None,
                 redistribute=True, opening=0.8):
    """Top n (after the optional score cut), the cap split equally (or by `weights`)."""
    shown = select(query, results, n, rel, gap)
    if not shown:
        return []
    w = weights(len(shown)) if callable(weights) else weights
    demands = [_demand(r, anchor) for r in shown]
    split = {True: waterfill, False: fixed_split, "top": topfirst_split}[redistribute]
    alloc = split(demands, cap, w)
    out = []
    for r, a in zip(shown, alloc):
        d = view(r, a, anchor, opening)
        if d:
            out.append(d)
    return out


def tiered_policy(query, results, cap, n_full=1, n_max=5, teaser=250, anchor="body",
                  teaser_anchor="body", rel=None, gap=None, same_doc="teaser", full_gap=None,
                  lead_from=1, opening=0.8):
    """The top n_full results split the cap equally (water-filling); results n_full..n_max-1 get a
    teaser of at most `teaser` characters (title line included) so that they stay visible. What
    the full results cannot use is then shared among all shown results (second water-filling).

    Explored options (all worse on dev; kept so the findings can be reproduced):
    same_doc="skip" drops the teaser of a result whose document is already shown in full.
    full_gap (precise only): every result within `full_gap` logits of the top is shown in full.
    lead_from: the lead (n_full=1) is the longest window among the top `lead_from` results."""
    sel = select(query, results, n_max, rel, gap)
    if not sel:
        return []
    if lead_from > 1 and n_full == 1:
        lead = max(sel[:lead_from], key=lambda r: (len(r["text"]) - (r["prefix_len"] or 0), -r["rank"]))
        sel = [lead] + [r for r in sel if r is not lead]
    k_full = min(n_full, len(sel))
    if full_gap is not None and query.get("path") == "precise":
        s0 = sel[0]["score"]
        k_full = max(k_full, sum(1 for r in sel if r["score"] >= s0 - full_gap))
    if same_doc == "skip":
        full_src = {r["source"] for r in sel[:k_full]}
        sel = sel[:k_full] + [r for r in sel[k_full:] if r["source"] not in full_src]
    anchors = [anchor] * k_full + [teaser_anchor] * (len(sel) - k_full)
    full_d = [_demand(r, a) for r, a in zip(sel, anchors)]
    first_d = [d if i < k_full else min(d, teaser) for i, d in enumerate(full_d)]
    # pass 1: teasers are small demands, so water-filling satisfies them first and splits the
    # rest equally among the full results.
    alloc = waterfill(first_d, cap)
    left = cap - sum(alloc)
    if left > 0:                       # pass 2: leftovers to whoever can still use them
        extra = waterfill([d - a for d, a in zip(full_d, alloc)], left)
        alloc = [a + e for a, e in zip(alloc, extra)]
    out = []
    for r, a, an in zip(sel, alloc, anchors):
        d = view(r, a, an, opening)
        if d:
            out.append(d)
    return out


# ── reported policies ────────────────────────────────────────────────────────────

def eq5_body(query, results, cap):
    """Top 5 results, the cap split equally (water-filling), each view from its window's first
    chunk (after the Bardic prefix, title line first). Cheap."""
    return split_policy(query, results, cap, n=5, anchor="body")


def path_n_body(query, results, cap):
    """Adaptive n, equal split: precise keeps the results within 3 logits of the top
    cross-encoder score (at most 5); hybrid and explore show the top 5 (RRF ratios are rank-based,
    no cut). Cap split equally (water-filling), body anchor. Cheap."""
    return split_policy(query, results, cap, n=5, anchor="body", gap=3.0)


def lead_teasers(query, results, cap):
    """n = 1 in full plus teasers: the top result gets the cap minus the teasers; results 2-5
    get 250 characters each (title line included), all views from the window's first chunk;
    leftovers water-filled. Cheap."""
    return tiered_policy(query, results, cap, n_full=1, n_max=5, teaser=250,
                         anchor="body", teaser_anchor="body")


def lead_teasers_both(query, results, cap):
    """lead_teasers, but a lead window too long to show whole shows its opening (80% of the
    room) and its matched chunk (20%), so the best-matching chunk is always in view. Cheap."""
    return tiered_policy(query, results, cap, n_full=1, n_max=5, teaser=250,
                         anchor="both", teaser_anchor="body", opening=0.8)


def lead_teasers10(query, results, cap):
    """lead_teasers with up to 10 results (every result of a 10-result search gets a teaser);
    identical to lead_teasers when 5 or fewer results come back. Cheap."""
    return tiered_policy(query, results, cap, n_full=1, n_max=10, teaser=250,
                         anchor="body", teaser_anchor="body")


def bprime_capped(query, results, cap):
    """Reference: B' (1,000 characters per result from the match, title line first), but results
    that would push the output past the cap are cut here instead of by the simulator, so that a
    result whose text never reaches the agent does not count as shown (srcvis)."""
    out, left = [], cap
    for r in results:
        if left <= 0:
            break
        off = r["match_offset"] or 0
        title = bool(off and r["title"])
        tc = _title_cost(r) if title else 0
        room = min(1000, left) - tc
        if room <= 0:
            break
        b = min(len(r["text"]), off + room)
        out.append({"rank": r["rank"], "pieces": [(off, b)], "title": title})
        left -= tc + (b - off)
    return out


# ── the n × anchor grid, for view_sim.py eval FILE.py:FUNC (e.g. n5_match = B''s anchor and
#    title rule with the cap split equally over the top 5) ─────────────────────────────────

def _mk(n, anchor, redistribute=True):
    def p(query, results, cap):
        return split_policy(query, results, cap, n=n, anchor=anchor, redistribute=redistribute)
    p.__doc__ = f"top {n}, equal split (redistribute={redistribute}), anchor={anchor}. Cheap."
    return p


for _n in (1, 2, 3, 4, 5, 6, 8, 10):
    for _a in ("match", "back", "body", "both", "start"):
        globals()[f"n{_n}_{_a}"] = _mk(_n, _a)
        globals()[f"n{_n}_{_a}_noredist"] = _mk(_n, _a, redistribute=False)
