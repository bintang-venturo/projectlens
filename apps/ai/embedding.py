from django.conf import settings

from apps.ai.providers.base import EmbeddingProvider


_embedding_cache: dict[str, EmbeddingProvider] = {}


def get_embedding_provider() -> EmbeddingProvider:
    provider_name = settings.EMBEDDING_PROVIDER
    if provider_name not in _embedding_cache:
        if provider_name == "gemini":
            from apps.ai.providers.gemini import GeminiEmbeddingProvider

            _embedding_cache[provider_name] = GeminiEmbeddingProvider()
        else:
            raise ValueError(f"Unknown embedding provider: {provider_name}")
    return _embedding_cache[provider_name]


class EmbeddingService:

    def __init__(self, provider: EmbeddingProvider | None = None):
        self.provider = provider or get_embedding_provider()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.provider.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self.provider.embed_query(text)
