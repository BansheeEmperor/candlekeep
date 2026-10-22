"""EXPLORATION LIBRARY of the "select_cheap" axis: every variant tried, as factories make_*(**params)
returning a policy. The reported policies are in policies.py (self-contained, same numbers; checked
identical on every dev suite and path).

Features used: the segments' `lex` (share of query content words in the segment), segment kinds,
the heading structure, positions and offsets (match_offset, prefix_len, window length, whether the
window holds the document start via doc_span[0]) and the rank. No `emb`, no `ce`, no `doc_text`.
Every policy here is cost class "lex" (cheap): a pass over the window's segments.

Displayed text = title line + pieces + gap markers, as view_sim.render counts it; every policy
keeps the total within `cap` itself. Families: make_contig / make_contig_ds / make_scan /
make_intro_match (contiguous variants), make_select / make_lgsel / make_dyn / make_global /
make_select2 (segment selection), make_core_extras / make_hooks_core / make_hooks_res (contiguous
core plus selected extras), make_sections (whole sections), make_switch (topic-only queries ->
contiguous, else make_select2).
"""
from __future__ import annotations

import re

GAP = "\n[…]\n"
GAP_LEN = len(GAP)


# ── accounting ───────────────────────────────────────────────────────

def title_len(r) -> int:
    return len(f"Document: {r['title'] or r['source']}\n\n")


def merge(pieces):
    """Sorted pieces, overlapping or touching ones merged (what render() will display)."""
    out = []
    for a, b in sorted((int(a), int(b)) for a, b in pieces if b > a):
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def cost(pieces, tl: int) -> int:
    ps = merge(pieces)
    return sum(b - a for a, b in ps) + GAP_LEN * max(0, len(ps) - 1) + (tl if ps else 0)


def close_gaps(pieces, text, limit: int):
    """Join neighbouring pieces whose gap is whitespace only or at most `limit` characters
    (showing the gap costs no more than a marker and keeps the text contiguous)."""
    ps = merge(pieces)
    out = []
    for a, b in ps:
        if out:
            g = a - out[-1][1]
            if g <= limit or not text[out[-1][1]:a].strip():
                out[-1] = (out[-1][0], b)
                continue
        out.append((a, b))
    return out


# ── structure ────────────────────────────────────────────────────────

def heading_level(text, s) -> int:
    t = text[s["start"]:s["end"]].lstrip()
    return len(t) - len(t.lstrip("#")) or 1


def annotate(r):
    """Per non-prefix segment: section id, heading-path lex, index within its section."""
    text = r["text"]
    segs = [dict(s) for s in r["segments"] if s["kind"] != "prefix"]
    stack = []          # [(level, lex, seg index)]
    sec_id, idx_in_sec, sections = -1, 0, []
    for i, s in enumerate(segs):
        if s["kind"] == "heading":
            lvl = heading_level(text, s)
            stack = [h for h in stack if h[0] < lvl] + [(lvl, s["lex"], i)]
            sec_id += 1
            idx_in_sec = 0
            sections.append({"head": i, "level": lvl, "body": []})
            s.update(sec=sec_id, idx=-1, hlex=s["lex"], hpath=max(h[1] for h in stack), head=i)
            continue
        if sec_id < 0:                       # preamble before any heading
            sec_id = 0
            sections.append({"head": None, "level": 0, "body": []})
        sections[sec_id]["body"].append(i)
        near = stack[-1][1] if stack else 0.0
        # heading path without the level-1 document title
        path = max([h[1] for h in stack if h[0] > 1] or [0.0])
        s.update(sec=sec_id, idx=idx_in_sec, hlex=near, hpath=path,
                 head=sections[sec_id]["head"])
        idx_in_sec += 1
    return segs, sections


# ── per-result builders: (result, budget) -> pieces ──────────────────

def contig(r, budget, back=0, snap=True):
    """One contiguous slice from `back` characters before the matched chunk."""
    text, pl = r["text"], r["prefix_len"]
    mo = r["match_offset"] or pl
    start = max(pl, mo - back)
    if snap and back:
        cands = [s["start"] for s in r["segments"] if s["kind"] != "prefix" and s["start"] <= start]
        start = max(cands) if cands else start
        start = max(pl, start)
    room = budget - (title_len(r) if r["title"] else 0)
    if room <= 0:
        return []
    return [(start, min(len(text), start + room))]


def fit_greedy(r, budget, ranked, segs, must=(), close=GAP_LEN, with_heading=False):
    """Add segments in `ranked` order while the display fits `budget`; keep document order.
    `must`: pieces always included first (a contiguous core). Returns the merged pieces."""
    text = r["text"]
    tl = title_len(r) if r["title"] else 0
    chosen = close_gaps(list(must), text, close)
    if cost(chosen, tl) > budget:
        return []
    partial_done = False
    for i in ranked:
        s = segs[i]
        add = [(s["start"], s["end"])]
        if with_heading and s.get("head") is not None and s["kind"] != "heading":
            h = segs[s["head"]]
            add.append((h["start"], h["end"]))
        trial = close_gaps(chosen + add, text, close)
        c = cost(trial, tl)
        if c <= budget:
            chosen = trial
        elif not partial_done:
            # the head of the first segment that does not fit, when there is room for a sentence
            partial_done = True
            room = budget - cost(chosen, tl) - (GAP_LEN if chosen else tl)
            if room >= 60 and s["kind"] in ("para", "sentence", "list"):
                trial = close_gaps(chosen + [(s["start"], s["start"] + room)], text, close)
                if cost(trial, tl) <= budget:
                    chosen = trial
    return chosen


def fit_dynamic(r, budget, segs, pts, a_adj=0.5, must=(), close=GAP_LEN, with_heading=True, partial=True):
    """Greedy with an adjacency bonus: at each step take the unchosen segment with the most points,
    where a segment whose neighbour (previous or next body segment of the same section) is already
    shown gains a_adj; ties go to the segment nearest the matched chunk. Stops when nothing fits."""
    text = r["text"]
    tl = title_len(r) if r["title"] else 0
    mo = r["match_offset"] or r["prefix_len"]
    chosen = close_gaps(list(must), text, close)
    if cost(chosen, tl) > budget:
        return []
    body = [i for i in range(len(segs)) if pts[i] is not None]
    prev, nxt = {}, {}
    for a, b in zip(body, body[1:]):
        if segs[a]["sec"] == segs[b]["sec"]:
            nxt[a], prev[b] = b, a

    def shown(i):
        s = segs[i]
        return any(x <= s["start"] and s["end"] <= y for x, y in chosen)

    left = [i for i in body if not shown(i)]
    partial_done = not partial
    while left:
        best, bkey = None, None
        for i in left:
            v = pts[i]
            if a_adj and ((i in prev and shown(prev[i])) or (i in nxt and shown(nxt[i]))):
                v += a_adj
            key = (v, -abs(segs[i]["start"] - mo))
            if bkey is None or key > bkey:
                best, bkey = i, key
        s = segs[best]
        add = [(s["start"], s["end"])]
        if with_heading and s.get("head") is not None:
            h = segs[s["head"]]
            add.append((h["start"], h["end"]))
        trial = close_gaps(chosen + add, text, close)
        if cost(trial, tl) <= budget:
            chosen = trial
            left = [i for i in left if not shown(i)]
            continue
        left.remove(best)
        if not partial_done:
            partial_done = True
            room = budget - cost(chosen, tl) - GAP_LEN - (0 if chosen else tl)
            if room >= 60 and s["kind"] in ("para", "sentence", "list"):
                trial = close_gaps(chosen + [(s["start"], s["start"] + room)], text, close)
                if cost(trial, tl) <= budget:
                    chosen = trial
    return chosen


def make_dyn(weights=("harm",), max_results=None, a_adj=0.5, close=40, with_heading=True, core=0.0, mode="ds",
             ds_boost=0.0, **pt_kw):
    """Segment selection by seg_points with the adjacency bonus (fit_dynamic); optional contiguous core."""
    wf = W(*weights)

    def build(r, budget):
        segs, _ = annotate(r)
        pts = seg_points(r, segs, **pt_kw)
        must = []
        if core:
            pl = r["prefix_len"]
            start = pl if (mode == "ds" and at_doc_start(r)) else (r["match_offset"] or pl)
            tl = title_len(r) if r["title"] else 0
            must = contig_from(r, int((budget - tl) * core) + tl, start)
        return fit_dynamic(r, budget, segs, pts, a_adj=a_adj, must=must, close=close, with_heading=with_heading)

    def pol(query, results, cap):
        return allocate(results, cap, build, wf, max_results, ds_boost=ds_boost)
    return pol


def window_end(r):
    return len(r["text"])


# ── allocation over results ──────────────────────────────────────────

DS_BOOST = [0.0]      # sweep hook: weight multiplier (1 + DS_BOOST) for windows holding the document start


def allocate(results, cap, build, weights, max_results=None, min_budget=150, refill=True, ds_boost=None):
    """Give result r a share of the remaining budget proportional to weights[r] among the
    results still to come; a result that needs less passes its leftover down. A final pass
    hands any leftover back to the results in rank order (rebuilt with a larger budget)."""
    rs = results[:max_results] if max_results else list(results)
    n = len(rs)
    boost = DS_BOOST[0] if ds_boost is None else ds_boost
    w = [weights(i) * ((1 + boost) if at_doc_start(rs[i]) else 1) for i in range(n)]
    shown, remaining = {}, cap
    for i, r in enumerate(rs):
        share = remaining * w[i] / (sum(w[i:]) or 1)
        if share < min_budget:
            break
        pieces = build(r, int(share))
        c = cost(pieces, title_len(r) if r["title"] else 0)
        if pieces:
            shown[i] = (pieces, c, int(share))
            remaining -= c
    if refill and remaining > 50:
        for i in sorted(shown):
            pieces, c, b = shown[i]
            nb = c + remaining
            p2 = build(rs[i], nb)
            c2 = cost(p2, title_len(rs[i]) if rs[i]["title"] else 0)
            if c2 - c <= remaining and c2 > c:
                remaining -= c2 - c
                shown[i] = (p2, c2, nb)
            if remaining <= 50:
                break
    out = []
    for i in sorted(shown):
        pieces, c, _ = shown[i]
        out.append({"rank": rs[i]["rank"], "pieces": merge(pieces), "space": "window",
                    "title": bool(rs[i]["title"])})
    return out


def W(kind, p=None):
    if kind == "equal":
        return lambda i: 1.0
    if kind == "harm":
        return lambda i: 1.0 / (i + 1)
    if kind == "geo":
        return lambda i: p ** i
    if kind == "top":            # rank 0 gets p, the others equal
        return lambda i: p if i == 0 else 1.0
    raise ValueError(kind)


# ── scoring of segments ──────────────────────────────────────────────

def seg_scores(r, segs, a_lex=1.0, a_head=0.5, a_lead=0.3, a_near=0.5, near_len=600, code_pen=0.5,
               a_first=0.0):
    """A cheap relevance score per non-prefix segment."""
    mo = r["match_offset"] or r["prefix_len"]
    out = []
    for s in segs:
        if s["kind"] == "heading":
            out.append(-1.0)       # headings come with their body (with_heading), not alone
            continue
        sc = a_lex * s["lex"] + a_head * s["hpath"]
        if s["idx"] == 0:
            sc += a_lead
        if mo <= s["start"] < mo + near_len:
            sc += a_near
        if s["kind"] == "code":
            sc -= code_pen
        if a_first and s["start"] < r["prefix_len"] + 400:
            sc += a_first
        out.append(sc)
    return out


# ── policies ─────────────────────────────────────────────────────────

def make_contig(weights=("harm",), back=0, max_results=None, ds_boost=0.0):
    wf = W(*weights)

    def pol(query, results, cap):
        return allocate(results, cap, lambda r, b: contig(r, b, back), wf, max_results)
    return pol


def make_select(weights=("harm",), max_results=None, core=0, back=0, close=GAP_LEN, with_heading=True,
                old=False, ds_boost=0.0, **score_kw):
    """Greedy selection by seg_points (seg_scores when old=True) inside each result's share of the
    budget; optional contiguous core around the match."""
    wf = W(*weights)

    def build(r, budget):
        segs, _ = annotate(r)
        mo = r["match_offset"] or r["prefix_len"]
        if old:
            sc = seg_scores(r, segs, **score_kw)
            keep = [i for i in range(len(segs)) if sc[i] > -1.0]
        else:
            sc = seg_points(r, segs, **score_kw)
            keep = [i for i in range(len(segs)) if sc[i] is not None]
        order = sorted(keep, key=lambda i: (-sc[i], abs(segs[i]["start"] - mo)))
        must = []
        if core:
            must = contig(r, min(budget, core + (title_len(r) if r["title"] else 0)), back)
        return fit_greedy(r, budget, order, segs, must=must, close=close, with_heading=with_heading)

    def pol(query, results, cap):
        return allocate(results, cap, build, wf, max_results, ds_boost=ds_boost)
    return pol


def seg_points(r, segs, a_lex=1.0, a_head=0.5, a_lead=0.3, a_near=0.5, near_len=600, a_start=0.0, start_len=1000,
               code_pen=1.0, head_kind="hpath", a_doc=0.0, doc_len=1000, a_doc2=0.0, doc_len2=3000,
               doc_decay=False, near_decay=0.0, near_decay_len=2000):
    """Additive points per non-prefix segment (headings get None: they come with their body).
    a_start: the window's first start_len characters; a_doc / a_doc2: the document's first doc_len /
    doc_len2 characters, when the window holds the document's start."""
    mo = r["match_offset"] or r["prefix_len"]
    pl = r["prefix_len"]
    ds = at_doc_start(r)
    out = []
    for s in segs:
        if s["kind"] == "heading":
            out.append(None)
            continue
        p = a_lex * s["lex"]
        if head_kind == "hpath":
            h = s["hpath"]
        elif head_kind == "hlex":
            h = s["hlex"]
        else:                                  # "hany": the nearest heading has a query word
            h = 1.0 if s["hlex"] > 0 else 0.0
        p += a_head * h
        if s["idx"] == 0:
            p += a_lead
        if mo <= s["start"] < mo + near_len:
            p += a_near
        if a_start and s["start"] - pl < start_len:
            p += a_start
        if doc_decay and ds:                       # linear decay over the document's first doc_len chars
            p += a_doc * max(0.0, 1.0 - (s["start"] - pl) / doc_len)
        elif ds and s["start"] - pl < doc_len:
            p += a_doc
        elif ds and s["start"] - pl < doc_len2:
            p += a_doc2
        if near_decay and s["start"] >= mo:
            p += near_decay * max(0.0, 1.0 - (s["start"] - mo) / near_decay_len)
        if s["kind"] == "code":
            p -= code_pen
        out.append(p)
    return out


def make_global(rank_decay=0.5, max_results=None, close=GAP_LEN, with_heading=True, floor=0.0,
                guarantee=0, base=1.0, **pt_kw):
    """One greedy pass over the segments of all results: value = (base + points) * rank_decay**rank.
    `guarantee`: characters from the matched chunk every shown result gets first (keeps it visible)."""

    def pol(query, results, cap):
        rs = results[:max_results] if max_results else list(results)
        info, cands = {}, []
        for r in rs:
            segs, _ = annotate(r)
            pts = seg_points(r, segs, **pt_kw)
            info[r["rank"]] = (r, segs)
            for i, p in enumerate(pts):
                if p is None:
                    continue
                v = (base + p) * (rank_decay ** r["rank"])
                if v > floor:
                    mo = r["match_offset"] or r["prefix_len"]
                    cands.append((-v, r["rank"], abs(segs[i]["start"] - mo), i))
        cands.sort()
        chosen = {k: [] for k in info}
        cur = {k: 0 for k in info}
        total = 0
        if guarantee:
            for k, (r, segs) in info.items():
                ps = contig(r, guarantee)
                c = cost(ps, title_len(r) if r["title"] else 0)
                if ps and total + c <= cap:
                    chosen[k], cur[k], total = ps, c, total + c
        for _, k, _, i in cands:
            r, segs = info[k]
            s = segs[i]
            add = [(s["start"], s["end"])]
            if with_heading and s.get("head") is not None:
                h = segs[s["head"]]
                add.append((h["start"], h["end"]))
            trial = close_gaps(chosen[k] + add, r["text"], close)
            c = cost(trial, title_len(r) if r["title"] else 0)
            if total - cur[k] + c <= cap:
                total += c - cur[k]
                chosen[k], cur[k] = trial, c
        out = []
        for k in sorted(chosen):
            if chosen[k]:
                out.append({"rank": k, "pieces": merge(chosen[k]), "space": "window", "title": bool(info[k][0]["title"])})
        return out
    return pol


def at_doc_start(r) -> bool:
    """The window holds the document's first chunk (in the server: Arcane Recall's chunk indices)."""
    ds = r.get("doc_span")
    return bool(ds) and ds[0] < 5


def contig_from(r, budget, start):
    room = budget - (title_len(r) if r["title"] else 0)
    if room <= 0:
        return []
    return [(start, min(len(r["text"]), start + room))]


def backfilled(r, b, start):
    """Move `start` back when the rest of the window is shorter than the room (show the context
    before the match rather than leave budget unused), snapped to a segment start."""
    pl, n = r["prefix_len"], len(r["text"])
    room = b - (title_len(r) if r["title"] else 0)
    if n - start >= room:
        return start
    want = max(pl, n - room)
    cands = [s["start"] for s in r["segments"] if s["kind"] != "prefix" and want <= s["start"] <= start]
    return min(cands) if cands else start


def make_contig_ds(weights=("harm",), max_results=None, mode="ds", backfill=False, pre_fit=0.0, ds_boost=0.0):
    """Contiguous: from the window start when the window starts the document (mode ds), from
    the window start always (mode ws), else from the matched chunk. pre_fit: also from the window
    start when the matched chunk starts within pre_fit of the result's room from it."""
    wf = W(*weights)

    def build(r, b):
        pl = r["prefix_len"]
        mo = r["match_offset"] or pl
        start = pl if (mode == "ws" or (mode == "ds" and at_doc_start(r))) else mo
        room = b - (title_len(r) if r["title"] else 0)
        if pre_fit and start == mo and mo - pl <= pre_fit * room:
            start = pl
        if backfill:
            start = backfilled(r, b, start)
        return contig_from(r, b, start)

    def pol(query, results, cap):
        return allocate(results, cap, build, wf, max_results, ds_boost=ds_boost)
    return pol


def make_intro_match(weights=("harm",), max_results=None, intro=0.5, min_intro=300, ds_boost=0.0):
    """Two pieces: the document's start (a share `intro` of the result's budget, when the window
    holds it) and the matched chunk onward with the rest; one piece when they meet."""
    wf = W(*weights)

    def build(r, b):
        pl, text = r["prefix_len"], r["text"]
        mo = r["match_offset"] or pl
        tl = title_len(r) if r["title"] else 0
        room = b - tl
        if room <= 0:
            return []
        if not at_doc_start(r) or mo - pl <= room * intro:
            start = pl if at_doc_start(r) else mo
            return [(start, min(len(text), start + room))]
        ia = max(min_intro, int(room * intro))
        ia = min(ia, room)
        pieces = [(pl, pl + ia)]
        rest = room - ia - GAP_LEN
        if rest > 50:
            pieces.append((mo, min(len(text), mo + rest)))
        return merge(pieces)

    def pol(query, results, cap):
        return allocate(results, cap, build, wf, max_results, ds_boost=ds_boost)
    return pol


def scan(r, budget, start, skip=("code",), wrap=False, close=GAP_LEN, skip_fn=None, code_max=None):
    """Walk the window in document order from `start`, adding every segment that is not skipped
    (code blocks by default) while it fits; the last one may be cut. wrap: then continue from the
    window start up to `start`. code_max: show at most this many characters of a code block."""
    text = r["text"]
    tl = title_len(r) if r["title"] else 0
    segs = [s for s in r["segments"] if s["kind"] != "prefix"]
    first = [s for s in segs if s["end"] > start]
    order = first + ([s for s in segs if s["end"] <= start] if wrap else [])
    chosen, c = [], 0
    for s in order:
        if s["kind"] in skip or (skip_fn and skip_fn(s)):
            continue
        a = max(s["start"], start) if s in first else s["start"]
        e = s["end"]
        if code_max is not None and s["kind"] == "code":
            e = min(e, a + code_max)
        trial = close_gaps(chosen + [(a, e)], text, close)
        ct = cost(trial, tl)
        if ct <= budget:
            chosen, c = trial, ct
            continue
        room = budget - c - (0 if chosen and a - chosen[-1][1] <= close else GAP_LEN) - (0 if chosen else tl)
        if room >= 60:
            trial = close_gaps(chosen + [(a, a + room)], text, close)
            if cost(trial, tl) <= budget:
                chosen = trial
        break
    return chosen


def make_scan(weights=("harm",), max_results=None, mode="ds", skip=("code",), wrap=False, close=GAP_LEN,
              code_max=None, backfill=False, ds_boost=0.0):
    """Document order from the document start (window holds it) or the matched chunk, skipping code."""
    wf = W(*weights)

    def build(r, b):
        pl = r["prefix_len"]
        mo = r["match_offset"] or pl
        start = pl if (mode == "ws" or (mode == "ds" and at_doc_start(r))) else mo
        if backfill:
            start = backfilled(r, b, start)
        return scan(r, b, start, skip=skip, wrap=wrap, close=close, code_max=code_max)

    def pol(query, results, cap):
        return allocate(results, cap, build, wf, max_results, ds_boost=ds_boost)
    return pol


def make_core_extras(weights=("harm",), max_results=None, core=0.6, min_core=400, mode="ds", close=40,
                     with_heading=True, code_max=None, match_core=0, ds_boost=0.0, **pt_kw):
    """A contiguous core (a share `core` of the result's budget) from the document start when the
    window holds it, else from the matched chunk; the rest of the budget goes to the best segments
    elsewhere in the window by seg_points (document order kept, gap markers counted).
    match_core: when the core starts at the document start and the matched chunk lies outside it,
    the first `match_core` characters of the matched chunk are added first."""
    wf = W(*weights)

    def build(r, budget):
        pl = r["prefix_len"]
        mo = r["match_offset"] or pl
        tl = title_len(r) if r["title"] else 0
        room = budget - tl
        if room <= 0:
            return []
        start = pl if (mode == "ws" or (mode == "ds" and at_doc_start(r))) else mo
        clen = max(min(room, min_core), int(room * core))
        if code_max is not None:
            must = scan(r, clen + tl, start, skip=(), close=close, code_max=code_max)
        else:
            must = contig_from(r, clen + tl, start)
        if match_core and start != mo and must and not (must[0][0] <= mo < must[-1][1]):
            left = budget - cost(must, tl) - GAP_LEN
            if left >= 100:
                must = must + [(mo, min(len(r["text"]), mo + min(match_core, left)))]
        segs, _ = annotate(r)
        pts = seg_points(r, segs, **pt_kw)
        keep = [i for i in range(len(segs)) if pts[i] is not None]
        order = sorted(keep, key=lambda i: (-pts[i], abs(segs[i]["start"] - mo)))
        return fit_greedy(r, budget, order, segs, must=must, close=close, with_heading=with_heading)

    def pol(query, results, cap):
        return allocate(results, cap, build, wf, max_results, ds_boost=ds_boost)
    return pol


STOP = set("a an and are as at be by can do does for from has have how i in is it its of on or that the this to "
           "was what when where which who why will with you your vs versus about into than then there these those "
           "should would could my we our".split())


def words(s: str) -> set:
    """Content words, as the segments' `lex` feature tokenises them."""
    return {w for w in re.findall(r"[a-z0-9][a-z0-9\-\.]*[a-z0-9]|[a-z0-9]", s.lower()) if w not in STOP and len(w) > 1}


def has_word(w: str, sw: set) -> bool:
    return w in sw or (len(w) >= 5 and any(x.startswith(w[:5]) for x in sw))


def residual_words(query: str, r) -> list:
    """The query's content words that are not in the result's title: what the query asks about
    the document beyond naming its topic."""
    tw = words(r["title"] or "") | words(r["source"].rsplit(".", 1)[0].replace("-", " ").replace("_", " "))
    return sorted(w for w in words(query) if not has_word(w, tw))


def make_select2(weights=("harm",), max_results=None, close=40, with_heading=True, a_lex=0.5, a_rlex=1.5,
                 a_lead=0.3, a_doc=1.5, doc_len=1000, a_doc2=0.75, doc_len2=3000, code_pen=1.0, ds_boost=1.0,
                 rlex_mode="share", a_rhead=0.0):
    """Segment selection whose lexical evidence adapts to the query: plain lex counts a little
    (a_lex), lex over the query words missing from the result's title counts a lot (a_rlex).
    A query that only names a document's topic is led by the document-start prior; a query
    with extra specific words is led by where those words occur."""
    wf = W(*weights)

    def pol(query, results, cap):
        def build(r, budget):
            segs, _ = annotate(r)
            res_w = residual_words(query["query"], r)
            pts = seg_points(r, segs, a_lex=a_lex, a_head=0.0, a_lead=a_lead, a_near=0.0, a_doc=a_doc,
                             doc_len=doc_len, a_doc2=a_doc2, doc_len2=doc_len2, code_pen=code_pen)
            if res_w and a_rlex:
                text = r["text"]
                for i, s in enumerate(segs):
                    if pts[i] is None:
                        continue
                    sw = words(text[s["start"]:s["end"]])
                    hit = sum(1 for w in res_w if has_word(w, sw))
                    v = hit / len(res_w) if rlex_mode == "share" else (1.0 if hit else 0.0)
                    pts[i] += a_rlex * v
                    if a_rhead and s.get("head") is not None:
                        h = segs[s["head"]]
                        hw = words(text[h["start"]:h["end"]])
                        pts[i] += a_rhead * sum(1 for w in res_w if has_word(w, hw)) / len(res_w)
            mo = r["match_offset"] or r["prefix_len"]
            keep = [i for i in range(len(segs)) if pts[i] is not None]
            order = sorted(keep, key=lambda i: (-pts[i], abs(segs[i]["start"] - mo)))
            return fit_greedy(r, budget, order, segs, close=close, with_heading=with_heading)
        return allocate(results, cap, build, wf, max_results, ds_boost=ds_boost)
    return pol


def make_hooks_res(weights=("harm",), max_results=None, max_hooks=2, hook_share=0.4, min_share=0.5, pre_fit=0.5,
                   close=40, with_heading=True, ds_boost=1.0, also_lex=0.0):
    """Contiguous core plus hooks found by the query's residual words (those not in the result's
    title). Core: from the window start when the window holds the document start or the matched
    chunk begins in the first pre_fit of the room, else from the matched chunk. Hooks: body
    segments outside the core holding at least min_share of the residual words, most first, at
    most max_hooks and hook_share of the room. also_lex: a segment with lex >= also_lex is a hook
    too (0 = off)."""
    wf = W(*weights)

    def pol(query, results, cap):
        def build(r, budget):
            text = r["text"]
            pl = r["prefix_len"]
            mo = r["match_offset"] or pl
            tl = title_len(r) if r["title"] else 0
            room = budget - tl
            if room <= 0:
                return []
            start = pl if at_doc_start(r) else mo
            if start == mo and mo - pl <= pre_fit * room:
                start = pl
            segs, _ = annotate(r)
            res_w = residual_words(query["query"], r)
            cands = []
            for i, s in enumerate(segs):
                if s["kind"] in ("heading", "code"):
                    continue
                share = 0.0
                if res_w:
                    sw = words(text[s["start"]:s["end"]])
                    share = sum(1 for w in res_w if has_word(w, sw)) / len(res_w)
                strong = (res_w and share >= min_share) or (also_lex and s["lex"] >= also_lex)
                if not strong:
                    continue
                cands.append((-(share + s["lex"] + (0.5 if s["idx"] == 0 else 0.0)), abs(s["start"] - mo), i))
            cands.sort()
            hooks = []
            core_end_guess = start + int(room * (1 - hook_share))
            for _, _, i in cands:
                if len([1 for _ in hooks]) and len(merge(hooks)) >= max_hooks:
                    break
                s = segs[i]
                if start <= s["start"] < core_end_guess:
                    continue                     # the core shows it
                add = [(s["start"], s["end"])]
                if with_heading and s.get("head") is not None:
                    h = segs[s["head"]]
                    add.append((h["start"], h["end"]))
                trial = close_gaps(hooks + add, text, close)
                if cost(trial, 0) <= room * hook_share:
                    hooks = trial
            lo, hi = start, min(len(text), start + room)
            while lo < hi:                       # the longest core that fits with the hooks
                mid = (lo + hi + 1) // 2
                if cost(close_gaps(hooks + [(start, mid)], text, close), tl) <= budget:
                    lo = mid
                else:
                    hi = mid - 1
            out = close_gaps(hooks + ([(start, lo)] if lo > start else []), text, close)
            while out and cost(out, tl) > budget:
                a, b = out[-1]
                over = cost(out, tl) - budget
                out[-1:] = [(a, b - over)] if b - a > over else []
            return out
        return allocate(results, cap, build, wf, max_results, ds_boost=ds_boost)
    return pol


def make_switch(per_result=True, pre_fit=0.5, ds_boost=1.0, **sel_kw):
    """Topic-only query (every content word is in the result's title): the contiguous view
    (make_contig_ds); otherwise segment selection (make_select2). per_result: decide per result
    (its own title), else once per search by the top result's title."""
    contig = make_contig_ds(pre_fit=pre_fit, ds_boost=ds_boost)
    sel = make_select2(ds_boost=ds_boost, **sel_kw)

    def pol(query, results, cap):
        if not results:
            return []
        if not per_result:
            return contig(query, results, cap) if not residual_words(query["query"], results[0]) else sel(query, results, cap)
        wf = W("harm")
        pl_cache = {}

        def build(r, budget):
            if residual_words(query["query"], r):
                return pl_cache.setdefault(("s", r["rank"], budget), _select2_build(query, r, budget, **sel_kw))
            start = r["prefix_len"] if at_doc_start(r) else (r["match_offset"] or r["prefix_len"])
            room = budget - (title_len(r) if r["title"] else 0)
            if start != r["prefix_len"] and start - r["prefix_len"] <= pre_fit * room:
                start = r["prefix_len"]
            return contig_from(r, budget, start)
        return allocate(results, cap, build, wf, None, ds_boost=ds_boost)
    return pol


def _select2_build(query, r, budget, close=40, with_heading=True, a_lex=0.5, a_rlex=1.5, a_lead=0.3, a_doc=1.5,
                   doc_len=1000, a_doc2=0.75, doc_len2=3000, code_pen=1.0):
    segs, _ = annotate(r)
    res_w = residual_words(query["query"], r)
    pts = seg_points(r, segs, a_lex=a_lex, a_head=0.0, a_lead=a_lead, a_near=0.0, a_doc=a_doc, doc_len=doc_len,
                     a_doc2=a_doc2, doc_len2=doc_len2, code_pen=code_pen)
    if res_w and a_rlex:
        for i, s in enumerate(segs):
            if pts[i] is None:
                continue
            sw = words(r["text"][s["start"]:s["end"]])
            pts[i] += a_rlex * sum(1 for w in res_w if has_word(w, sw)) / len(res_w)
    mo = r["match_offset"] or r["prefix_len"]
    keep = [i for i in range(len(segs)) if pts[i] is not None]
    order = sorted(keep, key=lambda i: (-pts[i], abs(segs[i]["start"] - mo)))
    return fit_greedy(r, budget, order, segs, close=close, with_heading=with_heading)


BOLD_ITEM = re.compile(r"\s*([-*+]|\d+[.)])\s+\*\*[^*\n]+\*\*")

LG_DEFAULT = {"doc1": 2.5, "doc2": 1.75, "doc_len1": 1000, "doc_len2": 3000, "win1": 0.75, "lead": 1.0,
              "bold": 1.0, "plain": -1.0, "lex": 0.75, "head": 0.4, "before": -0.5, "code": -1.75,
              "near": 0.0, "near_len": 600}


def seg_logit(r, segs, w):
    """Cheap evidence (log-odds-like points) that a segment holds an answer fact. Signs and rough
    sizes from a logistic fit on dev CEN segments, rounded; see the module docstring."""
    text = r["text"]
    pl = r["prefix_len"]
    mo = r["match_offset"] or pl
    ds = at_doc_start(r)
    out = []
    for s in segs:
        if s["kind"] == "heading":
            out.append(None)
            continue
        pos = s["start"] - pl
        p = 0.0
        if ds and pos < w["doc_len1"]:
            p += w["doc1"]
        elif ds and pos < w["doc_len2"]:
            p += w["doc2"]
        if pos < 1000:
            p += w["win1"]
        if s["idx"] == 0:
            p += w["lead"]
        if s["kind"] == "list":
            p += w["bold"] if BOLD_ITEM.match(text, s["start"]) else w["plain"]
        if s["kind"] == "code":
            p += w["code"]
        p += w["lex"] * s["lex"]
        if s["hlex"] > 0:
            p += w["head"]
        if s["end"] <= mo and not ds:
            p += w["before"]
        if w["near"] and mo <= s["start"] < mo + w["near_len"]:
            p += w["near"]
        out.append(p)
    return out


def make_lgsel(weights=("harm",), max_results=None, close=40, with_heading=True, density=False, bias=-5.0,
               ds_boost=0.0, **wkw):
    """Greedy segment selection by seg_logit points (density=False) or by estimated facts per
    character, sigmoid(bias + points) / length (density=True), inside each result's share."""
    import math
    w = dict(LG_DEFAULT, **wkw)
    wf = W(*weights)

    def build(r, budget):
        segs, _ = annotate(r)
        pts = seg_logit(r, segs, w)
        mo = r["match_offset"] or r["prefix_len"]
        keep = [i for i in range(len(segs)) if pts[i] is not None]
        if density:
            def key(i):
                L = max(40, segs[i]["end"] - segs[i]["start"])
                return (-(1 / (1 + math.exp(-(bias + pts[i])))) / L, abs(segs[i]["start"] - mo))
        else:
            def key(i):
                return (-pts[i], abs(segs[i]["start"] - mo))
        order = sorted(keep, key=key)
        return fit_greedy(r, budget, order, segs, close=close, with_heading=with_heading)

    def pol(query, results, cap):
        return allocate(results, cap, build, wf, max_results, ds_boost=ds_boost)
    return pol


def make_hooks_core(weights=("harm",), max_results=None, theta=0.5, hook_share=0.35, max_hooks=4, mode="ds",
                    close=40, with_heading=True, code_max=None, hook_kinds=("para", "sentence", "list", "table"),
                    head_hooks=False, pre_fit=0.0, ds_boost=0.0):
    """Strong lexical hooks first, then the contiguous core.
    Hooks: body segments outside the core's natural start region whose lex >= theta (share of the
    query's content words), best first, at most max_hooks and hook_share of the result's room.
    Core: contiguous from the document start when the window holds it, else from the matched
    chunk, filling what is left (code blocks cut to code_max characters when set).
    head_hooks: a segment that is the first of a section whose heading has lex >= theta is a hook too."""
    wf = W(*weights)

    def build(r, budget):
        text = r["text"]
        pl = r["prefix_len"]
        mo = r["match_offset"] or pl
        tl = title_len(r) if r["title"] else 0
        room = budget - tl
        if room <= 0:
            return []
        start = pl if (mode == "ds" and at_doc_start(r)) else mo
        if pre_fit and start == mo and mo - pl <= pre_fit * room:
            start = pl                        # an early match: show the window from its start
        segs, _ = annotate(r)
        cands = []
        for i, s in enumerate(segs):
            if s["kind"] not in hook_kinds:
                continue
            strong = s["lex"] >= theta or (head_hooks and s["idx"] == 0 and s["hlex"] >= theta)
            if not strong:
                continue
            if start <= s["start"] < start + int(room * (1 - hook_share)):
                continue                      # the core will show it anyway
            cands.append((-(s["lex"] + (0.5 if s["idx"] == 0 else 0)), abs(s["start"] - mo), i))
        cands.sort()
        hooks, used = [], 0
        for _, _, i in cands[:max_hooks]:
            s = segs[i]
            add = [(s["start"], s["end"])]
            if with_heading and s.get("head") is not None:
                h = segs[s["head"]]
                add.append((h["start"], h["end"]))
            trial = close_gaps(hooks + add, text, close)
            c = cost(trial, 0)
            if c <= room * hook_share:
                hooks, used = trial, c
        # core: contiguous from start, as long as the room left allows
        left = room - used
        core = []
        if left > 0:
            def total(core_end):
                return cost(close_gaps(hooks + [(start, core_end)], text, close), tl)
            if code_max is None:
                lo, hi = start, min(len(text), start + left)
                while lo < hi:                 # longest core that fits with the hooks
                    mid = (lo + hi + 1) // 2
                    if total(mid) <= budget:
                        lo = mid
                    else:
                        hi = mid - 1
                if lo > start:
                    core = [(start, lo)]
            else:
                core = scan(r, left + tl, start, skip=(), close=close, code_max=code_max)
        out = close_gaps(hooks + core, text, close)
        while out and cost(out, tl) > budget:   # safety: trim the last piece
            a, b = out[-1]
            over = cost(out, tl) - budget
            if b - a > over:
                out[-1] = (a, b - over)
            else:
                out.pop()
        return out

    def pol(query, results, cap):
        return allocate(results, cap, build, wf, max_results, ds_boost=ds_boost)
    return pol


def section_spans(r):
    """Sections of the window: a heading (with any heading-only parents just above it) and its body
    up to the next heading. Returns [{start, end, body_start, heads, segs}] in document order."""
    segs, _ = annotate(r)
    out, cur = [], None
    for i, s in enumerate(segs):
        if s["kind"] == "heading":
            if cur is not None and not cur["segs"]:
                cur["heads"].append(i)          # heading-only parent: joins the next section
                continue
            if cur is not None:
                out.append(cur)
            cur = {"heads": [i], "segs": []}
            continue
        if cur is None:
            cur = {"heads": [], "segs": []}
        cur["segs"].append(i)
    if cur is not None:
        out.append(cur)
    for sec in out:
        idx = sec["heads"] + sec["segs"]
        sec["start"] = segs[min(idx)]["start"]
        sec["end"] = segs[max(idx)]["end"]
        sec["body_start"] = segs[sec["segs"][0]]["start"] if sec["segs"] else sec["end"]
    return segs, out


def make_sections(weights=("harm",), max_results=None, sec_cap=900, a_head=1.0, a_body=1.0, a_doc=1.0, doc_len=1000,
                  a_match=1.0, code_pen=0.5, close=40, body="max", keep_going=False, ds_boost=0.0):
    """Whole sections, best first: score = a_head * heading lex (path, without the document title)
    + a_body * body lex (max or mean over the body) + a_doc (the section starts in the document's
    first doc_len characters, when the window holds them) + a_match (it holds the matched chunk)
    - code_pen * (share of the section's characters in code). Each section is shown from its
    heading, at most sec_cap characters; the last one that does not fit is cut."""
    wf = W(*weights)

    def build(r, budget):
        text = r["text"]
        tl = title_len(r) if r["title"] else 0
        pl = r["prefix_len"]
        mo = r["match_offset"] or pl
        ds = at_doc_start(r)
        segs, secs = section_spans(r)
        scored = []
        for k, sec in enumerate(secs):
            hl = max([segs[i]["lex"] for i in sec["heads"] if heading_level(text, segs[i]) > 1] or [0.0])
            if not hl and sec["segs"]:
                hl = segs[sec["segs"][0]]["hpath"]
            bl = [segs[i]["lex"] for i in sec["segs"]] or [0.0]
            b = max(bl) if body == "max" else sum(bl) / len(bl)
            code = sum(segs[i]["end"] - segs[i]["start"] for i in sec["segs"] if segs[i]["kind"] == "code")
            size = max(1, sec["end"] - sec["start"])
            sc = a_head * hl + a_body * b - code_pen * code / size
            if ds and sec["start"] - pl < doc_len:
                sc += a_doc
            if sec["start"] <= mo < sec["end"] + 2 or (mo <= sec["start"] < mo + 1):
                sc += a_match
            scored.append((-sc, abs(sec["start"] - mo), k))
        scored.sort()
        chosen = []
        for _, _, k in scored:
            sec = secs[k]
            a, e = sec["start"], min(sec["end"], sec["start"] + sec_cap)
            if mo > sec["start"] and mo < sec["end"] and mo + 300 > e:   # keep the matched chunk inside the cap
                a = max(sec["start"], min(mo, sec["end"]) - sec_cap // 3)
                e = min(sec["end"], a + sec_cap)
            trial = close_gaps(chosen + [(a, e)], text, close)
            if cost(trial, tl) <= budget:
                chosen = trial
                continue
            room = budget - cost(chosen, tl) - GAP_LEN - (0 if chosen else tl)
            if room >= 150:
                trial = close_gaps(chosen + [(a, a + room)], text, close)
                if cost(trial, tl) <= budget:
                    chosen = trial
            if not keep_going:
                break
        return chosen

    def pol(query, results, cap):
        return allocate(results, cap, build, wf, max_results, ds_boost=ds_boost)
    return pol


bprime_like = make_contig(("equal",))
