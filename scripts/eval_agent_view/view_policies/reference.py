"""Reference display policies for view_sim.py: B′ and C′'s displays, and simple baselines."""


def _bprime(query, results, cap, budget=1000):
    out = []
    for r in results:
        off = r["match_offset"] or 0
        title = bool(off and r["title"])
        room = budget - (len(f"Document: {r['title']}\n\n") if title else 0)
        out.append({"rank": r["rank"], "pieces": [(off, off + max(0, room))], "title": title})
    return out


def bprime(query, results, cap):
    """B′ as shipped: per result, up to 1,000 characters from the matched chunk (title line first when it starts mid-window)."""
    return _bprime(query, results, cap, 1000)


def bprime_500(query, results, cap):
    return _bprime(query, results, cap, 500)


def bprime_1700(query, results, cap):
    return _bprime(query, results, cap, 1700)


def window_start(query, results, cap, budget=1000):
    return [{"rank": r["rank"], "pieces": [(0, budget)], "title": False} for r in results]
