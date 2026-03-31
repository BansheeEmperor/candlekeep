"""Lexical search and rank fusion for hybrid retrieval."""
import re
from typing import List
import logging
from rank_bm25 import BM25Okapi
from candlekeep.database.interface import SearchResult

logger = logging.getLogger(__name__)

# Regex for word tokenization used in normalization
_WORD_RE = re.compile(r"\w+")

# Common English stop words — filtered from BM25 to focus on technical tokens.
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "if", "in",
    "into", "is", "it", "no", "not", "of", "on", "or", "such", "that", "the",
    "their", "then", "there", "these", "they", "this", "to", "was", "will", "with"
}

_bm25_cache = None
_corpus_ids = None

def clear_bm25_cache():
    """Clear BM25 cache when the database is repopulated."""
    global _bm25_cache, _corpus_ids
    _bm25_cache = None
    _corpus_ids = None

def update_bm25_cache(db):
    """Lazily initialize BM25 on the full corpus."""
    global _bm25_cache, _corpus_ids
    if _bm25_cache is not None:
        return _bm25_cache, _corpus_ids

    # Fetch ALL documents from ChromaDB
    results = db.collection.get()
    documents = results['documents']
    _corpus_ids = results['ids']
    metadatas = results['metadatas']

    # Tokenize corpus
    tokenized_corpus = [_tokenize(doc) for doc in documents]
    _bm25_cache = BM25Okapi(tokenized_corpus)
    return _bm25_cache, _corpus_ids

def _tokenize(text: str) -> List[str]:
    """Surgical tokenization for technical documentation."""
    # Preserves: versions (v1.2), flags (--flag), paths (/var/log)
    tokens = re.findall(r"[\w\-\.]+", text.lower())
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 1]

def reciprocal_rank_fusion(results_lists: List[List[SearchResult]], k: int = 60, top_n: int = 5) -> List[SearchResult]:
    """Combines multiple search rankings using Reciprocal Rank Fusion."""
    scores = {}
    doc_map = {}

    for results in results_lists:
        for rank, res in enumerate(results):
            if res.doc_id not in scores:
                scores[res.doc_id] = 0.0
                doc_map[res.doc_id] = res
            scores[res.doc_id] += 1.0 / (k + rank + 1)

    sorted_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
    
    final_results = []
    for doc_id, score in sorted_ids:
        res = doc_map[doc_id]
        res.score = score  # Overwrite with fused score
        final_results.append(res)
    
    return final_results

def _get_sparse_results(db, query: str, n_results: int, category: str | None = None) -> List[SearchResult]:
    """Get sparse (BM25) results."""
    bm25, corpus_ids = update_bm25_cache(db)
    tokenized_query = _tokenize(query)
    scores = bm25.get_scores(tokenized_query)
    
    # Map back to SearchResult
    top_indices = scores.argsort()[::-1][:n_results * 2] # Fetch extra for category filtering
    results = []
    for idx in top_indices:
        if scores[idx] <= 0: continue
        
        doc_id = corpus_ids[idx]
        # We need the metadata/text for SearchResult
        # For efficiency, we only fetch what we need
        data = db.collection.get(ids=[doc_id])
        if not data['documents']: continue
        
        res = SearchResult(
            doc_id=doc_id,
            text=data['documents'][0],
            metadata=data['metadatas'][0],
            score=float(scores[idx])
        )
        if category and res.metadata.get("category") != category:
            continue
        results.append(res)
        if len(results) >= n_results: break
        
    return results

def hybrid_search(db, query: str, n_results: int = 5, category: str | None = None) -> List[SearchResult]:
    """ रोड 1: HYBRID (Vector + Sparse BM25). """
    # 1. Vector Search
    vector_results = db.search(query, n_results=n_results * 4, category=category)
    
    # 2. Sparse Search (BM25)
    sparse_results = _get_sparse_results(db, query, n_results * 4, category)
    
    # 3. Combine with RRF (2-way: vector + sparse)
    fused_results = reciprocal_rank_fusion(
        [vector_results, sparse_results], k=60, top_n=n_results * 4,
    )
    
    # 5. Apply Arcane Recall (context expansion)
    import os
    # Benchmarking ablation: skip expansion if isolation is requested
    if os.environ.get("CANDLEKEEP_NO_RECALL", "false").lower() == "true":
        return fused_results[:n_results]
        
    from candlekeep.rag.arcane_recall import expand_results
    expanded = expand_results(db, fused_results, n_results=n_results, query=query)
    
    return expanded

def explore_search(
    db,
    query: str,
    n_results: int = 5,
    category: str | None = None,
    depth: int = 1,
) -> List[SearchResult]:
    """Hybrid search with recursive smart graph expansion and path scoring.

    1. Extract entities from query.
    2. Identify unpaired entities (co-occurring partners not in query).
    3. Recursively expand entities up to 'depth' with Path Scoring.
    4. Dynamically allocate M slots for graph results based on depth.
    5. Fill slots with unique graph docs sorted by cumulative path similarity.
    """
    from candlekeep.rag.arcane_recall import expand_results
    from candlekeep.rag.extractor import get_extractor

    # Dynamic slots: ensure enough room for deep chains, but keep RRF anchor
    # e.g. depth 1 (2-hop) -> 3 slots; depth 3 (4-hop) -> 6 slots
    m_slots = min(n_results - 2, (depth + 1) * 2)

    # Standard 2-way RRF
    vector_results = db.search(query, n_results=n_results * 4, category=category)
    sparse_results = _get_sparse_results(db, query, n_results * 4, category)
    fused = reciprocal_rank_fusion(
        [vector_results, sparse_results], k=60, top_n=n_results * 4,
    )

    # Graph-based expansion
    extractor = get_extractor()
    query_entities = set(extractor.extract(query))
    
    # 1. Identify "seeds" for expansion: entities in the query
    # We prioritize expansion for entities that don't have their co-occurring 
    # partners already present in the query (unpaired).
    unpaired = set()
    for ent in query_entities:
        neighbors = db.graph_store.get_related(ent, top_n=50)
        is_paired = any(n[0] in query_entities for n in neighbors)
        if not is_paired:
            unpaired.add(ent)

    # 2. Expand recursively with Path Scoring
    # entity_scores: {entity: cumulative_jaccard_score}
    entity_scores = {ent: 1.0 for ent in unpaired}
    to_expand = list(unpaired)
    
    for _ in range(depth):
        level_discovered = {}
        for ent in to_expand:
            parent_score = entity_scores[ent]
            # Large fan-out for reranking
            neighbors = db.graph_store.get_related(ent, top_n=20)
            for n_ent, jaccard in neighbors:
                if n_ent in query_entities: continue
                
                # Path Scoring: Score = Path Similarity * Edge Similarity
                path_score = parent_score * jaccard
                if path_score > level_discovered.get(n_ent, 0):
                    level_discovered[n_ent] = path_score
        
        if not level_discovered:
            break
            
        # Merge level results into main score map
        for ent, score in level_discovered.items():
            if score > entity_scores.get(ent, 0):
                entity_scores[ent] = score
        
        # Next level expansion: follow only the top paths to control noise
        to_expand = sorted(level_discovered.keys(), key=lambda x: level_discovered[x], reverse=True)[:5]

    # 3. Collect unique documents from discovered entities
    # doc_id -> highest path score that reached it
    candidate_docs = {}
    for ent, score in entity_scores.items():
        if ent in query_entities: continue # Don't pull query docs into graph slots
        
        mentions = db.graph_store.get_entity_mentions(ent, limit=5)
        for doc_id, _ in mentions:
            if score > candidate_docs.get(doc_id, 0):
                candidate_docs[doc_id] = score

    # Sort candidate documents by their best path score
    sorted_doc_ids = sorted(candidate_docs.keys(), key=lambda x: candidate_docs[x], reverse=True)
    
    graph_unique = []
    seen_ids = {r.doc_id for r in fused[:n_results - m_slots]}
    
    # 4. Fill slots with batch-fetched docs for efficiency
    if sorted_doc_ids:
        to_fetch = [did for did in sorted_doc_ids if did not in seen_ids][:m_slots * 2]
        if to_fetch:
            data = db.collection.get(ids=to_fetch)
            doc_data_map = {did: (txt, meta) for did, txt, meta in zip(data['ids'], data['documents'], data['metadatas'])}
            
            for did in to_fetch:
                if did in doc_data_map:
                    txt, meta = doc_data_map[did]
                    res = SearchResult(
                        doc_id=did,
                        text=txt,
                        metadata=meta,
                        score=candidate_docs[did] # Graph-specific path score
                    )
                    graph_unique.append(res)
                    if len(graph_unique) >= m_slots:
                        break

    # 5. Combine RRF results with Graph results
    final = fused[:n_results - m_slots]
    final.extend(graph_unique)
    
    # Backfill if graph didn't find enough unique results
    if len(final) < n_results:
        used_ids = {r.doc_id for r in final}
        for r in fused[n_results - m_slots:]:
            if r.doc_id not in used_ids:
                final.append(r)
                used_ids.add(r.doc_id)
            if len(final) >= n_results:
                break

    import os
    # Benchmarking ablation: skip expansion if isolation is requested
    if os.environ.get("CANDLEKEEP_NO_RECALL", "false").lower() == "true":
        return final[:n_results]

    expanded = expand_results(db, final, n_results=n_results, query=query)
    return expanded
