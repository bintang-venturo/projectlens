from unittest.mock import MagicMock, patch

import pytest

from apps.ai.embedding import EmbeddingService, get_embedding_provider
from apps.ai.providers.base import AIProvider, EmbeddingProvider
from apps.ai.providers.gemini import GeminiEmbeddingProvider, GeminiProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeEmbeddingProvider(EmbeddingProvider):

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.4, 0.5, 0.6]


def _mock_embed_response(embeddings_values: list[list[float]]):
    response = MagicMock()
    embedding_objects = []
    for values in embeddings_values:
        emb = MagicMock()
        emb.values = values
        embedding_objects.append(emb)
    response.embeddings = embedding_objects
    return response


# ===========================================================================
# EmbeddingProvider ABC
# ===========================================================================


class TestEmbeddingProviderABC:

    def test_is_abstract(self):
        with pytest.raises(TypeError):
            EmbeddingProvider()

    def test_embed_documents_is_abstract(self):
        assert hasattr(EmbeddingProvider.embed_documents, "__isabstractmethod__")

    def test_embed_query_is_abstract(self):
        assert hasattr(EmbeddingProvider.embed_query, "__isabstractmethod__")

    def test_separate_from_ai_provider(self):
        assert not issubclass(EmbeddingProvider, AIProvider)
        assert not issubclass(AIProvider, EmbeddingProvider)

    def test_fake_provider_is_subclass(self):
        assert issubclass(FakeEmbeddingProvider, EmbeddingProvider)

    def test_fake_provider_instantiable(self):
        provider = FakeEmbeddingProvider()
        assert isinstance(provider, EmbeddingProvider)


# ===========================================================================
# AIProvider ABC (regression — ensure unchanged)
# ===========================================================================


class TestAIProviderUnchanged:

    def test_is_abstract(self):
        with pytest.raises(TypeError):
            AIProvider()

    def test_generate_is_abstract(self):
        assert hasattr(AIProvider.generate, "__isabstractmethod__")

    def test_gemini_provider_is_subclass(self):
        assert issubclass(GeminiProvider, AIProvider)


# ===========================================================================
# GeminiEmbeddingProvider
# ===========================================================================


class TestGeminiEmbeddingProvider:

    def test_is_embedding_provider_subclass(self):
        assert issubclass(GeminiEmbeddingProvider, EmbeddingProvider)

    def test_is_not_ai_provider_subclass(self):
        assert not issubclass(GeminiEmbeddingProvider, AIProvider)

    @patch("apps.ai.providers.gemini.genai.Client")
    def test_embed_documents(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.embed_content.return_value = _mock_embed_response(
            [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        )

        provider = GeminiEmbeddingProvider()
        result = provider.embed_documents(["text1", "text2", "text3"])

        assert len(result) == 3
        assert result[0] == [0.1, 0.2]
        assert result[1] == [0.3, 0.4]
        assert result[2] == [0.5, 0.6]
        mock_client.models.embed_content.assert_called_once()

    @patch("apps.ai.providers.gemini.genai.Client")
    def test_embed_documents_passes_model(self, mock_client_cls, settings):
        settings.EMBEDDING_MODEL = "test-model-123"
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.embed_content.return_value = _mock_embed_response([[0.1]])

        provider = GeminiEmbeddingProvider()
        provider.embed_documents(["text"])

        call_kwargs = mock_client.models.embed_content.call_args
        assert call_kwargs.kwargs["model"] == "test-model-123"

    @patch("apps.ai.providers.gemini.genai.Client")
    def test_embed_documents_passes_texts(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.embed_content.return_value = _mock_embed_response(
            [[0.1], [0.2]]
        )

        provider = GeminiEmbeddingProvider()
        provider.embed_documents(["hello", "world"])

        call_kwargs = mock_client.models.embed_content.call_args
        assert call_kwargs.kwargs["contents"] == ["hello", "world"]

    @patch("apps.ai.providers.gemini.genai.Client")
    def test_embed_documents_empty_list(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.embed_content.return_value = _mock_embed_response([])

        provider = GeminiEmbeddingProvider()
        result = provider.embed_documents([])

        assert result == []

    @patch("apps.ai.providers.gemini.genai.Client")
    def test_embed_query(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.embed_content.return_value = _mock_embed_response(
            [[0.7, 0.8, 0.9]]
        )

        provider = GeminiEmbeddingProvider()
        result = provider.embed_query("what is this?")

        assert result == [0.7, 0.8, 0.9]

    @patch("apps.ai.providers.gemini.genai.Client")
    def test_embed_query_passes_text(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.embed_content.return_value = _mock_embed_response([[0.1]])

        provider = GeminiEmbeddingProvider()
        provider.embed_query("search term")

        call_kwargs = mock_client.models.embed_content.call_args
        assert call_kwargs.kwargs["contents"] == "search term"

    @patch("apps.ai.providers.gemini.genai.Client")
    def test_uses_api_key_from_settings(self, mock_client_cls, settings):
        settings.EMBEDDING_API_KEY = "test-api-key-789"
        GeminiEmbeddingProvider()
        mock_client_cls.assert_called_once_with(api_key="test-api-key-789")

    @patch("apps.ai.providers.gemini.genai.Client")
    def test_uses_model_from_settings(self, mock_client_cls, settings):
        settings.EMBEDDING_MODEL = "custom-embed-model"
        provider = GeminiEmbeddingProvider()
        assert provider.model == "custom-embed-model"


# ===========================================================================
# get_embedding_provider
# ===========================================================================


class TestGetEmbeddingProvider:

    @patch("apps.ai.providers.gemini.genai.Client")
    def test_returns_gemini_provider(self, mock_client_cls, settings):
        settings.EMBEDDING_PROVIDER = "gemini"
        provider = get_embedding_provider()
        assert isinstance(provider, GeminiEmbeddingProvider)

    def test_raises_on_unknown_provider(self, settings):
        settings.EMBEDDING_PROVIDER = "unknown"
        with pytest.raises(ValueError, match="Unknown embedding provider"):
            get_embedding_provider()

    @patch("apps.ai.providers.gemini.genai.Client")
    def test_returns_embedding_provider_instance(self, mock_client_cls, settings):
        settings.EMBEDDING_PROVIDER = "gemini"
        provider = get_embedding_provider()
        assert isinstance(provider, EmbeddingProvider)


# ===========================================================================
# EmbeddingService
# ===========================================================================


class TestEmbeddingService:

    def test_with_injected_provider(self):
        provider = FakeEmbeddingProvider()
        service = EmbeddingService(provider=provider)
        assert service.provider is provider

    def test_embed_documents_delegates(self):
        provider = FakeEmbeddingProvider()
        service = EmbeddingService(provider=provider)
        result = service.embed_documents(["a", "b"])
        assert len(result) == 2
        assert result[0] == [0.1, 0.2, 0.3]

    def test_embed_query_delegates(self):
        provider = FakeEmbeddingProvider()
        service = EmbeddingService(provider=provider)
        result = service.embed_query("test")
        assert result == [0.4, 0.5, 0.6]

    def test_embed_documents_returns_list_of_lists(self):
        provider = FakeEmbeddingProvider()
        service = EmbeddingService(provider=provider)
        result = service.embed_documents(["a", "b", "c"])
        assert len(result) == 3
        assert all(isinstance(r, list) for r in result)
        assert all(isinstance(v, float) for r in result for v in r)

    def test_embed_query_returns_list_of_floats(self):
        provider = FakeEmbeddingProvider()
        service = EmbeddingService(provider=provider)
        result = service.embed_query("test")
        assert isinstance(result, list)
        assert all(isinstance(v, float) for v in result)

    @patch("apps.ai.providers.gemini.genai.Client")
    def test_default_provider_from_settings(self, mock_client_cls, settings):
        settings.EMBEDDING_PROVIDER = "gemini"
        service = EmbeddingService()
        assert isinstance(service.provider, GeminiEmbeddingProvider)

    def test_same_provider_for_documents_and_queries(self):
        provider = FakeEmbeddingProvider()
        service = EmbeddingService(provider=provider)
        service.embed_documents(["text"])
        service.embed_query("query")
        assert service.provider is provider

    def test_embed_documents_preserves_order(self):
        mock_provider = MagicMock(spec=EmbeddingProvider)
        mock_provider.embed_documents.return_value = [
            [1.0, 0.0],
            [0.0, 1.0],
            [0.5, 0.5],
        ]
        service = EmbeddingService(provider=mock_provider)
        result = service.embed_documents(["first", "second", "third"])
        assert result[0] == [1.0, 0.0]
        assert result[1] == [0.0, 1.0]
        assert result[2] == [0.5, 0.5]

    def test_embed_documents_empty_list(self):
        mock_provider = MagicMock(spec=EmbeddingProvider)
        mock_provider.embed_documents.return_value = []
        service = EmbeddingService(provider=mock_provider)
        result = service.embed_documents([])
        assert result == []
