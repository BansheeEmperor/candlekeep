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
    """Hybrid search with recursive smart graph expansion."""
    from candlekeep.rag.arcane_recall import expand_results
    from candlekeep.rag.extractor import get_extractor

    m_slots = 2

    # Standard 2-way RRF
    vector_results = db.search(query, n_results=n_results * 4, category=category)
    sparse_results = _get_sparse_results(db, query, n_results * 4, category)
    fused = reciprocal_rank_fusion(
        [vector_results, sparse_results], k=60, top_n=n_results * 4,
    )

    # Graph-based expansion
    extractor = get_extractor()
    query_entities = set(extractor.extract(query))
    
    # 1. Identify unpaired entities in the query
    unpaired = set()
    for ent in query_entities:
        neighbors = db.graph_store.get_related(ent, top_n=50)
        is_paired = any(n[0] in query_entities for n in neighbors)
        if not is_paired:
            unpaired.add(ent)

    # 2. Expand recursively up to 'depth'
    to_expand = unpaired
    discovered_entities = set()
    
    for _ in range(depth):
        level_discovered = set()
        for ent in to_expand:
            neighbors = db.graph_store.get_related(ent, top_n=5)
            for n_ent, _ in neighbors:
                if n_ent not in query_entities and n_ent not in discovered_entities:
                    level_discovered.add(n_ent)
        
        if not level_discovered:
            break
            
        discovered_entities.update(level_discovered)
        to_expand = level_discovered

    # 3. Collect unique documents from discovered entities
    graph_unique = []
    seen_ids = {r.doc_id for r in fused[:n_results - m_slots]}
    
    for ent in discovered_entities:
        mentions = db.graph_store.get_entity_mentions(ent, limit=5)
        for doc_id, _ in mentions:
            if doc_id not in seen_ids:
                # Fetch full doc data
                data = db.collection.get(ids=[doc_id])
                if data['documents']:
                    res = SearchResult(
                        doc_id=doc_id,
                        text=data['documents'][0],
                        metadata=data['metadatas'][0],
                        score=0.1  # Heuristic score for graph matches
                    )
                    graph_unique.append(res)
                    seen_ids.add(doc_id)
            if len(graph_unique) >= m_slots:
                break
        if len(graph_unique) >= m_slots:
            break

    # 4. Fill slots
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
