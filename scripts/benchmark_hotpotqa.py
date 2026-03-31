"""
Scientific Multi-Hop RAG Benchmark (HotpotQA & MuSiQue).

Standardized suite for comparing Candlekeep against LlamaIndex using a normalized 
evaluation methodology:
1.  Context Normalization: Caps retrieved context at 8,000 characters to compare 
    information density/precision rather than raw volume.
2.  Economic Tracking: Measures automated API costs per 1,000 queries to highlight 
    architectural efficiency trade-offs.
3.  Recursive Support: Benchmarks deep reasoning chains (3+ hops) via dataset-aware 
    graph traversal controls.
"""

import argparse
import asyncio
import json
import os
import sys
import time
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple, Set, Optional

import numpy as np
from dotenv import load_dotenv
from datasets import Dataset

# RAGAS 0.4.3
from ragas.dataset_schema import SingleTurnSample
from ragas.metrics import faithfulness, answer_relevancy, context_recall

# Core Framework
sys.path.insert(0, str(Path(__file__).parent.parent))
from candlekeep.config import Settings
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.rag.processor import DocumentProcessor
from candlekeep.rag.hybrid import clear_bm25_cache
from candlekeep.rag.router import search_with_routing

@dataclass
class BenchmarkConfig:
    aws_profile: str = os.environ.get("AWS_PROFILE")
    aws_region: str = os.environ.get("AWS_REGION", "us-east-1")
    
    # Dataset selection: "hotpotqa", "musique"
    dataset: str = "hotpotqa"
    
    # Provider selection: "bedrock", "openai", "gemini"
    provider: str = os.environ.get("HOTPOT_PROVIDER", "bedrock")
    
    # Models
    evaluator_model: str = os.environ.get("BEDROCK_JUDGE_MODEL", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
    generator_model: str = os.environ.get("BEDROCK_GEN_MODEL", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
    
    # Alternative Models (only used if provider is changed)
    openai_model: str = os.environ.get("OPENAI_MODEL", "gpt-4o")
    gemini_model: str = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-exp")
    
    subset_n: int = 5
    sandbox_size: int = 5000
    concurrency: int = 8
    use_cloud: bool = False
    no_recall: bool = False
    skip_li: bool = False
    
    # Hybrid Graph Toggles
    use_mknn: bool = False
    use_orphan_grounding: bool = False
    use_clustering: bool = False
    
    top_k: int = 25 # Initial retrieval k; results are subsequently trimmed by character count.
    
    # Recursive Depth for graph traversal
    # HotpotQA: 1 hop (2 docs)
    # MuSiQue: 2 or 3 hops (3-4 docs)
    path_depth: int = 1
    
    # context_char_limit: Normalizes 'volume' of information across frameworks.
    # Different frameworks return chunks of varying lengths (atomic triplets vs. long prose).
    # 8,000 characters is approximately 2,000 tokens, providing a fair 'information budget'.
    context_char_limit: int = 8000
    
    # Pricing (approximate USD per 1M tokens) for economic efficiency comparison.
    # Enables measuring 'Performance per Dollar' rather than just 'Time'.
    # Haiku 4.5 (Generator): $0.25 input / $1.25 output
    # Sonnet 4.5 (Judge/Retrieval): $3.00 input / $15.00 output
    
    # Storage Paths
    @property
    def storage_dir(self) -> str:
        return f"./storage/{self.dataset}"
    
    @property
    def ck_dir(self) -> str:
        return f"{self.storage_dir}/ck"
    
    @property
    def li_dir(self) -> str:
        return f"{self.storage_dir}/li"

# --- Optimized LlamaIndex Subclass Bridge ---
from llama_index.core.llms import CustomLLM, CompletionResponse, CompletionResponseGen, LLMMetadata, ChatMessage, MessageRole
from llama_index.core.llms.callbacks import llm_completion_callback

class UnifiedLLMBridge(CustomLLM):
    """Bridge to multiple providers with unified cost tracking."""
    model_id: str
    provider: str
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    _llm: Any = None
    _bedrock_client: Any = None
    
    def __init__(self, config: BenchmarkConfig, model_id: Optional[str] = None):
        provider = config.provider.lower()
        if provider == "bedrock":
            actual_model = model_id or config.evaluator_model
        elif provider == "openai":
            actual_model = config.openai_model
        elif provider == "gemini":
            actual_model = config.gemini_model
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        super().__init__(
            model_id=actual_model, 
            provider=provider
        )
        
        if provider == "bedrock":
            import boto3
            from botocore.config import Config
            b_config = Config(
                read_timeout=300, 
                connect_timeout=300, 
                retries={"max_attempts": 10, "mode": "adaptive"}
            )
            session = boto3.Session(profile_name=config.aws_profile)
            self._bedrock_client = session.client("bedrock-runtime", region_name=config.aws_region, config=b_config)
        elif provider == "openai":
            from llama_index.llms.openai import OpenAI
            self._llm = OpenAI(model=self.model_id)
        elif provider == "gemini":
            from llama_index.llms.gemini import Gemini
            self._llm = Gemini(model=f"models/{self.model_id}")

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(context_window=200000, num_output=4096, model_name=self.model_id)

    @llm_completion_callback()
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        if self.provider == "bedrock":
            # DIRECT BOTO3 CALL to avoid LlamaIndex Bedrock bugs
            payload = {
                "anthropic_version": "bedrock-2023-05-31", 
                "max_tokens": 4096, 
                "messages": [{"role": "user", "content": prompt}]
            }
            response = self._bedrock_client.invoke_model(modelId=self.model_id, body=json.dumps(payload))
            body = json.loads(response.get("body").read())
            
            # Track usage
            usage = body.get("usage", {})
            self.total_input_tokens += usage.get("input_tokens", 0)
            self.total_output_tokens += usage.get("output_tokens", 0)
            
            return CompletionResponse(text=body["content"][0]["text"], raw=body)
            
        res = self._llm.complete(prompt, **kwargs)
        
        # Track usage for other providers
        usage = {}
        if self.provider == "openai":
            usage = getattr(res, "raw", {}).get("usage", {})
        elif self.provider == "gemini":
            raw = getattr(res, "raw", None)
            if hasattr(raw, "usage_metadata"):
                usage = {
                    "input_tokens": raw.usage_metadata.prompt_token_count,
                    "output_tokens": raw.usage_metadata.candidates_token_count
                }

        self.total_input_tokens += usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0)
        self.total_output_tokens += usage.get("output_tokens", 0) or usage.get("completion_tokens", 0)
        
        return res

    @llm_completion_callback()
    async def acomplete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        if self.provider == "bedrock":
            # Bedrock doesn't implement acomplete, so we wrap direct sync in a thread
            return await asyncio.to_thread(self.complete, prompt, **kwargs)

        res = await self._llm.acomplete(prompt, **kwargs)
        
        # Usage tracking for async
        usage = {}
        if self.provider == "openai":
            usage = getattr(res, "raw", {}).get("usage", {})
        elif self.provider == "gemini":
            raw = getattr(res, "raw", None)
            if hasattr(raw, "usage_metadata"):
                usage = {
                    "input_tokens": raw.usage_metadata.prompt_token_count,
                    "output_tokens": raw.usage_metadata.candidates_token_count
                }

        self.total_input_tokens += usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0)
        self.total_output_tokens += usage.get("output_tokens", 0) or usage.get("completion_tokens", 0)
        
        return res

    def get_cost(self) -> float:
        """Calculate cost in USD based on tracked tokens."""
        m = self.model_id.lower()
        if "sonnet-4-5" in m:
            in_p, out_p = 3.00, 15.00
        elif "haiku-4-5" in m:
            in_p, out_p = 0.25, 1.25
        elif "gpt-4o" in m:
            in_p, out_p = 2.50, 10.00
        elif "gemini-2.0-flash" in m:
            in_p, out_p = 0.10, 0.40
        else:
            in_p, out_p = 1.00, 1.00 # Default fallback
            
        return (self.total_input_tokens * in_p / 1_000_000) + (self.total_output_tokens * out_p / 1_000_000)

    def reset_metrics(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    @llm_completion_callback()
    def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
        raise NotImplementedError()

def load_benchmark_queries(config: BenchmarkConfig) -> List[Dict[str, Any]]:
    """Loads query data and ground truth mappings for selected dataset."""
    base_path = Path(f"tests/fixtures/beir/{config.dataset}")
    corpus_path = base_path / "corpus.jsonl"
    queries_path = base_path / "queries.jsonl"
    qrels_path = base_path / "qrels/test.tsv"

    corpus_map = {}
    title_map = {}
    with open(corpus_path, "r") as f:
        for line in f:
            doc = json.loads(line)
            corpus_map[doc["_id"]] = doc["text"]
            title_map[doc["_id"]] = doc.get("title", doc["_id"])

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
                    if len(ground_truth_map) >= config.subset_n: continue
                    ground_truth_map[qid] = []
                ground_truth_map[qid].append(cid)

    queries = []
    for qid, cids in ground_truth_map.items():
        queries.append({
            "id": qid,
            "query": query_id_to_text[qid],
            "required_titles": [title_map[cid] for cid in cids if cid in title_map],
            "ground_truth": [{"text": corpus_map[cid]} for cid in cids if cid in corpus_map]
        })
    return queries

def ingest_phase(config: BenchmarkConfig):
    """Phase 1: Build the Sandbox and Persist all Indexes."""
    print(f"--- Phase 1: Ingestion & Index Persistence ({config.dataset}) ---")
    
    # 1. Build Sandbox
    queries = load_benchmark_queries(config)
    required_doc_ids = set()
    for q in queries:
        for doc in q['ground_truth']:
            # We need to find the ID for this text to match corpus_map
            # But we can just use the required_titles and map them back if needed,
            # or better, just store the IDs in the query object.
            pass

    # Re-map queries to get required IDs easily
    base_path = Path(f"tests/fixtures/beir/{config.dataset}")
    qrels_path = base_path / "qrels/test.tsv"
    corpus_path = base_path / "corpus.jsonl"
    
    query_ids = {q['id'] for q in queries}
    required_doc_ids = set()
    with open(qrels_path, "r") as f:
        next(f)
        for line in f:
            qid, cid, score = line.strip().split("\t")
            if qid in query_ids and int(score) > 0:
                required_doc_ids.add(cid)

    corpus_map = {}
    with open(corpus_path, "r") as f:
        for line in f:
            doc = json.loads(line)
            corpus_map[doc["_id"]] = doc["text"]

    sandbox_dir = Path(f"tests/fixtures/{config.dataset}_sandbox")
    sandbox_dir.mkdir(exist_ok=True)
    for f in sandbox_dir.glob("*.md"): f.unlink()

    doc_paths = []
    for cid in required_doc_ids:
        if cid in corpus_map:
            doc_file = sandbox_dir / f"{cid.replace('/', '_')}.md"
            doc_file.write_text(corpus_map[cid])
            doc_paths.append(doc_file)

    for cid, text in corpus_map.items():
        if len(doc_paths) >= config.sandbox_size: break
        if cid not in required_doc_ids:
            doc_file = sandbox_dir / f"{cid.replace('/', '_')}.md"
            doc_file.write_text(text)
            doc_paths.append(doc_file)

    # 2. Ingest Candlekeep
    print("  (Ingesting Candlekeep...)")
    os.environ["CANDLEKEEP_MIN_COOCCURRENCE"] = "1"
    os.environ["CANDLEKEEP_USE_MKNN"] = "true" if config.use_mknn else "false"
    os.environ["CANDLEKEEP_USE_ORPHAN_GROUNDING"] = "true" if config.use_orphan_grounding else "false"
    os.environ["CANDLEKEEP_USE_CLUSTERING"] = "true" if config.use_clustering else "false"
    
    settings = Settings.from_env()
    settings.device = "mps"
    settings.data_dir = Path(config.ck_dir)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    store = ChromaVectorStore(settings)
    collection_name = f"{config.dataset}_flagship"
    try: store.client.delete_collection(collection_name)
    except: pass
    store.collection = store.client.get_or_create_collection(collection_name)
    processor = DocumentProcessor(settings)
    all_chunks = []
    for path in doc_paths:
        res = processor.process(path)
        all_chunks.extend(res.chunks)
    # Initialize LLM bridge for Alias Linker if needed
    llm = None
    if os.environ.get("CANDLEKEEP_ALIAS_LINKER", "false").lower() == "true":
        llm = UnifiedLLMBridge(config)

    store.add_documents(all_chunks, llm=llm)

    # 3. Ingest LlamaIndex
    if not config.skip_li:
        print(f"  (Ingesting LlamaIndex Graph for {len(doc_paths)} docs...)")
        from llama_index.core import PropertyGraphIndex, Document
        from llama_index.core.indices.property_graph import SimpleLLMPathExtractor
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        
        documents = [Document(text=p.read_text(), id_=p.stem, metadata={"file_name": p.name}) for p in doc_paths]
        li_llm = UnifiedLLMBridge(config)
        li_embed = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5", device="mps")
        extractor = SimpleLLMPathExtractor(llm=li_llm, max_paths_per_chunk=10, num_workers=8)
        
        # Stable pattern: Let PropertyGraphIndex handle the orchestration
        # We use show_progress to keep the socket alive and see what's happening
        index = PropertyGraphIndex.from_documents(
            documents,
            llm=li_llm,
            embed_model=li_embed,
            property_graph_extractors=[extractor],
            show_progress=True
        )
        
        shutil.rmtree(config.li_dir, ignore_errors=True)
        os.makedirs(config.li_dir, exist_ok=True)
        index.storage_context.persist(persist_dir=config.li_dir)
    
    print("  ✓ All Indexes Persisted.")

def generate_answer(query: str, contexts: List[str], config: BenchmarkConfig) -> str:
    """Generate answer using selected LLM provider."""
    context_text = "\n\n".join(contexts)
    prompt = f"Answer the medical question based ONLY on the provided context.\n" \
             f"If the answer is not in the context, say 'I do not know'.\n\n" \
             f"Question: {query}\n\nContext:\n{context_text}\n\nAnswer:"

    if config.use_cloud:
        bridge = UnifiedLLMBridge(config, model_id=config.generator_model)
        return bridge.complete(prompt).text
    return "Mock Answer"

def benchmark_phase(config: BenchmarkConfig):
    """Phase 2: Load and Benchmark."""
    print(f"--- Phase 2: Scientific Benchmarking ({config.dataset}) ---")
    
    if config.no_recall:
        os.environ["CANDLEKEEP_NO_RECALL"] = "true"
        print("  ⚠ Arcane Recall (Context Expansion) DISABLED for this run.")
    else:
        os.environ["CANDLEKEEP_NO_RECALL"] = "false"

    queries = load_benchmark_queries(config)
    
    # 1. Load Candlekeep
    settings = Settings.from_env()
    settings.device = "mps"
    settings.data_dir = Path(config.ck_dir)
    ck_store = ChromaVectorStore(settings)
    
    # Use a dataset-specific collection name
    collection_name = f"{config.dataset}_flagship"
    ck_store.collection = ck_store.client.get_or_create_collection(collection_name)

    # Initialize graph store
    from candlekeep.database.graph_store import GraphStore
    ck_store.graph_store = GraphStore(settings.data_dir / "graph.db")

    # Warmup Candlekeep (Pre-load spaCy and BM25)
    print("  🕯 Pre-loading Candlekeep (spaCy/BM25)...")
    search_with_routing(ck_store, "warmup query", n_results=1, query_type="explore")
    
    # 2. Load LlamaIndex (LEAN CONFIGURATION)
    li_llm = None
    if not config.skip_li:
        from llama_index.core import StorageContext, load_index_from_storage
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        
        li_embed = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5", device="mps")
        li_llm = UnifiedLLMBridge(config)
        li_storage = StorageContext.from_defaults(persist_dir=config.li_dir)
        # MUST PASS LLM HERE AS WELL
        li_index = load_index_from_storage(storage_context=li_storage, llm=li_llm, embed_model=li_embed)
        
        # Use Default Retriever (includes LLM Synonym Expansion) for true out-of-the-box comparison
        li_retriever = li_index.as_retriever(
            similarity_top_k=config.top_k,
            path_depth=config.path_depth
        )
    else:
        li_retriever = None

    def calculate_hop(contexts, titles):
        text = "\n\n".join(contexts).lower()
        return sum(1 for t in titles if t.lower() in text) / len(titles)

    def run_eval(framework, runner, queries):
        print(f"  Evaluating {framework}...")
        results_data = []
        retrieval_cost = 0.0
        
        # Reset cost tracking for LlamaIndex LLM if applicable
        if hasattr(li_llm, 'reset_metrics'):
            li_llm.reset_metrics()

        for q in queries:
            t0 = time.perf_counter()
            if framework == "candlekeep":
                res = search_with_routing(runner, q['query'], n_results=config.top_k, query_type="explore", depth=config.path_depth)
                raw_contexts = [r.text for r in res]
            elif framework == "llamaindex-graph-only":
                nodes = runner.retrieve(q['query'])
                raw_contexts = [n.text for n in nodes]
            else:
                nodes = runner.retrieve(q['query'])
                raw_contexts = [n.text for n in nodes]
            
            # NORMALIZATION: Limit context by character count
            contexts = []
            curr_chars = 0
            for ctx in raw_contexts:
                if curr_chars + len(ctx) > config.context_char_limit:
                    # Optional: Add partial chunk if we want to be strict on token count
                    remaining = config.context_char_limit - curr_chars
                    if remaining > 100: # Only bother if substantial
                        contexts.append(ctx[:remaining])
                    break
                contexts.append(ctx)
                curr_chars += len(ctx)

            lat = (time.perf_counter() - t0) * 1000
            hop = calculate_hop(contexts, q['required_titles'])
            
            print(f"    Generating answer for query: {q['query'][:50]}...")
            answer = generate_answer(q['query'], contexts, config)
            results_data.append({
                "latency": lat, 
                "hop": hop, 
                "contexts": contexts, 
                "q": q, 
                "answer": answer,
                "chars": curr_chars
            })
        
        # Total cost for this framework's retrieval phase
        if "llamaindex" in framework:
            retrieval_cost = li_llm.get_cost()
            
        return results_data, retrieval_cost

    frameworks = {
        "Candlekeep-Explore": (ck_store, "candlekeep"), 
    }
    if not config.skip_li:
        frameworks["LlamaIndex-Graph"] = (li_retriever, "llamaindex")
    
    final_report = {}
    for name, (runner, type_id) in frameworks.items():
        data, cost = run_eval(type_id, runner, queries)
        
        # Scoring
        from ragas.llms import LangchainLLMWrapper
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from langchain_aws import ChatBedrock, BedrockEmbeddings
        from botocore.config import Config
        b_config = Config(read_timeout=300, connect_timeout=300, retries={"max_attempts": 5})
        judge = LangchainLLMWrapper(ChatBedrock(
            model_id=config.evaluator_model, 
            region_name=config.aws_region, 
            credentials_profile_name=config.aws_profile, 
            config=b_config,
            model_kwargs={"max_tokens": 4096}
        ))
        embed = LangchainEmbeddingsWrapper(BedrockEmbeddings(model_id="amazon.titan-embed-text-v2:0", region_name=config.aws_region, credentials_profile_name=config.aws_profile))
        
        faithfulness.llm, answer_relevancy.llm, context_recall.llm = judge, judge, judge
        answer_relevancy.embeddings = embed
        
        samples = [SingleTurnSample(user_input=d['q']['query'], response=d['answer'], retrieved_contexts=d['contexts'], reference="\n\n".join([doc["text"] for doc in d['q']['ground_truth']])) for d in data]
        
        async def score_all():
            tasks = [m.single_turn_ascore(s) for s in samples for m in [faithfulness, answer_relevancy, context_recall]]
            return await asyncio.gather(*tasks)
        
        scores = asyncio.run(score_all())
        final_report[name] = {
            "latency": np.mean([d['latency'] for d in data]), 
            "hop": np.mean([d['hop'] for d in data]), 
            "faithful": np.mean(scores[0::3]), 
            "relevant": np.mean(scores[1::3]),
            "cost": cost / len(queries) if len(queries) > 0 else 0, # Avg cost per query
            "chars": np.mean([d['chars'] for d in data])
        }

    print("\n" + "="*115 + "\nHOTPOTQA SCIENTIFIC REPORT (Decoupled, Normalized & Cost-Aware)\n" + "="*115)
    header = f"{'Framework':<22} {'Hop Rate':>10} {'Faithful':>10} {'Relevant':>10} {'Latency':>10} {'Cost/1k':>10} {'Chars':>10}"
    print(header + "\n" + "-" * len(header))
    for n, s in final_report.items():
        print(f"{n:<22} {s['hop']:>10.4f} {s['faithful']:>10.4f} {s['relevant']:>10.4f} {s['latency']:>8.1f}ms ${s['cost']*1000:>8.2f} {s['chars']:>10.0f}")

def main():
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--ingest", action="store_true")
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--queries", type=int, default=5)
    parser.add_argument("--sandbox", type=int, default=5000)
    parser.add_argument("--no-recall", action="store_true")
    parser.add_argument("--cloud", action="store_true")
    parser.add_argument("--provider", type=str, default="bedrock", choices=["bedrock", "openai", "gemini"])
    parser.add_argument("--dataset", type=str, default="hotpotqa", choices=["hotpotqa", "musique"])
    parser.add_argument("--depth", type=int, default=1, help="Recursive traversal depth")
    parser.add_argument("--skip-li", action="store_true", help="Skip LlamaIndex ingestion/benchmark")
    
    # Hybrid Graph Flags
    parser.add_argument("--mknn", action="store_true", help="Enable Mutual K-Nearest Neighbors links")
    parser.add_argument("--og", action="store_true", help="Enable Orphan Grounding (vector search for unlinked entities)")
    parser.add_argument("--ec", action="store_true", help="Enable Entity Clustering (semantic canonicalization)")
    
    parser.add_argument("--eval-model", type=str, help="Override evaluator model ID")
    parser.add_argument("--gen-model", type=str, help="Override generator model ID")
    args = parser.parse_args()
    
    config = BenchmarkConfig(
        subset_n=args.queries, 
        sandbox_size=args.sandbox, 
        no_recall=args.no_recall, 
        use_cloud=args.cloud,
        provider=args.provider,
        dataset=args.dataset,
        path_depth=args.depth,
        skip_li=args.skip_li,
        use_mknn=args.mknn,
        use_orphan_grounding=args.og,
        use_clustering=args.ec
    )
    if args.eval_model: config.evaluator_model = args.eval_model
    if args.gen_model: config.generator_model = args.gen_model
    
    if args.ingest: ingest_phase(config)
    if args.benchmark: benchmark_phase(config)

if __name__ == "__main__":
    main()
