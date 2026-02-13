"""Benchmark framework for RAG quality evaluation."""
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any
import json
import time


@dataclass
class BenchmarkQuery:
    """A test query with expected results."""
    query: str
    difficulty: str  # easy, medium, hard
    expected_sources: List[str]  # Documents that should be retrieved
    expected_content: List[str]  # Key phrases that should appear in results
    category: str | None = None


@dataclass
class BenchmarkResult:
    """Results from a single query."""
    query: str
    difficulty: str
    retrieved_sources: List[str]
    retrieved_count: int
    expected_sources: List[str]
    expected_content: List[str]
    found_content: List[str]
    precision: float  # % of retrieved that are relevant
    recall: float  # % of relevant that are retrieved
    latency_ms: float
    top_score: float


class RAGBenchmark:
    """Benchmark RAG retrieval quality."""
    
    def __init__(self, search_fn, queries: List[BenchmarkQuery]):
        """Initialize with search function and test queries.
        
        Args:
            search_fn: Function that takes (query, n_results) and returns results
            queries: List of benchmark queries
        """
        self.search_fn = search_fn
        self.queries = queries
    
    def run(self, n_results: int = 5) -> List[BenchmarkResult]:
        """Run benchmark and return results."""
        results = []
        
        for q in self.queries:
            start = time.time()
            search_results = self.search_fn(q.query, n_results)
            latency = (time.time() - start) * 1000
            
            # Extract sources from results (normalize to relative paths)
            retrieved_sources = []
            for r in search_results:
                source = r.metadata.get('source', '')
                # Normalize to relative path for comparison
                if 'tests/fixtures' in source:
                    source = source[source.index('tests/fixtures'):]
                retrieved_sources.append(source)
            
            # Normalize expected sources
            expected_sources = [s if not s.startswith('/') else s[s.index('tests/'):] if 'tests/' in s else s 
                              for s in q.expected_sources]
            
            # Calculate precision: how many retrieved are relevant?
            relevant_retrieved = sum(1 for s in retrieved_sources if s in expected_sources)
            precision = relevant_retrieved / len(retrieved_sources) if retrieved_sources else 0
            
            # Calculate recall: how many relevant were retrieved?
            recall = relevant_retrieved / len(expected_sources) if expected_sources else 0
            
            # Check for expected content
            all_text = ' '.join([r.text for r in search_results])
            found_content = [c for c in q.expected_content if c.lower() in all_text.lower()]
            
            # Get top score
            top_score = search_results[0].score if search_results else 0.0
            
            results.append(BenchmarkResult(
                query=q.query,
                difficulty=q.difficulty,
                retrieved_sources=retrieved_sources,
                retrieved_count=len(retrieved_sources),
                expected_sources=expected_sources,
                expected_content=q.expected_content,
                found_content=found_content,
                precision=precision,
                recall=recall,
                latency_ms=latency,
                top_score=top_score
            ))
        
        return results
    
    def summarize(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Generate summary statistics."""
        total = len(results)
        
        # Overall metrics
        avg_precision = sum(r.precision for r in results) / total
        avg_recall = sum(r.recall for r in results) / total
        avg_latency = sum(r.latency_ms for r in results) / total
        avg_top_score = sum(r.top_score for r in results) / total
        
        # F1 score (harmonic mean of precision and recall)
        f1 = 2 * (avg_precision * avg_recall) / (avg_precision + avg_recall) if (avg_precision + avg_recall) > 0 else 0
        
        # By difficulty
        by_difficulty = {}
        for difficulty in ['easy', 'medium', 'hard']:
            diff_results = [r for r in results if r.difficulty == difficulty]
            if diff_results:
                by_difficulty[difficulty] = {
                    'count': len(diff_results),
                    'precision': sum(r.precision for r in diff_results) / len(diff_results),
                    'recall': sum(r.recall for r in diff_results) / len(diff_results),
                    'latency_ms': sum(r.latency_ms for r in diff_results) / len(diff_results)
                }
        
        # Content match rate
        content_matches = sum(len(r.found_content) for r in results)
        content_expected = sum(len(r.expected_content) for r in results)
        content_match_rate = content_matches / content_expected if content_expected > 0 else 0
        
        return {
            'total_queries': total,
            'avg_precision': avg_precision,
            'avg_recall': avg_recall,
            'f1_score': f1,
            'avg_latency_ms': avg_latency,
            'avg_top_score': avg_top_score,
            'content_match_rate': content_match_rate,
            'by_difficulty': by_difficulty
        }
    
    def print_report(self, results: List[BenchmarkResult], summary: Dict[str, Any]):
        """Print formatted benchmark report."""
        print("\n" + "="*80)
        print("RAG BENCHMARK REPORT")
        print("="*80)
        
        print(f"\n📊 Overall Metrics ({summary['total_queries']} queries)")
        print(f"  Precision:  {summary['avg_precision']:.1%}")
        print(f"  Recall:     {summary['avg_recall']:.1%}")
        print(f"  F1 Score:   {summary['f1_score']:.1%}")
        print(f"  Content:    {summary['content_match_rate']:.1%} (expected phrases found)")
        print(f"  Latency:    {summary['avg_latency_ms']:.1f}ms avg")
        print(f"  Top Score:  {summary['avg_top_score']:.3f} avg")
        
        print(f"\n📈 By Difficulty")
        for diff, metrics in summary['by_difficulty'].items():
            print(f"  {diff.capitalize():8} ({metrics['count']:2} queries): "
                  f"P={metrics['precision']:.1%} R={metrics['recall']:.1%} "
                  f"L={metrics['latency_ms']:.0f}ms")
        
        print(f"\n🔍 Query Details")
        for r in results:
            status = "✓" if r.precision > 0.5 and r.recall > 0.5 else "✗"
            print(f"  {status} [{r.difficulty[0].upper()}] {r.query[:60]:60} "
                  f"P={r.precision:.1%} R={r.recall:.1%}")
        
        print("\n" + "="*80 + "\n")
    
    def save_results(self, results: List[BenchmarkResult], summary: Dict[str, Any], path: str):
        """Save results to JSON file."""
        data = {
            'summary': summary,
            'results': [
                {
                    'query': r.query,
                    'difficulty': r.difficulty,
                    'precision': r.precision,
                    'recall': r.recall,
                    'latency_ms': r.latency_ms,
                    'top_score': r.top_score,
                    'retrieved_sources': r.retrieved_sources,
                    'expected_sources': r.expected_sources,
                    'found_content': r.found_content,
                    'expected_content': r.expected_content
                }
                for r in results
            ]
        }
        
        Path(path).write_text(json.dumps(data, indent=2))
        print(f"💾 Results saved to {path}")
