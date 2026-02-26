"""Tests for graded relevance metrics."""
import pytest
from candlekeep.eval.metrics import (
    calculate_dcg_graded,
    calculate_ndcg_graded,
)


class TestDCGGraded:
    def test_perfect_ranking(self):
        """Grade-3 doc at rank 1 should produce maximum DCG."""
        retrieved = ["a:0", "b:0", "c:0"]
        grades = {"a:0": 3, "b:0": 1, "c:0": 0}
        dcg = calculate_dcg_graded(retrieved, grades, k=3)
        # 3/log2(2) + 1/log2(3) + 0 = 3.0 + 0.6309 = 3.6309
        assert dcg == pytest.approx(3.6309, abs=0.001)

    def test_reversed_ranking(self):
        """Grade-1 at rank 1, grade-3 at rank 2 — worse DCG."""
        retrieved = ["b:0", "a:0", "c:0"]
        grades = {"a:0": 3, "b:0": 1, "c:0": 0}
        dcg = calculate_dcg_graded(retrieved, grades, k=3)
        # 1/log2(2) + 3/log2(3) = 1.0 + 1.8928 = 2.8928
        assert dcg == pytest.approx(2.8928, abs=0.001)

    def test_empty_grades(self):
        dcg = calculate_dcg_graded(["a:0"], {}, k=5)
        assert dcg == 0.0

    def test_all_irrelevant(self):
        grades = {"a:0": 0, "b:0": 0}
        dcg = calculate_dcg_graded(["a:0", "b:0"], grades, k=5)
        assert dcg == 0.0

    def test_k_truncation(self):
        """Only first k results should count."""
        retrieved = ["a:0", "b:0", "c:0"]
        grades = {"a:0": 0, "b:0": 0, "c:0": 3}
        dcg_k2 = calculate_dcg_graded(retrieved, grades, k=2)
        assert dcg_k2 == 0.0  # grade-3 doc is at rank 3, beyond k=2


class TestNDCGGraded:
    def test_perfect_ranking(self):
        """Ideal ranking should produce nDCG = 1.0."""
        retrieved = ["a:0", "b:0"]
        grades = {"a:0": 3, "b:0": 1}
        ndcg = calculate_ndcg_graded(retrieved, grades, k=5)
        assert ndcg == pytest.approx(1.0, abs=0.001)

    def test_reversed_ranking(self):
        """Swapped ranking should produce nDCG < 1.0."""
        retrieved = ["b:0", "a:0"]
        grades = {"a:0": 3, "b:0": 1}
        ndcg = calculate_ndcg_graded(retrieved, grades, k=5)
        assert 0.0 < ndcg < 1.0

    def test_empty_grades(self):
        ndcg = calculate_ndcg_graded(["a:0"], {}, k=5)
        assert ndcg == 0.0

    def test_single_perfect(self):
        """Single grade-3 doc at rank 1."""
        ndcg = calculate_ndcg_graded(["a:0"], {"a:0": 3}, k=5)
        assert ndcg == pytest.approx(1.0, abs=0.001)

    def test_unknown_chunk_scores_zero(self):
        """Chunks not in grades dict get gain=0."""
        retrieved = ["unknown:99", "a:0"]
        grades = {"a:0": 3}
        ndcg = calculate_ndcg_graded(retrieved, grades, k=5)
        # a:0 is at rank 2, not rank 1 — nDCG < 1.0
        assert 0.0 < ndcg < 1.0

    def test_all_zero_grades(self):
        grades = {"a:0": 0, "b:0": 0}
        ndcg = calculate_ndcg_graded(["a:0", "b:0"], grades, k=5)
        assert ndcg == 0.0

    def test_graded_vs_binary_discrimination(self):
        """Graded nDCG should distinguish rankings that binary nDCG cannot.

        Both rankings have the same binary relevance (both docs are relevant),
        but graded nDCG should prefer the one with the higher-grade doc first.
        """
        grades = {"a:0": 3, "b:0": 1}

        # Good ranking: grade-3 first
        ndcg_good = calculate_ndcg_graded(["a:0", "b:0"], grades, k=5)
        # Bad ranking: grade-1 first
        ndcg_bad = calculate_ndcg_graded(["b:0", "a:0"], grades, k=5)

        assert ndcg_good > ndcg_bad
