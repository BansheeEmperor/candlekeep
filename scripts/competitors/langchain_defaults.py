"""LangChain default-config competitor.

Answers: "If a team follows LangChain's RAG tutorial out of the box,
how does their system compare to Candlekeep out of the box?"

Every parameter matches LangChain's official tutorial and docs:
  - Embedding: all-mpnet-base-v2 (HuggingFace tab default, 109M params, 768d)
  - Chunking: RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
  - Retrieval: Chroma similarity_search, k=4 (tutorial default)
  - No frontmatter parsing, no context prefixes, no post-processing

This is NOT the forced-equal competitor (langchain_rag.py). That one
uses bge-small and 512/50 chunks to isolate retrieval strategy. This
one uses LangChain's own recommended defaults to test the full
out-of-the-box experience.

Sources:
  - https://python.langchain.com/docs/tutorials/rag/
  - RecursiveCharacterTextSplitter defaults: chunk_size=1000, chunk_overlap=200
  - HuggingFace embedding tab: sentence-transformers/all-mpnet-base-v2
"""
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from candlekeep.database.interface import SearchResult
from scripts.competitors.base import Competitor

# Singleton for the LangChain-default embedding model.
# all-mpnet-base-v2: 109M params, 768 dims — LangChain's HuggingFace default.
_lc_default_embeddings: HuggingFaceEmbeddings | None = None


def _get_lc_default_embeddings() -> HuggingFaceEmbeddings:
    global _lc_default_embeddings
    if _lc_default_embeddings is None:
        _lc_default_embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _lc_default_embeddings


class LangChainDefaults(Competitor):
    """LangChain out-of-the-box RAG pipeline.

    Matches the official tutorial at python.langchain.com/docs/tutorials/rag/:
      - RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
      - HuggingFaceEmbeddings(all-mpnet-base-v2)
      - Chroma.similarity_search_with_relevance_scores(k=4)

    No frontmatter parsing. Documents are read as plain text and split.
    This is what a team gets on day one with LangChain.
    """

    name = "langchain-defaults"

    def __init__(self):
        self._embeddings = _get_lc_default_embeddings()
        # LangChain tutorial defaults — no customization
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
        )
        self._vectorstore: Chroma | None = None
        self._collection_name = "lc_defaults_bench"

    def ingest(self, doc_paths: list[Path]) -> int:
        all_docs = []
        for path in doc_paths:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            # No frontmatter parsing — LangChain tutorial doesn't do this.
            # The full text (including YAML frontmatter) goes through the splitter.
            chunks = self._splitter.split_text(text)
            for i, chunk in enumerate(chunks):
                all_docs.append(Document(
                    page_content=chunk,
                    metadata={
                        "source": str(path),
                        "chunk_index": i,
                    },
                ))

        if not all_docs:
            return 0

        self._vectorstore = Chroma.from_documents(
            documents=all_docs,
            embedding=self._embeddings,
            collection_name=self._collection_name,
            collection_metadata={"hnsw:space": "cosine"},
        )
        return len(all_docs)

    def search(self, query: str, k: int = 5) -> list[SearchResult]:
        if self._vectorstore is None:
            return []

        # similarity_search_with_score returns (doc, distance) where
        # distance is cosine distance (lower = more similar).
        # Convert to similarity: score = 1 - distance.
        results = self._vectorstore.similarity_search_with_score(query, k=k)
        return [
            SearchResult(
                text=doc.page_content,
                metadata=doc.metadata,
                score=max(0.0, 1.0 - dist),
                doc_id=doc.metadata.get("source", ""),
            )
            for doc, dist in results
        ]

    def reset(self) -> None:
        if self._vectorstore is not None:
            try:
                self._vectorstore.delete_collection()
            except Exception:
                pass
        self._vectorstore = None
