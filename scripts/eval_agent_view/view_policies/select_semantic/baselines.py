"""Simple (cost class: offsets/lengths only) baselines for the select_semantic axis, at the 4,000 cap.

These are the bar the semantic policies must beat. All respect the cap themselves.
"""
GAP_LEN = len("\n[…]\n")


def _tcost(r):
    return len(f"Document: {r['title'] or r['source']}\n\n")


def _span_display(r, a, b, room):
    """Contiguous [a, b) of the window clipped to `room` displayed characters (title line when a > 0)."""
    title = a > 0
    t = _tcost(r) if title else 0
    if room - t <= 0:
        return None, 0
    b = min(b, a + room - t)
    if b <= a:
        return None, 0
    return {"rank": r["rank"], "pieces": [(a, b)], "title": title}, t + (b - a)


def bprime_capped(query, results, cap):
    """B′ (1,000 from match_offset, title line when mid-window), with results dropped once the cap is reached."""
    out, left = [], cap
    for r in results:
        off = r["match_offset"] or 0
        d, used = _span_display(r, off, off + 1000, min(1000, left))
        if d:
            out.append(d)
            left -= used
    return out


def equal_mo(query, results, cap):
    """B′ with the budget split equally: cap / n per result, from match_offset onward."""
    n = max(1, len(results))
    out, left = [], cap
    for r in results:
        off = r["match_offset"] or 0
        d, used = _span_display(r, off, len(r["text"]), min(cap // n, left))
        if d:
            out.append(d)
            left -= used
    return out


def _fill(results, cap, start_fn, lookback=0, min_room=150):
    out, left = [], cap
    for r in results:
        if left < min_room:
            break
        a = max(0, start_fn(r) - lookback)
        if 0 < a <= r["prefix_len"]:
            a = 0                               # show the prefix rather than a title line when it is that close
        d, used = _span_display(r, a, len(r["text"]), left)
        if d:
            out.append(d)
            left -= used
    return out


def fill_mo(query, results, cap):
    """Rank order; each result's window from match_offset to its end until the cap runs out."""
    return _fill(results, cap, lambda r: r["match_offset"] or 0)


def fill_full(query, results, cap):
    """Rank order; each whole window (Bardic prefix included) until the cap runs out."""
    return _fill(results, cap, lambda r: 0)


def fill_mo_back300(query, results, cap):
    return _fill(results, cap, lambda r: r["match_offset"] or 0, lookback=300)


def fill_mo_back600(query, results, cap):
    return _fill(results, cap, lambda r: r["match_offset"] or 0, lookback=600)


def _shares(results, cap, weights, start_fn, lookback=0):
    """Budget split by weights (renormalised over the results present); unused budget flows down the ranks."""
    n = len(results)
    if not n:
        return []
    w = weights[:n] + [weights[-1]] * max(0, n - len(weights))
    tot = sum(w)
    out, left, carry = [], cap, 0
    for r, wi in zip(results, w):
        room = min(left, int(cap * wi / tot) + carry)
        a = max(0, start_fn(r) - lookback)
        if 0 < a <= r["prefix_len"]:
            a = 0
        d, used = _span_display(r, a, len(r["text"]), room)
        carry = room - used
        if d:
            out.append(d)
            left -= used
    return out


def top_heavy_mo(query, results, cap):
    """Shares 8:4:2:1:1 by rank, from match_offset; leftovers pass to the next rank."""
    return _shares(results, cap, [8, 4, 2, 1, 1], lambda r: r["match_offset"] or 0)


def top_heavy_mo_back300(query, results, cap):
    return _shares(results, cap, [8, 4, 2, 1, 1], lambda r: r["match_offset"] or 0, lookback=300)
