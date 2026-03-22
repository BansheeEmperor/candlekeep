"""LangChain RAG competitor.

Tests LangChain's default retrieval pipeline: RecursiveCharacterTextSplitter
+ Chroma vectorstore + similarity search retriever. This is what most teams
deploy when they follow LangChain's RAG tutorial.

Uses the shared embedding model (bge-small-en-v1.5) via LangChain's
HuggingFaceEmbeddings wrapper. Uses forced-equal chunking (512 chars,
50 overlap) for apples-to-apples comparison.

Two variants:
  - langchain: Default Chroma.as_retriever() with similarity search
  - langchain-mmr: Chroma.as_retriever() with MMR (maximal marginal
    relevance) — LangChain's built-in diversity mechanism, comparable
    to Prismatic Dispersal
"""
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from candlekeep.database.interface import SearchResult
from scripts.competitors.base import (
    Competitor,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    _parse_frontmatter,
)

# Shared LangChain embedding wrapper — uses the same underlying model
# as all other competitors (bge-small-en-v1.5).
_lc_embeddings: HuggingFaceEmbeddings | None = None


def _get_lc_embeddings(device: str = "mps") -> HuggingFaceEmbeddings:
    global _lc_embeddings
    if _lc_embeddings is None:
        _lc_embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
            model_kwargs={"device": device},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _lc_embeddings


class LangChainRAG(Competitor):
    """LangChain default RAG: RecursiveCharacterTextSplitter + Chroma retriever.

    This is the pipeline from LangChain's quickstart tutorial with
    forced-equal chunking parameters for fair comparison.
    """

    name = "langchain"

    def __init__(self, use_mmr: bool = False, device: str = "mps", hybrid: bool = False):
        self._use_mmr = use_mmr
        self._hybrid = hybrid
        if hybrid:
            self.name = "langchain-advanced"
        elif use_mmr:
            self.name = "langchain-mmr"
        self._embeddings = _get_lc_embeddings(device=device)
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n", " ", ""],
        )
        self._vectorstore: Chroma | None = None
        self._collection_name = f"lc_{self.name}_bench"

    def ingest(self, doc_paths: list[Path]) -> int:
        all_docs = []
        for path in doc_paths:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            frontmatter, content = _parse_frontmatter(text)

            # LangChain's standard flow: split text, create Document objects
            chunks = self._splitter.split_text(content)
            for i, chunk in enumerate(chunks):
                metadata = {
                    "source": str(path),
                    "filename": path.name,
                    "chunk_index": i,
                }
                metadata.update(frontmatter)
                all_docs.append(Document(page_content=chunk, metadata=metadata))

        if not all_docs:
            return 0

        # Create Chroma vectorstore from documents
        self._vectorstore = Chroma.from_documents(
            documents=all_docs,
            embedding=self._embeddings,
            collection_name=self._collection_name,
        )
        return len(all_docs)

    def search(self, query: str, k: int = 5) -> list[SearchResult]:
        if self._vectorstore is None:
            return []

        if self._hybrid:
            # Advanced path: Vector + Rerank
            # (Note: LangChain EnsembleRetriever requires a separate BM25 instance,
            # for this benchmark we'll focus on the Reranker step which is the main lag)
            
            # 1. Fetch more candidates
            docs = self._vectorstore.similarity_search(query, k=k*4)
            
            # 2. Manual Cross-Encoder Rerank (using same model as CK)
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            import torch
            
            model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSequenceClassification.from_pretrained(model_name)
            model.to("mps" if torch.backends.mps.is_available() else "cpu")
            model.eval()
            
            pairs = [[query, doc.page_content] for doc in docs]
            with torch.no_grad():
                inputs = tokenizer(pairs, padding=True, truncation=True, return_tensors="pt").to(model.device)
                logits = model(**inputs).logits.flatten().tolist()
            
            # Sort by score
            scored_docs = sorted(zip(logits, docs), key=lambda x: x[0], reverse=True)[:k]
            
            return [
                SearchResult(
                    text=doc.page_content,
                    metadata=doc.metadata,
                    score=float(score),
                    doc_id=doc.metadata.get("source", ""),
                )
                for score, doc in scored_docs
            ]

        elif self._use_mmr:
            # MMR diversity search
            docs = self._vectorstore.max_marginal_relevance_search(
                query, k=k, fetch_k=k * 3, lambda_mult=0.7,
            )
            return [
                SearchResult(
                    text=doc.page_content,
                    metadata=doc.metadata,
                    score=1.0 - (i * 0.1),
                    doc_id=doc.metadata.get("source", ""),
                )
                for i, doc in enumerate(docs)
            ]
        else:
            # Default similarity search with scores
            results = self._vectorstore.similarity_search_with_relevance_scores(
                query, k=k,
            )
            return [
                SearchResult(
                    text=doc.page_content,
                    metadata=doc.metadata,
                    score=score,
                    doc_id=doc.metadata.get("source", ""),
                )
                for doc, score in results
            ]

    def reset(self) -> None:
        if self._vectorstore is not None:
            try:
                self._vectorstore.delete_collection()
            except Exception:
                pass
        self._vectorstore = None
