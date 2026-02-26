#!/usr/bin/env python3
"""Generate graded relevance annotations for the Centurion Set.

Runs all three search paths (simple, hybrid, precise) against the eval
suite, pools unique (query, chunk) pairs, and assigns relevance grades
using a heuristic based on source match and content keyword overlap.

Grading heuristic:
    3 (Perfect):          From expected source, high keyword overlap (>=40%)
    2 (Highly relevant):  From expected source, lower keyword overlap (<40%)
    1 (Marginally relevant): Wrong source but some keyword overlap (>=20%)
    0 (Irrelevant):       Wrong source and low/no keyword overlap

The output is written back into eval_suite_100.json as a new
"graded_relevance" field on each query, keyed by "source:chunk_index".

Usage:
    python scripts/annotate_graded_relevance.py [--dry-run]
"""
import sys
import os
import json
import argparse
from pathlib import Path
from collections import defaultdict

os.environ["CANDLEKEEP_DEVICE"] = "cpu"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from candlekeep.config import Settings
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.rag.router import search_with_routing


def normalize_source(source: str) -> str:
    """Normalize source path to match expected_sources format."""
    if "tests/fixtures" in source:
        return source[source.index("tests/fixtures"):]
    return source


def grade_chunk(
    chunk_source: str,
    chunk_text: str,
    chunk_index: int,
    expected_sources: list[str],
    expected_content: list[str],
) -> int:
    """Assign a 0-3 relevance grade to a (query, chunk) pair.

    Uses source membership and keyword overlap as signals.
    """
    from_expected = chunk_source in expected_sources
    text_lower = chunk_text.lower()

    # Keyword overlap ratio
    if expected_content:
        hits = sum(1 for kw in expected_content if kw.lower() in text_lower)
        kw_ratio = hits / len(expected_content)
    else:
        kw_ratio = 0.0

    if from_expected:
        if kw_ratio >= 0.40:
            return 3  # Perfect: right doc, high keyword match
        else:
            return 2  # Highly relevant: right doc, less keyword match
    else:
        if kw_ratio >= 0.20:
            return 1  # Marginally relevant: wrong doc but topically related
        else:
            return 0  # Irrelevant


def pool_results(store, query: str, k: int = 5) -> dict:
    """Run all 3 search paths and pool unique chunks.

    Returns dict of chunk_id -> {source, chunk_index, text, paths}
    where paths is the set of search paths that returned this chunk.
    """
    pool = {}
    for path_name in ("simple", "hybrid", "precise"):
        try:
            results = search_with_routing(store, query, n_results=k, query_type=path_name)
        except (SystemExit, Exception) as e:
            # Cross-encoder may not be available; skip precise path
            print(f"  ⚠ {path_name} path failed: {e}", file=sys.stderr)
            continue
        for r in results:
            source = normalize_source(r.metadata.get("source", ""))
            idx = r.metadata.get("chunk_index", 0)
            chunk_id = f"{source}:{idx}"
            if chunk_id not in pool:
                pool[chunk_id] = {
                    "source": source,
                    "chunk_index": idx,
                    "text": r.text,
                    "paths": set(),
                }
            pool[chunk_id]["paths"].add(path_name)
    return pool


def main():
    parser = argparse.ArgumentParser(description="Generate graded relevance annotations")
    parser.add_argument("--dry-run", action="store_true", help="Print stats without writing")
    parser.add_argument("--k", type=int, default=5, help="Top-k results per path")
    args = parser.parse_args()

    # Load eval suite
    suite_path = Path(__file__).parent.parent / "tests" / "fixtures" / "eval_suite_100.json"
    with open(suite_path) as f:
        suite = json.load(f)

    # Connect to ChromaDB
    settings = Settings.from_env()
    store = ChromaVectorStore(settings)

    # Ingest corpus if collection is empty
    stats = store.get_stats()
    if stats.get("total_chunks", 0) == 0:
        print("Collection empty — ingesting corpus...")
        from candlekeep.rag.processor import DocumentProcessor
        processor = DocumentProcessor(settings)
        fixtures = Path(__file__).parent.parent / "tests" / "fixtures"
        doc_count = 0
        for subdir in ["sample_docs", "scale_docs"]:
            d = fixtures / subdir
            if d.exists():
                for doc_path in sorted(d.glob("*")):
                    if doc_path.is_file():
                        chunks = processor.process(str(doc_path))
                        store.add_documents(chunks)
                        doc_count += 1
        print(f"Ingested {doc_count} documents")

    total_pairs = 0
    grade_counts = defaultdict(int)
    queries_with_grades = 0

    for i, q in enumerate(suite["queries"]):
        query_text = q["query"]
        expected_sources = q.get("expected_sources", [])
        expected_content = q.get("expected_content", [])
        category = q.get("category", "")

        # Pool results from all 3 paths
        pool = pool_results(store, query_text, k=args.k)

        # Grade each unique chunk
        graded = {}
        for chunk_id, info in pool.items():
            grade = grade_chunk(
                chunk_source=info["source"],
                chunk_text=info["text"],
                chunk_index=info["chunk_index"],
                expected_sources=expected_sources,
                expected_content=expected_content,
            )
            graded[chunk_id] = grade
            grade_counts[grade] += 1
            total_pairs += 1

        # For adversarial queries (no expected sources), all results should be 0
        if category == "adversarial" and not expected_sources:
            graded = {cid: 0 for cid in graded}

        q["graded_relevance"] = graded
        if graded:
            queries_with_grades += 1

        if (i + 1) % 20 == 0:
            print(f"  Processed {i + 1}/{len(suite['queries'])} queries...")

    # Update metadata
    suite["metadata"]["version"] = "1.1"
    suite["metadata"]["graded_relevance"] = {
        "scale": "0-3 (irrelevant, marginal, highly relevant, perfect)",
        "method": "heuristic (source match + keyword overlap)",
        "total_pairs": total_pairs,
        "grade_distribution": dict(grade_counts),
    }

    # Print summary
    print(f"\nAnnotation Summary")
    print(f"{'='*50}")
    print(f"Queries processed:    {len(suite['queries'])}")
    print(f"Queries with grades:  {queries_with_grades}")
    print(f"Total (query, chunk) pairs: {total_pairs}")
    print(f"Grade distribution:")
    for grade in sorted(grade_counts.keys()):
        label = {0: "Irrelevant", 1: "Marginal", 2: "Highly relevant", 3: "Perfect"}[grade]
        count = grade_counts[grade]
        pct = count / total_pairs * 100 if total_pairs else 0
        print(f"  {grade} ({label:>16s}): {count:4d} ({pct:5.1f}%)")

    if args.dry_run:
        print("\n[DRY RUN] No files written.")
        return

    # Write updated eval suite
    with open(suite_path, "w") as f:
        json.dump(suite, f, indent=2)
    print(f"\nUpdated {suite_path}")


if __name__ == "__main__":
    main()
