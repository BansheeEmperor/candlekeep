"""Command line tool for running the Centurion evaluation suite."""
import sys
import os

# Force CPU to avoid GPU issues
os.environ["CANDLEKEEP_DEVICE"] = "cpu"

import json
import tempfile
import shutil
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from candlekeep.config import Settings
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.rag.processor import DocumentProcessor
from candlekeep.rag.router import search_with_routing
from candlekeep.eval.runner import BenchmarkRunner, EvalQuery


def run_evaluation(query_type: str = "simple"):
    print(f"🚀 Starting Centurion Eval (Path: {query_type.upper()})")
    
    # 1. Setup temporary database
    temp_dir = tempfile.mkdtemp(prefix="candlekeep_eval_")
    try:
        settings = Settings.from_env()
        settings.chroma_path = temp_dir
        vector_store = ChromaVectorStore(settings)
        processor = DocumentProcessor(settings)
        
        # 2. Seed database
        print("📦 Seeding database...")
        fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
        sample_docs = fixtures_dir / "sample_docs"
        scale_docs = fixtures_dir / "scale_docs"
        
        doc_count = 0
        for doc_path in list(sample_docs.glob("*")) + list(scale_docs.glob("*")):
            if doc_path.is_file():
                chunks = processor.process(str(doc_path))
                vector_store.add_documents(chunks)
                doc_count += 1
        print(f"✅ Ingested {doc_count} documents.")
        
        # 3. Load evaluation suite
        suite_path = fixtures_dir / "eval_suite_100.json"
        with open(suite_path, "r") as f:
            suite_data = json.load(f)
            
        queries = [
            EvalQuery(
                query=q["query"],
                expected_sources=q["expected_sources"],
                category=q["category"],
                difficulty=q["difficulty"]
            )
            for q in suite_data["queries"]
        ]
        
        # 4. Define search function
        def search_fn(query: str, k: int):
            return search_with_routing(vector_store, query, n_results=k, query_type=query_type)
            
        # 5. Run evaluation
        runner = BenchmarkRunner(search_fn)
        results = runner.run_suite(queries, k=5)
        summary = runner.summarize(results)
        
        # 6. Print summary
        print("\n" + "="*40)
        print("CENTURION EVALUATION SUMMARY")
        print("="*40)
        print(f"Total Queries:   {summary['total_queries']}")
        print(f"MRR:             {summary['mrr']:.4f}  (95% CI: {summary['mrr_ci'][0]:.4f}–{summary['mrr_ci'][1]:.4f})")
        print(f"nDCG@5:          {summary['avg_ndcg_5']:.4f}  (95% CI: {summary['avg_ndcg_5_ci'][0]:.4f}–{summary['avg_ndcg_5_ci'][1]:.4f})")
        print(f"Hit Rate@1:      {summary['avg_hit_rate_1']:.4f}")
        print(f"Hit Rate@5:      {summary['avg_hit_rate_5']:.4f}  (95% CI: {summary['avg_hit_rate_5_ci'][0]:.4f}–{summary['avg_hit_rate_5_ci'][1]:.4f})")
        print(f"Avg Precision@5: {summary['avg_precision_5']:.4f}")
        print(f"Avg Tokens:      {summary['avg_tokens']:.1f}")
        print(f"Total Tokens:    {summary['total_tokens']}")
        print(f"Avg Latency:     {summary['avg_latency_ms']:.2f}ms")
        
        print("\n📊 By Category:")
        for cat, metrics in summary["by_category"].items():
            print(f"  {cat:12} (n={metrics['count']:2}): MRR={metrics['mrr']:.4f}, nDCG@5={metrics['avg_ndcg_5']:.4f}")
        
        # 7. Save report
        output_dir = Path(__file__).parent.parent / "tests" / "results"
        output_dir.mkdir(exist_ok=True)
        report_path = output_dir / f"centurion_{query_type}.json"
        runner.save_report(results, summary, str(report_path))
        
    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    query_type = "simple"
    if len(sys.argv) > 1:
        query_type = sys.argv[1]
    run_evaluation(query_type)
