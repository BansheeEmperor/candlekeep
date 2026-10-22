"""Combined display policies (axis "combined") for view_sim.py.

The explorers' ideas stacked into one factory, `make(...)`. The named policies at the bottom are the
ones reported; the factory options they do not use are kept because the findings cite them
(ablations and negative results).

How a policy builds its display (per search, within `cap` displayed characters)
  1 groups      The results are grouped by document (windows of the same source pooled, kept in
                document order). Documents come in order of their best rank (or of a relevance key).
  2 points      Every body segment of a group gets select_res's cheap points (select_cheap axis):
                  0.5 * lex + 1.5 * (share of the query's residual words: content words that are not
                  in the document's title or file name) + 0.3 if it is the first segment of its
                  section + 1.5 when it starts in the document's first 1,000 characters (0.75 up to
                  3,000) - 1 for code.
                The document-start prior uses the segment's offset in its DOCUMENT: in window space
                it applies to the window that holds the document start and, with doc_offsets, to any
                window by its position in the document (the server knows it from chunk indices).
  3 space       "window": a group shows pieces of its windows only (one display per window, one title
                line per document). "doc": a group shows pieces of the whole document text (doc_text,
                segmented as view_sim does), so it can show text outside its windows, e.g. the
                document's opening or a passage that holds the query's residual words.
  4 must piece  must_match = L: the top result's matched chunk, [match_offset, match_offset + L), is
                always shown first (the hedge against a position prior hiding what the search found).
  5 selection   Greedy by points inside the group's budget: each segment comes with its section heading,
                gaps of at most `close` characters are shown instead of a marker, document order is
                kept; the first segment that does not fit may be shown cut, once.
  6 allocation  Water-filling over the groups: each group first gets min(floor, demand), then the rest
                of the cap by weight (geometric w**k by document rank, optionally times 1 + ds_boost when
                one of its windows holds the document start), no group above its demand; what a group
                cannot use goes back to the groups in order. The reported policies use floor 200 and
                w = 0.1 ("lead + teasers": the top document gets nearly everything, every other
                document a 200-character teaser).

Displayed text is counted exactly as view_sim.render counts it (title lines, pieces, gap markers).
Policies use only their arguments; standard library only; deterministic.

Reported policies (dev split, cap 4,000; CEN facts_share (facts_all) hybrid / precise / explore;
B' as shipped: 38.6 (5) / 22.2 (1) / 36.6 (4); 0 violations and a 4,000 maximum for all three)
  doc_select_ce  [ce + doc]  79.9 (23) / 76.3 (21) / 74.0 (21)   CEN-G 77.0 (22) / 74.0 (21) / 71.6 (20)
  doc_select     [doc]       73.7 (21) / 74.2 (21) / 72.2 (21)   CEN-G 77.0 (22) / 74.0 (21) / 74.6 (21)
  win_select     [cheap]     70.6 (18) / 73.7 (20) / 50.6 (7)    CEN-G 71.2 (18) / 72.8 (20) / 48.3 (8)
Cost classes: "cheap" = lex, structure, offsets, lengths, ranks and window text only; "doc" = also the
top document's text beyond its windows (Arcane Recall's expand_results already fetches every chunk of
each result's document, get_chunks_by_source); "ce" = one cross-encoder call per segment of every
returned window. The dev JSONs and the analysis are in the combined axis's scratch folder.
"""
from __future__ import annotations

import re

GAP = "\n[…]\n"
GAP_LEN = len(GAP)
STOP = set("a an and are as at be by can do does for from has have how i in is it its of on or that the this to "
           "was what when where which who why will with you your vs versus about into than then there these those "
           "should would could my we our".split())


# ── accounting (as view_sim.render counts the displayed text) ─────────

def title_len(r) -> int:
    return len(f"Document: {r['title'] or r['source']}\n\n") if r.get("title") else 0


def merge(pieces):
    out = []
    for a, b in sorted((int(a), int(b)) for a, b in pieces if b > a):
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def body_cost(pieces) -> int:
    ps = merge(pieces)
    return sum(b - a for a, b in ps) + GAP_LEN * max(0, len(ps) - 1)


def close_gaps(pieces, text, limit):
    """Join pieces whose gap is whitespace only or at most `limit` characters."""
    out = []
    for a, b in merge(pieces):
        if out and (a - out[-1][1] <= limit or not text[out[-1][1]:a].strip()):
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return out


# ── text features (computed as view_sim computes them) ───────────────

def words(s: str) -> set:
    return {w for w in re.findall(r"[a-z0-9][a-z0-9\-\.]*[a-z0-9]|[a-z0-9]", s.lower()) if w not in STOP and len(w) > 1}


def has_word(w: str, sw: set) -> bool:
    return w in sw or (len(w) >= 5 and any(x.startswith(w[:5]) for x in sw))


def lexical(query_words: set, seg: str) -> float:
    """view_sim.lexical: share of the query's content words found in the segment."""
    if not query_words:
        return 0.0
    sw = words(seg)
    return sum(1 for w in query_words if has_word(w, sw)) / len(query_words)


def residual_words(query: str, r) -> list:
    """Query content words that are not in the result's title or file name."""
    tw = words(r.get("title") or "") | words(r["source"].rsplit(".", 1)[0].replace("-", " ").replace("_", " "))
    return sorted(w for w in words(query) if not has_word(w, tw))


def segment(text: str, prefix_len: int):
    """view_sim.segment: prefix, headings, paragraphs (long ones split into sentences), list items,
    table blocks and fenced code blocks, as (start, end, kind)."""
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
        first = block.lstrip()
        if first.startswith("#"):
            nl = block.find("\n")
            if nl < 0:
                out.append((i, j, "heading"))
                i = j
                continue
            out.append((i, i + nl, "heading"))
            i = i + nl + 1
            continue
        if first.startswith("|"):
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


def at_doc_start(r) -> bool:
    """The window holds the document's first chunk (server: Arcane Recall's chunk index 0)."""
    ds = r.get("doc_span")
    return bool(ds) and ds[0] < 5


def doc_aligned(r) -> bool:
    """The window body is doc_text[doc_span], whitespace aside (99% of results)."""
    ds, doc = r.get("doc_span"), r.get("doc_text")
    if not ds or not doc:
        return False
    a, b = ds
    return re.sub(r"\s+", "", r["text"][r["prefix_len"]:]) == re.sub(r"\s+", "", doc[a:b])


def to_doc(r, x):
    """Document offset of window position x (approximate by whitespace)."""
    return r["doc_span"][0] + max(0, x - r["prefix_len"])


def sections(segs):
    """Annotate segments in place: sec, idx (index of a body segment in its section; -1 for a
    heading) and head (index of its section heading)."""
    sec_id, idx, head = -1, 0, None
    for i, s in enumerate(segs):
        if s["kind"] == "heading":
            sec_id, idx, head = sec_id + 1, 0, i
            s.update(sec=sec_id, idx=-1, head=i)
            continue
        if sec_id < 0:
            sec_id = 0
        s.update(sec=sec_id, idx=idx, head=head)
        idx += 1
    return segs


def heading_level(text: str, a: int) -> int:
    t = text[a:a + 12].lstrip()
    return len(t) - len(t.lstrip("#")) or 1


def top_level(levels) -> int:
    """A document's top section level: the smallest heading level, unless only one heading has it
    (a title), then the next one."""
    if not levels:
        return 0
    lv = sorted(set(levels))
    if len(lv) > 1 and levels.count(lv[0]) == 1:
        return lv[1]
    return lv[0]


# ── a group: one document's windows and their selection ──────────────

PTS = dict(a_lex=0.5, a_rlex=1.5, a_lead=0.3, a_doc=1.5, a_doc2=0.75, doc_len=1000, doc_len2=3000, code_pen=1.0)


class Group:
    """Candidate segments of one group (a document's windows) with points, and the greedy
    selection within a budget. Space "doc": one display of doc_text; "window": one display per
    window (title line on the first one)."""

    def __init__(self, wins, query, cfg, is_top):
        self.wins = wins
        self.cfg = cfg
        self.r = min(wins, key=lambda w: w["rank"])          # the document's best-ranked window
        want_doc = cfg["space"] == "doc" and (not cfg.get("doc_top_only") or is_top)
        self.space = "doc" if want_doc and all(doc_aligned(w) for w in wins) else "window"
        pk = dict(PTS, **cfg.get("pts", {}))
        qw = words(query)
        res_w = residual_words(query, self.r) if pk["a_rlex"] else []
        self.cands = []          # (unit, start, end, kind, head_start, head_end, points, distance to a match)
        if self.space == "doc":
            self._doc_cands(qw, res_w, pk, is_top)
        else:
            self._win_cands(res_w, pk, is_top)
        if cfg.get("seg_order") == "pos":                 # comparator: plain document order
            self.cands.sort(key=lambda c: (c[0], c[1]))
        else:
            self.cands.sort(key=lambda c: (-c[6], c[7], c[0], c[1]))
        self.sel = {}
        self.must = None                                    # (unit, start, end), shown first
        L = cfg.get("must_match", 0)
        has_top = any(w["rank"] == 0 for w in wins)          # holds the search's top result
        if L and (has_top or cfg.get("match_scope", "top") == "all"):
            w = next(w for w in wins if w["rank"] == 0) if has_top else self.r
            mo = max(w["match_offset"] or w["prefix_len"], w["prefix_len"])
            end = min(len(w["text"]), mo + L)
            if end > mo:
                self.must = (0, to_doc(w, mo), to_doc(w, end)) if self.space == "doc" else (self.wins.index(w), mo, end)

    # points --------------------------------------------------------------
    def _points(self, kind, idx, doff, inwin, ce_hit, match_hit, pk, lexv, resv, top_lead=False):
        p = pk["a_lex"] * lexv + pk["a_rlex"] * resv
        if idx == 0:
            p += pk["a_lead"]
            if top_lead:
                p += self.cfg.get("a_top", 0.0)
        if doff is not None:
            if doff < pk["doc_len"]:
                p += pk["a_doc"]
            elif doff < pk["doc_len2"]:
                p += pk["a_doc2"]
        if kind == "code":
            p -= pk["code_pen"]
        if inwin:
            p += self.cfg.get("a_win", 0.0)
        if ce_hit:
            p += self.cfg.get("a_ce", 0.0)
        if match_hit:
            p += self.cfg.get("a_match", 0.0)
        return p

    def _ce_sets(self):
        """Per window: its segments within ce_delta of the window's best logit (if that is >= ce_floor)."""
        out = []
        d, fl = self.cfg.get("ce_delta"), self.cfg.get("ce_floor", -5.0)
        for w in self.wins:
            body = [s for s in w["segments"] if s["kind"] not in ("prefix", "heading")]
            if d is None or not body:
                out.append([])
                continue
            top = max(s["ce"] for s in body)
            out.append([(s["start"], s["end"]) for s in body if top >= fl and s["ce"] >= top - d])
        return out

    def _match_region(self, is_top):
        """a_match (bonus variant of the hedge): the segments overlapping the best window's matched chunk."""
        if not self.cfg.get("a_match") or (self.cfg.get("match_scope", "top") == "top" and not is_top):
            return None
        w = self.r
        mo = max(w["match_offset"] or w["prefix_len"], w["prefix_len"])
        return w, mo, mo + self.cfg.get("match_len", 300)

    def _doc_cands(self, qw, res_w, pk, is_top):
        doc = self.r["doc_text"]
        self.text = doc
        spans = [tuple(w["doc_span"]) for w in self.wins]
        anchors = [to_doc(w, max(w["match_offset"] or w["prefix_len"], w["prefix_len"])) for w in self.wins]
        ce_doc = [(to_doc(w, a), to_doc(w, b)) for w, cs in zip(self.wins, self._ce_sets()) for a, b in cs]
        mr = self._match_region(is_top)
        mdoc = (to_doc(mr[0], mr[1]), to_doc(mr[0], mr[2])) if mr else None
        restrict = self.cfg.get("restrict", False)
        segs = sections([{"start": a, "end": b, "kind": k} for a, b, k in segment(doc, 0)])
        lv = {i: heading_level(doc, s["start"]) for i, s in enumerate(segs) if s["kind"] == "heading"}
        tl = top_level(list(lv.values()))
        for s in segs:
            if s["kind"] == "heading":
                continue
            a, b = s["start"], s["end"]
            inwin = any(a < y and b > x for x, y in spans)
            if restrict and not inwin:
                continue
            t = doc[a:b]
            resv = 0.0
            if res_w:
                sw = words(t)
                resv = sum(1 for x in res_w if has_word(x, sw)) / len(res_w)
            ce_hit = any(a < y and b > x for x, y in ce_doc)
            m_hit = bool(mdoc) and a < mdoc[1] and b > mdoc[0]
            top = s.get("head") is not None and lv.get(s["head"]) == tl
            p = self._points(s["kind"], s["idx"], a, inwin, ce_hit, m_hit, pk, lexical(qw, t), resv, top)
            h = segs[s["head"]] if s.get("head") is not None else None
            self.cands.append((0, a, b, s["kind"], h["start"] if h else None, h["end"] if h else None, p,
                               min(abs(a - m) for m in anchors)))

    def _win_cands(self, res_w, pk, is_top):
        self.text = None
        ce_sets = self._ce_sets()
        mr = self._match_region(is_top)
        for wi, w in enumerate(self.wins):
            pl = w["prefix_len"]
            ds = at_doc_start(w)
            mo = max(w["match_offset"] or pl, pl)
            segs = sections([dict(s) for s in w["segments"] if s["kind"] != "prefix"])
            lv = {i: heading_level(w["text"], s["start"]) for i, s in enumerate(segs) if s["kind"] == "heading"}
            tl = top_level(list(lv.values()))
            for s in segs:
                if s["kind"] == "heading":
                    continue
                a, b = s["start"], s["end"]
                resv = 0.0
                if res_w:
                    sw = words(w["text"][a:b])
                    resv = sum(1 for x in res_w if has_word(x, sw)) / len(res_w)
                ce_hit = any(a < y and b > x for x, y in ce_sets[wi])
                m_hit = bool(mr) and mr[0] is w and a < mr[2] and b > mr[1]
                if ds:
                    doff = a - pl
                elif self.cfg.get("doc_offsets") and w.get("doc_span"):
                    doff = to_doc(w, a)                     # the window's position in its document
                else:
                    doff = None
                top = s.get("head") is not None and lv.get(s["head"]) == tl
                p = self._points(s["kind"], s["idx"], doff, False, ce_hit, m_hit, pk, s["lex"], resv, top)
                h = segs[s["head"]] if s.get("head") is not None else None
                self.cands.append((wi, a, b, s["kind"], h["start"] if h else None, h["end"] if h else None, p,
                                   abs(a - mo)))

    # costs ---------------------------------------------------------------
    def unit_text(self, u):
        return self.text if self.space == "doc" else self.wins[u]["text"]

    def _unit_order(self, u):
        if self.space == "doc":
            return (0, 0)
        w = self.wins[u]
        return ((w.get("doc_span") or (10 ** 9,))[0], w["rank"])

    def cost_of(self, sel):
        total, first = 0, True
        for u in sorted(sel, key=self._unit_order):
            ps = sel[u]
            if not ps:
                continue
            total += body_cost(ps) + (title_len(self.r) if first else 0)
            first = False
        return total

    def cost(self):
        return self.cost_of(self.sel)

    def demand(self):
        if self.space == "doc":
            return len(self.text) + title_len(self.r)
        return sum(len(w["text"]) - w["prefix_len"] for w in self.wins) + title_len(self.r)

    # selection -----------------------------------------------------------
    def fill(self, budget):
        """Greedy in points order (with `adj`, a candidate next to one already added gains adj
        points); each candidate comes with its section heading and is added while the group fits;
        the first one that does not fit may be shown cut, once."""
        close = self.cfg.get("close", 40)
        adj = self.cfg.get("adj", 0.0)
        sel = {}
        if self.must:
            u, a, b = self.must
            trial = {u: [(a, b)]}
            if self.cost_of(trial) <= budget:
                sel = trial
        partial_done = False
        n = len(self.cands)
        used = [False] * n
        if adj:
            pos = sorted(range(n), key=lambda i: (self.cands[i][0], self.cands[i][1]))
            where = {i: k for k, i in enumerate(pos)}
        boosted = set()
        ptr = 0
        while True:
            while ptr < n and used[ptr]:
                ptr += 1
            pick = ptr if ptr < n else None
            if boosted:
                bi = max(boosted, key=lambda i: (self.cands[i][6] + adj, -i))
                if pick is None or self.cands[bi][6] + adj > self.cands[pick][6]:
                    pick = bi
            if pick is None:
                break
            used[pick] = True
            boosted.discard(pick)
            u, a, b, kind, ha, hb, p, _ = self.cands[pick]
            add = [(a, b)] + ([(ha, hb)] if ha is not None else [])
            trial = dict(sel)
            trial[u] = close_gaps(sel.get(u, []) + add, self.unit_text(u), close)
            if self.cost_of(trial) <= budget:
                sel = trial
                if adj:
                    k = where[pick]
                    for j in (k - 1, k + 1):
                        if 0 <= j < n and not used[pos[j]] and self.cands[pos[j]][0] == u:
                            boosted.add(pos[j])
            elif not partial_done:
                partial_done = True
                cur = self.cost_of(sel)
                room = budget - cur - (GAP_LEN if sel.get(u) else (0 if cur else title_len(self.r)))
                if room >= 60 and kind in ("para", "sentence", "list"):
                    trial = dict(sel)
                    trial[u] = close_gaps(sel.get(u, []) + [(a, a + room)], self.unit_text(u), close)
                    if self.cost_of(trial) <= budget:
                        sel = trial
        self.sel = sel
        return self.cost()

    def displays(self):
        out, first = [], True
        for u in sorted(self.sel, key=self._unit_order):
            ps = self.sel[u]
            if not ps:
                continue
            w = self.r if self.space == "doc" else self.wins[u]
            out.append({"rank": w["rank"], "pieces": merge(ps), "space": self.space,
                        "title": bool(self.r.get("title")) and first})
            first = False
        return out


# ── groups and allocation ────────────────────────────────────────────

def _seg_max(r, f):
    v = [s[f] for s in r["segments"] if s["kind"] not in ("prefix", "heading")]
    return max(v) if v else -99.0


def _desc(r, f):
    return next((s[f] for s in r["segments"] if s["kind"] == "prefix"), -99.0)


def make_groups(results, mode, order):
    """Groups in allocation order. mode "doc": a document's windows together, in document order;
    "result": one group per result. order: "rank" (best rank), "ce" (best segment logit), "emb" (best
    segment cosine), "desc" (cosine of the Bardic prefix: one vector per document)."""
    if mode == "result":
        gs = [[r] for r in results]
    else:
        by = {}
        for r in results:
            by.setdefault(r["source"], []).append(r)
        gs = [sorted(g, key=lambda r: ((r.get("doc_span") or (10 ** 9,))[0], r["rank"])) for g in by.values()]

    def best(g):
        return min(r["rank"] for r in g)
    if order == "rank":
        return sorted(gs, key=best)
    if order in ("ce", "emb"):
        return sorted(gs, key=lambda g: (-max(_seg_max(r, order) for r in g), best(g)))
    if order == "desc":
        return sorted(gs, key=lambda g: (-_desc(g[0], "emb"), best(g)))
    raise ValueError(order)


def waterfill(demands, weights, total):
    """Split `total` in proportion to weights; nobody above its demand; the rest goes on."""
    n = len(demands)
    alloc = [0.0] * n
    act = [i for i in range(n) if demands[i] > 0 and weights[i] > 0]
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


def make(n_max=None, group="doc", space="doc", order="rank", w="harm", ds_boost=1.0, floor=0, n_floor=None,
         min_budget=150, alloc="seq", **cfg):
    """Build a policy.

    n_max      results considered (None: all)
    group      "doc" (pool a document's windows) or "result"
    space      "doc" or "window"; cfg doc_top_only=True: document space for the first group only
    order      document order: "rank", "ce", "emb", "desc"
    alloc      "seq": select_res's walk (group k gets remaining * w_k / sum(w_k..); the walk stops at a
               share under min_budget). "wf": water-filling with a floor per group (the first n_floor
               groups) and weights up to each group's demand.
    w          "harm" 1/(k+1), "equal", or a float r (geometric r**k); times 1 + ds_boost for a group one
               of whose windows holds the document start
    cfg        must_match (L chars of the top result's matched chunk always shown), doc_offsets (window
               space: document-start prior by the window's document offset), pts (point constants),
               close (gap shown instead of a marker), and the probes a_win, a_match/match_len/match_scope,
               ce_delta/a_ce/ce_floor, a_top, adj, seg_order="pos", restrict.
    Whatever is left after the first pass goes back to the groups in order."""
    cfg = dict(cfg, space=space)

    def weights(gs):
        out = []
        for k, g in enumerate(gs):
            base = 1.0 / (k + 1) if w == "harm" else (1.0 if w == "equal" else w ** k)
            if any(at_doc_start(r) for r in g):
                base *= 1 + ds_boost
            out.append(base)
        return out

    def policy(query, results, cap):
        res = list(results[:n_max] if n_max else results)
        if not res:
            return []
        gs = make_groups(res, group, order)
        G = [Group(g, query["query"], cfg, k == 0) for k, g in enumerate(gs)]
        ws = weights(gs)
        shown = {}
        remaining = cap
        if alloc == "seq":
            for k, grp in enumerate(G):
                share = remaining * ws[k] / (sum(ws[k:]) or 1)
                if share < min_budget:
                    break
                c = grp.fill(int(share))
                if c:
                    shown[k] = c
                    remaining -= c
        else:
            dem = [grp.demand() for grp in G]
            nf = len(G) if n_floor is None else n_floor
            base = [min(floor, d) if k < nf else 0 for k, d in enumerate(dem)]
            if cfg.get("must_match"):          # room for the top result's matched chunk wherever its document sits
                for k, grp in enumerate(G):
                    if grp.must is not None and any(x["rank"] == 0 for x in grp.wins):
                        base[k] = max(base[k], min(cfg["must_match"] + title_len(grp.r) + 100, dem[k]))
            extra = waterfill([d - b for d, b in zip(dem, base)], ws, max(0, cap - sum(base)))
            for k, grp in enumerate(G):
                tgt = int(base[k] + extra[k])
                if tgt < min_budget or remaining < min_budget:
                    continue
                c = grp.fill(min(tgt, remaining))
                if c:
                    shown[k] = c
                    remaining -= c
        if remaining > 50:                     # leftover back to the groups in order
            for k in sorted(shown):
                grp = G[k]
                c = shown[k]
                saved = grp.sel
                c2 = grp.fill(c + remaining)
                if c < c2 <= c + remaining:
                    remaining -= c2 - c
                    shown[k] = c2
                else:
                    grp.sel = saved
                if remaining <= 50:
                    break
        out = []
        for k in sorted(shown):
            out += G[k].displays()
        return out

    return policy


# ── reported policies ────────────────────────────────────────────────
# Shared: documents pooled; select_res's points (document-start prior by document offset); the top
# result's matched chunk (300 characters) always shown; allocation "lead + teasers" by water-filling:
# every document first gets a 200-character floor (title line included), the rest of the cap goes by
# weight 0.1**k over document ranks, so the top document gets nearly all of it; whatever a document
# cannot use is passed on to the next.

_FINAL = dict(group="doc", alloc="wf", floor=200, w=0.1, ds_boost=0.0, must_match=300, doc_offsets=True)

_doc_select = make(space="doc", doc_top_only=True, **_FINAL)
_win_select = make(space="window", **_FINAL)
_doc_select_ce = make(space="doc", doc_top_only=True, order="ce", **_FINAL)


def doc_select(query, results, cap):
    """[doc] The top document is read as a whole: select_res's points over every segment of its
    document text (its opening, passages with the query's residual words, section leads), plus the
    top result's matched chunk; the other documents show 200-character teasers of their best window
    segments (more when the top document cannot use the budget). Cost: doc_text of the top document
    (in today's server expand_results already holds every chunk of it), lex, offsets."""
    return _doc_select(query, results, cap)


def win_select(query, results, cap):
    """[cheap] Window text only: the windows of each document pooled and selected by select_res's
    points (document-start prior by the window's position in its document), plus the top result's
    matched chunk; lead + teasers allocation. Cost: lex, structure, offsets (window positions from
    chunk indices), lengths, ranks."""
    return _win_select(query, results, cap)


def doc_select_ce(query, results, cap):
    """[ce + doc] doc_select with the documents ordered by their best segment cross-encoder logit:
    the document read as a whole is the one with the best-scoring segment, not necessarily the top
    result's; the top result's matched chunk stays shown. Cost: one cross-encoder call per segment of
    every returned window (about 40-125 per search), plus doc_text of one document."""
    return _doc_select_ce(query, results, cap)


# ── checks and ablations cited in the findings ───────────────────────
repro_select_res = make(group="result", space="window")            # = select_cheap/policies.py:select_res
doc_select_dsx2 = make(space="doc", doc_top_only=True, **dict(_FINAL, ds_boost=1.0))   # with the start boost
pooled_res = make(group="doc", space="window")                      # + windows of a document pooled
doc_res = make(group="doc", space="doc")                            # + document space (every document)
doc_res_must = make(group="doc", space="doc", must_match=300)       # + the matched-chunk piece
_G45 = dict(_FINAL, floor=150, w=0.45, ds_boost=1.0)                # the flatter allocation (geometric 0.45, start x2)
doc_select_g45 = make(space="doc", doc_top_only=True, **_G45)
win_select_g45 = make(space="window", **_G45)
doc_select_ce_g45 = make(space="doc", doc_top_only=True, order="ce", **_G45)
doc_head_match = make(space="doc", seg_order="pos", **_FINAL)       # contiguous comparator: document head + match
