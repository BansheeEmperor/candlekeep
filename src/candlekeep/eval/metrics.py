"""Information Retrieval metrics for RAG evaluation."""
import numpy as np
from typing import Dict, List, Set


def calculate_reciprocal_rank(retrieved_ids: List[str], ground_truth_ids: Set[str]) -> float:
    """Calculate the Reciprocal Rank (RR).
    
    RR = 1 / rank of the first relevant document.
    """
    for i, doc_id in enumerate(retrieved_ids):
        if doc_id in ground_truth_ids:
            return 1.0 / (i + 1)
    return 0.0


def calculate_dcg(retrieved_ids: List[str], ground_truth_ids: Set[str], k: int) -> float:
    """Calculate Discounted Cumulative Gain (DCG) at K."""
    dcg = 0.0
    for i, doc_id in enumerate(retrieved_ids[:k]):
        if doc_id in ground_truth_ids:
            # Relevance is binary here (1 or 0)
            dcg += 1.0 / np.log2(i + 2)
    return dcg


def calculate_ndcg(retrieved_ids: List[str], ground_truth_ids: Set[str], k: int) -> float:
    """Calculate Normalized Discounted Cumulative Gain (nDCG) at K.
    
    Deduplicates retrieved_ids to treat multiple chunks from the same document as a single hit.
    """
    if not ground_truth_ids:
        return 0.0
    
    # Deduplicate while preserving order
    unique_retrieved = []
    seen = set()
    for doc_id in retrieved_ids[:k]:
        if doc_id not in seen:
            unique_retrieved.append(doc_id)
            seen.add(doc_id)
    
    dcg = calculate_dcg(unique_retrieved, ground_truth_ids, k)
    
    # IDCG is the DCG of the ideal ranking (all unique relevant docs at the top)
    n_relevant = min(len(ground_truth_ids), k)
    idcg = sum(1.0 / np.log2(i + 2) for i in range(n_relevant))
    
    if idcg == 0:
        return 0.0
    
    return dcg / idcg


def calculate_hit_rate(retrieved_ids: List[str], ground_truth_ids: Set[str], k: int) -> float:
    """Calculate Hit Rate at K (also known as Recall@K)."""
    if not ground_truth_ids:
        return 1.0 if not retrieved_ids else 0.0
    
    hits = any(doc_id in ground_truth_ids for doc_id in retrieved_ids[:k])
    return 1.0 if hits else 0.0


def calculate_precision_at_k(retrieved_ids: List[str], ground_truth_ids: Set[str], k: int) -> float:
    """Calculate Precision at K."""
    if not retrieved_ids:
        return 1.0 if not ground_truth_ids else 0.0
    
    actual_k = min(len(retrieved_ids), k)
    relevant_retrieved = sum(1 for doc_id in retrieved_ids[:actual_k] if doc_id in ground_truth_ids)
    return relevant_retrieved / actual_k


# ── Graded relevance metrics ────────────────────────────────────────
# These functions accept a dict mapping chunk IDs to integer relevance
# grades (0-3) instead of a binary set of relevant IDs.


def calculate_dcg_graded(
    retrieved_ids: List[str],
    relevance_grades: Dict[str, int],
    k: int,
) -> float:
    """Calculate DCG at K with graded relevance (0-3 scale).

    Args:
        retrieved_ids: Ordered list of retrieved chunk identifiers.
        relevance_grades: Mapping of chunk_id -> relevance grade (0-3).
        k: Cutoff rank.
    """
    dcg = 0.0
    for i, doc_id in enumerate(retrieved_ids[:k]):
        gain = relevance_grades.get(doc_id, 0)
        if gain > 0:
            dcg += gain / np.log2(i + 2)
    return dcg


def calculate_ndcg_graded(
    retrieved_ids: List[str],
    relevance_grades: Dict[str, int],
    k: int,
) -> float:
    """Calculate nDCG at K with graded relevance.

    Unlike the binary variant, this does NOT deduplicate retrieved_ids —
    each position is scored independently using its chunk-level grade.

    Args:
        retrieved_ids: Ordered list of retrieved chunk identifiers
            (format: "source_path:chunk_index").
        relevance_grades: Mapping of chunk_id -> relevance grade (0-3).
        k: Cutoff rank.

    Returns:
        Normalized DCG in [0, 1].  Returns 0.0 when no grades are
        provided or all grades are zero.
    """
    if not relevance_grades:
        return 0.0

    dcg = calculate_dcg_graded(retrieved_ids, relevance_grades, k)

    # IDCG: the best possible DCG from the top-k highest grades
    ideal_gains = sorted(relevance_grades.values(), reverse=True)[:k]
    idcg = sum(g / np.log2(i + 2) for i, g in enumerate(ideal_gains) if g > 0)

    if idcg == 0:
        return 0.0

    return dcg / idcg

