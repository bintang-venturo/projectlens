from dataclasses import dataclass

from django.conf import settings

from apps.ai.embedding import EmbeddingService
from core.chroma import ChromaService


@dataclass
class RetrievalResult:
    content: str
    source: str
    page: int
    score: float


class RetrievalService:

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        chroma_service: ChromaService | None = None,
    ):
        self.embedding_service = embedding_service or EmbeddingService()
        self.chroma_service = chroma_service or ChromaService()

    def search(self, query: str, k: int | None = None) -> list[RetrievalResult]:
        if k is None:
            k = settings.RETRIEVAL_K

        query_embedding = self.embedding_service.embed_query(query)
        raw = self.chroma_service.query(query_embedding=query_embedding, n_results=k)

        return self._normalize(raw)

    def _normalize(self, raw: dict) -> list[RetrievalResult]:
        ids = raw.get("ids") or [[]]
        documents = raw.get("documents") or [[]]
        metadatas = raw.get("metadatas") or [[]]
        distances = raw.get("distances") or [[]]

        results = []
        for doc, meta, dist in zip(
            documents[0], metadatas[0], distances[0]
        ):
            score = 1.0 - dist
            results.append(
                RetrievalResult(
                    content=doc or "",
                    source=meta.get("source", ""),
                    page=int(meta.get("page", 0)),
                    score=round(score, 4),
                )
            )
        return results
