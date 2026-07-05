"""LlamaIndex competitor: default pipeline and SentenceWindow retrieval.

Tests LlamaIndex's built-in retrieval strategies against Candlekeep:
- llamaindex: Default VectorStoreIndex with SimpleNodeParser
- llamaindex-window: SentenceWindowNodeParser (similar to Arcane Recall)
"""
import os
from pathlib import Path
from typing import List

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from candlekeep.database.interface import SearchResult
from scripts.competitors.base import (
    Competitor, get_shared_embedding_model, _parse_frontmatter,
)


class LlamaIndexRAG(Competitor):
    """LlamaIndex default VectorStoreIndex."""

    def __init__(self, use_window: bool = False):
        self.name = "llamaindex-window" if use_window else "llamaindex"
        self._use_window = use_window
        self._index = None
        self._retriever = None

    def ingest(self, doc_paths: list[Path]) -> int:
        from llama_index.core import VectorStoreIndex, Settings, Document
        from llama_index.core.node_parser import SentenceWindowNodeParser, SentenceSplitter
        from llama_index.core.embeddings import BaseEmbedding
        import numpy as np

        # Use shared embedding model via a wrapper
        model = get_shared_embedding_model()

        class BGESmallEmbedding(BaseEmbedding):
            """Wrapper to use shared bge-small model with LlamaIndex."""
            def __init__(self):
                super().__init__(model_name="bge-small-en-v1.5", embed_batch_size=32)

            def _get_text_embedding(self, text: str) -> list[float]:
                return model.encode([text], convert_to_numpy=True)[0].tolist()

            def _get_query_embedding(self, query: str) -> list[float]:
                return model.encode([query], convert_to_numpy=True)[0].tolist()

            async def _aget_query_embedding(self, query: str) -> list[float]:
                return self._get_query_embedding(query)

            def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
                return model.encode(texts, convert_to_numpy=True).tolist()

        Settings.embed_model = BGESmallEmbedding()
        Settings.llm = None  # No LLM needed for retrieval
        Settings.chunk_size = 512
        Settings.chunk_overlap = 50

        # Load documents
        documents = []
        for path in doc_paths:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            frontmatter, content = _parse_frontmatter(text)
            documents.append(Document(
                text=content,
                metadata={"source": str(path), "filename": path.name, **frontmatter},
            ))

        if not documents:
            return 0

        if self._use_window:
            node_parser = SentenceWindowNodeParser.from_defaults(
                window_size=3,
                window_metadata_key="window",
                original_text_metadata_key="original_text",
            )
        else:
            node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)

        nodes = node_parser.get_nodes_from_documents(documents)
        self._index = VectorStoreIndex(nodes)

        if self._use_window:
            from llama_index.core.postprocessor import MetadataReplacementPostProcessor
            self._retriever = self._index.as_retriever(similarity_top_k=5)
            self._postprocessor = MetadataReplacementPostProcessor(
                target_metadata_key="window"
            )
        else:
            self._retriever = self._index.as_retriever(similarity_top_k=5)
            self._postprocessor = None

        return len(nodes)

    def search(self, query: str, k: int = 5) -> list[SearchResult]:
        if not self._retriever:
            return []

        nodes = self._retriever.retrieve(query)

        if self._postprocessor:
            # Apply window replacement for sentence window mode
            from llama_index.core.schema import NodeWithScore, QueryBundle
            query_bundle = QueryBundle(query_str=query)
            nodes = self._postprocessor.postprocess_nodes(nodes, query_bundle)

        results = []
        for node in nodes[:k]:
            meta = dict(node.metadata) if hasattr(node, 'metadata') else {}
            if hasattr(node, 'node'):
                text = node.node.get_content()
                meta = dict(node.node.metadata)
            else:
                text = node.get_content() if hasattr(node, 'get_content') else str(node)

            results.append(SearchResult(
                text=text,
                metadata=meta,
                score=node.score if hasattr(node, 'score') else 0.0,
                doc_id=meta.get("source", ""),
            ))

        return results

    def reset(self) -> None:
        self._index = None
        self._retriever = None


class LlamaIndexArcaneRecall(Competitor):
    """LlamaIndex retrieval + Candlekeep's Arcane Recall expansion.
    
    Uses LlamaIndex's VectorStoreIndex for initial retrieval, then
    pipes results through Arcane Recall for context expansion using
    a parallel bge-small ChromaDB store.
    """
    name = "llamaindex-arcane"

    def __init__(self):
        self._index = None
        self._retriever = None
        self._db = None  # Parallel store for Arcane Recall

    def ingest(self, doc_paths: list[Path]) -> int:
        from llama_index.core import VectorStoreIndex, Settings, Document
        from llama_index.core.node_parser import SentenceSplitter
        from llama_index.core.embeddings import BaseEmbedding
        from scripts.competitors.candlekeep_configs import (
            _EphemeralVectorDB, _chunk_with_bardic_knowledge,
        )

        model = get_shared_embedding_model()

        class BGESmallEmbedding(BaseEmbedding):
            def __init__(self):
                super().__init__(model_name="bge-small-en-v1.5", embed_batch_size=32)
            def _get_text_embedding(self, text: str) -> list[float]:
                return model.encode([text], convert_to_numpy=True)[0].tolist()
            def _get_query_embedding(self, query: str) -> list[float]:
                return model.encode([query], convert_to_numpy=True)[0].tolist()
            async def _aget_query_embedding(self, query: str) -> list[float]:
                return self._get_query_embedding(query)
            def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
                return model.encode(texts, convert_to_numpy=True).tolist()

        Settings.embed_model = BGESmallEmbedding()
        Settings.llm = None
        Settings.chunk_size = 512
        Settings.chunk_overlap = 50

        # LlamaIndex documents (for retrieval)
        documents = []
        for path in doc_paths:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            frontmatter, content = _parse_frontmatter(text)
            documents.append(Document(
                text=content,
                metadata={"source": str(path), "filename": path.name, **frontmatter},
            ))

        if not documents:
            return 0

        node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
        nodes = node_parser.get_nodes_from_documents(documents)
        self._index = VectorStoreIndex(nodes)
        self._retriever = self._index.as_retriever(similarity_top_k=10)

        # Parallel ChromaDB store for Arcane Recall expansion
        self._db = _EphemeralVectorDB("llamaindex_arcane")
        total = 0
        for path in doc_paths:
            if not path.is_file():
                continue
            chunks = _chunk_with_bardic_knowledge(path, strategy="all")
            if chunks:
                self._db.add_documents(chunks)
                total += len(chunks)

        return total

    def search(self, query: str, k: int = 5) -> list[SearchResult]:
        if not self._retriever or not self._db:
            return []

        from candlekeep.rag.arcane_recall import expand_results

        # Step 1: LlamaIndex retrieval
        nodes = self._retriever.retrieve(query)

        # Convert to SearchResult format
        initial_results = []
        for node in nodes:
            meta = {}
            if hasattr(node, 'node'):
                text = node.node.get_content()
                meta = dict(node.node.metadata)
            else:
                text = node.get_content() if hasattr(node, 'get_content') else str(node)
                meta = dict(node.metadata) if hasattr(node, 'metadata') else {}

            initial_results.append(SearchResult(
                text=text,
                metadata=meta,
                score=node.score if hasattr(node, 'score') else 0.0,
                doc_id=meta.get("source", ""),
            ))

        # Step 2: Arcane Recall expansion using parallel ChromaDB store
        expanded = expand_results(self._db, initial_results, n_results=k, query=query)
        return expanded[:k]

    def reset(self) -> None:
        self._index = None
        self._retriever = None
        if self._db:
            self._db.clear()
        self._db = None


class LlamaIndexBKArcane(Competitor):
    """LlamaIndex retrieval with Bardic Knowledge chunks + Arcane Recall.
    
    Same chunks as Candlekeep (with BK prefix), fed to LlamaIndex for
    retrieval, then expanded with Arcane Recall. Isolates whether
    LlamaIndex's retrieval algorithm is better than Candlekeep's
    vector search on identical input.
    """
    name = "llamaindex-bk-arcane"

    def __init__(self):
        self._index = None
        self._retriever = None
        self._db = None

    def ingest(self, doc_paths: list[Path]) -> int:
        from llama_index.core import VectorStoreIndex, Settings, Document
        from llama_index.core.node_parser import SentenceSplitter
        from llama_index.core.embeddings import BaseEmbedding
        from llama_index.core.schema import TextNode
        from scripts.competitors.candlekeep_configs import (
            _EphemeralVectorDB, _chunk_with_bardic_knowledge,
        )

        model = get_shared_embedding_model()

        class BGESmallEmbedding(BaseEmbedding):
            def __init__(self):
                super().__init__(model_name="bge-small-en-v1.5", embed_batch_size=32)
            def _get_text_embedding(self, text: str) -> list[float]:
                return model.encode([text], convert_to_numpy=True)[0].tolist()
            def _get_query_embedding(self, query: str) -> list[float]:
                return model.encode([query], convert_to_numpy=True)[0].tolist()
            async def _aget_query_embedding(self, query: str) -> list[float]:
                return self._get_query_embedding(query)
            def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
                return model.encode(texts, convert_to_numpy=True).tolist()

        Settings.embed_model = BGESmallEmbedding()
        Settings.llm = None

        # Use Candlekeep's BK chunks directly as LlamaIndex nodes
        nodes = []
        self._db = _EphemeralVectorDB("llamaindex_bk_arcane")
        total = 0

        for path in doc_paths:
            if not path.is_file():
                continue
            chunks = _chunk_with_bardic_knowledge(path, strategy="all")
            if not chunks:
                continue
            self._db.add_documents(chunks)
            total += len(chunks)

            for c in chunks:
                nodes.append(TextNode(
                    text=c.text,
                    metadata=c.metadata,
                ))

        if not nodes:
            return 0

        self._index = VectorStoreIndex(nodes)
        self._retriever = self._index.as_retriever(similarity_top_k=10)
        return total

    def search(self, query: str, k: int = 5) -> list[SearchResult]:
        if not self._retriever or not self._db:
            return []

        from candlekeep.rag.arcane_recall import expand_results

        nodes = self._retriever.retrieve(query)
        initial = []
        for node in nodes:
            meta = {}
            if hasattr(node, 'node'):
                text = node.node.get_content()
                meta = dict(node.node.metadata)
            else:
                text = node.get_content() if hasattr(node, 'get_content') else str(node)
                meta = dict(node.metadata) if hasattr(node, 'metadata') else {}
            initial.append(SearchResult(
                text=text, metadata=meta,
                score=node.score if hasattr(node, 'score') else 0.0,
                doc_id=meta.get("source", ""),
            ))

        expanded = expand_results(self._db, initial, n_results=k, query=query)
        return expanded[:k]

    def reset(self):
        self._index = None
        self._retriever = None
        if self._db:
            self._db.clear()
        self._db = None
