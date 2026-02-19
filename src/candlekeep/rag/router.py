"""Adaptive query routing based on agent-provided query type."""
import re
from typing import List, Literal

import numpy as np

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
# With Ward-before-Dispersal ordering, the threshold must be low enough
# to preserve a viable candidate pool for diversity selection. At k=60
# with 2 lists, the max RRF score is ~0.033 and the top-5 averages ~0.016.
# Threshold sweep (Entry 44) confirmed 0.015 produces zero adversarial
# leaks while preserving full legitimate retrieval quality. The previous
# value (0.03) filtered 94% of all RRF scores, collapsing the candidate
# pool to 1 result per query.
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


def _apply_prismatic_dispersal(
    db: VectorDatabase,
    results: List[SearchResult],
    n_results: int,
    strategy: str,
) -> List[SearchResult]:
    """Apply Prismatic Dispersal (sine-distance diversity reranking).

    Reorders positions 2–k to penalise chunks that are semantically
    redundant with already-selected results.  The top-1 result (highest
    relevance) is always preserved.

    This step requires embeddings for the candidate results.  It calls
    db.get_embeddings() once to embed the expanded text of each candidate.
    At the default n_results=5 with a 3× candidate pool, this is 15
    texts embedded in a single batch — typically < 5ms on a warm model.

    Strategies:
        iterative — simple path, λ=0.2.  Diversity = min sine distance
                    to any already-selected chunk.
        centroid  — hybrid path, λ=0.3.  Diversity = sine distance to
                    the running centroid of the selected set.

    Data: Research Diary Entry 43.
    """
    if len(results) <= 1:
        return results[:n_results]

    from candlekeep.rag.diversity import sine_rerank_iterative, sine_rerank_centroid

    texts = [r.text for r in results]
    raw_embeddings = db.get_embeddings(texts)
    embeddings = [np.array(e) for e in raw_embeddings]

    if strategy == "centroid":
        return sine_rerank_centroid(results, embeddings, top_k=n_results, lambda_=0.3)
    else:
        return sine_rerank_iterative(results, embeddings, top_k=n_results, lambda_=0.2)


def search_with_routing(
    db: VectorDatabase,
    query: str,
    n_results: int = 5,
    category: str | None = None,
    query_type: QueryType = "simple",
) -> List[SearchResult]:
    """Route search to optimal technique stack based on query type.

    All paths use Arcane Recall (±2 chunk expansion) by default.

    The simple and hybrid paths apply Prismatic Dispersal after Arcane
    Recall to reorder results for diversity before the Relevance Ward
    filters low-confidence matches.  This requires over-fetching from
    Arcane Recall / hybrid_search by a 3× candidate pool multiplier so
    the sine step has room to select for diversity.  Previous behaviour
    fetched exactly n_results from Arcane Recall on these paths; the new
    flow fetches n_results × 3 candidates, sine-selects down to
    n_results, then applies the Ward.

    The Relevance Ward uses an adaptive threshold: queries detected as
    lexical (version numbers, acronyms, technical identifiers) use a
    relaxed threshold of 0.65 to avoid filtering legitimate results that
    score in the 0.67–0.75 range.  Non-lexical queries retain the 0.75
    threshold.

    Stacks:
        simple  -> Arcane Recall -> Ward -> Prismatic Dispersal (iterative)
        hybrid  -> BM25+Vector+RRF+Arcane Recall -> Ward -> Prismatic Dispersal (centroid)
        precise -> Arcane Recall -> Ward -> Divine Insight -> Ward

    For complex multi-part questions, the agent should decompose into
    multiple simple searches and synthesize the results itself.
    """
    from candlekeep.rag.arcane_recall import search_with_arcane_recall
    from candlekeep.rag.diversity import CANDIDATE_POOL_MULTIPLIER

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
        # Over-fetch so Prismatic Dispersal has a candidate pool to
        # select from.  hybrid_search internally runs Arcane Recall with
        # this larger n, then sine reranking selects down to n_results.
        pool = n_results * CANDIDATE_POOL_MULTIPLIER
        results = hybrid_search(db, processed, pool, category=category)
        # The Relevance Ward (hybrid RRF scores) — applied BEFORE Dispersal
        # so the diversity step only operates on results above the threshold.
        results = [r for r in results if r.score >= HYBRID_RELEVANCE_THRESHOLD]
        # Prismatic Dispersal: centroid strategy, λ=0.3
        results = _apply_prismatic_dispersal(db, results, n_results, strategy="centroid")

    else:
        # Over-fetch so Prismatic Dispersal has a candidate pool.
        pool = n_results * CANDIDATE_POOL_MULTIPLIER
        results = search_with_arcane_recall(db, processed, pool)
        # The Relevance Ward (adaptive threshold for lexical queries) —
        # applied BEFORE Dispersal so diversity selection only considers
        # results above the threshold.
        threshold = _get_vector_threshold(processed)
        results = [r for r in results if r.score >= threshold]
        # Prismatic Dispersal: iterative strategy, λ=0.2
        results = _apply_prismatic_dispersal(db, results, n_results, strategy="iterative")

    return results
