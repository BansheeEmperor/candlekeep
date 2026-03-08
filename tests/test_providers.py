"""Unit tests for the provider abstraction layer."""
from unittest.mock import MagicMock, patch
import json
import pytest

from candlekeep.providers.base import LLMProvider, VisionProvider, ProviderError


# ---------------------------------------------------------------------------
# ProviderError
# ---------------------------------------------------------------------------

class TestProviderError:
    def test_message_includes_provider_name(self):
        err = ProviderError("anthropic", "rate limited")
        assert "[anthropic]" in str(err)
        assert "rate limited" in str(err)

    def test_preserves_cause(self):
        cause = ValueError("bad")
        err = ProviderError("openai", "fail", cause)
        assert err.__cause__ is cause


# ---------------------------------------------------------------------------
# Factory — env-driven instantiation
# ---------------------------------------------------------------------------

class TestFactory:
    def test_missing_llm_provider_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            from candlekeep.providers.factory import create_llm_provider
            with pytest.raises(ProviderError, match="CANDLEKEEP_LLM_PROVIDER"):
                create_llm_provider()

    def test_missing_vlm_provider_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            from candlekeep.providers.factory import create_vision_provider
            with pytest.raises(ProviderError, match="CANDLEKEEP_VLM_PROVIDER"):
                create_vision_provider()

    def test_unknown_provider_raises(self):
        from candlekeep.providers.factory import create_llm_provider
        with pytest.raises(ProviderError, match="Unknown"):
            create_llm_provider("nonexistent")

    def test_missing_api_key_raises(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=False):
            from candlekeep.providers.factory import create_llm_provider
            # Remove the key entirely
            import os
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with pytest.raises(ProviderError, match="ANTHROPIC_API_KEY"):
                create_llm_provider("anthropic")

    def test_openai_compat_requires_base_url(self):
        with patch.dict("os.environ", {}, clear=True):
            from candlekeep.providers.factory import create_llm_provider
            with pytest.raises(ProviderError, match="CANDLEKEEP_LLM_BASE_URL"):
                create_llm_provider("openai_compat")


# ---------------------------------------------------------------------------
# Anthropic provider (mocked)
# ---------------------------------------------------------------------------

class TestAnthropicLLM:
    def test_complete_returns_text(self):
        mock_client = MagicMock()
        block = MagicMock()
        block.text = "hello world"
        mock_client.messages.create.return_value = MagicMock(content=[block])

        from candlekeep.providers.anthropic import AnthropicLLM
        llm = AnthropicLLM.__new__(AnthropicLLM)
        llm._client = mock_client
        llm._model = "claude-test"

        result = llm.complete("say hi")
        assert result == "hello world"

    def test_complete_wraps_errors(self):
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("boom")

        from candlekeep.providers.anthropic import AnthropicLLM
        llm = AnthropicLLM.__new__(AnthropicLLM)
        llm._client = mock_client
        llm._model = "claude-test"

        with pytest.raises(ProviderError, match="boom"):
            llm.complete("fail")


class TestAnthropicVision:
    def test_caption_returns_text(self):
        mock_client = MagicMock()
        block = MagicMock()
        block.text = "a cat"
        mock_client.messages.create.return_value = MagicMock(content=[block])

        from candlekeep.providers.anthropic import AnthropicVision
        v = AnthropicVision.__new__(AnthropicVision)
        v._client = mock_client
        v._model = "claude-test"

        result = v.caption(b"\x89PNG\r\n")
        assert result == "a cat"


# ---------------------------------------------------------------------------
# OpenAI provider (mocked)
# ---------------------------------------------------------------------------

class TestOpenAILLM:
    def test_complete_returns_text(self):
        mock_client = MagicMock()
        choice = MagicMock()
        choice.message.content = "hi there"
        mock_client.chat.completions.create.return_value = MagicMock(choices=[choice])

        from candlekeep.providers.openai import OpenAILLM
        llm = OpenAILLM.__new__(OpenAILLM)
        llm._client = mock_client
        llm._model = "gpt-test"

        assert llm.complete("hello") == "hi there"

    def test_complete_wraps_errors(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("nope")

        from candlekeep.providers.openai import OpenAILLM
        llm = OpenAILLM.__new__(OpenAILLM)
        llm._client = mock_client
        llm._model = "gpt-test"

        with pytest.raises(ProviderError):
            llm.complete("fail")


class TestOpenAIVision:
    def test_caption_returns_text(self):
        mock_client = MagicMock()
        choice = MagicMock()
        choice.message.content = "a dog"
        mock_client.chat.completions.create.return_value = MagicMock(choices=[choice])

        from candlekeep.providers.openai import OpenAIVision
        v = OpenAIVision.__new__(OpenAIVision)
        v._client = mock_client
        v._model = "gpt-test"

        assert v.caption(b"\x89PNG\r\n") == "a dog"


# ---------------------------------------------------------------------------
# Bedrock provider (mocked)
# ---------------------------------------------------------------------------

class TestBedrockLLM:
    def test_complete_returns_text(self):
        mock_client = MagicMock()
        body = json.dumps({"content": [{"text": "bedrock says hi"}]}).encode()
        mock_client.invoke_model.return_value = {"body": MagicMock(read=MagicMock(return_value=body))}

        from candlekeep.providers.bedrock import BedrockLLM
        llm = BedrockLLM.__new__(BedrockLLM)
        llm._client = mock_client
        llm._model = "anthropic.claude-test"

        assert llm.complete("hello") == "bedrock says hi"

    def test_complete_wraps_errors(self):
        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = RuntimeError("aws error")

        from candlekeep.providers.bedrock import BedrockLLM
        llm = BedrockLLM.__new__(BedrockLLM)
        llm._client = mock_client
        llm._model = "test"

        with pytest.raises(ProviderError, match="aws error"):
            llm.complete("fail")


class TestBedrockVision:
    def test_caption_returns_text(self):
        mock_client = MagicMock()
        body = json.dumps({"content": [{"text": "a chart"}]}).encode()
        mock_client.invoke_model.return_value = {"body": MagicMock(read=MagicMock(return_value=body))}

        from candlekeep.providers.bedrock import BedrockVision
        v = BedrockVision.__new__(BedrockVision)
        v._client = mock_client
        v._model = "test"

        assert v.caption(b"\x89PNG\r\n") == "a chart"


# ---------------------------------------------------------------------------
# OpenAI-compatible provider (mocked)
# ---------------------------------------------------------------------------

class TestOpenAICompatLLM:
    def test_complete_returns_text(self):
        mock_client = MagicMock()
        choice = MagicMock()
        choice.message.content = "ollama says hi"
        mock_client.chat.completions.create.return_value = MagicMock(choices=[choice])

        from candlekeep.providers.openai_compat import OpenAICompatLLM
        llm = OpenAICompatLLM.__new__(OpenAICompatLLM)
        llm._client = mock_client
        llm._model = "llama3"

        assert llm.complete("hello") == "ollama says hi"


class TestOpenAICompatVision:
    def test_caption_returns_text(self):
        mock_client = MagicMock()
        choice = MagicMock()
        choice.message.content = "a diagram"
        mock_client.chat.completions.create.return_value = MagicMock(choices=[choice])

        from candlekeep.providers.openai_compat import OpenAICompatVision
        v = OpenAICompatVision.__new__(OpenAICompatVision)
        v._client = mock_client
        v._model = "llava"

        assert v.caption(b"\x89PNG\r\n") == "a diagram"


# ---------------------------------------------------------------------------
# Interface contracts
# ---------------------------------------------------------------------------

class TestInterfaceContracts:
    def test_llm_provider_has_name(self):
        from candlekeep.providers.openai import OpenAILLM
        llm = OpenAILLM.__new__(OpenAILLM)
        llm._client = MagicMock()
        llm._model = "test"
        assert llm.name == "openai"

    def test_vision_provider_has_name(self):
        from candlekeep.providers.anthropic import AnthropicVision
        v = AnthropicVision.__new__(AnthropicVision)
        v._client = MagicMock()
        v._model = "test"
        assert v.name == "anthropic"

    def test_all_providers_are_subclasses(self):
        from candlekeep.providers.anthropic import AnthropicLLM, AnthropicVision
        from candlekeep.providers.openai import OpenAILLM, OpenAIVision
        from candlekeep.providers.bedrock import BedrockLLM, BedrockVision
        from candlekeep.providers.openai_compat import OpenAICompatLLM, OpenAICompatVision

        assert issubclass(AnthropicLLM, LLMProvider)
        assert issubclass(OpenAILLM, LLMProvider)
        assert issubclass(BedrockLLM, LLMProvider)
        assert issubclass(OpenAICompatLLM, LLMProvider)

        assert issubclass(AnthropicVision, VisionProvider)
        assert issubclass(OpenAIVision, VisionProvider)
        assert issubclass(BedrockVision, VisionProvider)
        assert issubclass(OpenAICompatVision, VisionProvider)
