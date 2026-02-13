"""Embedding manager with model caching and selection."""
from sentence_transformers import SentenceTransformer
from candlekeep.config import Settings, EMBEDDING_MODELS, EmbeddingModel


class EmbeddingManager:
    _instance: "EmbeddingManager | None" = None
    _model: SentenceTransformer | None = None
    _current_model: str | None = None

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_env()

    @classmethod
    def get_instance(cls, settings: Settings | None = None) -> "EmbeddingManager":
        if cls._instance is None:
            cls._instance = cls(settings)
        return cls._instance

    def get_model(self, model_name: EmbeddingModel | None = None) -> SentenceTransformer:
        """Load model from local cache. Exits if not found locally."""
        model_name = model_name or self.settings.embedding_model
        model_id = EMBEDDING_MODELS[model_name]

        if self._model is not None and self._current_model == model_id:
            return self._model

        cache_dir = self.settings.models_dir
        # Check if model exists locally before loading
        if not any(cache_dir.glob(f"models--{model_id.replace('/', '--')}*")):
            import sys
            print(f"[candlekeep] ❌ Model '{model_id}' not found locally in {cache_dir}. "
                  f"Run ./scripts/setup.sh to download models.", file=sys.stderr)
            sys.exit(1)

        trust_remote_code = model_name == "nomic"
        self._model = SentenceTransformer(
            model_id,
            cache_folder=str(cache_dir),
            trust_remote_code=trust_remote_code,
            local_files_only=True,
        )
        self._current_model = model_id
        return self._model

    def embed(self, texts: list[str] | str, model_name: EmbeddingModel | None = None, is_query: bool = False) -> list[list[float]]:
        """Generate embeddings for texts."""
        model_name = model_name or self.settings.embedding_model
        model = self.get_model(model_name)
        if isinstance(texts, str):
            texts = [texts]
        
        # Nomic requires prefixes
        if model_name == "nomic":
            prefix = "search_query: " if is_query else "search_document: "
            texts = [prefix + t for t in texts]
        
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def embed_query(self, query: str, model_name: EmbeddingModel | None = None) -> list[float]:
        """Generate embedding for a single query."""
        return self.embed([query], model_name, is_query=True)[0]
