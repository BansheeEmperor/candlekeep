"""Benchmark runner for executing IR evaluation."""
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Callable
from dataclasses import dataclass, asdict

from candlekeep.eval.metrics import (
    calculate_reciprocal_rank,
    calculate_ndcg,
    calculate_hit_rate,
    calculate_precision_at_k
)


@dataclass
class EvalQuery:
    query: str
    expected_sources: List[str]
    category: str
    difficulty: str


@dataclass
class EvalResult:
    query: str
    category: str
    difficulty: str
    retrieved_sources: List[str]
    rr: float
    ndcg_5: float
    hit_rate_1: float
    hit_rate_5: float
    precision_5: float
    latency_ms: float


class BenchmarkRunner:
    """Runs IR evaluation against a search function."""
    
    def __init__(self, search_fn: Callable):
        self.search_fn = search_fn
        
    def run_suite(self, queries: List[EvalQuery], k: int = 5) -> List[EvalResult]:
        results = []
        for q in queries:
            start_time = time.time()
            # The search_fn should return a list of objects with a .metadata['source'] attribute
            search_results = self.search_fn(q.query, k)
            latency = (time.time() - start_time) * 1000
            
            retrieved_sources = []
            for r in search_results:
                source = r.metadata.get('source', '')
                # Normalize source path to match expected_sources format
                if 'tests/fixtures' in source:
                    source = source[source.index('tests/fixtures'):]
                retrieved_sources.append(source)
            
            ground_truth = set(q.expected_sources)
            
            results.append(EvalResult(
                query=q.query,
                category=q.category,
                difficulty=q.difficulty,
                retrieved_sources=retrieved_sources,
                rr=calculate_reciprocal_rank(retrieved_sources, ground_truth),
                ndcg_5=calculate_ndcg(retrieved_sources, ground_truth, 5),
                hit_rate_1=calculate_hit_rate(retrieved_sources, ground_truth, 1),
                hit_rate_5=calculate_hit_rate(retrieved_sources, ground_truth, 5),
                precision_5=calculate_precision_at_k(retrieved_sources, ground_truth, 5),
                latency_ms=latency
            ))
        return results

    def summarize(self, results: List[EvalResult]) -> Dict[str, Any]:
        if not results:
            return {}
            
        summary = {
            "mrr": sum(r.rr for r in results) / len(results),
            "avg_ndcg_5": sum(r.ndcg_5 for r in results) / len(results),
            "avg_hit_rate_1": sum(r.hit_rate_1 for r in results) / len(results),
            "avg_hit_rate_5": sum(r.hit_rate_5 for r in results) / len(results),
            "avg_precision_5": sum(r.precision_5 for r in results) / len(results),
            "avg_latency_ms": sum(r.latency_ms for r in results) / len(results),
            "by_category": {},
            "total_queries": len(results)
        }
        
        categories = set(r.category for r in results)
        for cat in categories:
            cat_results = [r for r in results if r.category == cat]
            summary["by_category"][cat] = {
                "mrr": sum(r.rr for r in cat_results) / len(cat_results),
                "avg_ndcg_5": sum(r.ndcg_5 for r in cat_results) / len(cat_results),
                "avg_hit_rate_5": sum(r.hit_rate_5 for r in cat_results) / len(cat_results),
                "count": len(cat_results)
            }
            
        return summary

    def save_report(self, results: List[EvalResult], summary: Dict[str, Any], output_path: str):
        report = {
            "summary": summary,
            "details": [asdict(r) for r in results]
        }
        Path(output_path).write_text(json.dumps(report, indent=2))
        print(f"Report saved to {output_path}")
