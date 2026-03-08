"""Abstract base classes for LLM and Vision providers."""
from abc import ABC, abstractmethod


class ProviderError(Exception):
    """Raised when a provider call fails."""

    def __init__(self, provider: str, message: str, cause: Exception | None = None):
        self.provider = provider
        super().__init__(f"[{provider}] {message}")
        self.__cause__ = cause


class LLMProvider(ABC):
    """Text completion provider."""

    @abstractmethod
    def complete(self, prompt: str, *, max_tokens: int = 1024, temperature: float = 0.0) -> str:
        """Return a text completion for *prompt*."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""


class VisionProvider(ABC):
    """Image captioning provider."""

    @abstractmethod
    def caption(self, image_bytes: bytes, *, prompt: str = "Describe this image in detail.", max_tokens: int = 1024) -> str:
        """Return a text caption for the given image."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
