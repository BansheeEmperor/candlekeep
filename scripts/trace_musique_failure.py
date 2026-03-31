
import sys
import os
import json
import time
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.benchmark_hotpotqa import BenchmarkConfig, load_benchmark_queries, UnifiedLLMBridge
from candlekeep.config import Settings
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.database.graph_store import GraphStore
from candlekeep.rag.router import search_with_routing
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

async def diagnostic():
    config = BenchmarkConfig(dataset="musique", subset_n=50, path_depth=3, sandbox_size=5000)
    queries = load_benchmark_queries(config)
    
    # 1. Load Candlekeep
    settings = Settings.from_env()
    settings.device = "mps"
    settings.data_dir = Path(config.ck_dir)
    ck_store = ChromaVectorStore(settings)
    collection_name = f"{config.dataset}_flagship"
    ck_store.collection = ck_store.client.get_collection(collection_name)
    ck_store.graph_store = GraphStore(settings.data_dir / "graph.db")
    
    # 2. Load LlamaIndex
    li_embed = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5", device="mps")
    li_llm = UnifiedLLMBridge(config)
    li_storage = StorageContext.from_defaults(persist_dir=config.li_dir)
    li_index = load_index_from_storage(storage_context=li_storage, llm=li_llm, embed_model=li_embed)
    li_retriever = li_index.as_retriever(similarity_top_k=config.top_k, path_depth=config.path_depth)

    print(f"Tracing {len(queries)} queries for ranking/recall discrepancies...")
    
    for i, q in enumerate(queries):
        required = set(q['required_titles'])
        
        # CK Search
        ck_res = search_with_routing(ck_store, q['query'], n_results=config.top_k, query_type="explore", depth=config.path_depth)
        ck_all_found = {r.metadata.get('title') for r in ck_res if r.metadata.get('title') in required}
        
        # Enforce 8000 char normalization manually
        curr_chars = 0
        ck_normalized_found = set()
        for r in ck_res:
            txt = r.text
            if curr_chars + len(txt) > 8000: break
            if r.metadata.get('title') in required:
                ck_normalized_found.add(r.metadata.get('title'))
            curr_chars += len(txt)

        # LI Search
        li_nodes = li_retriever.retrieve(q['query'])
        li_all_found = {n.metadata.get('title') for n in li_nodes if n.metadata.get('title') in required}
        
        curr_chars_li = 0
        li_normalized_found = set()
        for n in li_nodes:
            if curr_chars_li + len(n.text) > 8000: break
            if n.metadata.get('title') in required:
                li_normalized_found.add(n.metadata.get('title'))
            curr_chars_li += len(n.text)

        if len(li_normalized_found) > len(ck_normalized_found):
            print(f"\n[{i}] Query: {q['query']}")
            print(f"    Required: {required}")
            print(f"    CK Found (Norm): {ck_normalized_found} ({len(ck_normalized_found)}/{len(required)})")
            print(f"    LI Found (Norm): {li_normalized_found} ({len(li_normalized_found)}/{len(required)})")
            
            if len(ck_all_found) > len(ck_normalized_found):
                print(f"    [!] RANKING ISSUE: CK found it but it was cut off by 8000 char limit.")
                # Show ranks
                for idx, r in enumerate(ck_res):
                    if r.metadata.get('title') in required:
                        print(f"        Rank {idx}: {r.metadata.get('title')} (score {r.score:.4f})")
            else:
                print(f"    [!] RECALL ISSUE: CK graph traversal never reached the missing doc.")
            break

if __name__ == "__main__":
    asyncio.run(diagnostic())
