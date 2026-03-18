"""Script to perform overfitting check and threshold sensitivity analysis."""
import sys
from pathlib import Path
import os
import json

# Add src and project root to path
sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent))

# Force CPU
os.environ["CANDLEKEEP_DEVICE"] = "cpu"

from candlekeep.config import Settings
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.rag.processor import DocumentProcessor
from candlekeep.rag.router import search_with_routing
from candlekeep.eval.runner import BenchmarkRunner, EvalQuery
from tests.benchmark_queries import BENCHMARK_QUERIES

def run_sensitivity_sweep():
    # Setup
    fixtures_dir = Path("tests/fixtures")
    sample_docs = fixtures_dir / "sample_docs"
    scale_docs = fixtures_dir / "scale_docs"
    settings = Settings.from_env()
    
    import tempfile
    import shutil
    temp_dir = tempfile.mkdtemp()
    settings.chroma_path = temp_dir
    vector_store = ChromaVectorStore(settings)
    processor = DocumentProcessor(settings)
    
    # Seed
    for doc_path in list(sample_docs.glob("*")) + list(scale_docs.glob("*")):
        if doc_path.is_file():
            vector_store.add_documents(processor.process(str(doc_path)).chunks)
            
    # 1. Overfitting Check (Original 23 Queries)
    print("--- OVERFITTING CHECK (N=23) ---")
    orig_queries = [
        EvalQuery(q.query, q.expected_sources, q.category, q.difficulty)
        for q in BENCHMARK_QUERIES
    ]
    runner = BenchmarkRunner(lambda query, k: search_with_routing(vector_store, query, n_results=k, query_type="hybrid"))
    orig_summary = runner.summarize(runner.run_suite(orig_queries))
    print(f"Original 23-Query MRR: {orig_summary['mrr']:.4f}")
    
    # 2. Threshold Sweep (N=108)
    print("\n--- THRESHOLD SENSITIVITY SWEEP (N=108) ---")
    with open(fixtures_dir / "eval_suite_100.json", "r") as f:
        suite_data = json.load(f)
    full_queries = [EvalQuery(q["query"], q["expected_sources"], q["category"], q["difficulty"]) for q in suite_data["queries"]]
    
    thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]
    sweep_results = []
    
    # We need to manually override the threshold in the search function
    # The search_with_routing eventually calls vector_store.search
    # We'll monkeypatch or use environment variables if the code supports it
    
    for t in thresholds:
        import candlekeep.rag.router
        candlekeep.rag.router.MIN_RELEVANCE_SCORE = t
        
        # Checking vector_store.py search logic
        res = runner.run_suite(full_queries)
        summary = runner.summarize(res)
        
        # Calculate Adversarial Leakage (queries where expected_sources is empty but retrieved is NOT)
        adv_queries = [r for r in res if r.category == "adversarial"]
        leakage = sum(1 for r in adv_queries if r.retrieved_sources) / len(adv_queries)
        
        # Calculate Lexical Recall (Hit Rate @ 5)
        lex_queries = [r for r in res if r.category == "lexical"]
        lex_recall = sum(1 for r in lex_queries if r.hit_rate_5 > 0) / len(lex_queries)
        
        print(f"Threshold: {t:.2f} | Lexical Recall: {lex_recall:.2f} | Adversarial Leakage: {leakage:.2f} | Total MRR: {summary['mrr']:.4f}")
        sweep_results.append({
            "threshold": t,
            "lex_recall": lex_recall,
            "leakage": leakage,
            "mrr": summary["mrr"]
        })
    
    shutil.rmtree(temp_dir)
    return orig_summary, sweep_results

if __name__ == "__main__":
    run_sensitivity_sweep()
