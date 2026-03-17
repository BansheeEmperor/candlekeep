"""Query-time graph augmentation: entity lookup → related chunks for the explore path."""
from candlekeep.database.interface import SearchResult, VectorDatabase
from candlekeep.database.graph_store import GraphStore


def get_graph_chunks(
    db: VectorDatabase,
    graph_store: GraphStore,
    query: str,
    n_results: int = 5,
    entity_filter: list[str] | None = None,
) -> list[SearchResult]:
    """Return chunks related to query entities via the co-occurrence graph.

    Steps:
    1. Extract entities from query (or use entity_filter if provided).
    2. For each entity, fetch top-5 related entities by Jaccard.
    3. For each related entity, retrieve chunks via ChromaDB metadata filter.
    4. Deduplicate and return.
    """
    from candlekeep.rag.extractor import get_extractor
    from candlekeep.config import Settings

    settings = getattr(db, "settings", None) or Settings.from_env()

    if entity_filter is not None:
        query_entities = entity_filter
    else:
        extractor = get_extractor(ruler_path=settings.entity_ruler_path)
        query_entities = extractor.extract(query)

    if not query_entities:
        return []

    # Collect related entities across all query entities
    related: dict[str, float] = {}  # entity -> best jaccard score
    for qe in query_entities:
        for entity, score in graph_store.get_related(qe, top_n=5):
            if entity not in related or score > related[entity]:
                related[entity] = score

    if not related:
        return []

    # Fetch chunks for each related entity via ChromaDB array metadata filter
    seen_ids: set[str] = set()
    results: list[SearchResult] = []

    for entity, jaccard in sorted(related.items(), key=lambda x: x[1], reverse=True):
        try:
            raw = db.collection.get(
                where={"entities": {"$contains": entity}},
                limit=n_results,
            )
        except Exception:
            continue
        for doc_id, text, meta in zip(raw["ids"], raw["documents"], raw["metadatas"]):
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                results.append(SearchResult(
                    text=text,
                    metadata=meta,
                    score=jaccard,
                    doc_id=doc_id,
                ))

    return results[:n_results * 2]
