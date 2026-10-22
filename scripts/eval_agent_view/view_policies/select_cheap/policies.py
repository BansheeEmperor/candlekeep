"""Display policies of the "select_cheap" axis: choose WHAT to show inside each result from cheap
features only (view_sim.py's policy API). Standard library only; deterministic.

Cost class of every policy here: lex (cheap). They read the query text, the window text, its
segments (`kind`, `lex`), the heading structure, offsets (`prefix_len`, `match_offset`) and whether
the window holds the document's start (`doc_span[0] == 0`; in the server, whether Arcane Recall's
window includes chunk 0 of the document). No `emb`, no `ce`, no `doc_text`.

What the dev split showed (round 2, cap 4,000; details in the search report):
  * the strongest cheap signal is the DOCUMENT START: in a window that holds it, the first 1,000
    characters carry 2.25 answer facts per 1,000 characters, against 0.30 in the first 1,000
    characters of a window that does not; of the top result's facts that sit before the match
    point, 28 of 32 (hybrid) and 75 of 78 (precise) are in windows holding the document start;
  * lexical overlap with the query helps on queries that ask something specific about a
    document (CEN "lexical" questions), and does nothing on topic-only questions;
  * code blocks almost never hold answer facts, but they are the gold text of API documents.

Policies (all split the budget over the results by rank, weight 1/(rank+1), doubled for a window
that holds its document's start; a result whose share would be under 150 characters is dropped;
leftover budget goes back to the results in rank order):

  contig_start   baseline: one contiguous slice per result, from the window start when the window
                 holds the document start or the matched chunk begins within the first half of the
                 result's room, else from the matched chunk.
  hooks1         contig_start's slice, plus at most one lexical "hook": the best body segment
                 outside the slice with lex >= 0.5 (and its heading), within 35% of the room.
  select_doc     greedy segment selection: points = lex + 0.3 (first segment of its section)
                 + 1.5 (document's first 1,000 characters) or + 0.75 (up to 3,000), - 1 (code);
                 ties nearest the matched chunk; headings come with their segments; gaps of up to
                 40 characters are shown rather than marked; document order kept.
  select_res     select_doc with query-adaptive lexical evidence: 0.5 * lex + 1.5 * (share of the
                 query's "residual" words found in the segment), where residual words are the
                 query's content words that are not in the result's title (or file name).

Reference variants (cited in the findings, not recommended): contig_match (B′'s view with the
bigger budget, split 1/(rank+1)) and select_lex (lexical greedy selection without the
document-start prior).

The exploration library with every variant tried (factories make_*) is select_cheap.py.
"""
from __future__ import annotations

import re

GAP = "\n[…]\n"
GAP_LEN = len(GAP)
MIN_BUDGET = 150
STOP = set("a an and are as at be by can do does for from has have how i in is it its of on or that the this to "
           "was what when where which who why will with you your vs versus about into than then there these those "
           "should would could my we our".split())


# ── accounting (as view_sim.render counts the displayed text) ─────────

def _title_len(r) -> int:
    return len(f"Document: {r['title'] or r['source']}\n\n") if r["title"] else 0


def _merge(pieces):
    out = []
    for a, b in sorted((int(a), int(b)) for a, b in pieces if b > a):
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def _cost(pieces, tl: int) -> int:
    ps = _merge(pieces)
    return sum(b - a for a, b in ps) + GAP_LEN * max(0, len(ps) - 1) + (tl if ps else 0)


def _close_gaps(pieces, text, limit: int):
    """Join pieces whose gap is whitespace or at most `limit` characters (cheaper than a marker
    and it keeps the text contiguous)."""
    out = []
    for a, b in _merge(pieces):
        if out and (a - out[-1][1] <= limit or not text[out[-1][1]:a].strip()):
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return out


# ── structure and features ───────────────────────────────────────────

def _at_doc_start(r) -> bool:
    ds = r.get("doc_span")
    return bool(ds) and ds[0] < 5


def _annotate(r):
    """Non-prefix segments with: sec (section id), idx (index of a body segment in its section),
    head (index of its section heading or None), hlex (lex of that heading), hpath (highest lex
    of the headings above it, the level-1 document title excluded)."""
    text = r["text"]
    segs = [dict(s) for s in r["segments"] if s["kind"] != "prefix"]
    stack, sec_id, idx, head = [], -1, 0, None
    for i, s in enumerate(segs):
        if s["kind"] == "heading":
            t = text[s["start"]:s["end"]].lstrip()
            lvl = len(t) - len(t.lstrip("#")) or 1
            stack = [h for h in stack if h[0] < lvl] + [(lvl, s["lex"])]
            sec_id, idx, head = sec_id + 1, 0, i
            s.update(sec=sec_id, idx=-1, head=i, hlex=s["lex"])
            continue
        if sec_id < 0:
            sec_id = 0
        s.update(sec=sec_id, idx=idx, head=head, hlex=stack[-1][1] if stack else 0.0,
                 hpath=max([h[1] for h in stack if h[0] > 1] or [0.0]))
        idx += 1
    return segs


def _words(s: str) -> set:
    return {w for w in re.findall(r"[a-z0-9][a-z0-9\-\.]*[a-z0-9]|[a-z0-9]", s.lower()) if w not in STOP and len(w) > 1}


def _has_word(w: str, sw: set) -> bool:
    return w in sw or (len(w) >= 5 and any(x.startswith(w[:5]) for x in sw))


def _residual_words(query: str, r) -> list:
    tw = _words(r["title"] or "") | _words(r["source"].rsplit(".", 1)[0].replace("-", " ").replace("_", " "))
    return sorted(w for w in _words(query) if not _has_word(w, tw))


def _start(r, room, pre_fit=0.5) -> int:
    """Where a contiguous view starts: the window start when it holds the document start or
    the matched chunk begins within pre_fit of the room, else the matched chunk."""
    pl = r["prefix_len"]
    mo = r["match_offset"] or pl
    if _at_doc_start(r) or mo - pl <= pre_fit * room:
        return pl
    return mo


# ── allocation over results ──────────────────────────────────────────

def _allocate(results, cap, build, ds_boost=1.0):
    rs = list(results)
    w = [(1.0 / (i + 1)) * ((1 + ds_boost) if _at_doc_start(r) else 1.0) for i, r in enumerate(rs)]
    shown, remaining = {}, cap
    for i, r in enumerate(rs):
        share = remaining * w[i] / (sum(w[i:]) or 1)
        if share < MIN_BUDGET:
            break
        pieces = build(r, int(share))
        c = _cost(pieces, _title_len(r))
        if pieces:
            shown[i] = (pieces, c)
            remaining -= c
    if remaining > 50:                      # leftover back to the results in rank order
        for i in sorted(shown):
            pieces, c = shown[i]
            p2 = build(rs[i], c + remaining)
            c2 = _cost(p2, _title_len(rs[i]))
            if c < c2 <= c + remaining:
                remaining -= c2 - c
                shown[i] = (p2, c2)
            if remaining <= 50:
                break
    return [{"rank": rs[i]["rank"], "pieces": _merge(shown[i][0]), "space": "window", "title": bool(rs[i]["title"])}
            for i in sorted(shown)]


# ── per-result builders ──────────────────────────────────────────────

def _contig(r, budget):
    room = budget - _title_len(r)
    if room <= 0:
        return []
    start = _start(r, room)
    return [(start, min(len(r["text"]), start + room))]


def _fit_greedy(r, budget, order, segs, close=40):
    """Add segments (with their section heading) in `order` while the display fits; the first
    segment that does not fit may be shown cut, once."""
    text, tl = r["text"], _title_len(r)
    chosen, partial_done = [], False
    for i in order:
        s = segs[i]
        add = [(s["start"], s["end"])]
        if s.get("head") is not None:
            h = segs[s["head"]]
            add.append((h["start"], h["end"]))
        trial = _close_gaps(chosen + add, text, close)
        if _cost(trial, tl) <= budget:
            chosen = trial
        elif not partial_done:
            partial_done = True
            room = budget - _cost(chosen, tl) - (GAP_LEN if chosen else tl)
            if room >= 60 and s["kind"] in ("para", "sentence", "list"):
                trial = _close_gaps(chosen + [(s["start"], s["start"] + room)], text, close)
                if _cost(trial, tl) <= budget:
                    chosen = trial
    return chosen


def _points(r, segs, a_lex=1.0, a_lead=0.3, a_doc=1.5, a_doc2=0.75, doc_len=1000, doc_len2=3000, code_pen=1.0,
            residual=None, a_rlex=0.0):
    pl = r["prefix_len"]
    ds = _at_doc_start(r)
    out = []
    for s in segs:
        if s["kind"] == "heading":
            out.append(None)
            continue
        p = a_lex * s["lex"]
        if s["idx"] == 0:
            p += a_lead
        if ds and s["start"] - pl < doc_len:
            p += a_doc
        elif ds and s["start"] - pl < doc_len2:
            p += a_doc2
        if s["kind"] == "code":
            p -= code_pen
        if residual and a_rlex:
            sw = _words(r["text"][s["start"]:s["end"]])
            p += a_rlex * sum(1 for w in residual if _has_word(w, sw)) / len(residual)
        out.append(p)
    return out


def _select(r, budget, pts, segs, close=40):
    mo = r["match_offset"] or r["prefix_len"]
    keep = [i for i in range(len(segs)) if pts[i] is not None]
    order = sorted(keep, key=lambda i: (-pts[i], abs(segs[i]["start"] - mo)))
    return _fit_greedy(r, budget, order, segs, close)


def _hooks1(r, budget, theta=0.5, hook_share=0.35, close=40):
    text, tl = r["text"], _title_len(r)
    room = budget - tl
    if room <= 0:
        return []
    start = _start(r, room)
    mo = r["match_offset"] or r["prefix_len"]
    segs = _annotate(r)
    cands = sorted((-(s["lex"] + (0.5 if s["idx"] == 0 else 0.0)), abs(s["start"] - mo), i)
                   for i, s in enumerate(segs)
                   if s["kind"] in ("para", "sentence", "list", "table") and s["lex"] >= theta
                   and not (start <= s["start"] < start + int(room * (1 - hook_share))))
    hooks, used = [], 0
    for _, _, i in cands[:1]:
        s = segs[i]
        add = [(s["start"], s["end"])]
        if s.get("head") is not None:
            h = segs[s["head"]]
            add.append((h["start"], h["end"]))
        trial = _close_gaps(add, text, close)
        if _cost(trial, 0) <= room * hook_share:
            hooks, used = trial, _cost(trial, 0)
    if room - used <= 0:
        return hooks
    lo, hi = start, min(len(text), start + room - used)
    while lo < hi:                           # the longest contiguous slice that fits beside the hook
        mid = (lo + hi + 1) // 2
        if _cost(_close_gaps(hooks + [(start, mid)], text, close), tl) <= budget:
            lo = mid
        else:
            hi = mid - 1
    out = _close_gaps(hooks + ([(start, lo)] if lo > start else []), text, close)
    while out and _cost(out, tl) > budget:   # safety
        a, b = out[-1]
        over = _cost(out, tl) - budget
        out[-1:] = [(a, b - over)] if b - a > over else []
    return out


# ── the policies ─────────────────────────────────────────────────────

def contig_start(query, results, cap):
    """Baseline. One contiguous slice per result: from the window start when the window holds the
    document start or the matched chunk begins in the first half of the result's room, else from
    the matched chunk. Cost class: lex (offsets only)."""
    return _allocate(results, cap, _contig)


def hooks1(query, results, cap):
    """contig_start plus at most one lexical hook per result (best body segment outside the slice
    with lex >= 0.5, with its heading, within 35% of the room). Cost class: lex."""
    return _allocate(results, cap, _hooks1)


def select_doc(query, results, cap):
    """Greedy segment selection: lex + 0.3 lead + 1.5 / 0.75 document start (first 1,000 / 3,000
    characters, when the window holds it) - 1 code; document order kept. Cost class: lex."""
    def build(r, budget):
        segs = _annotate(r)
        return _select(r, budget, _points(r, segs), segs)
    return _allocate(results, cap, build)


def select_res(query, results, cap):
    """select_doc with query-adaptive lexical evidence: 0.5 * lex + 1.5 * share of the query's
    residual words (content words not in the result's title) in the segment. Cost class: lex."""
    def build(r, budget):
        segs = _annotate(r)
        res_w = _residual_words(query["query"], r)
        return _select(r, budget, _points(r, segs, a_lex=0.5, residual=res_w, a_rlex=1.5), segs)
    return _allocate(results, cap, build)


# ── reference variants (cited in the findings; not recommended) ──────

def contig_match(query, results, cap):
    """B′'s view with the bigger budget: one contiguous slice from the matched chunk per result,
    budget split 1/(rank+1), no document-start weighting. Cost class: lex (offsets only)."""
    def build(r, budget):
        room = budget - _title_len(r)
        if room <= 0:
            return []
        mo = r["match_offset"] or r["prefix_len"]
        return [(mo, min(len(r["text"]), mo + room))]
    return _allocate(results, cap, build, ds_boost=0.0)


def select_lex(query, results, cap):
    """The axis's naive starting point: greedy selection by lexical overlap with structure bonuses
    and no document-start prior: lex + 0.5 * heading-path lex + 0.3 lead + 0.5 (first 600
    characters from the matched chunk) - 1 code; gaps of up to 5 characters shown; budget split
    1/(rank+1). Cost class: lex."""
    def build(r, budget):
        segs = _annotate(r)
        mo = r["match_offset"] or r["prefix_len"]
        pts = []
        for s in segs:
            if s["kind"] == "heading":
                pts.append(None)
                continue
            p = s["lex"] + 0.5 * s["hpath"] + (0.3 if s["idx"] == 0 else 0.0)
            if mo <= s["start"] < mo + 600:
                p += 0.5
            if s["kind"] == "code":
                p -= 1.0
            pts.append(p)
        return _select(r, budget, pts, segs, close=GAP_LEN)
    return _allocate(results, cap, build, ds_boost=0.0)
