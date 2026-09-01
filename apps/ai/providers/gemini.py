from django.conf import settings
from google import genai

from .base import AIProvider, EmbeddingProvider


class GeminiProvider(AIProvider):

    def __init__(self):
        self.client = genai.Client(api_key=settings.EMBEDDING_API_KEY)
        self.model = settings.GEMINI_MODEL

    def generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        return response.text


class GeminiEmbeddingProvider(EmbeddingProvider):

    def __init__(self):
        self.client = genai.Client(api_key=settings.EMBEDDING_API_KEY)
        self.model = settings.EMBEDDING_MODEL

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        response = self.client.models.embed_content(
            model=self.model,
            contents=texts,
        )
        return [e.values for e in response.embeddings]

    def embed_query(self, text: str) -> list[float]:
        response = self.client.models.embed_content(
            model=self.model,
            contents=text,
        )
        return response.embeddings[0].values
