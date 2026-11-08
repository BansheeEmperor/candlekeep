"""What the search tool shows the agent: an answer-focused display within one character budget.

A search returns ranked results, each an Arcane Recall window. The answer the agent needs is
mostly in the top document, but often outside the 1,000 characters after the matched chunk
that a per-result view shows: before the match, further down, or outside the window (research
diary Entries 63 and 64). This display spends one budget for the whole search:

1. Groups. Results of the same document are pooled; documents keep the order of their best
   rank.
2. Passages. Every passage (paragraph, sentence of a long paragraph, list item, table, code
   block) gets points: query words it contains (0.5 x share), query words that are not in the
   document's title or file name (1.5 x share), the first passage of a section (+0.3), its
   position in the document (+1.5 in the first 1,000 characters, +0.75 up to 3,000), code
   (-1). The top document is read as a whole (all its chunks, stitched); the others offer only
   their windows.
3. Selection. Passages are taken in order of points, each with its section heading, while the
   document's share of the budget allows; gaps of up to 40 characters are shown instead of a
   gap marker; the first passage that does not fit may be shown cut, once. The top result's
   matched chunk (its first 300 characters) is always shown.
4. Allocation (the Freynan Mirror). Each document's relevance r is the query's cosine to its best
   stored chunk embedding (Arcane Recall's `_doc_relevance`). A document gets no budget when r
   is below the floor: the higher of an absolute floor (`min_relevance`) and the most relevant
   document's r minus a gap (`relevance_gap`). Every document above the floor gets up to 200
   characters, and the rest goes by weight WMIN + (1 - WMIN) * ((r - floor) / (r_max - floor))^2,
   so documents of almost equal relevance get almost equal shares; what a document cannot use is
   passed on. When no document reaches the absolute floor, only the top result's matched chunk is
   shown. Without relevance scores (a result without stored embeddings), the split is by
   document rank instead: weight 0.1^k, so the top document gets nearly all of it ("lead +
   teasers").

The constants were chosen on half of the evaluation's questions and confirmed on the other half
(Entries 64 and 67); they are frozen here. Displayed text (title lines, passages and gap markers)
never exceeds the budget; per-result header lines are not counted.
"""
from __future__ import annotations

import re

GAP = "\n[…]\n"
GAP_LEN = len(GAP)
FLOOR = 200            # characters every document can get
WEIGHT = 0.1           # without relevance scores: share of the rest by document rank, WEIGHT ** k
SHARPEN = 2.0          # the relevance split's exponent (cosines are compressed)
WMIN = 0.05            # the least weight of a document above the relevance floor
MUST = 300             # characters of the top result's matched chunk that are always shown
CLOSE = 40             # gaps up to this many characters are shown instead of a marker
MIN_BUDGET = 150       # a document's share below this is not shown
MIN_CUT = 60           # the shortest cut passage worth showing
POINTS = dict(lex=0.5, rlex=1.5, lead=0.3, doc=1.5, doc2=0.75, doc_len=1000, doc_len2=3000, code=1.0)
STOP = set("a an and are as at be by can do does for from has have how i in is it its of on or that the this to "
           "was what when where which who why will with you your vs versus about into than then there these those "
           "should would could my we our".split())
_PREFIX = re.compile(r"Document: [^\n]*\n\n")


# ── text ─────────────────────────────────────────────────────────────

def words(s: str) -> set:
    return {w for w in re.findall(r"[a-z0-9][a-z0-9\-\.]*[a-z0-9]|[a-z0-9]", s.lower()) if w not in STOP and len(w) > 1}


def _has_word(w: str, sw: set) -> bool:
    return w in sw or (len(w) >= 5 and any(x.startswith(w[:5]) for x in sw))


def _share(qw, text: str) -> float:
    if not qw:
        return 0.0
    sw = words(text)
    return sum(1 for w in qw if _has_word(w, sw)) / len(qw)


def segment(text: str, prefix_len: int) -> list:
    """Passages of a text as (start, end, kind): prefix, heading, para, sentence (of a paragraph
    over 400 characters), list (item), table, code (fenced block)."""
    out = []
    if prefix_len:
        out.append((0, prefix_len, "prefix"))
    i, n = prefix_len, len(text)
    while i < n:
        while i < n and text[i] in "\n ":
            i += 1
        if i >= n:
            break
        if text.startswith("```", i):
            j = text.find("\n```", i + 3)
            j = n if j < 0 else min(n, j + 4)
            out.append((i, j, "code"))
            i = j
            continue
        j = text.find("\n\n", i)
        j = n if j < 0 else j
        block = text[i:j]
        if block.lstrip().startswith("#"):
            nl = block.find("\n")
            if nl < 0:
                out.append((i, j, "heading"))
                i = j
                continue
            out.append((i, i + nl, "heading"))
            i = i + nl + 1
            continue
        if block.lstrip().startswith("|"):
            out.append((i, j, "table"))
        elif re.match(r"(\s*([-*+]|\d+[.)])\s)", block):
            k = i
            for line in re.split(r"(?<=\n)", block):
                if line.strip():
                    out.append((k, k + len(line.rstrip("\n")), "list"))
                k += len(line)
        elif len(block) > 400:
            k = i
            for sent in re.split(r"(?<=[.!?])\s+", block):
                pos = text.find(sent, k)
                if pos < 0:
                    continue
                out.append((pos, pos + len(sent), "sentence"))
                k = pos + len(sent)
        else:
            out.append((i, j, "para"))
        i = j
    return [(a, b, k) for a, b, k in out if b > a]


def _sections(segs):
    """(start, end, kind, index in its section (-1 for a heading), index of its section heading)."""
    out, idx, head = [], 0, None
    for i, (a, b, k) in enumerate(segs):
        if k == "heading":
            idx, head = 0, i
            out.append((a, b, k, -1, i))
            continue
        out.append((a, b, k, idx, head))
        idx += 1
    return out


def _merge(pieces):
    out = []
    for a, b in sorted((int(a), int(b)) for a, b in pieces if b > a):
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def _body_cost(pieces) -> int:
    ps = _merge(pieces)
    return sum(b - a for a, b in ps) + GAP_LEN * max(0, len(ps) - 1)


def _close_gaps(pieces, text, limit):
    out = []
    for a, b in _merge(pieces):
        if out and (a - out[-1][1] <= limit or not text[out[-1][1]:a].strip()):
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return out


def _waterfill(demands, weights, total):
    """Split total in proportion to weights; nobody above its demand; the rest goes on."""
    alloc = [0.0] * len(demands)
    act = [i for i in range(len(demands)) if demands[i] > 0 and weights[i] > 0]
    rem = float(total)
    while act and rem > 1e-9:
        ws = sum(weights[i] for i in act)
        done = [i for i in act if demands[i] - alloc[i] <= rem * weights[i] / ws]
        if not done:
            for i in act:
                alloc[i] += rem * weights[i] / ws
            break
        for i in done:
            rem -= demands[i] - alloc[i]
            alloc[i] = float(demands[i])
        act = [i for i in act if i not in done]
    return alloc


# ── results ──────────────────────────────────────────────────────────

def items_of(results) -> list:
    """The display's view of SearchResults (rank order)."""
    out = []
    for rank, r in enumerate(results):
        m = r.metadata or {}
        text = r.text or ""
        pl = m.get("_prefix_len")              # Arcane Recall's header length; else the Bardic prefix line
        if not isinstance(pl, int) or not 0 <= pl <= len(text):
            mm = _PREFIX.match(text)
            pl = mm.end() if mm else 0
        span = m.get("_doc_span")
        out.append({"rank": rank, "doc": m.get("source") or m.get("filename") or "",
                    "source": m.get("filename") or m.get("source") or "", "score": r.score, "text": text,
                    "prefix_len": pl, "match_offset": m.get("_match_offset", 0) or 0, "title": m.get("title"),
                    "doc_text": m.get("_doc_text"), "doc_span": tuple(span) if span else None,
                    "relevance": m.get("_doc_relevance")})
    return out


def _title_len(r) -> int:
    return len(f"Document: {r['title'] or r['source']}\n\n") if r.get("title") else 0


def _aligned(r) -> bool:
    """The window body is doc_text[doc_span], whitespace aside."""
    ds, doc = r.get("doc_span"), r.get("doc_text")
    if not ds or not doc:
        return False
    a, b = ds
    return re.sub(r"\s+", "", r["text"][r["prefix_len"]:]) == re.sub(r"\s+", "", doc[a:b])


def _to_doc(r, x):
    return r["doc_span"][0] + max(0, x - r["prefix_len"])


def _at_doc_start(r) -> bool:
    ds = r.get("doc_span")
    return bool(ds) and ds[0] < 5


def _residual(query: str, r) -> list:
    """Query content words that are not in the result's title or file name."""
    tw = words(r.get("title") or "") | words(r["source"].rsplit(".", 1)[0].replace("-", " ").replace("_", " "))
    return sorted(w for w in words(query) if not _has_word(w, tw))


def _points(kind, idx, doff, lex, res) -> float:
    p = POINTS["lex"] * lex + POINTS["rlex"] * res
    if idx == 0:
        p += POINTS["lead"]
    if doff is not None:
        if doff < POINTS["doc_len"]:
            p += POINTS["doc"]
        elif doff < POINTS["doc_len2"]:
            p += POINTS["doc2"]
    if kind == "code":
        p -= POINTS["code"]
    return p


class _Group:
    """One document's results: candidate passages with points, and the greedy selection within a
    budget. The top document is read as a whole when its windows align with its text ("doc");
    otherwise a group shows pieces of its windows ("window", one display per window)."""

    def __init__(self, wins, query, is_top):
        self.wins = wins
        self.r = min(wins, key=lambda w: w["rank"])
        self.space = "doc" if is_top and all(_aligned(w) for w in wins) else "window"
        qw = words(query)
        rw = _residual(query, self.r)
        self.cands = []          # (unit, start, end, kind, heading start, heading end, points, distance to a match)
        if self.space == "doc":
            doc = self.text = self.r["doc_text"]
            anchors = [_to_doc(w, max(w["match_offset"] or w["prefix_len"], w["prefix_len"])) for w in wins]
            segs = _sections(segment(doc, 0))
            for a, b, kind, idx, head in segs:
                if kind == "heading":
                    continue
                t = doc[a:b]
                p = _points(kind, idx, a, _share(qw, t), _share(rw, t) if rw else 0.0)
                h = segs[head] if head is not None else None
                self.cands.append((0, a, b, kind, h[0] if h else None, h[1] if h else None, p,
                                   min(abs(a - m) for m in anchors)))
        else:
            self.text = None
            for wi, w in enumerate(wins):
                pl, text = w["prefix_len"], w["text"]
                mo = max(w["match_offset"] or pl, pl)
                segs = _sections([s for s in segment(text, pl) if s[2] != "prefix"])
                for a, b, kind, idx, head in segs:
                    if kind == "heading":
                        continue
                    if _at_doc_start(w):
                        doff = a - pl
                    elif w.get("doc_span"):
                        doff = _to_doc(w, a)
                    else:
                        doff = None
                    t = text[a:b]
                    p = _points(kind, idx, doff, _share(qw, t), _share(rw, t) if rw else 0.0)
                    h = segs[head] if head is not None else None
                    self.cands.append((wi, a, b, kind, h[0] if h else None, h[1] if h else None, p, abs(a - mo)))
        self.cands.sort(key=lambda c: (-c[6], c[7], c[0], c[1]))
        self.sel = {}
        self.must = None
        top = next((w for w in wins if w["rank"] == 0), None)
        if top is not None:
            mo = max(top["match_offset"] or top["prefix_len"], top["prefix_len"])
            end = min(len(top["text"]), mo + MUST)
            if end > mo:
                self.must = ((0, _to_doc(top, mo), _to_doc(top, end)) if self.space == "doc"
                             else (wins.index(top), mo, end))

    def _unit_text(self, u):
        return self.text if self.space == "doc" else self.wins[u]["text"]

    def _unit_order(self, u):
        if self.space == "doc":
            return (0, 0)
        w = self.wins[u]
        return ((w.get("doc_span") or (10 ** 9,))[0], w["rank"])

    def cost_of(self, sel) -> int:
        total, first = 0, True
        for u in sorted(sel, key=self._unit_order):
            if sel[u]:
                total += _body_cost(sel[u]) + (_title_len(self.r) if first else 0)
                first = False
        return total

    def demand(self) -> int:
        if self.space == "doc":
            return len(self.text) + _title_len(self.r)
        return sum(len(w["text"]) - w["prefix_len"] for w in self.wins) + _title_len(self.r)

    def fill(self, budget: int) -> int:
        sel = {}
        if self.must:
            u, a, b = self.must
            if self.cost_of({u: [(a, b)]}) <= budget:
                sel = {u: [(a, b)]}
        cut_done = False
        for u, a, b, kind, ha, hb, _p, _d in self.cands:
            add = [(a, b)] + ([(ha, hb)] if ha is not None else [])
            trial = dict(sel)
            trial[u] = _close_gaps(sel.get(u, []) + add, self._unit_text(u), CLOSE)
            if self.cost_of(trial) <= budget:
                sel = trial
            elif not cut_done:
                cut_done = True
                cur = self.cost_of(sel)
                room = budget - cur - (GAP_LEN if sel.get(u) else (0 if cur else _title_len(self.r)))
                if room >= MIN_CUT and kind in ("para", "sentence", "list"):
                    trial = dict(sel)
                    trial[u] = _close_gaps(sel.get(u, []) + [(a, a + room)], self._unit_text(u), CLOSE)
                    if self.cost_of(trial) <= budget:
                        sel = trial
        self.sel = sel
        return self.cost_of(sel)

    def displays(self) -> list:
        out, first = [], True
        for u in sorted(self.sel, key=self._unit_order):
            if self.sel[u]:
                w = self.r if self.space == "doc" else self.wins[u]
                out.append({"rank": w["rank"], "pieces": _merge(self.sel[u]), "space": self.space,
                            "title": bool(self.r.get("title")) and first})
                first = False
        return out


def _relevance_split(groups, min_relevance, relevance_gap):
    """The Freynan Mirror: (the groups kept, their weights), or None when a document has no
    relevance score. No group kept: nothing reaches the absolute floor."""
    rel = [min(g, key=lambda r: r["rank"]).get("relevance") for g in groups]
    if any(not isinstance(v, (int, float)) for v in rel):
        return None
    floors = [f for f in (min_relevance, max(rel) - relevance_gap if relevance_gap is not None else None)
              if f is not None]
    floor = max(floors) if floors else None
    keep = [k for k in range(len(groups)) if floor is None or rel[k] >= floor]
    if not keep:
        return [], []
    top = max(rel[k] for k in keep)
    base = floor if floor is not None and floor < top else min(rel[k] for k in keep) - 1e-6
    span = top - base
    weights = [WMIN + (1 - WMIN) * ((rel[k] - base) / span) ** SHARPEN if span > 1e-9 else 1.0 for k in keep]
    return [groups[k] for k in keep], weights


def select(query: str, items: list, budget: int, min_relevance: float | None = None,
           relevance_gap: float | None = None) -> list:
    """The displays for one search: [{rank, pieces, space ("doc" or "window"), title}], in order.
    min_relevance / relevance_gap: the Freynan Mirror's absolute and relative floors (None: none)."""
    if not items:
        return []
    by = {}
    for r in items:
        by.setdefault(r["doc"], []).append(r)
    groups = sorted((sorted(g, key=lambda r: ((r.get("doc_span") or (10 ** 9,))[0], r["rank"])) for g in by.values()),
                    key=lambda g: min(r["rank"] for r in g))
    split = _relevance_split(groups, min_relevance, relevance_gap)
    if split is None:
        weights = [WEIGHT ** k for k in range(len(groups))]
    else:
        kept, weights = split
        if not kept:                         # nothing is relevant enough: the top result's matched chunk only
            top = _Group(groups[0], query, True)
            if top.must is None:
                return []
            u, a, b = top.must
            top.sel = {u: [(a, b)]} if top.cost_of({u: [(a, b)]}) <= budget else {}
            return top.displays()
        groups = kept
    G = [_Group(g, query, k == 0) for k, g in enumerate(groups)]
    dem = [g.demand() for g in G]
    base = [min(FLOOR, d) for d in dem]
    for k, g in enumerate(G):
        if g.must is not None:
            base[k] = max(base[k], min(MUST + _title_len(g.r) + 100, dem[k]))
    extra = _waterfill([d - b for d, b in zip(dem, base)], weights, max(0, budget - sum(base)))
    shown, remaining = {}, budget
    for k, g in enumerate(G):
        target = int(base[k] + extra[k])
        if target < MIN_BUDGET or remaining < MIN_BUDGET:
            continue
        c = g.fill(min(target, remaining))
        if c:
            shown[k] = c
            remaining -= c
    if remaining > 50:                       # what is left goes back to the documents in order
        for k in sorted(shown):
            g, c, saved = G[k], shown[k], G[k].sel
            c2 = g.fill(c + remaining)
            if c < c2 <= c + remaining:
                remaining -= c2 - c
                shown[k] = c2
            else:
                g.sel = saved
            if remaining <= 50:
                break
    if not shown and G[0].fill(budget):      # every document is shorter than MIN_BUDGET: show the first
        shown[0] = G[0].cost_of(G[0].sel)
    out = []
    for k in sorted(shown):
        out += G[k].displays()
    return out


def render(items: list, displays: list) -> str:
    blocks = []
    for d in displays:
        r = items[d["rank"]]
        src = r["text"] if d["space"] == "window" else (r["doc_text"] or "")
        body = GAP.join(src[max(0, a):min(len(src), b)] for a, b in d["pieces"])
        title = f"Document: {r['title'] or r['source']}\n\n" if d["title"] else ""
        blocks.append(f"**Score: {r['score']:.3f}** | Source: {r['source']}\n```\n{title}{body}\n```\n")
    return "\n".join(blocks)


def render_results(query: str, results, budget: int, min_relevance: float | None = None,
                   relevance_gap: float | None = None) -> str:
    """The search tool's output for results (SearchResults in rank order) within budget characters."""
    items = items_of(results)
    return render(items, select(query, items, budget, min_relevance, relevance_gap))
