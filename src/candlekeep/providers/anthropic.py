"""Anthropic (Claude) provider."""
from __future__ import annotations

import base64

from candlekeep.providers.base import LLMProvider, VisionProvider, ProviderError

_NAME = "anthropic"


def _client(api_key: str):
    try:
        import anthropic
    except ImportError:
        raise ProviderError(_NAME, "pip install anthropic")
    return anthropic.Anthropic(api_key=api_key)


class AnthropicLLM(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self._client = _client(api_key)
        self._model = model

    @property
    def name(self) -> str:
        return _NAME

    def complete(self, prompt: str, *, max_tokens: int = 1024, temperature: float = 0.0) -> str:
        try:
            resp = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text
        except Exception as exc:
            raise ProviderError(_NAME, str(exc), exc)


class AnthropicVision(VisionProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self._client = _client(api_key)
        self._model = model

    @property
    def name(self) -> str:
        return _NAME

    def caption(self, image_bytes: bytes, *, prompt: str = "Describe this image in detail.", max_tokens: int = 1024) -> str:
        media_type = _guess_media_type(image_bytes)
        b64 = base64.standard_b64encode(image_bytes).decode()
        try:
            resp = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                        {"type": "text", "text": prompt},
                    ],
                }],
            )
            return resp.content[0].text
        except Exception as exc:
            raise ProviderError(_NAME, str(exc), exc)


_SIGNATURES = {b"\x89PNG": "image/png", b"\xff\xd8\xff": "image/jpeg", b"GIF8": "image/gif", b"RIFF": "image/webp"}


def _guess_media_type(data: bytes) -> str:
    for sig, mime in _SIGNATURES.items():
        if data[:len(sig)] == sig:
            return mime
    return "image/png"
