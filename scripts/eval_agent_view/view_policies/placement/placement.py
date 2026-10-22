"""Placement policies for view_sim.py: where each result's view sits around the match point.

Axis: given a per-result character budget (fixed allocation, below), choose WHICH part of the
Arcane Recall window (or of the document, for the "beyond the window" variants) to show.

Allocation (shared by every policy here, so that only placement varies):
  water-filling of the search cap over the shown results. Each result has a demand (title line +
  the text it could usefully show) and a weight; the cap is split in proportion to the weights,
  and whatever a short window cannot use is passed on to the others.
    eq   weights 1, 1, 1, ...             (equal split)
    rw   weights 1 / (1 + 0.5 * rank)     (mild rank weighting: 1, .67, .5, .4, .33, ...)
  Every result keeps a view (no result is dropped), so srcvis only changes through the cap.

Placements (per result, given body budget L = allocation - title line):
  match      [mo, mo + L)                                      B'-like; cut at the window end
  lead(s)    the L-long interval with the match at fraction s of it, clamped inside the body; when
             the window ends early the interval slides back ("fill backward")
  start      [pl, pl + L): the window body from its first character
  fits(m)    window start when the match (and m characters of it) fits in the view, else lead(s)
  snap       lead(s), then the start snaps back to the previous heading or paragraph start
             (at most `back` characters)
  section    from the heading of the section that contains the match; then the rest of the
             window after it, then before it
  head(h)    window start when the match fits; otherwise two pieces: the first h*L characters of the
             body and the match region (lead s), joined by a gap marker
  doc        any of the above, extended into doc_text outside the window when the window is used up
             (space "doc"; needs a fetch of the document's other chunks)

  firstlex   from the first segment before the match with lex >= t, snapped to its heading
  headlex / headsec / intro / fits / headfix   variants of head (see each function)
  make_dochead / make_dochead2   head, with the head piece taken from the document's opening (doc space)

Cost classes: everything uses offsets, lengths and segment kinds only (cheap; firstlex also uses the
segments' lex), except the `doc` variants (doc_text beyond the window: moderate, an extra fetch of
the document's chunks).

Title line: "Document: <title>\\n\\n" is shown on every result that has a title, as B' does (the
views never start at character 0). It counts against the cap.

Named policies (bottom of the file; evaluated with view_sim.py eval --split dev --cap 4000):
  lead_rw (baseline), match_rw, start_rw, head75_rw, firstlex_rw, dochead75_rw, and _eq variants.
"""
from __future__ import annotations

import re

GAP_COST = len("\n[…]\n")
HEAD_RE = re.compile(r"\s*(#+)")


# ── helpers ──────────────────────────────────────────────────────────

def title_cost(r) -> int:
    return len(f"Document: {r['title'] or r['source']}\n\n") if r.get("title") else 0


def weights(results, scheme: str) -> list[float]:
    if scheme == "eq":
        return [1.0 for _ in results]
    if scheme == "rw":
        return [1.0 / (1.0 + 0.5 * r["rank"]) for r in results]
    if scheme.startswith("rw"):                      # rw<k>: 1 / (1 + k * rank)
        k = float(scheme[2:])
        return [1.0 / (1.0 + k * r["rank"]) for r in results]
    raise ValueError(scheme)


def waterfill(demands: list[int], w: list[float], cap: int) -> list[int]:
    """Split `cap` in proportion to `w`; a share above a result's demand goes to the others."""
    n = len(demands)
    alloc = [0.0] * n
    active = [i for i in range(n) if demands[i] > 0]
    rem = float(cap)
    while active and rem > 1e-9:
        tot = sum(w[i] for i in active)
        if tot <= 0:
            break
        done = [i for i in active if demands[i] - alloc[i] <= rem * w[i] / tot]
        if not done:
            for i in active:
                alloc[i] += rem * w[i] / tot
            break
        for i in done:
            rem -= demands[i] - alloc[i]
            alloc[i] = float(demands[i])
        active = [i for i in active if i not in done]
    return [int(a) for a in alloc]


def body(r) -> tuple[int, int, int]:
    """(pl, n, mo): body start, window end, match offset clamped into the body."""
    pl, n = r["prefix_len"], len(r["text"])
    mo = min(max(r["match_offset"] or 0, pl), n)
    return pl, n, mo


def slide(a: int, L: int, lo: int, hi: int) -> tuple[int, int]:
    """The L-long interval starting at a, moved inside [lo, hi) (shorter if [lo, hi) is)."""
    a = max(lo, min(a, hi - L))
    return a, min(hi, a + L)


def heading_level(text: str, a: int) -> int:
    m = HEAD_RE.match(text, a)
    return len(m.group(1)) if m else 0


def boundaries(r, kinds=("heading", "para", "list", "table", "code", "sentence")) -> list[int]:
    return sorted({s["start"] for s in r["segments"] if s["kind"] in kinds and s["start"] >= r["prefix_len"]})


def snap_back(r, a: int, back: int, kinds) -> int:
    """The latest boundary of `kinds` at or before a, if it is at most `back` characters before a."""
    cands = [s for s in boundaries(r, kinds) if a - back <= s <= a]
    return max(cands) if cands else a


def section_of(r, mo: int) -> tuple[int, int]:
    """(start, end) of the section containing mo: from the last heading at or before mo to the next
    heading of the same or a higher level (or the window end)."""
    pl, n, _ = body(r)
    heads = [(s["start"], heading_level(r["text"], s["start"])) for s in r["segments"] if s["kind"] == "heading"]
    before = [(a, lv) for a, lv in heads if a <= mo]
    if not before:
        start, lvl = pl, 0
    else:
        start, lvl = before[-1]
    end = n
    for a, lv in heads:
        if a > max(mo, start) and (lvl == 0 or lv <= lvl):
            end = a
            break
    return start, end


# ── placements (window space) ────────────────────────────────────────

def place_match(r, L, **_):
    pl, n, mo = body(r)
    return [(mo, min(n, mo + L))]


def place_lead(r, L, s=0.0, fill=True, **_):
    pl, n, mo = body(r)
    a = mo - int(round(s * L))
    if not fill:
        a = max(pl, a)
        return [(a, min(n, a + L))]
    return [slide(a, L, pl, n)]


def place_start(r, L, **_):
    pl, n, _ = body(r)
    return [(pl, min(n, pl + L))]


def place_fits(r, L, m=300, s=0.0, **_):
    pl, n, mo = body(r)
    if mo - pl + min(m, n - mo) <= L:
        return [(pl, min(n, pl + L))]
    return place_lead(r, L, s=s)


def place_snap(r, L, s=0.0, back=400, kinds=("heading",), **_):
    pl, n, mo = body(r)
    a = mo - int(round(s * L))
    a = max(pl, a)
    a2 = snap_back(r, a, back, kinds)
    return [slide(a2, L, pl, n)]


def place_section(r, L, after_first=True, **_):
    """Section that contains the match, from its heading; then extend after, then before."""
    pl, n, mo = body(r)
    a, b = section_of(r, mo)
    if b - a >= L:
        return [(a, a + L)]
    rest = L - (b - a)
    if after_first:
        b2 = min(n, b + rest)
        rest -= b2 - b
        a2 = max(pl, a - rest)
        return [(a2, b2)]
    a2 = max(pl, a - rest)
    rest -= a - a2
    return [(a2, min(n, b + rest))]


def place_head(r, L, h=0.4, s=0.0, m=300, minpiece=0, small="lead", **_):
    """Window start if the match fits; else the first h*L characters plus the match region.
    When either piece would be shorter than `minpiece`, one piece instead: `small` (lead or start)."""
    pl, n, mo = body(r)
    if mo - pl + min(m, n - mo) <= L:
        return [(pl, min(n, pl + L))]
    hl = int(h * L)
    ml = L - hl - GAP_COST
    if ml <= 0 or hl <= 0 or min(hl, ml) < minpiece:
        return place_start(r, L) if small == "start" else place_lead(r, L, s=s)
    a, b = slide(mo - int(round(s * ml)), ml, pl + hl, n)     # match piece never overlaps the head piece
    if b - a < ml:                                            # the window is short: give the rest to the head
        hl = min(a - pl, hl + ml - (b - a))
    return [(pl, pl + hl), (a, b)]


def at_doc_start(r) -> bool:
    """The window begins at the document's first character (its introduction is in the window)."""
    return bool(r.get("doc_span")) and r["doc_span"][0] == 0


def place_intro(r, L, s=0.0, inner="start", h=0.6, m=300, **_):
    """When the window begins at the document start: `inner` (start or head); else lead(s)."""
    if at_doc_start(r):
        return place_start(r, L) if inner == "start" else place_head(r, L, h=h, s=s, m=m)
    return place_lead(r, L, s=s)


def place_firstlex(r, L, t=0.5, snap=True, **_):
    """From the first segment that holds at least a share t of the query's content words (lex), snapped
    back to the heading above it; the match when no segment before the match qualifies."""
    pl, n, mo = body(r)
    a = mo
    for sg in r["segments"]:
        if sg["kind"] == "prefix" or sg["start"] < pl:
            continue
        if sg["start"] >= mo:
            break
        if sg["lex"] >= t:
            a = sg["start"]
            break
    if snap and a < mo:
        heads = [sg["start"] for sg in r["segments"] if sg["kind"] == "heading" and pl <= sg["start"] <= a]
        if heads:
            a = heads[-1]
    return [slide(a, L, pl, n)]


def place_headfix(r, L, H=1000, s=0.0, m=300, **_):
    """Window start when the match fits; else a head piece of min(H, L/2) characters plus the match region."""
    h = min(H, L // 2) / max(L, 1)
    return place_head(r, L, h=h, s=s, m=m)


def place_headlex(r, L, h=0.75, t=0.5, m=300, **_):
    """head(h), but the second piece starts at the first lex-relevant segment after the head piece (snapped
    to its heading) when one exists before the match; else at the match."""
    pl, n, mo = body(r)
    if mo - pl + min(m, n - mo) <= L:
        return [(pl, min(n, pl + L))]
    hl = int(h * L)
    ml = L - hl - GAP_COST
    if ml <= 0:
        return place_lead(r, L)
    anchor = mo
    for sg in r["segments"]:
        if sg["start"] < pl + hl or sg["kind"] == "prefix":
            continue
        if sg["start"] >= mo:
            break
        if sg["lex"] >= t:
            heads = [x["start"] for x in r["segments"] if x["kind"] == "heading" and pl + hl <= x["start"] <= sg["start"]]
            anchor = heads[-1] if heads else sg["start"]
            break
    a, b = slide(anchor, ml, pl + hl, n)
    if b - a < ml:
        hl = min(a - pl, hl + ml - (b - a))
    return [(pl, pl + hl), (a, b)]


def place_headsec(r, L, m=300, hmin=0.5, minpiece=150, **_):
    """head, with the split set by structure: the match piece is the section that contains the match
    (from the match to the section end), at most (1 - hmin) * L; the head piece gets the rest."""
    pl, n, mo = body(r)
    if mo - pl + min(m, n - mo) <= L:
        return [(pl, min(n, pl + L))]
    _, se = section_of(r, mo)
    ml = max(min(se - mo, int((1 - hmin) * L)), minpiece)
    hl = L - ml - GAP_COST
    if hl < minpiece:
        return place_lead(r, L)
    a, b = slide(mo, ml, pl + hl, n)
    if b - a < ml:
        hl = min(a - pl, hl + ml - (b - a))
    return [(pl, pl + hl), (a, b)]


PLACEMENTS = {"match": place_match, "lead": place_lead, "start": place_start, "fits": place_fits,
              "snap": place_snap, "section": place_section, "head": place_head, "intro": place_intro,
              "firstlex": place_firstlex, "headfix": place_headfix, "headlex": place_headlex,
              "headsec": place_headsec}


def make_firstocc(first="head", later="lead", alloc="rw", **kw):
    """`first` placement for the first shown result of each document, `later` for its other results."""
    pf, plat = make(place=first, alloc=alloc, **kw), make(place=later, alloc=alloc, **kw)

    def policy(query, results, cap):
        a = {d["rank"]: d for d in pf(query, results, cap)}
        b = {d["rank"]: d for d in plat(query, results, cap)}
        seen, out = set(), []
        for r in results:
            src = a if r["source"] not in seen else b
            seen.add(r["source"])
            if r["rank"] in src:
                out.append(src[r["rank"]])
        return enforce_cap(out, results, cap)

    return policy


# ── doc space ────────────────────────────────────────────────────────

def doc_ok(r) -> bool:
    if not r.get("doc_text") or not r.get("doc_span"):
        return False
    a, b = r["doc_span"]
    return r["doc_text"][a:b] == r["text"][r["prefix_len"]:]


def to_doc(r, pieces):
    a0 = r["doc_span"][0]
    pl = r["prefix_len"]
    return [(a0 + max(0, x - pl), a0 + max(0, y - pl)) for x, y in pieces]


def extend_doc(r, pieces, L, taken, after_first=True):
    """Doc-space pieces extended outside the window by the unused budget (after the window, then
    before it), avoiding doc ranges another result of the same document shows (`taken`)."""
    dl = len(r["doc_text"])
    used = sum(b - a for a, b in pieces) + GAP_COST * (len(pieces) - 1)
    rest = L - used
    if rest <= 0:
        return pieces
    pieces = [list(p) for p in pieces]

    def free_after(x):
        lim = dl
        for a, b in taken:
            if a >= x:
                lim = min(lim, a)
            elif b > x:
                return x
        return lim

    def free_before(x):
        lim = 0
        for a, b in taken:
            if b <= x:
                lim = max(lim, b)
            elif a < x:
                return x
        return lim

    order = ("after", "before") if after_first else ("before", "after")
    for side in order:
        if rest <= 0:
            break
        if side == "after":
            end = pieces[-1][1]
            new = min(free_after(end), end + rest)
            rest -= new - end
            pieces[-1][1] = new
        else:
            st = pieces[0][0]
            new = max(free_before(st), st - rest)
            rest -= st - new
            pieces[0][0] = new
    return [tuple(p) for p in pieces]


# ── the policy builder ───────────────────────────────────────────────

def topn(policy, n):
    """Show only the first n results (interaction check with the number of results; not this axis)."""
    def wrapped(query, results, cap):
        return policy(query, results[:n], cap)
    return wrapped


def make(place="lead", alloc="eq", doc=None, doc_after_first=True, **kw):
    """doc=None: window only. doc="surplus": allocation by window demand; the cap left over once every
    window is used up extends the views into their documents (same weights). doc="own": each result's
    demand is its whole document, so a short window extends into its document instead of passing its
    share on to the other results."""
    fn = PLACEMENTS[place]

    def policy(query, results, cap):
        if not results:
            return []
        tcs = [title_cost(r) for r in results]
        wdem = [t + len(r["text"]) - r["prefix_len"] for r, t in zip(results, tcs)]
        ddem = [t + (len(r["doc_text"]) if doc_ok(r) else len(r["text"]) - r["prefix_len"])
                for r, t in zip(results, tcs)]
        w = weights(results, alloc) if not alloc.startswith("fixed") else None
        if alloc.startswith("fixed"):        # fixed<k>: B'-style, k characters per result in rank order, cut at the cap
            k, left, budgets = int(alloc[5:]), cap, []
            for d in wdem:
                b = max(0, min(k, d, left))
                budgets.append(b)
                left -= b
        elif doc == "own0":                  # only the top result may extend into its document
            ddem = [dd if r["rank"] == 0 else wd for r, dd, wd in zip(results, ddem, wdem)]
            budgets = waterfill(ddem, w, cap)
        elif doc == "own":
            budgets = waterfill(ddem, w, cap)
        else:
            budgets = waterfill(wdem, w, cap)
            if doc == "surplus" and sum(budgets) < cap:
                extra = waterfill([d - b for d, b in zip(ddem, budgets)], w, cap - sum(budgets))
                budgets = [b + e for b, e in zip(budgets, extra)]
        out = []
        taken: dict[str, list] = {}
        if doc:
            for r in results:
                if doc_ok(r):
                    taken.setdefault(r["source"], []).append(tuple(r["doc_span"]))
        for r, t, b in zip(results, tcs, budgets):
            L = b - t
            if L <= 0:
                continue
            pieces = fn(r, L, **kw)
            pieces = [(x, y) for x, y in pieces if y > x]
            if not pieces:
                continue
            space = "window"
            if doc and doc_ok(r) and (doc != "own0" or r["rank"] == 0):
                pieces = to_doc(r, pieces)
                others = [s for s in taken.get(r["source"], []) if tuple(s) != tuple(r["doc_span"])]
                pieces = extend_doc(r, pieces, L, others, doc_after_first)
                space = "doc"
            out.append({"rank": r["rank"], "pieces": pieces, "space": space, "title": bool(r.get("title"))})
        return enforce_cap(out, results, cap)

    return policy


def make_dochead(h=0.75, m=300, alloc="rw", top_only=False, minpiece=0):
    """head(h) placement; when a window does not begin at its document's start, the head piece is the
    document's opening (doc_text[0:...], fetched) instead of the window's first characters, unless
    another shown result of the same document already begins at the document start."""

    def policy(query, results, cap):
        if not results:
            return []
        tcs = [title_cost(r) for r in results]
        starts = {r["source"] for r in results if at_doc_start(r)}

        def use_doc(r):
            return (doc_ok(r) and not at_doc_start(r) and r["source"] not in starts
                    and (not top_only or r["rank"] == 0))

        dem = [t + len(r["text"]) - r["prefix_len"] + (GAP_COST + r["doc_span"][0] if use_doc(r) else 0)
               for r, t in zip(results, tcs)]
        budgets = waterfill(dem, weights(results, alloc), cap)
        out = []
        for r, t, b in zip(results, tcs, budgets):
            L = b - t
            if L <= 0:
                continue
            if not use_doc(r):
                pieces = [(x, y) for x, y in place_head(r, L, h=h, m=m, minpiece=minpiece) if y > x]
                if pieces:
                    out.append({"rank": r["rank"], "pieces": pieces, "space": "window", "title": bool(r.get("title"))})
                continue
            pl, n, mo = body(r)
            a0, a1 = r["doc_span"]
            hl = min(int(h * L), a0)
            ml = L - hl - GAP_COST
            if ml <= 0 or min(hl, ml) < minpiece:
                hl, ml = 0, L
            ma, mb = slide(a0 + (mo - pl), ml, a0, a1)
            if mb - ma < ml:                       # short window: the rest goes to the document opening
                hl = min(a0, hl + ml - (mb - ma))
            pieces = ([(0, hl)] if hl > 0 else []) + [(ma, mb)]
            if hl >= ma:                           # touching: one piece
                pieces = [(0, mb)]
            out.append({"rank": r["rank"], "pieces": pieces, "space": "doc", "title": bool(r.get("title"))})
        return enforce_cap(out, results, cap)

    return policy


def make_dochead2(h=0.75, m=300, alloc="rw", ranks=(0,), minpiece=0):
    """head(h) for every result; for the results in `ranks`, the head rule is applied to the whole
    document instead of the window: the document's opening when the match fits in the view from it,
    else the opening (h*L) plus the match region, which may run past the window's end."""

    def policy(query, results, cap):
        if not results:
            return []
        tcs = [title_cost(r) for r in results]
        starts = {}
        for r in results:
            if at_doc_start(r):
                starts.setdefault(r["source"], set()).add(r["rank"])

        def use_doc(r):
            # not when another result of the same document already shows the document's start
            return doc_ok(r) and r["rank"] in ranks and not (starts.get(r["source"], set()) - {r["rank"]})

        dem = [t + (len(r["doc_text"]) if use_doc(r) else len(r["text"]) - r["prefix_len"])
               for r, t in zip(results, tcs)]
        budgets = waterfill(dem, weights(results, alloc), cap)
        taken = {}
        for r in results:
            if doc_ok(r):
                taken.setdefault(r["source"], []).append((r["rank"], tuple(r["doc_span"])))
        out = []
        for r, t, b in zip(results, tcs, budgets):
            L = b - t
            if L <= 0:
                continue
            if not use_doc(r):
                pieces = [(x, y) for x, y in place_head(r, L, h=h, m=m, minpiece=minpiece) if y > x]
                if pieces:
                    out.append({"rank": r["rank"], "pieces": pieces, "space": "window", "title": bool(r.get("title"))})
                continue
            pl, n, mo = body(r)
            a0 = r["doc_span"][0]
            dl = len(r["doc_text"])
            md = a0 + (mo - pl)
            # the match piece stops where another result's window of the same document begins
            hi = dl
            for rk, (x, y) in taken.get(r["source"], []):
                if rk != r["rank"] and x >= md:
                    hi = min(hi, x)
            virt = {"prefix_len": 0, "text": r["doc_text"][:hi], "match_offset": md}
            pv = place_head(virt, L, h=h, m=m, minpiece=minpiece)
            pieces = [(x, y) for x, y in pv if y > x]
            if pieces:
                out.append({"rank": r["rank"], "pieces": pieces, "space": "doc", "title": bool(r.get("title"))})
        return enforce_cap(out, results, cap)

    return policy


def shown_len(d, results) -> int:
    r = results[d["rank"]]
    pieces = sorted(d["pieces"])
    merged = []
    for a, b in pieces:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    t = len(f"Document: {r['title'] or r['source']}\n\n") if d.get("title") else 0
    return t + sum(b - a for a, b in merged) + GAP_COST * max(0, len(merged) - 1)


def enforce_cap(out, results, cap):
    """Safety net: trim the last displays so that the total stays within the cap."""
    total = sum(shown_len(d, results) for d in out)
    while out and total > cap:
        d = out[-1]
        over = total - cap
        a, b = d["pieces"][-1]
        if b - a > over:
            d["pieces"][-1] = (a, b - over)
        else:
            d["pieces"] = d["pieces"][:-1]
            if not d["pieces"]:
                out.pop()
        total = sum(shown_len(x, results) for x in out)
    return out


# ── named policies (reported; dev JSONs from view_sim.py eval) ──────────────
# Allocation everywhere: water-filling of the cap, weights 1 / (1 + 0.5 * rank) ("rw"), all results
# kept; "_eq" variants use equal weights. Only the placement differs between them.

_match_rw = make(place="match", alloc="rw")
_lead_rw = make(place="lead", alloc="rw", s=0.0)
_start_rw = make(place="start", alloc="rw")
_head75_rw = make(place="head", alloc="rw", h=0.75, m=300, minpiece=150)
_firstlex_rw = make(place="firstlex", alloc="rw", t=0.5)
_dochead75_rw = make_dochead(h=0.75, m=300, alloc="rw", top_only=True, minpiece=150)
_lead_eq = make(place="lead", alloc="eq", s=0.0)
_head75_eq = make(place="head", alloc="eq", h=0.75, m=300, minpiece=150)
_dochead75_eq = make_dochead(h=0.75, m=300, alloc="eq", top_only=True, minpiece=150)


def match_rw(query, results, cap):
    """Baseline: B' placement (from match_offset, cut at the window end), rw allocation of the cap."""
    return _match_rw(query, results, cap)


def lead_rw(query, results, cap):
    """Strongest simple baseline: B' placement plus fill-backward (the view slides back when the window
    ends before the budget does), rw allocation. Cheap."""
    return _lead_rw(query, results, cap)


def start_rw(query, results, cap):
    """Each view from the window's first body character. Cheap. Hides the matched chunk when it is deep."""
    return _start_rw(query, results, cap)


def head75_rw(query, results, cap):
    """Window start when the matched chunk (300 characters of it) fits in the view; else the first 75% of
    the budget from the window start plus 25% from the match point (gap marker between). No split when a
    piece would be under 150 characters (then B' placement with fill-backward). Cheap."""
    return _head75_rw(query, results, cap)


def firstlex_rw(query, results, cap):
    """From the first segment before the match holding half the query's content words (lex), snapped back
    to its heading; else from the match. Fill-backward. Cheap (lex)."""
    return _firstlex_rw(query, results, cap)


def dochead75_rw(query, results, cap):
    """head75_rw, except for the top result when its window does not begin at its document's start (and no
    other result shows that start): 75% of its budget from the document's opening (doc_text, fetched) and
    25% from the match point, always split. Moderate cost (one extra fetch of the top document's first
    chunks)."""
    return _dochead75_rw(query, results, cap)


def lead_eq(query, results, cap):
    return _lead_eq(query, results, cap)


def head75_eq(query, results, cap):
    return _head75_eq(query, results, cap)


def dochead75_eq(query, results, cap):
    return _dochead75_eq(query, results, cap)
