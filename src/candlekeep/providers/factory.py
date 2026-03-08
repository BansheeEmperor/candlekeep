"""Provider factory — creates LLM / Vision providers from env-driven config."""
from __future__ import annotations

import os

from candlekeep.providers.base import LLMProvider, VisionProvider, ProviderError

_VALID = ("anthropic", "openai", "bedrock", "openai_compat")


def create_llm_provider(provider: str | None = None) -> LLMProvider:
    """Instantiate an LLMProvider from environment variables.

    *provider* defaults to ``CANDLEKEEP_LLM_PROVIDER``.
    """
    provider = provider or os.getenv("CANDLEKEEP_LLM_PROVIDER", "")
    if not provider:
        raise ProviderError("factory", "CANDLEKEEP_LLM_PROVIDER is not set")
    return _build_llm(provider)


def create_vision_provider(provider: str | None = None) -> VisionProvider:
    """Instantiate a VisionProvider from environment variables.

    *provider* defaults to ``CANDLEKEEP_VLM_PROVIDER``.
    """
    provider = provider or os.getenv("CANDLEKEEP_VLM_PROVIDER", "")
    if not provider:
        raise ProviderError("factory", "CANDLEKEEP_VLM_PROVIDER is not set")
    return _build_vision(provider)


# -- internal helpers --------------------------------------------------------

def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _build_llm(provider: str) -> LLMProvider:
    if provider == "anthropic":
        from candlekeep.providers.anthropic import AnthropicLLM
        return AnthropicLLM(
            api_key=_require("ANTHROPIC_API_KEY"),
            model=_env("CANDLEKEEP_LLM_MODEL", "claude-sonnet-4-20250514"),
        )
    if provider == "openai":
        from candlekeep.providers.openai import OpenAILLM
        return OpenAILLM(
            api_key=_require("OPENAI_API_KEY"),
            model=_env("CANDLEKEEP_LLM_MODEL", "gpt-4o-mini"),
        )
    if provider == "bedrock":
        from candlekeep.providers.bedrock import BedrockLLM
        return BedrockLLM(
            region=_env("AWS_REGION", "us-east-1"),
            model=_env("CANDLEKEEP_LLM_MODEL", "anthropic.claude-3-haiku-20240307-v1:0"),
        )
    if provider == "openai_compat":
        from candlekeep.providers.openai_compat import OpenAICompatLLM
        return OpenAICompatLLM(
            base_url=_require("CANDLEKEEP_LLM_BASE_URL"),
            model=_env("CANDLEKEEP_LLM_MODEL", "default"),
            api_key=_env("CANDLEKEEP_LLM_API_KEY", "not-needed"),
        )
    raise ProviderError("factory", f"Unknown LLM provider '{provider}'. Valid: {_VALID}")


def _build_vision(provider: str) -> VisionProvider:
    if provider == "anthropic":
        from candlekeep.providers.anthropic import AnthropicVision
        return AnthropicVision(
            api_key=_require("ANTHROPIC_API_KEY"),
            model=_env("CANDLEKEEP_VLM_MODEL", "claude-sonnet-4-20250514"),
        )
    if provider == "openai":
        from candlekeep.providers.openai import OpenAIVision
        return OpenAIVision(
            api_key=_require("OPENAI_API_KEY"),
            model=_env("CANDLEKEEP_VLM_MODEL", "gpt-4o-mini"),
        )
    if provider == "bedrock":
        from candlekeep.providers.bedrock import BedrockVision
        return BedrockVision(
            region=_env("AWS_REGION", "us-east-1"),
            model=_env("CANDLEKEEP_VLM_MODEL", "anthropic.claude-3-haiku-20240307-v1:0"),
        )
    if provider == "openai_compat":
        from candlekeep.providers.openai_compat import OpenAICompatVision
        return OpenAICompatVision(
            base_url=_require("CANDLEKEEP_VLM_BASE_URL"),
            model=_env("CANDLEKEEP_VLM_MODEL", "default"),
            api_key=_env("CANDLEKEEP_VLM_API_KEY", "not-needed"),
        )
    raise ProviderError("factory", f"Unknown VLM provider '{provider}'. Valid: {_VALID}")


def _require(key: str) -> str:
    val = os.getenv(key, "")
    if not val:
        raise ProviderError("factory", f"Required env var {key} is not set")
    return val
