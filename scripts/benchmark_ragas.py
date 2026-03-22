"""Benchmark Candlekeep vs LlamaIndex vs LangChain (Scientific Quality Version)."""
import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, str(Path.cwd() / "src"))
sys.path.insert(0, str(Path.cwd()))

from candlekeep.config import Settings
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.rag.router import search_with_routing
from candlekeep.database.interface import SearchResult

# Standard evaluation libraries (Stable Ragas 0.3/0.4 API)
# We import the pre-initialized instances from the older module path
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from datasets import Dataset

from scripts.competitors.llamaindex_rag import LlamaIndexRAG
from scripts.competitors.langchain_rag import LangChainRAG


def load_nfcorpus(subset_n: int = 5) -> tuple[List[Dict[str, Any]], List[Path]]:
    """Load NFCorpus queries and REAL ground truth."""
    base_path = Path("tests/fixtures/beir/nfcorpus")
    corpus_path = base_path / "corpus.jsonl"
    queries_path = base_path / "queries.jsonl"
    qrels_path = base_path / "qrels/test.tsv"
    
    if not qrels_path.exists():
        print("Error: NFCorpus files not found.")
        sys.exit(1)

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
    with open(qrels_path, "r") as f:
        next(f)
        for line in f:
            qid, cid, score = line.strip().split("\t")
            if int(score) > 0:
                if qid not in ground_truth_map:
                    ground_truth_map[qid] = []
                if cid in corpus_map:
                    ground_truth_map[qid].append(corpus_map[cid])

    queries = []
    processed_qids = list(ground_truth_map.keys())[:subset_n]
    for qid in processed_qids:
        if qid in query_id_to_text:
            queries.append({
                "id": qid,
                "query": query_id_to_text[qid],
                "ground_truth": ground_truth_map[qid]
            })
            
    shared_docs_dir = Path("tests/fixtures/tmp_benchmark_corpus")
    shared_docs_dir.mkdir(exist_ok=True)
    doc_paths = []
    
    relevant_cids = set()
    for qid in processed_qids:
        with open(qrels_path, "r") as f:
            next(f)
            for line in f:
                row_qid, cid, score = line.strip().split("\t")
                if row_qid == qid and int(score) > 0:
                    relevant_cids.add(cid)

    ingested_count = 0
    for cid in list(relevant_cids):
        if cid in corpus_map:
            doc_file = shared_docs_dir / f"{cid}.md"
            doc_file.write_text(corpus_map[cid])
            doc_paths.append(doc_file)
            ingested_count += 1

    for cid, text in corpus_map.items():
        if ingested_count >= 300:
            break
        if cid not in relevant_cids:
            doc_file = shared_docs_dir / f"{cid}.md"
            doc_file.write_text(text)
            doc_paths.append(doc_file)
            ingested_count += 1
            
    return queries, doc_paths


# Global state
_CK_STORE = None
_LI_COMP = None
_LI_ADV = None
_LC_COMP = None
_LC_ADV = None
_GENAI_CLIENT = None

def get_genai_client():
    global _GENAI_CLIENT
    if _GENAI_CLIENT is None:
        token = os.environ.get("GEMINI_API_TOKEN")
        if token:
            from google import genai
            _GENAI_CLIENT = genai.Client(api_key=token)
    return _GENAI_CLIENT

def generate_answer(query: str, contexts: List[str], local: bool = False) -> str:
    """Generate an answer using Gemini or LM Studio based on context."""
    if local:
        from openai import OpenAI
        client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio", timeout=1200)
        context_text = "\n\n".join(contexts)
        prompt = f"""Answer the following question based ONLY on the provided context. 
If the answer is not in the context, say 'I do not know'.

Question: {query}

Context:
{context_text}

Answer:"""
        try:
            for attempt in range(3):
                try:
                    response = client.chat.completions.create(
                        model="meta-llama-3.1-8b-instruct",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    time.sleep(2.0)
                    return response.choices[0].message.content
                except Exception as e:
                    if "No models loaded" in str(e) and attempt < 2:
                        print(f"    (Waiting for LLM to load in LM Studio...)")
                        time.sleep(10)
                        continue
                    raise e
        except Exception as e:
            return f"Error generating local answer: {e}"

    client = get_genai_client()
    if not client:
        return "Mock answer (no Gemini token)."
    
    context_text = "\n\n".join(contexts)
    prompt = f"""Answer the following question based ONLY on the provided context. 
If the answer is not in the context, say 'I do not know'.

Question: {query}

Context:
{context_text}

Answer:"""
    
    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt
        )
        time.sleep(4.1)
        return response.text
    except Exception as e:
        return f"Error generating answer: {e}"


def setup_all_frameworks(doc_paths: List[Path], local: bool = False):
    global _CK_STORE, _LI_COMP, _LI_ADV, _LC_COMP, _LC_ADV
    settings = Settings.from_env()
    settings.device = "mps"
    _CK_STORE = ChromaVectorStore(settings)
    
    bench_collection_name = "ck_benchmark_scientific"
    try:
        _CK_STORE.client.delete_collection(bench_collection_name)
    except Exception:
        pass
    _CK_STORE.collection = _CK_STORE.client.get_or_create_collection(bench_collection_name)
    
    from candlekeep.rag.processor import DocumentProcessor
    from candlekeep.rag.hybrid import clear_bm25_cache
    processor = DocumentProcessor(settings)
    print(f"  (Ingesting Candlekeep with {len(doc_paths)} docs in batch...)")
    all_chunks = []
    for path in doc_paths:
        result = processor.process(path)
        all_chunks.extend(result.chunks)
    _CK_STORE.add_documents(all_chunks)
    
    clear_bm25_cache()
    print("  (Warming up Candlekeep...)")
    search_with_routing(_CK_STORE, "warmup", n_results=1, query_type="hybrid")

    # Ingest other frameworks
    print("  (Ingesting LlamaIndex Naive...)")
    _LI_COMP = LlamaIndexRAG(device="mps")
    _LI_COMP.ingest(doc_paths)
    
    print("  (Ingesting LlamaIndex Advanced...)")
    _LI_ADV = LlamaIndexRAG(device="mps", hybrid=True)
    _LI_ADV.ingest(doc_paths)

    print("  (Ingesting LangChain Naive...)")
    _LC_COMP = LangChainRAG(device="mps")
    _LC_COMP.ingest(doc_paths)
    
    print("  (Ingesting LangChain Advanced...)")
    _LC_ADV = LangChainRAG(device="mps", hybrid=True)
    _LC_ADV.ingest(doc_paths)


def run_candlekeep(query: str, k: int = 3, local: bool = False) -> Dict[str, Any]:
    start = time.perf_counter()
    results = search_with_routing(_CK_STORE, query, n_results=k, query_type="hybrid")
    latency = time.perf_counter() - start
    contexts = [r.text for r in results]
    answer = generate_answer(query, contexts, local=local)
    return {"answer": answer, "contexts": contexts, "latency": latency}

def run_candlekeep_simple(query: str, k: int = 3, local: bool = False) -> Dict[str, Any]:
    start = time.perf_counter()
    results = _CK_STORE.search(query, n_results=k)
    latency = time.perf_counter() - start
    contexts = [r.text for r in results]
    answer = generate_answer(query, contexts, local=local)
    return {"answer": answer, "contexts": contexts, "latency": latency}

def run_llamaindex(query: str, k: int = 3, local: bool = False) -> Dict[str, Any]:
    start = time.perf_counter()
    results = _LI_COMP.search(query, k=k)
    latency = time.perf_counter() - start
    contexts = [r.text for r in results]
    answer = generate_answer(query, contexts, local=local)
    return {"answer": answer, "contexts": contexts, "latency": latency}

def run_llamaindex_adv(query: str, k: int = 3, local: bool = False) -> Dict[str, Any]:
    start = time.perf_counter()
    results = _LI_ADV.search(query, k=k)
    latency = time.perf_counter() - start
    contexts = [r.text for r in results]
    answer = generate_answer(query, contexts, local=local)
    return {"answer": answer, "contexts": contexts, "latency": latency}

def run_langchain(query: str, k: int = 3, local: bool = False) -> Dict[str, Any]:
    start = time.perf_counter()
    results = _LC_COMP.search(query, k=k)
    latency = time.perf_counter() - start
    contexts = [r.text for r in results]
    answer = generate_answer(query, contexts, local=local)
    return {"answer": answer, "contexts": contexts, "latency": latency}

def run_langchain_adv(query: str, k: int = 3, local: bool = False) -> Dict[str, Any]:
    start = time.perf_counter()
    results = _LC_ADV.search(query, k=k)
    latency = time.perf_counter() - start
    contexts = [r.text for r in results]
    answer = generate_answer(query, contexts, local=local)
    return {"answer": answer, "contexts": contexts, "latency": latency}


def mock_evaluate(samples: List[Dict[str, Any]]):
    import random
    time.sleep(0.2) 
    return {
        "faithfulness": random.uniform(0.7, 0.95),
        "answer_relevancy": random.uniform(0.7, 0.95),
        "context_precision": random.uniform(0.7, 0.95),
        "context_recall": random.uniform(0.7, 0.95),
    }


def benchmark_suite(queries: List[Dict[str, Any]], framework: str, use_mock: bool = True, local: bool = False):
    runner_map = {
        "candlekeep": run_candlekeep,
        "candlekeep-simple": run_candlekeep_simple,
        "llamaindex": run_llamaindex,
        "llamaindex-adv": run_llamaindex_adv,
        "langchain": run_langchain,
        "langchain-adv": run_langchain_adv,
    }
    
    run_fn = runner_map[framework]
    print(f"Benchmarking {framework}...")
    latencies = []
    
    samples_data = []
    for q in queries:
        res = run_fn(q["query"], local=local)
        
        def truncate(text, max_words=300): 
            words = text.split()
            if len(words) > max_words:
                return " ".join(words[:max_words])
            return text

        from ragas.dataset_schema import SingleTurnSample
        sample = SingleTurnSample(
            user_input=q["query"],
            response=res["answer"],
            retrieved_contexts=[truncate(c) for c in res["contexts"]],
            reference=truncate("\n\n".join(q["ground_truth"]))
        )
        samples_data.append(sample)
        latencies.append(res["latency"])
        time.sleep(2.0)
    
    if use_mock:
        score_dict = mock_evaluate(None)
    else:
        # THE PERFECT MANUAL PIPELINE
        # Avoids evaluate() buggy type checks, uses old API instances + Langchain wrapper.
        
        if local:
            print(f"    (Configuring Manual RAGAS stable evaluation for {framework}...)")
            from langchain_openai import ChatOpenAI
            from ragas.llms import LangchainLLMWrapper
            from ragas.embeddings.base import BaseRagasEmbedding
            from openai import OpenAI
            
            # Simple LangChain wrapper does NOT force JSON Schema
            langchain_llm = ChatOpenAI(
                base_url="http://127.0.0.1:1234/v1", 
                api_key="lm-studio",
                model_name="meta-llama-3.1-8b-instruct",
                timeout=1200
            )
            # Ragas 0.4.3 complains about this wrapper during evaluation, but we are bypassing evaluate()!
            evaluator_llm = LangchainLLMWrapper(langchain_llm)
            
            class LocalRagasEmbeddings(BaseRagasEmbedding):
                def __init__(self, base_url, model):
                    super().__init__()
                    self.client = OpenAI(base_url=base_url, api_key="lm-studio", timeout=1200)
                    self.model = model
                def embed_text(self, text: str) -> List[float]:
                    if not isinstance(text, str): text = str(text)
                    res = self.client.embeddings.create(input=text, model=self.model)
                    return res.data[0].embedding
                async def aembed_text(self, text: str) -> List[float]: return self.embed_text(text)
                def embed_query(self, text: str) -> List[float]: return self.embed_text(text)
                def embed_documents(self, texts: List[str]) -> List[List[float]]:
                    return [self.embed_text(t) for t in texts]

            evaluator_embeddings = LocalRagasEmbeddings("http://127.0.0.1:1234/v1", "text-embedding-nomic-embed-text-v1.5")
        else:
            from ragas.llms import llm_factory
            from ragas.embeddings import embedding_factory
            google_key = os.environ.get("GEMINI_API_TOKEN")
            from openai import OpenAI
            g_client = OpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/", api_key=google_key)
            evaluator_llm = llm_factory(model="gemini-3.1-flash-lite-preview", provider="openai", client=g_client)
            evaluator_embeddings = embedding_factory(model="text-embedding-004", provider="openai", client=g_client)

        # Initialize metrics directly into the pre-made stable instances
        faithfulness.llm = evaluator_llm
        answer_relevancy.llm = evaluator_llm
        answer_relevancy.embeddings = evaluator_embeddings
        answer_relevancy.n = 1
        context_precision.llm = evaluator_llm
        context_recall.llm = evaluator_llm

        metrics_list = [faithfulness, answer_relevancy, context_precision, context_recall]
        metric_names = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
        sums = {name: 0.0 for name in metric_names}
        
        print(f"    (Calling RAGAS Manual Loop...)")
        for i, sample in enumerate(samples_data):
            print(f"      - Evaluating sample {i+1}/{len(samples_data)}...")
            for metric, name in zip(metrics_list, metric_names):
                try:
                    import asyncio
                    res = asyncio.run(metric.single_turn_ascore(sample))
                    print(f"        -> {name}: {res}")
                    sums[name] += float(res)
                except Exception as e:
                    print(f"        (Error in {name}: {e})")
                time.sleep(5.0)
                
        score_dict = {k: v / len(samples_data) for k, v in sums.items()}
            
    metrics_dict = {
        "faithfulness": score_dict.get("faithfulness", 0.0),
        "answer_relevancy": score_dict.get("answer_relevancy", 0.0),
        "context_precision": score_dict.get("context_precision", 0.0),
        "context_recall": score_dict.get("context_recall", 0.0),
        "avg_latency_ms": (sum(latencies) / len(latencies)) * 1000
    }
    return metrics_dict


def main():
    parser = argparse.ArgumentParser(description="Candlekeep Scientific Quality Benchmark")
    parser.add_argument("--queries", type=int, default=2, help="Number of queries")
    parser.add_argument("--real", action="store_true", help="Use real Gemini RAGAS")
    parser.add_argument("--local", action="store_true", help="Use local LM Studio RAGAS")
    args = parser.parse_args()
    
    queries, doc_paths = load_nfcorpus(args.queries)
    setup_all_frameworks(doc_paths, local=args.local)
    
    frameworks = ["candlekeep", "candlekeep-simple", "llamaindex", "llamaindex-adv", "langchain", "langchain-adv"]
    
    all_scores = {}
    for fw in frameworks:
        score = benchmark_suite(queries, fw, use_mock=not (args.real or args.local), local=args.local)
        all_scores[fw] = score
        if args.local:
            print(f"  (Cooldown after {fw}...)")
            time.sleep(5.0)
        
    print("\n" + "="*85)
    print("SCIENTIFIC QUALITY BENCHMARK (RAGAS)")
    print("="*85)
    header = f"{'Framework':<20} {'Faithful':>10} {'Relevant':>10} {'Precision':>10} {'Recall':>10} {'Latency':>10}"
    print(header + "\n" + "-" * len(header))
    
    for fw in frameworks:
        s = all_scores[fw]
        print(f"{fw:<20} {s['faithfulness']:>10.4f} {s['answer_relevancy']:>10.4f} "
              f"{s['context_precision']:>10.4f} {s['context_recall']:>10.4f} {s['avg_latency_ms']:>8.1f}ms")


if __name__ == "__main__":
    main()
