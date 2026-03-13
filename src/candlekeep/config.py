"""Configuration for candlekeep with ChromaDB authentication."""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

EmbeddingModel = Literal["minilm", "bge-small", "nomic"]
DeviceType = Literal["auto", "cpu", "mps", "cuda"]

EMBEDDING_MODELS = {
    "minilm": "sentence-transformers/all-MiniLM-L6-v2",
    "bge-small": "BAAI/bge-small-en-v1.5",
    "nomic": "nomic-ai/nomic-embed-text-v1.5",
}


def detect_device() -> str:
    """Detect best available compute device."""
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_dotenv(env_file: Path | None = None) -> None:
    """Load .env file into environment variables."""
    if env_file is None:
        for candidate in [Path(".env"), Path(__file__).parent.parent.parent / ".env"]:
            if candidate.exists():
                env_file = candidate
                break
    if env_file is None or not env_file.exists():
        return
    
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            if line.startswith("export "):
                line = line[7:]
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


load_dotenv()


def get_data_dir() -> Path:
    """Get cross-platform data directory."""
    if os.getenv("CANDLEKEEP_DATA_DIR"):
        return Path(os.getenv("CANDLEKEEP_DATA_DIR"))
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif os.name == "posix" and "darwin" in os.uname().sysname.lower():
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "candlekeep"


@dataclass
class Settings:
    """Candlekeep configuration settings."""
    
    # ChromaDB connection
    chroma_url: str = field(default_factory=lambda: os.getenv("CHROMA_URL", "http://localhost:8000"))
    chroma_auth_token: str = field(default_factory=lambda: os.getenv("CHROMA_AUTH_TOKEN", ""))
    
    # Embedding settings
    embedding_model: EmbeddingModel = field(default_factory=lambda: os.getenv("CANDLEKEEP_EMBEDDING", "bge-small"))
    embedding_cache_size: int = field(default_factory=lambda: int(os.getenv("CANDLEKEEP_EMBEDDING_CACHE_SIZE", "500")))
    
    # Inference device
    device: str = field(default_factory=lambda: os.getenv("CANDLEKEEP_DEVICE", "auto"))
    
    # Document processing
    chunk_size: int = field(default_factory=lambda: int(os.getenv("CANDLEKEEP_CHUNK_SIZE", "512")))
    chunk_overlap: int = field(default_factory=lambda: int(os.getenv("CANDLEKEEP_CHUNK_OVERLAP", "50")))
    
    # Personality
    spice: bool = field(default_factory=lambda: os.getenv("CANDLEKEEP_SPICE", "false").lower() == "true")
    
    # Structural Integrity (Bardic Knowledge)
    bardic_knowledge: bool = field(default_factory=lambda: os.getenv("CANDLEKEEP_BARDIC_KNOWLEDGE", "true").lower() == "true")

    # Sparse backend for hybrid path (bm25 or colbert)
    sparse_backend: str = field(default_factory=lambda: os.getenv("CANDLEKEEP_SPARSE_BACKEND", "bm25"))

    # Transport settings (multi-agent HTTP mode)
    transport: str = field(default_factory=lambda: os.getenv("CANDLEKEEP_TRANSPORT", "stdio"))
    http_host: str = field(default_factory=lambda: os.getenv("CANDLEKEEP_HTTP_HOST", "127.0.0.1"))
    http_port: int = field(default_factory=lambda: int(os.getenv("CANDLEKEEP_HTTP_PORT", "8111")))
    mcp_token: str = field(default_factory=lambda: os.getenv("CANDLEKEEP_MCP_TOKEN", ""))

    # Rate limiting (HTTP mode only, per MCP session)
    rate_limit_search: int = field(default_factory=lambda: int(os.getenv("CANDLEKEEP_RATE_LIMIT_SEARCH", "30")))
    rate_limit_write: int = field(default_factory=lambda: int(os.getenv("CANDLEKEEP_RATE_LIMIT_WRITE", "5")))
    rate_limit_window: int = field(default_factory=lambda: int(os.getenv("CANDLEKEEP_RATE_LIMIT_WINDOW", "60")))

    # LLM / Vision provider selection (anthropic, openai, bedrock, openai_compat)
    llm_provider: str = field(default_factory=lambda: os.getenv("CANDLEKEEP_LLM_PROVIDER", ""))
    vlm_provider: str = field(default_factory=lambda: os.getenv("CANDLEKEEP_VLM_PROVIDER", ""))

    # VLM captioning options
    vlm_concurrency: int = field(default_factory=lambda: int(os.getenv("CANDLEKEEP_VLM_CONCURRENCY", "3")))
    vlm_max_cost_per_doc: float = field(default_factory=lambda: float(os.getenv("CANDLEKEEP_VLM_MAX_COST_PER_DOC", "0.0")))
    vlm_fetch_remote_images: bool = field(default_factory=lambda: os.getenv("CANDLEKEEP_VLM_FETCH_REMOTE_IMAGES", "false").lower() == "true")
    vlm_pdf_max_pages: int = field(default_factory=lambda: int(os.getenv("CANDLEKEEP_VLM_PDF_MAX_PAGES", "15")))

    # Data directory
    data_dir: Path = field(default_factory=get_data_dir)

    def __post_init__(self):
        if self.device == "auto":
            self.device = detect_device()
        self.data_dir = Path(self.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "models").mkdir(exist_ok=True)
        (self.data_dir / "chroma").mkdir(exist_ok=True)
        if self.vlm_provider and self.vlm_provider != "none":
            (self.data_dir / "image_captions").mkdir(exist_ok=True)
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables."""
        return cls()
    
    @property
    def chroma_host(self) -> str:
        """Extract host from CHROMA_URL."""
        parsed = urlparse(self.chroma_url)
        return parsed.hostname or "localhost"
    
    @property
    def chroma_port(self) -> int:
        """Extract port from CHROMA_URL."""
        parsed = urlparse(self.chroma_url)
        return parsed.port or 8000
    
    @property
    def chroma_ssl(self) -> bool:
        """Check if HTTPS is used."""
        parsed = urlparse(self.chroma_url)
        return parsed.scheme == "https"
    
    @property
    def models_dir(self) -> Path:
        return self.data_dir / "models"
    
    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"
    
    @property
    def embedding_model_name(self) -> str:
        return EMBEDDING_MODELS[self.embedding_model]

    @property
    def image_caption_cache_dir(self) -> Path:
        return self.data_dir / "image_captions"

    @property
    def normalisation_map_path(self) -> Path:
        return self.data_dir / "normalisation_map.json"
