"""Adaptive query routing based on agent-provided query type."""
import re
from typing import List, Literal

from candlekeep.database.interface import VectorDatabase, SearchResult
from candlekeep.rag.search import preprocess_negation

QueryType = Literal["simple", "precise", "hybrid"]

# ── The Relevance Ward thresholds ────────────────────────────────────

# Minimum score threshold — results below this are filtered as irrelevant.
# Based on score distribution analysis: adversarial=0.709, lowest legitimate=0.847.
MIN_RELEVANCE_SCORE = 0.75

# Adaptive threshold for lexical queries (version numbers, acronyms,
# technical identifiers).  These queries produce vector similarity scores
# in the 0.67–0.75 range — just below the standard Ward.  Relaxing to
# 0.65 recovers them with zero regressions on non-lexical queries and
# zero new adversarial leaks across legal, medical, and narrative corpora.
# Data: Research Diary Entry 40.  Design: DESIGN.md § 8.10.
MIN_RELEVANCE_SCORE_LEXICAL = 0.65

# RRF scores for hybrid are much smaller (usually < 0.1).
# With k=60 and 2 result lists (vector + BM25), the maximum possible
# RRF score is ~0.033 and the top-5 averages ~0.016.
# Threshold sweep (Entry 44) confirmed 0.015 produces zero adversarial
# leaks while preserving full legitimate retrieval quality.
HYBRID_RELEVANCE_THRESHOLD = 0.015

# The Relevance Ward for the precise path (post-reranking).
# Cross-encoder scores are logits (can be negative). Based on Centurion Set
# score distribution analysis: highest adversarial top-1 = -1.84, lowest
# legitimate top-1 = -9.46. Threshold set at -10.0 to maintain zero false
# negatives (no legitimate query filtered). Filters 54% of adversarial
# queries that pass the pre-reranking vector Ward. The remaining adversarial
# results score deeply negative (-1.8 to -10.0) and are unlikely to mislead
# a frontier LLM agent.
# Recalibrate with scripts/analyze_reranker_scores.py on new corpora.
MIN_RERANKER_SCORE = -10.0

# ── Adaptive Relevance Ward: lexical query detection ────────────────
#
# Queries containing version numbers, acronyms, or technical identifiers
# score lower on vector similarity because embeddings capture semantics,
# not literal strings.  The heuristic below detects these queries so the
# Ward can use the relaxed threshold (0.65) instead of the standard (0.75).
#
# Cross-domain validated (Entry 40): zero regressions on non-lexical
# queries, zero new adversarial leaks across technical, legal, medical,
# and narrative corpora.  A blanket reduction to 0.65 causes 1 adversarial
# leak on legal and 1 precision regression on narrative — the adaptive
# approach avoids both.

_VERSION_RE = re.compile(r"\d+\.\w+")                        # "8.x", "1.2", "92"
_ACRONYM_RE = re.compile(r"\b[A-Z]{2,}[-_]?\d*\b")           # "OWASP", "SQL", "IPv6"
_IDENTIFIER_RE = re.compile(r"\b\w+[-_.]\w+[-_.]\w+")        # "bge-small-en"
_SPECIFIC_RE = re.compile(
    r"\b(?:version|v\d|RFC|ISO|IEEE|NIST|OWASP|CVE|CWE|ANSI"
    r"|POSIX|SQL|YAML|JSON|XML|HTML|CSS|HTTP|HTTPS|TCP|UDP"
    r"|TLS|SSL|SSH|DNS|SMTP|IMAP|POP3|FTP|SFTP|NFS|SMB)\b",
    re.IGNORECASE,
)


def _is_lexical_query(query: str) -> bool:
    """Detect queries that contain literal technical identifiers.

    These queries benefit from a relaxed Relevance Ward threshold because
    vector similarity scores for exact identifiers fall in the 0.67–0.75
    range — below the standard 0.75 Ward but above adversarial noise.
    """
    return bool(
        _VERSION_RE.search(query)
        or _ACRONYM_RE.search(query)
        or _IDENTIFIER_RE.search(query)
        or _SPECIFIC_RE.search(query)
    )


def _get_vector_threshold(query: str) -> float:
    """Return the Relevance Ward threshold for a query.

    Lexical queries (version numbers, acronyms, technical identifiers)
    use the relaxed threshold; all others use the standard threshold.
    """
    if _is_lexical_query(query):
        return MIN_RELEVANCE_SCORE_LEXICAL
    return MIN_RELEVANCE_SCORE


def search_with_routing(
    db: VectorDatabase,
    query: str,
    n_results: int = 5,
    category: str | None = None,
    query_type: QueryType = "simple",
) -> List[SearchResult]:
    """Route search to optimal technique stack based on query type.

    All paths use Arcane Recall (±2 chunk expansion) by default.

    The Relevance Ward uses an adaptive threshold: queries detected as
    lexical (version numbers, acronyms, technical identifiers) use a
    relaxed threshold of 0.65 to avoid filtering legitimate results that
    score in the 0.67–0.75 range.  Non-lexical queries retain the 0.75
    threshold.

    Stacks:
        simple  -> Arcane Recall -> Ward
        hybrid  -> BM25+Vector+RRF+Arcane Recall -> Ward
        precise -> Arcane Recall -> Ward -> Divine Insight -> Ward

    For complex multi-part questions, the agent should decompose into
    multiple simple searches and synthesize the results itself.
    """
    from candlekeep.rag.arcane_recall import search_with_arcane_recall

    processed = preprocess_negation(query)

    if query_type == "precise":
        from candlekeep.rag.reranker import rerank_results
        device = getattr(db, 'settings', None)
        device = device.device if device else "cpu"
        threshold = _get_vector_threshold(processed)
        # Fetch candidates and apply threshold before slow reranking
        results = search_with_arcane_recall(db, processed, n_results * 3)
        results = [r for r in results if r.score >= threshold]

        if results:
            results = rerank_results(processed, results, top_k=n_results, device=device)
            # The Relevance Ward (post-reranking): filter results where the
            # cross-encoder score indicates low relevance.
            results = [r for r in results if r.score >= MIN_RERANKER_SCORE]

    elif query_type == "hybrid":
        from candlekeep.rag.hybrid import hybrid_search
        results = hybrid_search(db, processed, n_results, category=category)
        # The Relevance Ward (hybrid RRF scores)
        results = [r for r in results if r.score >= HYBRID_RELEVANCE_THRESHOLD]

    else:
        results = search_with_arcane_recall(db, processed, n_results)
        # The Relevance Ward (adaptive threshold for lexical queries)
        threshold = _get_vector_threshold(processed)
        results = [r for r in results if r.score >= threshold]

    return results
