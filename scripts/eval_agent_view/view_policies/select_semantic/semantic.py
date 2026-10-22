"""Semantic selection inside results (axis: select_semantic), for view_sim.py.

A display policy decides which characters of each result's Arcane Recall window the agent
sees, within `cap` displayed characters per search. This module chooses WHAT to show inside
each result from per-segment semantic features:

    emb  cosine(segment, query) with the server's embedder (bge-small): needs segment
         embeddings, computed at ingest (one vector per segment) or at query time (moderate)
    ce   cross-encoder logit of (query, segment): one cross-encoder call per segment at
         query time (expensive, about 1 ms per segment on MPS)
    lex  share of the query's content words in the segment (cheap)

plus offsets, lengths and ranks (cheap). Policies use only their arguments.

Cost accounting matches view_sim.render: displayed text = optional title line
"Document: <title>\\n\\n" + pieces + a gap marker "\\n[…]\\n" between non-touching pieces.
Selected segments whose separation is whitespace only (or at most `bridge` characters) are
joined by showing the text between them instead of a marker. A title line is added when the
first shown piece starts after 0 (the Bardic prefix, which carries the title, is not shown).

Policies (bottom of the file; dev CEN facts_share hybrid / precise / explore at cap 4000):
    ce_doc_thr          [ce]        documents by best segment logit; a cut window shows its
                                    segments within 2 logits of its best, then its head   .699/.708/.480
    ce_emb_skim         [ce + emb]  ce_doc_thr + openings of the sections whose heading is
                                    closest to the query                                   .715/.730/.489
    emb_doc_lexthr      [emb + lex] documents by best segment cosine; best-lex segments    .683/.688/.480
    descemb_doc_lexthr  [1 emb/doc] documents by description cosine; best-lex segments     .683/.688/.480
    cheap_doc_lexthr    [cheap]     documents by best rank; best-lex segments              .654/.688/.480
    cheap_doc_head      [cheap]     documents by best rank; each window from its start     .620/.658/.467
Negative results kept for the record: ce_greedy_trim, emb_greedy_trim, ce_global_greedy.
"""
from __future__ import annotations

import math
import re

GAP_LEN = len("\n[…]\n")


# ── per-result selection state ───────────────────────────────────────

class ResSel:
    """Segments chosen in one result's window, with exact incremental cost."""

    def __init__(self, r, bridge=0, use_title=True, drop_prefix=False):
        self.r = r
        self.text = r["text"]
        self.segs = [s for s in r["segments"] if s["end"] > s["start"] and not (drop_prefix and s["kind"] == "prefix")]
        self.n = len(self.segs)
        self.sel = [False] * self.n
        self.tcost = len(f"Document: {r['title'] or r['source']}\n\n") if use_title else 0
        self.bridge = bridge
        self.cost = 0
        self.count = 0
        self.tail = None            # optional partial extension (start, end) of the first run

    # geometry
    def _bridged(self, a, b):
        sa, sb = self.segs[a], self.segs[b]
        dist = sb["start"] - sa["end"]
        return dist <= max(self.bridge, GAP_LEN) or not self.text[sa["end"]:sb["start"]].strip()

    def _conn(self, a, b):
        return self.segs[b]["start"] - self.segs[a]["end"] if self._bridged(a, b) else GAP_LEN

    def _left(self, i):
        for j in range(i - 1, -1, -1):
            if self.sel[j]:
                return j
        return None

    def _right(self, i):
        for j in range(i + 1, self.n):
            if self.sel[j]:
                return j
        return None

    def marginal(self, i):
        if self.sel[i]:
            return 0
        s = self.segs[i]
        ln = s["end"] - s["start"]
        L, R = self._left(i), self._right(i)
        if L is None and R is None:
            return ln + (self.tcost if s["start"] > 0 else 0)
        if L is not None and R is not None:
            return ln + self._conn(L, i) + self._conn(i, R) - self._conn(L, R)
        if L is not None:
            return ln + self._conn(L, i)
        return ln + self._conn(i, R) - (self.tcost if s["start"] == 0 else 0)

    def add(self, i):
        c = self.marginal(i)
        self.sel[i] = True
        self.cost += c
        self.count += 1
        return c

    def adjacent_selected(self, i):
        return (i > 0 and self.sel[i - 1]) or (i + 1 < self.n and self.sel[i + 1])

    def pieces(self):
        out, prev = [], None
        for i in range(self.n):
            if not self.sel[i]:
                continue
            s = self.segs[i]
            if prev is not None and self._bridged(prev, i):
                out[-1][1] = s["end"]
            else:
                out.append([s["start"], s["end"]])
            prev = i
        if self.tail:
            a, b = self.tail
            for p in out:
                if p[1] == a:
                    p[1] = b
                    break
        return [tuple(p) for p in out]

    def display(self):
        p = self.pieces()
        if not p:
            return None
        return {"rank": self.r["rank"], "pieces": p, "title": bool(self.tcost) and p[0][0] > 0}

    def extend_tail(self, room):
        """Use up to `room` characters to continue the first run (the head, for head-based
        selectors) past its end, cut at a space; the text it adds is never selected elsewhere."""
        if room < 40 or not self.count or self.tail:
            return 0
        first = min(i for i in range(self.n) if self.sel[i])
        last = first
        while last + 1 < self.n and self.sel[last + 1] and self._bridged(last, last + 1):
            last += 1
        a = self.segs[last]["end"]
        nxt = last + 1
        while nxt < self.n and not self.sel[nxt]:
            nxt += 1
        limit = self.segs[nxt]["start"] if nxt < self.n else len(self.text)
        if a >= limit:
            return 0
        b = min(limit - GAP_LEN, a + room) if nxt < self.n else min(limit, a + room)
        if b < limit:
            sp = self.text.rfind(" ", a, b)
            if sp > a + 20:
                b = sp
        if b - a < 20:
            return 0
        self.tail = (a, b)
        self.cost += b - a
        return b - a


def display_cost(r, d):
    """Displayed characters of a display dict (as view_sim.render counts them)."""
    if not d:
        return 0
    t = len(f"Document: {r['title'] or r['source']}\n\n") if d.get("title") else 0
    ps = sorted(d["pieces"])
    m = []
    for a, b in ps:
        if m and m[-1][0] <= a <= m[-1][1]:
            m[-1][1] = max(m[-1][1], b)
        else:
            m.append([a, b])
    return t + sum(b - a for a, b in m) + GAP_LEN * (len(m) - 1)


# ── scores ───────────────────────────────────────────────────────────

def _z(vals):
    if not vals:
        return lambda x: 0.0
    mu = sum(vals) / len(vals)
    sd = math.sqrt(sum((v - mu) ** 2 for v in vals) / len(vals)) or 1.0
    return lambda x: (x - mu) / sd


def make_scorer(results, w_emb=0.0, w_ce=0.0, w_lex=0.0, z=True):
    """score(seg) = w_emb·z(emb) + w_ce·z(ce) + w_lex·z(lex); z over the search's non-prefix segments."""
    segs = [s for r in results for s in r["segments"] if s["kind"] != "prefix"] or \
           [s for r in results for s in r["segments"]]
    if z:
        ze = _z([s["emb"] for s in segs]) if w_emb else (lambda x: 0.0)
        zc = _z([s["ce"] for s in segs]) if w_ce else (lambda x: 0.0)
        zl = _z([s["lex"] for s in segs]) if w_lex else (lambda x: 0.0)
    else:
        ze = zc = zl = (lambda x: x)
    return lambda s: w_emb * ze(s["emb"]) + w_ce * zc(s["ce"]) + w_lex * zl(s["lex"])


# ── within-result selectors (fill one ResSel up to `budget`) ─────────

def sel_head(rs, budget, score=None):
    """The window from its start, segment by segment (no semantics): fill_full's behaviour."""
    for i in range(rs.n):
        c = rs.marginal(i)
        if rs.cost + c > budget:
            break
        rs.add(i)
    return rs


def sel_greedy(rs, budget, score, density=False, adj_bonus=0.0, mmr=0.0, words=None, skip_kinds=()):
    """Greedy by score (or score per character), with an optional bonus for segments next to
    the selection (contiguity) and an MMR-style penalty for lexical redundancy (Jaccard)."""
    base = [score(s) for s in rs.segs]
    cand = [i for i in range(rs.n) if rs.segs[i]["kind"] not in skip_kinds]
    if not (adj_bonus or mmr):
        if density:
            lo = min(base) if base else 0.0
            key = lambda i: (base[i] - lo + 1e-3) / max(20, rs.segs[i]["end"] - rs.segs[i]["start"])  # noqa: E731
        else:
            key = lambda i: base[i]  # noqa: E731
        for i in sorted(cand, key=lambda i: (-key(i), i)):
            c = rs.marginal(i)
            if rs.cost + c <= budget:
                rs.add(i)
        return rs
    # dynamic priorities
    ws = words or [None] * rs.n
    chosen = []
    left = set(cand)
    while left:
        best, bv = None, -1e18
        for i in left:
            v = base[i]
            if adj_bonus and rs.adjacent_selected(i):
                v += adj_bonus
            if mmr and chosen and ws[i]:
                sim = max(_jacc(ws[i], ws[j]) for j in chosen)
                v -= mmr * sim
            if v > bv:
                best, bv = i, v
        left.discard(best)
        c = rs.marginal(best)
        if rs.cost + c <= budget:
            rs.add(best)
            chosen.append(best)
    return rs


def sel_threshold(rs, budget, score, delta, fill="greedy"):
    """Segments scoring within `delta` of the result's best; fill the rest greedily if asked."""
    base = [score(s) for s in rs.segs]
    if not base:
        return rs
    top = max(base)
    for i in sorted(range(rs.n), key=lambda i: (-base[i], i)):
        if base[i] < top - delta:
            break
        c = rs.marginal(i)
        if rs.cost + c <= budget:
            rs.add(i)
    if fill == "greedy":
        sel_greedy(rs, budget, score)
    return rs


def sel_core_sat(rs, budget, score, core_share=0.6):
    """Contiguous core grown from the best segment toward the better-scoring neighbour, up to
    core_share of the budget; then the next best segments elsewhere (satellites)."""
    base = [score(s) for s in rs.segs]
    if not base:
        return rs
    b = max(range(rs.n), key=lambda i: (base[i], -i))
    core_budget = budget * core_share
    if rs.cost + rs.marginal(b) > budget:
        return rs
    rs.add(b)
    lo = hi = b
    while True:
        opts = []
        if lo > 0:
            opts.append((base[lo - 1], lo - 1))
        if hi + 1 < rs.n:
            opts.append((base[hi + 1], hi + 1))
        if not opts:
            break
        opts.sort(reverse=True)
        grown = False
        for _, i in opts:
            c = rs.marginal(i)
            if rs.cost + c <= core_budget:
                rs.add(i)
                lo, hi = min(lo, i), max(hi, i)
                grown = True
                break
        if not grown:
            break
    return sel_greedy(rs, budget, score)


def sel_head_sat(rs, budget, score, head_share=0.5, adj_bonus=1.0):
    """Core = the window head (its start, where documents state what they are about), up to
    head_share of the budget; satellites = greedy by score (with a contiguity bonus) after it."""
    sel_head(rs, budget * head_share)
    return sel_greedy(rs, budget, score, adj_bonus=adj_bonus)


def sel_head_mo(rs, budget, head_share=0.5):
    """Cheap: the window head up to head_share, then contiguous from the matched chunk."""
    sel_head(rs, budget * head_share)
    mo = rs.r["match_offset"] or 0
    for i in range(rs.n):
        if rs.segs[i]["end"] <= mo or rs.sel[i]:
            continue
        c = rs.marginal(i)
        if rs.cost + c > budget:
            break
        rs.add(i)
    return sel_head(rs, budget)


def sel_rel_threshold(rs, budget, score, delta, then="head"):
    """Segments within `delta` of the result's best score (best first), then the window head."""
    sel_threshold(rs, budget, score, delta, fill=None)
    return sel_head(rs, budget) if then == "head" else rs


_WORD = re.compile(r"[a-z0-9]{3,}")


def seg_words(rs):
    return [set(_WORD.findall(rs.text[s["start"]:s["end"]].lower())) for s in rs.segs]


def _jacc(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def sel_maxsum(rs, budget, score, tau):
    """The contiguous run of segments maximising sum(score - tau) within the budget."""
    base = [score(s) - tau for s in rs.segs]
    best, bv = None, -1e18
    for i in range(rs.n):
        tot, start = 0.0, rs.segs[i]["start"]
        t = rs.tcost if start > 0 else 0
        for j in range(i, rs.n):
            if rs.segs[j]["end"] - start + t > budget:
                break
            tot += base[j]
            if tot > bv:
                best, bv = (i, j), tot
    if best:
        for k in range(best[0], best[1] + 1):
            rs.add(k)
    return rs


# ── allocation across results ────────────────────────────────────────

def full_cost(r, bridge=0, **kw):
    rs = ResSel(r, bridge, **kw)
    for i in range(rs.n):
        rs.add(i)
    return rs.cost


def alloc_fill(results, cap, selector, per_cap=None, min_room=150, bridge=0, tail=True, order=None):
    """Results in `order` (default rank order). Each gets min(left, per_cap[k]); a window that
    fits is shown whole, a longer one is cut down by `selector`. With per_cap, a second pass
    gives the leftover to the cut results in the same order. A last pass continues the last
    run of each cut result with whatever is left (partial segment)."""
    order = list(range(len(results))) if order is None else order
    left = cap
    shown = {}
    for k, idx in enumerate(order):
        if left < min_room:
            break
        r = results[idx]
        room = left if per_cap is None else min(left, per_cap[min(k, len(per_cap) - 1)])
        rs = ResSel(r, bridge)
        if full_cost(r, bridge) <= room:
            for i in range(rs.n):
                rs.add(i)
        else:
            selector(rs, room)
        if rs.count:
            shown[idx] = rs
            left -= rs.cost
    if per_cap is not None:
        for idx in order:
            rs = shown.get(idx)
            if left < min_room:
                break
            if rs is None or rs.count == rs.n:
                continue
            before = rs.cost
            selector(rs, before + left)
            left -= rs.cost - before
    if tail:
        for idx in order:
            rs = shown.get(idx)
            if rs is not None and rs.count < rs.n:
                left -= rs.extend_tail(left)
    return [shown[i].display() for i in sorted(shown)]


def doc_groups(results, doc_key=None):
    """Windows grouped by document: documents by doc_key(results, idx) (default: best rank),
    the windows of a document in document order (doc_span start; rank when unaligned)."""
    groups = {}
    for i, r in enumerate(results):
        groups.setdefault(r["source"], []).append(i)
    val = {s: (doc_key(results, idx) if doc_key else -min(idx)) for s, idx in groups.items()}
    docs = sorted(groups, key=lambda s: (-val[s], min(groups[s])))
    return [sorted(groups[s], key=lambda i: ((results[i]["doc_span"] or (10 ** 9,))[0], i)) for s in docs], \
        [val[s] for s in docs]


def alloc_docs(results, cap, selector, groups, doc_caps=None, min_room=150, bridge=0, tail=True, prefix="keep",
               display_order="alloc"):
    """Like alloc_fill over documents: document k gets at most doc_caps[k] in a first pass
    (spent on its windows in document order), the leftover goes back in the same order.
    prefix: "keep" (every window may show its Bardic prefix), "first" (only the first shown
    window of a document; later ones show neither prefix nor title line), "title" (never the
    prefix; a title line instead)."""
    left = cap
    shown = {}

    def opts(idx, win):
        if prefix == "title":
            return {"drop_prefix": True}
        if prefix == "first" and any(j in shown for j in win if j != idx):
            return {"drop_prefix": True, "use_title": False}
        return {}

    def spend(win, room):
        nonlocal left
        used = 0
        for idx in win:
            if room - used < min_room or left < min_room:
                break
            kw = opts(idx, win)
            rs = shown.get(idx) or ResSel(results[idx], bridge, **kw)
            before = rs.cost
            budget = before + min(room - used, left)
            if rs.count == 0 and full_cost(results[idx], bridge, **kw) <= budget:
                for i in range(rs.n):
                    rs.add(i)
            elif rs.count < rs.n:
                selector(rs, budget)
            if rs.count:
                shown[idx] = rs
            used += rs.cost - before
            left -= rs.cost - before
        return used

    for k, win in enumerate(groups):
        if left < min_room:
            break
        room = left if doc_caps is None else min(left, doc_caps[min(k, len(doc_caps) - 1)])
        spend(win, room)
    if doc_caps is not None:
        for win in groups:
            if left < min_room:
                break
            spend(win, left)
    if tail:
        for win in groups:
            for idx in win:
                rs = shown.get(idx)
                if rs is not None and rs.count < rs.n:
                    left -= rs.extend_tail(left)
    order = [i for win in groups for i in win if i in shown] if display_order == "alloc" else sorted(shown)
    return [shown[i].display() for i in order]


def alloc_prio(results, cap, prio, bridge=0, tail=True, min_prio=-1e18):
    """One greedy over the segments of all results by prio(k, result, segment); each pick is
    added when its exact marginal cost fits what is left of the cap."""
    sels = [ResSel(r, bridge) for r in results]
    cands = []
    for k, rs in enumerate(sels):
        for i, s in enumerate(rs.segs):
            v = prio(k, results[k], s)
            if v >= min_prio:
                cands.append((-v, k, i))
    cands.sort()
    used = 0
    for _, k, i in cands:
        c = sels[k].marginal(i)
        if used + c <= cap:
            sels[k].add(i)
            used += c
    if tail:
        for rs in sels:
            if rs.count and rs.count < rs.n:
                used += rs.extend_tail(cap - used)
    return [rs.display() for rs in sels if rs.count]


def alloc_global(results, cap, score, rank_w, bridge=0, min_gain=-1e18, tail=True, density=False):
    """One greedy over the segments of all results: priority = score(seg) - rank_w * rank."""
    sels = [ResSel(r, bridge) for r in results]
    cands = []
    for k, rs in enumerate(sels):
        for i, s in enumerate(rs.segs):
            v = score(s) - rank_w * k
            if v < min_gain:
                continue
            if density:
                v = v / max(20, s["end"] - s["start"])
            cands.append((-v, k, i))
    cands.sort()
    used = 0
    for _, k, i in cands:
        c = sels[k].marginal(i)
        if used + c <= cap:
            sels[k].add(i)
            used += c
    if tail:
        for rs in sels:
            if rs.count and rs.count < rs.n:
                used += rs.extend_tail(cap - used)
    return [rs.display() for rs in sels if rs.count]


# ── policies (module-level functions for view_sim.py eval FILE.py:FUNC) ──
#
# Shared skeleton (doc-grouped fill): group the result windows by document; order the documents
# by a key; inside a document, its windows in document order (doc_span start). Walk that order:
# a window that fits in what is left of the cap is shown whole; a longer one is cut down by the
# selector; the leftover flows on. Displays are returned in that order (best document first).
# Dev numbers below are CEN facts_share (facts_all) for hybrid / precise / explore at cap 4000.

def _seg_max(r, f):
    v = [s[f] for s in r["segments"] if s["kind"] != "prefix"]
    return max(v) if v else -99.0


def _desc(r, f):
    """Feature of the Bardic prefix (title + description): the same text for every window of a
    document, so a per-document quantity (one embedding per document, computable at ingest)."""
    return next((s[f] for s in r["segments"] if s["kind"] == "prefix"), -99.0)


def _key_rank(results, idx):
    return -min(idx)


def _key_seg(f):
    return lambda results, idx: max(_seg_max(results[i], f) for i in idx)


def _key_desc(f):
    return lambda results, idx: _desc(results[idx[0]], f)


def _thr(f, delta):
    """Cut a long window: its segments within `delta` of its best `f` (best first), then its head."""
    return lambda rs, b: sel_rel_threshold(rs, b, lambda s: s[f], delta)


def _head(rs, b):
    return sel_head(rs, b)


CE_FLOOR = -5.0     # a window whose best logit is below this has no relevant segment: show its head


def _thr_ce(delta):
    """_thr for logits, guarded: below CE_FLOOR the 'near the best' set is noise, so the head."""
    def sel(rs, b):
        best = max((s["ce"] for s in rs.segs if s["kind"] != "prefix"), default=-99.0)
        return sel_head(rs, b) if best < CE_FLOOR else sel_rel_threshold(rs, b, lambda s: s["ce"], delta)
    return sel


def _doc_fill(results, cap, key, selector, **kw):
    if not results:
        return []
    groups, _ = doc_groups(results, key)
    return alloc_docs(results, cap, selector, groups, None, **kw)


def cheap_doc_head(query, results, cap):
    """[cheap: offsets, source names] Documents by best rank, windows in document order, each
    window from its start. Dev 62.0% (16) / 65.8% (18) / 46.7% (6)."""
    return _doc_fill(results, cap, _key_rank, _head)


def cheap_doc_lexthr(query, results, cap):
    """[cheap: + lex] cheap_doc_head, but a window too long for what is left shows first its
    segments with the window's best lex (query-word share), then its head.
    Dev 65.4% (16) / 68.8% (18) / 48.0% (6). The strongest fully cheap policy found."""
    return _doc_fill(results, cap, _key_rank, _thr("lex", 0.0))


def emb_order_head(query, results, cap):
    """[emb: segment embeddings] No grouping: results ordered by their best segment cosine,
    each window from its start, until the cap. Dev 66.5% (18) / 62.3% (17) / 43.1% (6)."""
    if not results:
        return []
    order = sorted(range(len(results)), key=lambda i: (-_seg_max(results[i], "emb"), i))
    return alloc_fill(results, cap, _head, order=order)


def descemb_doc_lexthr(query, results, cap):
    """[emb: ONE vector per document (title + description), at ingest; + lex] Documents by the
    cosine of their description; cut windows: best-lex segments, then head.
    Dev 68.3% (17) / 68.8% (18) / 48.0% (6)."""
    return _doc_fill(results, cap, _key_desc("emb"), _thr("lex", 0.0))


def emb_doc_lexthr(query, results, cap):
    """[emb: segment embeddings; + lex] Documents by their best segment cosine; cut windows:
    best-lex segments, then head. Dev 68.3% (17) / 68.8% (18) / 48.0% (6)."""
    return _doc_fill(results, cap, _key_seg("emb"), _thr("lex", 0.0))


def emb_doc_embthr(query, results, cap):
    """[emb only: segment embeddings] Documents by best segment cosine; cut windows: segments
    within 0.02 of the window's best cosine, then head. Dev 66.0% (17) / 66.9% (18) / 47.3% (6)."""
    return _doc_fill(results, cap, _key_seg("emb"), _thr("emb", 0.02))


def ce_doc_thr(query, results, cap):
    """[ce: one cross-encoder call per segment at query time] Documents by their best segment
    logit; a cut window shows its segments within 2 logits of its best (best first), then its
    head. One parameter; facts flat for delta 1..5 (GoldText falls as delta grows). Guard: a
    window whose best logit is under CE_FLOOR shows its head (no measurable effect on dev).
    Dev 69.9% (18) / 70.8% (19) / 48.0% (6)."""
    return _doc_fill(results, cap, _key_seg("ce"), _thr_ce(2.0))


def ce_doc_greedy(query, results, cap):
    """[ce] Documents by best segment logit; a cut window is filled greedily by
    z(ce) - 0.5 * start/1000 (position prior) + 2 when next to a chosen segment (contiguity).
    Dev 69.9% (18) / 71.0% (19) / 48.0% (6)."""
    if not results:
        return []
    sc = make_scorer(results, w_ce=1.0)
    prio = lambda s: sc(s) - 0.5 * s["start"] / 1000.0  # noqa: E731
    return _doc_fill(results, cap, _key_seg("ce"), lambda rs, b: sel_greedy(rs, b, prio, adj_bonus=2.0))


def _skim(rs, budget, d_ce=2.0, d_emb=0.10, lead=200, head_share=0.3):
    """ce anchors (within d_ce of the best logit); the head up to head_share of the budget; then
    the headings within d_emb of the best heading cosine, each with the `lead` characters after
    it (a section's opening); then the rest of the head."""
    if max((s["ce"] for s in rs.segs if s["kind"] != "prefix"), default=-99.0) >= CE_FLOOR:
        sel_threshold(rs, budget, lambda s: s["ce"], d_ce, fill=None)
    sel_head(rs, max(rs.cost, budget * head_share))
    hd = [i for i in range(rs.n) if rs.segs[i]["kind"] == "heading"]
    if hd:
        top = max(rs.segs[i]["emb"] for i in hd)
        for i in sorted(hd, key=lambda i: (-rs.segs[i]["emb"], i)):
            if rs.segs[i]["emb"] < top - d_emb:
                break
            if rs.sel[i] or rs.cost + rs.marginal(i) > budget:
                continue
            rs.add(i)
            end, j = rs.segs[i]["end"] + lead, i + 1
            while j < rs.n and rs.segs[j]["start"] < end:
                if rs.cost + rs.marginal(j) > budget:
                    break
                rs.add(j)
                j += 1
    return sel_head(rs, budget)


def ce_emb_skim(query, results, cap):
    """[ce + emb] ce_doc_thr, plus a skim of long windows: the openings of the sections whose
    heading is closest to the query (emb). 4 parameters; sensitive to `lead` (300 loses the gain).
    Dev 71.5% (19) / 73.0% (20) / 48.9% (6)."""
    return _doc_fill(results, cap, _key_seg("ce"), _skim)


def ce_doc_thr_gated(query, results, cap):
    """[ce] ce_doc_thr, but when no segment of the search reaches logit -3 (likely no answer)
    the search shows at most half the cap. Halves adversarial chars; costs CD-API GoldText."""
    segs = [s["ce"] for r in results for s in r["segments"] if s["kind"] != "prefix"]
    if segs and max(segs) < -3.0:
        cap = cap // 2
    return ce_doc_thr(query, results, cap)


# Negative results kept for the record (they lose to a window's head):

def ce_greedy_trim(query, results, cap):
    """[ce] Rank order; a cut window keeps its top segments by logit (no position, no contiguity).
    Dev 49.6% (8) / 58.1% (10) / 42.3% (6): worse than fill_full (57.9 / 65.3 / 42.8)."""
    sc = make_scorer(results, w_ce=1.0) if results else None
    return alloc_fill(results, cap, lambda rs, b: sel_greedy(rs, b, sc), tail=False) if results else []


def emb_greedy_trim(query, results, cap):
    """[emb] As ce_greedy_trim with cosine. Dev 49.6% (8) / 58.1% (10) / 41.9% (6)."""
    sc = make_scorer(results, w_emb=1.0) if results else None
    return alloc_fill(results, cap, lambda rs, b: sel_greedy(rs, b, sc), tail=False) if results else []


def ce_global_greedy(query, results, cap):
    """[ce] One greedy over all segments of all results: z(ce) - start/1000 - rank.
    Dev 67.9% (16) / 61.9% (12) / 46.9% (6); fragments the text (CEN GoldText 73 vs 99)."""
    if not results:
        return []
    sc = make_scorer(results, w_ce=1.0)
    return alloc_prio(results, cap, lambda k, r, s: sc(s) - s["start"] / 1000.0 - 1.0 * k)


def ce_doc_thr_embgate(query, results, cap):
    """[ce + emb] ce_doc_thr, but when no segment of the search reaches cosine 0.70 the search
    shows at most half the cap. A gentler gate than ce_doc_thr_gated on CD-API."""
    segs = [s["emb"] for r in results for s in r["segments"] if s["kind"] != "prefix"]
    if segs and max(segs) < 0.70:
        cap = cap // 2
    return ce_doc_thr(query, results, cap)


def emb_doc_mixthr(query, results, cap):
    """[emb: segment embeddings; + lex] Documents by best segment cosine; a cut window shows its
    segments within 0.25 of its best (z(lex) + z(emb)) / 2, then its head.
    Dev 68.4% (17) / 69.3% (18) / 46.7% (6); keeps more GoldText than emb_doc_lexthr."""
    if not results:
        return []
    sc = make_scorer(results, w_emb=0.5, w_lex=0.5)
    return _doc_fill(results, cap, _key_seg("emb"), lambda rs, b: sel_rel_threshold(rs, b, sc, 0.25))
