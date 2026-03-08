"""AWS Bedrock provider (optional dependency)."""
from __future__ import annotations

import base64
import json

from candlekeep.providers.base import LLMProvider, VisionProvider, ProviderError

_NAME = "bedrock"


def _client(region: str):
    try:
        import boto3
    except ImportError:
        raise ProviderError(_NAME, "pip install candlekeep[bedrock]")
    return boto3.client("bedrock-runtime", region_name=region)


class BedrockLLM(LLMProvider):
    def __init__(self, region: str = "us-east-1", model: str = "anthropic.claude-3-haiku-20240307-v1:0"):
        self._client = _client(region)
        self._model = model

    @property
    def name(self) -> str:
        return _NAME

    def complete(self, prompt: str, *, max_tokens: int = 1024, temperature: float = 0.0) -> str:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        })
        try:
            resp = self._client.invoke_model(modelId=self._model, body=body)
            result = json.loads(resp["body"].read())
            return result["content"][0]["text"]
        except Exception as exc:
            raise ProviderError(_NAME, str(exc), exc)


class BedrockVision(VisionProvider):
    def __init__(self, region: str = "us-east-1", model: str = "anthropic.claude-3-haiku-20240307-v1:0"):
        self._client = _client(region)
        self._model = model

    @property
    def name(self) -> str:
        return _NAME

    def caption(self, image_bytes: bytes, *, prompt: str = "Describe this image in detail.", max_tokens: int = 1024) -> str:
        b64 = base64.standard_b64encode(image_bytes).decode()
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                    {"type": "text", "text": prompt},
                ],
            }],
        })
        try:
            resp = self._client.invoke_model(modelId=self._model, body=body)
            result = json.loads(resp["body"].read())
            return result["content"][0]["text"]
        except Exception as exc:
            raise ProviderError(_NAME, str(exc), exc)
