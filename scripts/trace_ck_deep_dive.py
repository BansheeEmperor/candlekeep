
import sys
import os
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.benchmark_hotpotqa import BenchmarkConfig, load_benchmark_queries
from candlekeep.config import Settings
from candlekeep.database.vector_store import ChromaVectorStore
from candlekeep.database.graph_store import GraphStore
from candlekeep.rag.extractor import get_extractor

def trace_query(db, q, config, file_to_ids):
    query = q['query']
    required_titles = set(q['required_titles'])
    required_slugs = set(q['required_slugs'])
    
    # Identify required IDs by partial filename matching
    required_ids = set()
    for fname, ids in file_to_ids.items():
        for slug in required_slugs:
            if slug in fname:
                required_ids.update(ids)
    
    depth = config.path_depth
    n_results = config.top_k
    m_slots = min(n_results - 2, (depth + 1) * 2)

    print(f"\n" + "="*80)
    print(f"QUERY: {query}")
    print(f"REQUIRED: {required_titles}")
    
    # 1. Extraction
    extractor = get_extractor()
    query_entities = set(extractor.extract(query))
    print(f"STEP 1: Extracted Entities -> {query_entities}")

    # 2. Graph Seeds
    unpaired = set()
    for ent in query_entities:
        neighbors = db.graph_store.get_related(ent, top_n=50)
        is_paired = any(n[0] in query_entities for n in neighbors)
        if not is_paired:
            unpaired.add(ent)
    print(f"STEP 2: Expansion Seeds (Unpaired) -> {unpaired}")

    # 3. Recursive Expansion
    entity_scores = {ent: 1.0 for ent in unpaired}
    to_expand = list(unpaired)
    
    trace_found_docs = set()
    
    for d in range(depth):
        print(f"  HOP {d+1}: Expanding {len(to_expand)} entities...")
        level_discovered = {}
        for ent in to_expand:
            parent_score = entity_scores[ent]
            neighbors = db.graph_store.get_related(ent, top_n=20)
            for n_ent, jaccard in neighbors:
                if n_ent in query_entities: continue
                path_score = parent_score * jaccard
                if path_score > level_discovered.get(n_ent, 0):
                    level_discovered[n_ent] = path_score
        
        if not level_discovered:
            print("    -> No more neighbors found.")
            break
            
        for ent, score in level_discovered.items():
            if score > entity_scores.get(ent, 0):
                entity_scores[ent] = score
        
        # Check if we've found any required docs at this level
        for ent in level_discovered:
            mentions = db.graph_store.get_entity_mentions(ent, limit=10)
            for doc_id, _ in mentions:
                if doc_id in required_ids:
                    # Map doc_id back to title
                    data = db.collection.get(ids=[doc_id])
                    fname = data['metadatas'][0].get('filename', '')
                    for rt in required_titles:
                        if rt.lower().replace(' ', '_') in fname:
                            trace_found_docs.add(rt)
        
        to_expand = sorted(level_discovered.keys(), key=lambda x: level_discovered[x], reverse=True)[:5]

    # 4. Final Result check
    candidate_docs = {}
    for ent, score in entity_scores.items():
        if ent in query_entities: continue
        mentions = db.graph_store.get_entity_mentions(ent, limit=5)
        for doc_id, _ in mentions:
            if score > candidate_docs.get(doc_id, 0):
                candidate_docs[doc_id] = score
    
    sorted_doc_ids = sorted(candidate_docs.keys(), key=lambda x: candidate_docs[x], reverse=True)[:m_slots]
    final_titles = set()
    if sorted_doc_ids:
        data = db.collection.get(ids=sorted_doc_ids)
        for m in data['metadatas']:
            if m:
                fname = m.get('filename', '')
                for rt in required_titles:
                    if rt.lower().replace(' ', '_') in fname:
                        final_titles.add(rt)

    print(f"STEP 3: Result Summary")
    # Fetch final results as explore_search would
    from candlekeep.rag.router import search_with_routing
    ck_res = search_with_routing(db, query, n_results=n_results, query_type="explore", depth=depth)
    
    # Use benchmark-style string matching for verification
    context_text = "\n\n".join([r.text for r in ck_res]).lower()
    found_titles = {t for t in required_titles if t.lower() in context_text}
    
    print(f"    Titles found in context: {found_titles}")
    print(f"    Missed: {required_titles - found_titles}")
    
    return {
        "success": required_titles.issubset(found_titles),
        "partial": len(found_titles) > 0,
        "missed": required_titles - found_titles,
        "found": found_titles,
        "extraction_failed": len(query_entities) == 0,
        "expansion_depth": depth
    }

def main():
    config = BenchmarkConfig(dataset="musique", subset_n=50, path_depth=3, sandbox_size=5000)
    queries = load_benchmark_queries(config)
    
    settings = Settings.from_env()
    settings.data_dir = Path(config.ck_dir)
    db = ChromaVectorStore(settings)
    db.collection = db.client.get_collection(f"{config.dataset}_flagship")
    db.graph_store = GraphStore(settings.data_dir / "graph.db")

    # Build filename -> IDs map from the ACTUAL SANDBOX FILES
    print("Building filename map from musique_sandbox...")
    sandbox_dir = Path("tests/fixtures/musique_sandbox")
    file_to_ids = {}
    
    # We need to map the filenames in the sandbox to IDs in Chroma
    # Since we can't easily guess the IDs, we'll fetch from Chroma and match by metadata source
    all_data = db.collection.get(include=['metadatas'])
    print(f"Chroma Collection Size: {len(all_data['ids'])}")
    
    for did, meta in zip(all_data['ids'], all_data['metadatas']):
        fname = meta.get('filename')
        if fname:
            if fname not in file_to_ids: file_to_ids[fname] = []
            file_to_ids[fname].append(did)

    print(f"File map size: {len(file_to_ids)}")

    stats = {"total": 0, "full_success": 0, "partial_success": 0, "total_miss": 0, "extraction_failures": 0}
    
    for q in queries:
        required_fnames = []
        for t in q['required_titles']:
            slug = t.replace(' ', '_').replace('/', '_').lower()
            required_fnames.append(slug)
        
        q['required_slugs'] = required_fnames
        res = trace_query(db, q, config, file_to_ids)
        stats["total"] += 1
        if res["success"]: stats["full_success"] += 1
        elif res["partial"]: stats["partial_success"] += 1
        else: stats["total_miss"] += 1
        if res["extraction_failed"]: stats["extraction_failures"] += 1

    print("\n" + "#"*40)
    print("CANDLEKEEP DEEP-DIVE TRACE STATS")
    print("#"*40)
    for k, v in stats.items():
        print(f"{k:<20}: {v}")

if __name__ == "__main__":
    main()
