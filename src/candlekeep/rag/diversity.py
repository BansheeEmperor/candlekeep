"""Prismatic Dispersal: Sine-distance diversity reranking.

After Arcane Recall expands results with context, the candidate set may
contain chunks that are semantically redundant — multiple fragments saying
the same thing from different parts of the corpus.  Prismatic Dispersal
reorders positions 2–k to penalize chunks that are too similar to
already-selected results, surfacing diverse information facets.

The name comes from the D&D Prismatic spell family: a prism splits a
beam of light into its constituent colours, just as this step separates
a redundant result set into distinct information facets.  The sine
distance measures orthogonality between embedding vectors — 0 for
identical, 1 for maximally different — which maps to how a prism
measures wavelength separation.

Two strategies are provided, chosen per search path:

- **Iterative** (simple path, λ=0.2): At each step, pick the candidate
  that maximises  λ·relevance + (1-λ)·min_sine_to_any_selected.
  Similar to MMR with sine as the diversity kernel.

- **Centroid** (hybrid path, λ=0.3): Same objective, but diversity is
  measured against the running centroid (mean embedding) of the selected
  set rather than the worst-case pairwise distance.

The precise path skips this step — the cross-encoder already provides
implicit diversity through its joint query-document scoring.

Data: Research Diary Entry 43.
Design rationale: DESIGN.md § 3.8.
"""

from typing import List

import numpy as np

from candlekeep.database.interface import SearchResult


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _sine_dist(a: np.ndarray, b: np.ndarray) -> float:
    """Sine distance: orthogonality between two vectors.

    sin(θ) = √(1 - cos²(θ))
    Returns 0.0 for identical vectors, 1.0 for orthogonal vectors.
    """
    cos = _cosine_sim(a, b)
    return float(np.sqrt(max(0.0, 1.0 - cos * cos)))



def sine_rerank_iterative(
    results: List[SearchResult],
    embeddings: List[np.ndarray],
    top_k: int = 5,
    lambda_: float = 0.2,
) -> List[SearchResult]:
    """Iterative sine reranking — used on the simple path.

    Greedily selects each next chunk to maximise:
        λ · normalised_relevance + (1 - λ) · min_sine_distance_to_selected

    The top-1 result (highest relevance) is always preserved.
    Complexity: O(k · n) sine computations.
    """
    if len(results) <= 1:
        return results[:top_k]

    n = len(results)
    selected_indices: List[int] = [0]  # start with highest relevance
    remaining = set(range(1, n))

    max_score = results[0].score if results[0].score != 0 else 1.0

    while len(selected_indices) < top_k and remaining:
        best_idx = -1
        best_combined = -1.0

        for idx in remaining:
            rel = results[idx].score / max_score if max_score != 0 else 0

            min_sd = min(
                _sine_dist(embeddings[idx], embeddings[s])
                for s in selected_indices
            )

            combined = lambda_ * rel + (1 - lambda_) * min_sd
            if combined > best_combined:
                best_combined = combined
                best_idx = idx

        if best_idx >= 0:
            selected_indices.append(best_idx)
            remaining.discard(best_idx)
        else:
            break

    return [results[i] for i in selected_indices]


def sine_rerank_centroid(
    results: List[SearchResult],
    embeddings: List[np.ndarray],
    top_k: int = 5,
    lambda_: float = 0.3,
) -> List[SearchResult]:
    """Centroid sine reranking — used on the hybrid path.

    Greedily selects each next chunk to maximise:
        λ · normalised_relevance + (1 - λ) · sine_distance_to_centroid

    The centroid is the mean embedding of all selected chunks so far.
    The top-1 result (highest relevance) is always preserved.
    Complexity: O(k · n) sine computations + O(k · d) centroid updates.
    """
    if len(results) <= 1:
        return results[:top_k]

    n = len(results)
    selected_indices: List[int] = [0]
    centroid = np.array(embeddings[0], dtype=np.float64)
    remaining = set(range(1, n))

    max_score = results[0].score if results[0].score != 0 else 1.0

    while len(selected_indices) < top_k and remaining:
        best_idx = -1
        best_combined = -1.0

        for idx in remaining:
            rel = results[idx].score / max_score if max_score != 0 else 0
            sd = _sine_dist(centroid, embeddings[idx])
            combined = lambda_ * rel + (1 - lambda_) * sd

            if combined > best_combined:
                best_combined = combined
                best_idx = idx

        if best_idx >= 0:
            selected_indices.append(best_idx)
            remaining.discard(best_idx)
            k = len(selected_indices)
            centroid = centroid * ((k - 1) / k) + np.array(embeddings[best_idx]) / k
        else:
            break

    return [results[i] for i in selected_indices]


# ── Candidate pool multiplier ───────────────────────────────────────
#
# Prismatic Dispersal needs more candidates than the final n_results so
# it can select for diversity.  The benchmark (Entry 43) used a 3×
# candidate pool (15 candidates → 5 results).  This constant is used by
# the router to over-fetch from Arcane Recall / hybrid_search before
# sine-selecting down to the requested n_results.
#
# This changes the previous flow where simple and hybrid paths fetched
# exactly n_results from Arcane Recall.  The over-fetch adds a small
# amount of latency to the expansion phase (more chunks to expand) but
# the sine step itself is sub-millisecond.
CANDIDATE_POOL_MULTIPLIER = 3
