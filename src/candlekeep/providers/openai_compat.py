"""OpenAI-compatible provider (Ollama, LM Studio, vLLM, etc.)."""
from __future__ import annotations

import base64

from candlekeep.providers.base import LLMProvider, VisionProvider, ProviderError

_NAME = "openai_compat"


def _client(base_url: str, api_key: str):
    try:
        import openai
    except ImportError:
        raise ProviderError(_NAME, "pip install openai")
    return openai.OpenAI(base_url=base_url, api_key=api_key)


class OpenAICompatLLM(LLMProvider):
    def __init__(self, base_url: str, model: str, api_key: str = "not-needed"):
        self._client = _client(base_url, api_key)
        self._model = model

    @property
    def name(self) -> str:
        return _NAME

    def complete(self, prompt: str, *, max_tokens: int = 1024, temperature: float = 0.0) -> str:
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:
            raise ProviderError(_NAME, str(exc), exc)


class OpenAICompatVision(VisionProvider):
    def __init__(self, base_url: str, model: str, api_key: str = "not-needed"):
        self._client = _client(base_url, api_key)
        self._model = model

    @property
    def name(self) -> str:
        return _NAME

    def caption(self, image_bytes: bytes, *, prompt: str = "Describe this image in detail.", max_tokens: int = 1024) -> str:
        b64 = base64.standard_b64encode(image_bytes).decode()
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                        {"type": "text", "text": prompt},
                    ],
                }],
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:
            raise ProviderError(_NAME, str(exc), exc)
