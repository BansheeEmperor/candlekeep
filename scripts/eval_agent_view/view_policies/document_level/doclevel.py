"""Document-level display policies for view_sim.py (axis: document-level effects).

One growth model, with document-level switches (see `make`).

  * Every considered result (the first `n_max`) gets a "seed" that grows an interval at a
    speed set by its rank: decay**rank (`weight_by="result"`), or by its document's rank,
    decay**doc_rank, split among the document's results as member_decay**k (`weight_by="doc"`;
    member_decay=0: one seed per document, on its best result).  One global growth time is
    found by bisection, so the display uses the cap exactly; a seed that reaches its bounds
    stops, and its unused share goes to the others (water-filling).
  * Anchor: the start of the result's window (`anchor="start"`, growing forward), or its
    match point (`anchor="match"`, `alpha` of the growth before it, as B' starts there).
  * Bounds: the interval stays inside the result's Arcane Recall window (`ext="none"`), or,
    once it covers the window, grows into the adjacent document text (`ext="fill"`; `beta`
    of the extension goes before the window), up to `ext_chars` on each side (0 = no limit).
    `ext="all"` ignores the window and grows around the anchor in the whole document.
  * `lead`: the first `lead_ranks` documents also get a seed at the start of the document
    (`lead_space="doc"`, needs doc_text when the window does not start there), growing
    forward at `lead` times the result's speed (added to it unless `norm_seeds`).
  * `preview`: every considered document gets at least its window's first `preview` chars.
  * `whole_fits`: show the whole document instead when it fits in the result's share.
  * `merge`: results of the same document form one display (one title, pieces in document
    order, a joint budget: the union of their intervals is paid once).  `gap_fill`: a gap
    of at most that many characters between two pieces of one display is shown too.
    Displays are ordered by their document's best rank (order changes no simulator metric).
  * Results whose share falls under `min_len` (and whose interval is not already the whole
    window/document) are dropped, lowest rank first, and the budget is redistributed.
  * Title line ("Document: <title>"): `title="auto"` prints it unless the display opens
    with the document's own first heading.

Spaces: results whose window aligns exactly with the document (doc_span, checked here
whitespace-free; 99% of windows) are handled in document coordinates when a document
feature is on; otherwise in window coordinates.  Window coordinates skip the Bardic prefix
(the title line replaces it, as in B').

Named policies (bottom of the file) and cost classes:
  start_window          cheap  baseline: window start, rank-decayed shares, no document feature
  doc_merge_cheap       cheap  + same-document merge, shares by document rank
  doc_extend            doc    + document coordinates, windows grow into the adjacent text
  doc_one_lead          doc    one seed per document + the top document's opening (lead 0.5)
  doc_one_lead_preview  doc    doc_one_lead + a 150-character preview of every document (top 10)
  match_doc_lead        doc    doc_one_lead's document features on B''s match-point anchor
  doc_head              doc    contrast only: every document from its first character
"cheap" uses offsets, lengths and the window text only.  "doc" shows document text outside
the windows: the server's Arcane Recall already fetches every chunk of each result's
document (`get_chunks_by_source` in expand_results), so the text is in memory there; the
cost is plumbing (keep the stitched document), not an extra query.
"""
from __future__ import annotations

import bisect

GAP_LEN = len("\n[…]\n")


def _title_len(r):
    return len(f"Document: {r['title'] or r['source']}\n\n")


def _prepare(r, want_doc):
    """Coordinates of one result: space, bounds of the window, anchor, outer bounds."""
    text = r["text"] or ""
    pl = r.get("prefix_len") or 0
    mo = max(r.get("match_offset") or 0, pl)
    ds, doc = r.get("doc_span"), r.get("doc_text")
    # the window starts at the document start (in the server: its first chunk has chunk_index 0)
    base = {"rank": r["rank"], "source": r["source"], "tlen": _title_len(r), "at_start": bool(ds and ds[0] == 0),
            "heading_first": bool(doc and doc.lstrip().startswith("#"))}
    if want_doc and ds and doc:
        a, b = ds
        wp = [pl + i for i, ch in enumerate(text[pl:]) if not ch.isspace()]
        dp = [a + i for i, ch in enumerate(doc[a:b]) if not ch.isspace()]
        if wp and len(wp) == len(dp) and all(text[x] == doc[y] for x, y in zip(wp, dp)):
            k = bisect.bisect_left(wp, mo)
            m = dp[k] if k < len(dp) else b
            return dict(base, space="doc", lo=a, hi=b, m=m, dlo=0, dhi=len(doc))
    return dict(base, space="window", lo=pl, hi=len(text), m=min(mo, len(text)), dlo=pl, dhi=len(text))


def _clamp_place(m, ell, lo, hi, alpha):
    s = m - alpha * ell
    s = max(lo, min(s, hi - ell))
    return s, s + ell


def _snap(src, a, b, reach):
    """Move a piece's end back to the last line break or sentence end within `reach` characters."""
    if b >= len(src) or reach <= 0:
        return a, b
    lo = max(a + 1, b - reach)
    cut = max(src.rfind("\n", lo, b), src.rfind(". ", lo, b) + 1 if src.rfind(". ", lo, b) >= 0 else -1)
    return (a, cut) if cut > a else (a, b)


def make(n_max=5, decay=0.6, alpha=0.3, beta=0.5, ext="none", ext_chars=0, whole_fits=False,
         merge=True, gap_fill=0, min_len=200, title="mid", doc_space=None, weights=None,
         anchor="match", lead=0.0, lead_ranks=1, lead_space="doc", mix=None, norm_seeds=False,
         weight_by="result", member_decay=0.5, snap=0, preview=0):
    """Build a policy.  doc_space=None: document coordinates only when a document feature is on.

    mix=(s_start, s_match): every result gets a window-start seed and a match seed with these
    relative speeds (overrides `anchor`).  norm_seeds: a result's seeds (lead included) share
    its speed decay**rank instead of adding to it.
    weight_by="doc": speeds by document rank (decay**doc_rank, documents in order of their best
    result), split among a document's results by member_decay**k (k = 0 for its best result).
    """
    use_doc = doc_space if doc_space is not None else (
        ext != "none" or whole_fits or gap_fill > 0 or merge or (lead > 0 and lead_space == "doc"))

    def grow(sd, share):
        """Interval of one seed for a share of `share` characters."""
        it = sd["it"]
        lo, hi, dlo, dhi = it["lo"], it["hi"], it["dlo"], it["dhi"]
        if sd["kind"] == "preview":     # a floor: the first `preview` characters of the window
            return float(lo), float(min(hi, lo + min(share, preview)))
        if sd["kind"] == "lead":
            top = dhi if (it["space"] == "doc" and lead_space == "doc") else hi
            start = dlo if (it["space"] == "doc" and lead_space == "doc") else lo
            return float(start), float(min(top, start + share))
        m, a = sd["m"], sd["alpha"]
        if it["space"] == "doc":
            if whole_fits and share >= dhi - dlo:
                return float(dlo), float(dhi)
            if ext == "all":
                ell = min(share, dhi - dlo)
                return _clamp_place(m, ell, dlo, dhi, a)
            if ext == "fill" and share > hi - lo:
                extra = share - (hi - lo)
                xlo = dlo if not ext_chars else max(dlo, lo - ext_chars)
                xhi = dhi if not ext_chars else min(dhi, hi + ext_chars)
                before = beta * extra
                s, e = lo - before, hi + (extra - before)
                if s < xlo:
                    e, s = e + (xlo - s), xlo
                if e > xhi:
                    s, e = max(xlo, s - (e - xhi)), xhi
                return s, e
        ell = min(share, hi - lo)
        return _clamp_place(m, ell, lo, hi, a)

    def seeds_of(items):
        out = []
        lead_docs = []
        for it in items:
            own = []
            if mix is not None:
                if mix[0] > 0:
                    own.append({"it": it, "kind": "match", "m": it["lo"], "alpha": 0.0, "w": mix[0]})
                if mix[1] > 0:
                    own.append({"it": it, "kind": "match", "m": it["m"], "alpha": alpha, "w": mix[1]})
            else:
                if anchor == "start":
                    m, a = it["lo"], 0.0
                elif isinstance(anchor, (int, float)) and not isinstance(anchor, bool):
                    # window start, unless the match point lies more than `anchor` characters in
                    m, a = (it["lo"], 0.0) if it["m"] - it["lo"] <= anchor else (it["m"], alpha)
                elif anchor == "mid":
                    m, a = (it["lo"] + it["hi"]) / 2, 0.5
                else:
                    m, a = it["m"], alpha
                own.append({"it": it, "kind": "match", "m": m, "alpha": a, "w": 1.0})
            if lead > 0 and it["source"] not in lead_docs and len(lead_docs) < lead_ranks:
                lead_docs.append(it["source"])
                if lead_space == "firstwin":
                    # cheap lead: the start of this document's window that begins at the document start
                    host = next((x for x in items if x["source"] == it["source"] and x["at_start"]), None)
                    if host is not None and host is not it:
                        out.append({"it": host, "kind": "match", "m": host["lo"], "alpha": 0.0,
                                    "w": it["w"] * lead})
                else:
                    own.append({"it": it, "kind": "lead", "w": lead})
            tot = sum(sd["w"] for sd in own) if norm_seeds else (sum(sd["w"] for sd in own if sd["kind"] != "lead") or 1.0)
            for sd in own:
                sd["w"] = it["w"] * sd["w"] / tot
            out += own
            if preview > 0 and it["source"] not in {o["it"]["source"] for o in out if o["kind"] == "preview"}:
                out.append({"it": it, "kind": "preview", "w": 1.0})   # fast, saturates at `preview` chars
        return out

    def layout(seeds, t):
        """Display units at growth time t: list of (key, best_rank, space, [pieces], title_len)."""
        units = {}
        order = []
        for sd in seeds:
            it = sd["it"]
            s, e = grow(sd, sd["w"] * t)
            s, e = int(s), int(e)
            if e <= s:
                continue
            key = ("doc", it["source"]) if (merge and it["space"] == "doc") else ("res", it["rank"])
            if key not in units:
                units[key] = {"rank": it["rank"], "space": it["space"], "pieces": [], "source": it["source"],
                              "tlen": it["tlen"], "dlo": it["dlo"], "heading_first": it["heading_first"]}
                order.append(key)
            u = units[key]
            u["rank"] = min(u["rank"], it["rank"])
            u["pieces"].append((s, e))
        out = []
        seen_src = set()
        for key in sorted(order, key=lambda k: units[k]["rank"]):
            u = units[key]
            ps = sorted(u["pieces"])
            merged = [list(ps[0])]
            for s, e in ps[1:]:
                if s <= merged[-1][1] + (gap_fill if u["space"] == "doc" else 0):
                    merged[-1][1] = max(merged[-1][1], e)
                else:
                    merged.append([s, e])
            at_doc_start = u["space"] == "doc" and merged[0][0] <= u["dlo"]
            if title == "never":
                tl = 0
            elif title == "always":
                tl = u["tlen"]
            elif title == "auto":   # no title when the display opens with the document's own heading
                tl = 0 if (at_doc_start and u["heading_first"]) else u["tlen"]
            else:   # "mid": no title when the display starts at the document start
                tl = 0 if at_doc_start else u["tlen"]
            if merge and u["space"] == "window" and u["source"] in seen_src:
                tl = 0          # same document shown just above: its title already printed
            seen_src.add(u["source"])
            out.append((key, u["rank"], u["space"], [tuple(p) for p in merged], tl, u["source"]))
        return out

    def cost(units):
        return sum(tl + sum(e - s for s, e in ps) + GAP_LEN * (len(ps) - 1) for _, _, _, ps, tl, _ in units)

    def solve(seeds, cap):
        t_hi = max((sd["it"]["dhi"] - sd["it"]["dlo"] + 1) / sd["w"] for sd in seeds)
        if cost(layout(seeds, t_hi)) <= cap:
            return t_hi
        lo, hi = 0.0, t_hi
        for _ in range(50):
            mid = (lo + hi) / 2
            if cost(layout(seeds, mid)) <= cap:
                lo = mid
            else:
                hi = mid
        return lo

    def policy(query, results, cap):
        res = results[:n_max]
        if not res:
            return []
        items = [_prepare(r, use_doc) for r in res]
        if weight_by == "doc":
            docs, members = [], {}
            for it in items:
                if it["source"] not in members:
                    docs.append(it["source"])
                    members[it["source"]] = []
                members[it["source"]].append(it)
            for d, src in enumerate(docs):
                ms = members[src]
                z = sum(member_decay ** k for k in range(len(ms)))
                for k, it in enumerate(ms):
                    it["w"] = decay ** d * member_decay ** k / z
        else:
            for i, it in enumerate(items):
                it["w"] = (weights[i] if weights and i < len(weights) else decay ** i)
        # a zero-speed result only shows through its document's other results (merge)
        items = [it for it in items if it["w"] > 0]
        while True:
            seeds = seeds_of(items)
            seeded = {id(sd["it"]) for sd in seeds}
            items = [it for it in items if id(it) in seeded]
            if not items:
                return []
            t = solve(seeds, cap)
            drop = None
            for it in reversed(items):
                own = [sd for sd in seeds if sd["it"] is it]
                tot = sum(sd["w"] for sd in own) * t
                s, e = grow(own[0], own[0]["w"] * t)
                full = (e - s) >= (it["hi"] - it["lo"]) - 1
                if tot < min_len and not full:
                    drop = it
                    break
            if drop is None or len(items) == 1:
                break
            items = [it for it in items if it is not drop]
        units = layout(seeds, t)
        if merge:   # same-document displays stay together, in order of the document's best rank
            first = {}
            for u in units:
                first.setdefault(u[5], u[1])
            units.sort(key=lambda u: (first[u[5]], u[1]))
        out = []
        for key, rank, space, ps, tl, _ in units:
            if snap:
                r = results[rank]
                src = r["text"] if space == "window" else (r["doc_text"] or "")
                ps = [_snap(src, a, b, snap) for a, b in ps]
            out.append({"rank": rank, "pieces": ps, "space": space, "title": tl > 0})
        return out

    return policy


# ── named policies (see the findings for the comparison) ──────────────
# Shared choices: decay 0.45 (shares 1 : 0.45 : 0.2 : ...), min_len 200, the first 5 results,
# title line unless the display opens with the document's own heading.

# Strongest simple baseline (cheap): each result's window from its start, a rank-decayed share
# of the cap, unused share redistributed; no document-level feature.
start_window = make(decay=0.45, anchor="start", ext="none", merge=False, doc_space=False, title="auto")

# Document-level, cheap (no text outside the windows): one title per document, budget by
# document rank (a document's share goes 1 : 0.25 : ... to its windows in rank order).
doc_merge_cheap = make(decay=0.45, anchor="start", ext="none", merge=True, doc_space=False,
                       weight_by="doc", member_decay=0.25, title="auto")

# Document-level (doc_text): as doc_merge_cheap, in document coordinates, and a window that is
# shorter than its share grows into the adjacent document text (half before, half after).
doc_extend = make(decay=0.45, anchor="start", ext="fill", merge=True, weight_by="doc",
                  member_decay=0.25, title="auto")

# Document-level (doc_text), one seed per document: each top document grows from the start of
# its best window into the document; the top document also shows its opening (lead 0.5).
doc_one_lead = make(decay=0.45, anchor="start", ext="fill", merge=True, weight_by="doc",
                    member_decay=0.0, lead=0.5, title="auto")

# doc_one_lead with a preview floor: every document among the first 10 results gets at least
# the first 150 characters of its best window (plus title), the rest grows as in doc_one_lead.
doc_one_lead_preview = make(decay=0.45, anchor="start", ext="fill", merge=True, weight_by="doc",
                            member_decay=0.0, lead=0.5, title="auto", preview=150, n_max=10)

# The same document-level features on B''s anchor (the match point, 35% of growth before it).
match_doc_lead = make(decay=0.45, alpha=0.35, ext="fill", merge=True, weight_by="doc",
                      member_decay=0.0, lead=0.5, title="auto")

# Contrast only (not recommended): every document from its first character, ignoring the match.
doc_head = make(decay=0.45, mix=(0, 0), lead=1.0, lead_ranks=99, norm_seeds=True, ext="fill",
                merge=True, weight_by="doc", member_decay=0.0, title="auto")


def bprime_capped(query, results, cap):
    """B' (match point, 1,000 characters per result), stopped at the cap: the last result is cut short."""
    out, used = [], 0
    for r in results:
        off = r["match_offset"] or 0
        tl = _title_len(r) if (off and r["title"]) else 0
        room = min(1000, cap - used) - tl
        if room < 100:
            break
        out.append({"rank": r["rank"], "pieces": [(off, off + room)], "title": bool(tl)})
        used += tl + min(room, len(r["text"]) - off)
    return out
