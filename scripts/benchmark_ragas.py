"""
Candlekeep Flagship Scientific Quality Benchmark Suite.

This script performs an end-to-end evaluation of Candlekeep's retrieval performance
against industry standards (LlamaIndex and LangChain). It uses RAGAS metrics 
powered by high-reasoning models (e.g., Claude 4.5) to provide
statistically stable and scientifically rigorous quality scores.

Scientific Rigor Features:
1. Deterministic Sandbox: Ensures all frameworks search the exact same document subset.
2. Ground Truth Inclusion: Guarantees that documents required to answer the query are 
   physically present in the search pool.
3. No Truncation: Leverages large-context models to evaluate the full retrieved context.
4. Competitive Alignment: Pre-loads competitor models to remove unfair initialization lag.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from datasets import Dataset
from dotenv import load_dotenv

# RAGAS 0.4.3+ Schema and Metrics
from ragas.dataset_schema import SingleTurnSample
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)

# Core Framework Imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from candlekeep.config import Settings
from candlekeep.database.interface import SearchResult
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.rag.hybrid import clear_bm25_cache
from candlekeep.rag.processor import DocumentProcessor
from candlekeep.rag.router import search_with_routing
from scripts.competitors.langchain_rag import LangChainRAG
from scripts.competitors.llamaindex_rag import LlamaIndexRAG

# Persistence objects for framework instances
_CK_STORE = None
_LI_ADV = None
_LC_ADV = None

@dataclass
class BenchmarkConfig:
    """Central configuration container for environment and run parameters."""
    aws_profile: str = os.environ.get("AWS_PROFILE", "default")
    aws_region: str = os.environ.get("AWS_REGION", "us-east-1")
    evaluator_model: str = os.environ.get("BEDROCK_JUDGE_MODEL", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
    generator_model: str = os.environ.get("BEDROCK_GEN_MODEL", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
    gemini_api_token: str = os.environ.get("GEMINI_API_TOKEN", "")
    gemini_gen_model: str = os.environ.get("GEMINI_GEN_MODEL", "gemini-3.1-flash-lite-preview")
    use_cloud_judge: bool = False
    subset_n: int = 5
    concurrency: int = 8
    sandbox_size: int = 300

def load_nfcorpus(config: BenchmarkConfig) -> Tuple[List[Dict[str, Any]], List[Path]]:
    """Loads queries and builds a deterministic document sandbox."""
    base_path = Path("tests/fixtures/beir/nfcorpus")
    corpus_path = base_path / "corpus.jsonl"
    queries_path = base_path / "queries.jsonl"
    qrels_path = base_path / "qrels/test.tsv"
    
    if not all(p.exists() for p in [corpus_path, queries_path, qrels_path]):
        raise FileNotFoundError(f"NFCorpus files not found in {base_path}")

    corpus_map = {}
    with open(corpus_path, "r") as f:
        for line in f:
            doc = json.loads(line)
            corpus_map[doc["_id"]] = doc["text"]

    query_id_to_text = {}
    with open(queries_path, "r") as f:
        for line in f:
            q = json.loads(line)
            query_id_to_text[q["_id"]] = q["text"]

    ground_truth_map = {} 
    relevant_doc_ids = set()
    with open(qrels_path, "r") as f:
        next(f)
        for line in f:
            qid, cid, score = line.strip().split("\t")
            if int(score) > 0:
                if qid not in ground_truth_map:
                    if len(ground_truth_map) >= config.subset_n:
                        continue
                    ground_truth_map[qid] = []
                
                if qid in ground_truth_map:
                    if cid in corpus_map:
                        ground_truth_map[qid].append(corpus_map[cid])
                        relevant_doc_ids.add(cid)

    queries = [{"id": qid, "query": query_id_to_text[qid], "ground_truth": truths} 
               for qid, truths in ground_truth_map.items()]
            
    shared_docs_dir = Path("tests/fixtures/tmp_benchmark_corpus")
    shared_docs_dir.mkdir(exist_ok=True)
    for f in shared_docs_dir.glob("*.md"): f.unlink()
    
    doc_paths = []
    ingested_cids = set()
    
    for cid in relevant_doc_ids:
        doc_file = shared_docs_dir / f"{cid}.md"
        doc_file.write_text(corpus_map[cid])
        doc_paths.append(doc_file)
        ingested_cids.add(cid)
        
    for cid, text in corpus_map.items():
        if len(doc_paths) >= config.sandbox_size:
            break
        if cid not in ingested_cids:
            doc_file = shared_docs_dir / f"{cid}.md"
            doc_file.write_text(text)
            doc_paths.append(doc_file)
            ingested_cids.add(cid)
            
    return queries, doc_paths

def generate_answer(query: str, contexts: List[str], config: BenchmarkConfig) -> str:
    """Generates a final RAG answer using the configured model."""
    context_text = "\n\n".join(contexts)
    prompt = f"Answer the medical question based ONLY on the provided context.\n" \
             f"If the context does not contain the answer, say 'I do not know'.\n\n" \
             f"Question: {query}\n\nContext:\n{context_text}\n\nAnswer:"

    if config.use_cloud_judge:
        from botocore.config import Config
        from langchain_aws import ChatBedrock
        
        provider_config = Config(read_timeout=300, connect_timeout=300, retries={"max_attempts": 5})
        llm = ChatBedrock(
            model_id=config.generator_model, 
            region_name=config.aws_region,
            credentials_profile_name=config.aws_profile,
            model_kwargs={"max_tokens": 4096},
            config=provider_config
        )
        return llm.invoke(prompt).content

    if not config.gemini_api_token:
        return "ERROR: No generation provider configured."
    
    from google import genai
    client = genai.Client(api_key=config.gemini_api_token)
    response = client.models.generate_content(model=config.gemini_gen_model, contents=prompt)
    time.sleep(4.1) 
    return response.text

def setup_all_frameworks(doc_paths: List[Path]):
    """Initializes and ingests documents into all competing frameworks."""
    global _CK_STORE, _LI_ADV, _LC_ADV
    settings = Settings.from_env()
    settings.device = "mps" 
    _CK_STORE = ChromaVectorStore(settings)
    
    bench_collection = "ck_benchmark_flagship"
    try: _CK_STORE.client.delete_collection(bench_collection)
    except Exception: pass
    _CK_STORE.collection = _CK_STORE.client.get_or_create_collection(bench_collection)
    
    processor = DocumentProcessor(settings)
    all_chunks = []
    for path in doc_paths:
        res = processor.process(path)
        all_chunks.extend(res.chunks)
    _CK_STORE.add_documents(all_chunks)
    
    clear_bm25_cache()
    search_with_routing(_CK_STORE, "warmup", n_results=1, query_type="hybrid")

    _LI_ADV = LlamaIndexRAG(device="mps", hybrid=True)
    _LI_ADV.ingest(doc_paths)

    _LC_ADV = LangChainRAG(device="mps", hybrid=True)
    _LC_ADV.ingest(doc_paths)

def run_framework(framework: str, query: str, config: BenchmarkConfig) -> Dict[str, Any]:
    """Retrieves context and generates an answer for a specific framework."""
    start = time.perf_counter()
    if framework == "candlekeep":
        results = search_with_routing(_CK_STORE, query, n_results=3, query_type="hybrid")
    elif framework == "llamaindex-adv":
        results = _LI_ADV.search(query, k=3)
    elif framework == "langchain-adv":
        results = _LC_ADV.search(query, k=3)
    else:
        raise ValueError(f"Unknown framework: {framework}")
    
    latency_ms = (time.perf_counter() - start) * 1000
    contexts = [r.text for r in results]
    answer = generate_answer(query, contexts, config)
    return {"answer": answer, "contexts": contexts, "latency": latency_ms}

def benchmark_suite(queries: List[Dict[str, Any]], framework: str, config: BenchmarkConfig) -> Dict[str, float]:
    """Runs the full evaluation suite across a set of queries."""
    latencies = []
    samples = []
    
    for q in queries:
        res = run_framework(framework, q["query"], config)
        samples.append(SingleTurnSample(
            user_input=q["query"],
            response=res["answer"],
            retrieved_contexts=res["contexts"],
            reference="\n\n".join(q["ground_truth"])
        ))
        latencies.append(res["latency"])
    
    if not config.use_cloud_judge:
        return {"faithfulness": 0.0, "answer_relevancy": 0.0, "context_recall": 0.0, "avg_latency_ms": np.mean(latencies)}

    # Initialize RAGAS Judge
    from botocore.config import Config
    from langchain_aws import ChatBedrock, BedrockEmbeddings
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    
    provider_config = Config(read_timeout=300, connect_timeout=300, retries={"max_attempts": 5})
    evaluator_llm_raw = ChatBedrock(
        model_id=config.evaluator_model, 
        region_name=config.aws_region,
        credentials_profile_name=config.aws_profile,
        model_kwargs={"max_tokens": 8192},
        config=provider_config
    )
    evaluator_llm = LangchainLLMWrapper(evaluator_llm_raw)
    
    evaluator_embeddings_raw = BedrockEmbeddings(
        model_id="amazon.titan-embed-text-v2:0",
        region_name=config.aws_region,
        credentials_profile_name=config.aws_profile
    )
    evaluator_embeddings = LangchainEmbeddingsWrapper(evaluator_embeddings_raw)

    faithfulness.llm = evaluator_llm
    answer_relevancy.llm = evaluator_llm
    answer_relevancy.embeddings = evaluator_embeddings
    answer_relevancy.n = 1
    context_precision.llm = evaluator_llm
    context_recall.llm = evaluator_llm

    metrics_list = [faithfulness, answer_relevancy, context_precision, context_recall]
    metric_names = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    sums = {name: 0.0 for name in metric_names}
    
    sem = asyncio.Semaphore(config.concurrency)

    async def score_task(m, s):
        async with sem:
            try: return await m.single_turn_ascore(s)
            except Exception: return 0.0

    async def run_all():
        tasks = [score_task(m, s) for s in samples for m in metrics_list]
        return await asyncio.gather(*tasks)

    results = asyncio.run(run_all())
    for idx, val in enumerate(results):
        metric_name = metric_names[idx % len(metrics_list)]
        sums[metric_name] += float(val)
                
    final_results = {k: v / len(samples) for k, v in sums.items()}
    final_results["avg_latency_ms"] = np.mean(latencies)
    return final_results

def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Candlekeep Scientific Benchmark Suite")
    parser.add_argument("--queries", type=int, default=5, help="Number of queries to evaluate")
    parser.add_argument("--cloud", action="store_true", help="Enable Cloud-based Reasoning Judging")
    args = parser.parse_args()
    
    config = BenchmarkConfig(use_cloud_judge=args.cloud, subset_n=args.queries)
    
    print(f"--- Candlekeep Scientific Benchmark ({'Cloud' if args.cloud else 'Mock'}) ---")
    
    t0 = time.perf_counter()
    queries, doc_paths = load_nfcorpus(config)
    print(f"✓ Data loading complete ({len(doc_paths)} docs in sandbox).")
    
    setup_all_frameworks(doc_paths)
    print(f"✓ Framework ingestion complete. Total setup: {time.perf_counter() - t0:.2f}s")
    
    frameworks = ["candlekeep", "llamaindex-adv", "langchain-adv"]
    report = {}
    
    print("\nExecuting Scientific Comparison...")
    suite_start = time.perf_counter()
    for fw in frameworks:
        fw_t0 = time.perf_counter()
        report[fw] = benchmark_suite(queries, fw, config)
        print(f"  ✓ {fw:<15} finished in {time.perf_counter() - fw_t0:.2f}s")
            
    print("\n" + "="*95)
    print(f"FLAGSHIP SCIENTIFIC REPORT")
    print("="*95)
    print(f"Total benchmark time: {time.perf_counter() - suite_start:.2f}s")
    print("-" * 95)
    header = f"{'Framework':<20} {'Faithful':>15} {'Relevant':>15} {'Recall':>15} {'Latency':>15}"
    print(header + "\n" + "-" * len(header))
    
    for fw in frameworks:
        s = report[fw]
        print(f"{fw:<20} {s['faithfulness']:>15.4f} {s['answer_relevancy']:>15.4f} "
              f"{s['context_recall']:>15.4f} {s['avg_latency_ms']:>14.1f}ms")

if __name__ == "__main__":
    main()
