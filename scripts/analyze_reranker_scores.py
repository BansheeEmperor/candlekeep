#!/usr/bin/env python3
"""Analyze cross-encoder score distribution for adversarial vs legitimate queries.

Runs the precise path on the Centurion Set and records raw cross-encoder scores
to identify the gap between adversarial and legitimate queries. This data is used
to calibrate the Relevance Ward threshold for the precise path.

Usage:
    python scripts/analyze_reranker_scores.py
"""
import sys
import os
import json
import tempfile
import shutil
from pathlib import Path

os.environ["CANDLEKEEP_DEVICE"] = "cpu"

sys.path.append(str(Path(__file__).parent.parent / "src"))

from candlekeep.config import Settings
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.rag.processor import DocumentProcessor
from candlekeep.rag.router import MIN_RELEVANCE_SCORE
from candlekeep.rag.arcane_recall import search_with_arcane_recall
from candlekeep.rag.reranker import rerank_results
from candlekeep.rag.search import preprocess_negation


def main():
    print("=== Cross-Encoder Score Distribution Analysis ===\n")

    temp_dir = tempfile.mkdtemp(prefix="candlekeep_reranker_")
    try:
        settings = Settings.from_env()
        store = ChromaVectorStore(settings)
        processor = DocumentProcessor(settings)

        # Seed database
        fixtures = Path(__file__).parent.parent / "tests" / "fixtures"
        doc_count = 0
        for doc_dir in [fixtures / "sample_docs", fixtures / "scale_docs"]:
            for doc_path in doc_dir.glob("*"):
                if doc_path.is_file():
                    chunks = processor.process(str(doc_path))
                    store.add_documents(chunks)
                    doc_count += 1
        print(f"Ingested {doc_count} documents.\n")

        # Load Centurion Set
        suite_path = fixtures / "eval_suite_100.json"
        with open(suite_path) as f:
            suite = json.load(f)

        device = settings.device

        adversarial_scores = []
        legitimate_scores = []

        for q in suite["queries"]:
            query = q["query"]
            category = q["category"]
            processed = preprocess_negation(query)

            # Run precise path manually to capture raw scores
            candidates = search_with_arcane_recall(store, processed, n_results=15)
            candidates = [r for r in candidates if r.score >= MIN_RELEVANCE_SCORE]

            if not candidates:
                if category == "adversarial":
                    # Pre-reranking Ward already filtered everything — good
                    print(f"  [ADV] '{query[:50]}' — filtered by vector Ward (0 candidates)")
                continue

            reranked = rerank_results(processed, candidates, top_k=5, device=device)

            scores = [r.score for r in reranked]
            top_score = scores[0] if scores else None

            if category == "adversarial":
                adversarial_scores.extend(scores)
                label = "ADV"
            else:
                legitimate_scores.extend(scores)
                label = "LEG"

            print(f"  [{label}] '{query[:60]:<60}' top={top_score:+.4f}  "
                  f"scores=[{', '.join(f'{s:+.4f}' for s in scores[:5])}]")

        # Summary
        print("\n" + "=" * 70)
        print("SCORE DISTRIBUTION SUMMARY")
        print("=" * 70)

        if adversarial_scores:
            print(f"\nAdversarial (n={len(adversarial_scores)}):")
            print(f"  Max:  {max(adversarial_scores):+.4f}")
            print(f"  Mean: {sum(adversarial_scores)/len(adversarial_scores):+.4f}")
            print(f"  Min:  {min(adversarial_scores):+.4f}")
        else:
            print("\nAdversarial: all filtered by vector Relevance Ward (no candidates reached reranker)")

        if legitimate_scores:
            print(f"\nLegitimate (n={len(legitimate_scores)}):")
            print(f"  Max:  {max(legitimate_scores):+.4f}")
            print(f"  Mean: {sum(legitimate_scores)/len(legitimate_scores):+.4f}")
            print(f"  Min:  {min(legitimate_scores):+.4f}")

        if adversarial_scores and legitimate_scores:
            gap = min(legitimate_scores) - max(adversarial_scores)
            midpoint = (min(legitimate_scores) + max(adversarial_scores)) / 2
            print(f"\nGap (lowest legitimate - highest adversarial): {gap:+.4f}")
            print(f"Suggested threshold (midpoint): {midpoint:+.4f}")

            if gap > 0:
                print("\n✅ Clean separation — threshold will eliminate adversarial results "
                      "with zero false negatives.")
            else:
                print(f"\n⚠ Overlap detected — some adversarial scores exceed some legitimate scores.")
                print(f"  Consider a threshold that minimizes false negatives.")
                # Find threshold that filters all adversarial with minimum legitimate loss
                adv_max = max(adversarial_scores)
                leg_below = sum(1 for s in legitimate_scores if s <= adv_max)
                print(f"  If threshold = {adv_max:+.4f} (highest adversarial):")
                print(f"    Adversarial filtered: {len(adversarial_scores)}/{len(adversarial_scores)}")
                print(f"    Legitimate lost: {leg_below}/{len(legitimate_scores)}")

        # Save raw data
        output = {
            "adversarial_scores": adversarial_scores,
            "legitimate_scores": legitimate_scores,
        }
        output_path = Path(__file__).parent.parent / "tests" / "results"
        output_path.mkdir(exist_ok=True)
        (output_path / "reranker_score_distribution.json").write_text(json.dumps(output, indent=2))
        print(f"\nRaw scores saved to tests/results/reranker_score_distribution.json")

    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    main()
