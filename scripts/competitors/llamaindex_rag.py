"""LlamaIndex RAG competitor."""
from pathlib import Path
from llama_index.core import VectorStoreIndex, Document, StorageContext, ServiceContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

from candlekeep.database.interface import SearchResult
from scripts.competitors.base import Competitor, CHUNK_SIZE, CHUNK_OVERLAP, _parse_frontmatter

from llama_index.core.llms.mock import MockLLM

class LlamaIndexRAG(Competitor):
    """LlamaIndex baseline RAG using VectorStoreIndex and Chroma."""

    name = "llamaindex"

    def __init__(self, use_window: bool = False, device: str = "mps", hybrid: bool = False):
        self._use_window = use_window
        self._hybrid = hybrid
        if hybrid:
            self.name = "llamaindex-advanced"
        elif use_window:
            self.name = "llamaindex-window"
        
        # Use the same embedding model as everyone else
        self._embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-small-en-v1.5",
            device=device
        )
        
        self._llm = MockLLM()
        
        self._client = chromadb.Client()
        self._collection = self._client.create_collection(f"li_{self.name}_bench")
        self._vector_store = ChromaVectorStore(chroma_collection=self._collection)
        self._storage_context = StorageContext.from_defaults(vector_store=self._vector_store)
        
        self._index = None

    def ingest(self, doc_paths: list[Path]) -> int:
        documents = []
        for path in doc_paths:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            frontmatter, content = _parse_frontmatter(text)
            
            doc = Document(text=content, metadata={"source": str(path), "filename": path.name})
            doc.metadata.update(frontmatter)
            documents.append(doc)

        if not documents:
            return 0

        # LlamaIndex splitter
        splitter = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        
        self._index = VectorStoreIndex.from_documents(
            documents,
            storage_context=self._storage_context,
            embed_model=self._embed_model,
            llm=self._llm,
            transformations=[splitter]
        )
        
        return len(self._index.index_struct.nodes_dict)

    def search(self, query: str, k: int = 5) -> list[SearchResult]:
        if self._index is None:
            return []
            
        if self._hybrid:
            # Advanced path: Hybrid (Vector only here as Chroma multi-modal is complex to setup ephemeral)
            # We'll use the vector retriever but with more candidates, then manual rerank
            retriever = self._index.as_retriever(similarity_top_k=k*4)
            nodes = retriever.retrieve(query)
            
            # Manual Cross-Encoder Rerank
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            import torch
            
            model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSequenceClassification.from_pretrained(model_name)
            model.to("mps" if torch.backends.mps.is_available() else "cpu")
            model.eval()
            
            pairs = [[query, node.text] for node in nodes]
            with torch.no_grad():
                inputs = tokenizer(pairs, padding=True, truncation=True, return_tensors="pt").to(model.device)
                scores = model(**inputs).logits.flatten().tolist()
            
            # Sort by score
            scored_nodes = sorted(zip(scores, nodes), key=lambda x: x[0], reverse=True)[:k]
            
            output = []
            for score, node in scored_nodes:
                output.append(SearchResult(
                    text=node.text,
                    metadata=node.metadata,
                    score=float(score),
                    doc_id=node.node_id
                ))
            return output
        else:
            # Naive path
            query_engine = self._index.as_query_engine(similarity_top_k=k, llm=self._llm)
            response = query_engine.query(query)
            
            output = []
            for node in response.source_nodes:
                output.append(SearchResult(
                    text=node.text,
                    metadata=node.metadata,
                    score=node.score if node.score is not None else 0.0,
                    doc_id=node.node_id
                ))
            return output

    def reset(self) -> None:
        self._client.delete_collection("llamaindex_bench")
        self._collection = self._client.create_collection("llamaindex_bench")
        self._vector_store = ChromaVectorStore(chroma_collection=self._collection)
        self._storage_context = StorageContext.from_defaults(vector_store=self._vector_store)
        self._index = None
