
import sys
import os
import json
import time
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.benchmark_hotpotqa import BenchmarkConfig, load_benchmark_queries
from candlekeep.config import Settings
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.database.graph_store import GraphStore
from candlekeep.rag.extractor import get_extractor
from candlekeep.rag.hybrid import _get_sparse_results, reciprocal_rank_fusion

def run_parametrized_search(db, q, config, breadth, neighbor_depth, mentions_limit, score_threshold):
    query = q['query']
    required_titles = {t.lower() for t in q['required_titles']}
    depth = config.path_depth
    
    # Standard 2-way RRF (Baseline)
    vector_results = db.search(query, n_results=25 * 4)
    sparse_results = _get_sparse_results(db, query, 25 * 4)
    fused = reciprocal_rank_fusion(
        [vector_results, sparse_results], k=60, top_n=25 * 4,
    )

    # 1. Extraction
    extractor = get_extractor()
    query_entities = set(extractor.extract(query))

    # 2. Expansion Seeds
    unpaired = set()
    for ent in query_entities:
        neighbors = db.graph_store.get_related(ent, top_n=50)
        is_paired = any(n[0] in query_entities for n in neighbors)
        if not is_paired:
            unpaired.add(ent)

    # 3. Recursive Expansion
    entity_scores = {ent: 1.0 for ent in unpaired}
    to_expand = list(unpaired)
    
    for d in range(depth):
        level_discovered = {}
        for ent in to_expand:
            parent_score = entity_scores[ent]
            neighbors = db.graph_store.get_related(ent, top_n=neighbor_depth)
            for n_ent, jaccard in neighbors:
                if n_ent in query_entities: continue
                path_score = parent_score * jaccard
                if path_score < score_threshold: continue
                if path_score > level_discovered.get(n_ent, 0):
                    level_discovered[n_ent] = path_score
        
        if not level_discovered: break
        for ent, score in level_discovered.items():
            if score > entity_scores.get(ent, 0):
                entity_scores[ent] = score
        to_expand = sorted(level_discovered.keys(), key=lambda x: level_discovered[x], reverse=True)[:breadth]

    # 4. Final Document Gathering
    candidate_docs = {}
    for ent, score in entity_scores.items():
        if ent in query_entities: continue
        mentions = db.graph_store.get_entity_mentions(ent, limit=mentions_limit)
        for doc_id, _ in mentions:
            if score > candidate_docs.get(doc_id, 0):
                candidate_docs[doc_id] = score
    
    sorted_doc_ids = sorted(candidate_docs.keys(), key=lambda x: candidate_docs[x], reverse=True)
    
    # 5. Combine RRF results with Graph results
    m_slots = min(25 - 2, (depth + 1) * 2)
    final_results = fused[:25 - m_slots]
    
    graph_results = []
    if sorted_doc_ids:
        to_fetch = [did for did in sorted_doc_ids][:m_slots]
        res = db.collection.get(ids=to_fetch)
        docs = res.get('documents', [])
        for txt in docs:
            graph_results.append(txt)
            
    context_text = "\n\n".join([r.text for r in final_results] + graph_results).lower()
    found = sum(1 for t in required_titles if t in context_text)
    return found / len(required_titles)

async def sweep():
    config = BenchmarkConfig(dataset="musique", subset_n=50, path_depth=3, sandbox_size=5000)
    queries = load_benchmark_queries(config)
    
    settings = Settings.from_env()
    settings.data_dir = Path(config.ck_dir)
    db = ChromaVectorStore(settings)
    db.collection = db.client.get_collection(f"{config.dataset}_flagship")
    db.graph_store = GraphStore(settings.data_dir / "graph.db")

    base = {"breadth": 5, "neigh": 20, "mentions": 5, "thresh": 0.0}
    knobs = {
        "Expansion Breadth": ("breadth", [5, 10, 15, 20]),
        "Neighbor Depth": ("neigh", [20, 40, 60, 100]),
        "Mention Coverage": ("mentions", [5, 10, 15, 20]),
        "Score Threshold": ("thresh", [0.0, 0.02, 0.05, 0.1])
    }

    print("="*60)
    print(f"SWEEPING MUSIQUE (50 QUERIES, DEPTH 3)")
    print("="*60)

    for label, (key, values) in knobs.items():
        print(f"\nKnob: {label}")
        print(f"{'Value':>10} | {'Hop Rate':>10} | {'Latency':>10}")
        print("-" * 35)
        for val in values:
            p = base.copy()
            p[key] = val
            t0 = time.perf_counter()
            scores = [run_parametrized_search(db, q, config, p["breadth"], p["neigh"], p["mentions"], p["thresh"]) for q in queries]
            lat = (time.perf_counter() - t0) * 1000 / len(queries)
            avg_hop = sum(scores) / len(scores)
            print(f"{val:>10} | {avg_hop:>10.4f} | {lat:>8.1f}ms")

if __name__ == "__main__":
    asyncio.run(sweep())
