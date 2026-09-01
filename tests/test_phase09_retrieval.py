import chromadb
import pytest

from apps.ai.embedding import EmbeddingService
from apps.ai.providers.base import EmbeddingProvider
from apps.retrieval.services import RetrievalResult, RetrievalService
from core.chroma import COLLECTION_NAME, ChromaService

pytestmark = pytest.mark.no_embed_mock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeEmbeddingProvider(EmbeddingProvider):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(i)] * 3 for i in range(len(texts))]

    def embed_query(self, text: str) -> list[float]:
        return [0.0, 0.0, 0.0]


@pytest.fixture()
def chroma():
    client = chromadb.Client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    svc = ChromaService(client=client)
    return svc


@pytest.fixture()
def embedding():
    return EmbeddingService(provider=FakeEmbeddingProvider())


def _seed_collection(chroma: ChromaService, count: int = 3):
    ids = [f"doc.pdf:{i}:0" for i in range(count)]
    embeddings = [[float(i)] * 3 for i in range(count)]
    documents = [f"Content of page {i}" for i in range(count)]
    metadatas = [
        {"document_id": "test-uuid", "source": "doc.pdf", "page": i, "chunk_index": 0}
        for i in range(count)
    ]
    chroma.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)


# ---------------------------------------------------------------------------
# ChromaService.query
# ---------------------------------------------------------------------------

class TestChromaServiceQuery:
    def test_returns_documents_and_metadata(self, chroma):
        _seed_collection(chroma, count=3)
        result = chroma.query(query_embedding=[0.0, 0.0, 0.0], n_results=2)
        assert "documents" in result
        assert "metadatas" in result
        assert "distances" in result
        assert len(result["documents"][0]) == 2

    def test_respects_n_results(self, chroma):
        _seed_collection(chroma, count=5)
        result = chroma.query(query_embedding=[0.0, 0.0, 0.0], n_results=3)
        assert len(result["ids"][0]) == 3

    def test_returns_fewer_when_collection_smaller(self, chroma):
        _seed_collection(chroma, count=2)
        result = chroma.query(query_embedding=[0.0, 0.0, 0.0], n_results=10)
        assert len(result["ids"][0]) == 2

    def test_empty_collection(self, chroma):
        chroma.get_collection()
        result = chroma.query(query_embedding=[0.0, 0.0, 0.0], n_results=5)
        assert result["ids"] == [[]]


# ---------------------------------------------------------------------------
# RetrievalService.search
# ---------------------------------------------------------------------------

class TestRetrievalServiceSearch:
    def test_returns_list_of_retrieval_results(self, chroma, embedding):
        _seed_collection(chroma, count=3)
        svc = RetrievalService(embedding_service=embedding, chroma_service=chroma)
        results = svc.search("test query")
        assert isinstance(results, list)
        assert all(isinstance(r, RetrievalResult) for r in results)

    def test_result_contains_content_source_page_score(self, chroma, embedding):
        _seed_collection(chroma, count=1)
        svc = RetrievalService(embedding_service=embedding, chroma_service=chroma)
        results = svc.search("test query", k=5)
        assert len(results) == 1
        r = results[0]
        assert r.content == "Content of page 0"
        assert r.source == "doc.pdf"
        assert r.page == 0
        assert isinstance(r.score, float)

    def test_default_k_from_settings(self, chroma, embedding, settings):
        settings.RETRIEVAL_K = 3
        _seed_collection(chroma, count=10)
        svc = RetrievalService(embedding_service=embedding, chroma_service=chroma)
        results = svc.search("test query")
        assert len(results) == 3

    def test_custom_k_overrides_settings(self, chroma, embedding, settings):
        settings.RETRIEVAL_K = 3
        _seed_collection(chroma, count=10)
        svc = RetrievalService(embedding_service=embedding, chroma_service=chroma)
        results = svc.search("test query", k=7)
        assert len(results) == 7

    def test_empty_collection_returns_empty(self, chroma, embedding):
        chroma.get_collection()
        svc = RetrievalService(embedding_service=embedding, chroma_service=chroma)
        results = svc.search("test query")
        assert results == []

    def test_score_is_bounded(self, chroma, embedding):
        _seed_collection(chroma, count=3)
        svc = RetrievalService(embedding_service=embedding, chroma_service=chroma)
        results = svc.search("test query")
        for r in results:
            assert r.score <= 1.0

    def test_results_ordered_by_relevance(self, chroma, embedding):
        _seed_collection(chroma, count=5)
        svc = RetrievalService(embedding_service=embedding, chroma_service=chroma)
        results = svc.search("test query")
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# RetrievalService does not generate answers
# ---------------------------------------------------------------------------

class TestRetrievalServiceBoundary:
    def test_returns_raw_content_not_generated_answer(self, chroma, embedding):
        _seed_collection(chroma, count=1)
        svc = RetrievalService(embedding_service=embedding, chroma_service=chroma)
        results = svc.search("What is on page 0?")
        assert results[0].content == "Content of page 0"

    def test_no_ai_provider_used(self, chroma, embedding):
        _seed_collection(chroma, count=1)
        svc = RetrievalService(embedding_service=embedding, chroma_service=chroma)
        results = svc.search("test", k=5)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

class TestNormalization:
    def test_metadata_page_is_int(self, chroma, embedding):
        _seed_collection(chroma, count=1)
        svc = RetrievalService(embedding_service=embedding, chroma_service=chroma)
        results = svc.search("test query")
        assert isinstance(results[0].page, int)

    def test_score_rounded_to_four_decimals(self, chroma, embedding):
        _seed_collection(chroma, count=1)
        svc = RetrievalService(embedding_service=embedding, chroma_service=chroma)
        results = svc.search("test query")
        score_str = str(results[0].score)
        if "." in score_str:
            decimals = len(score_str.split(".")[1])
            assert decimals <= 4

    def test_multiple_sources(self, chroma, embedding):
        chroma.upsert(
            ids=["a.pdf:0:0", "b.pdf:1:0"],
            embeddings=[[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]],
            documents=["Content A", "Content B"],
            metadatas=[
                {"document_id": "uuid-a", "source": "a.pdf", "page": 0, "chunk_index": 0},
                {"document_id": "uuid-b", "source": "b.pdf", "page": 1, "chunk_index": 0},
            ],
        )
        svc = RetrievalService(embedding_service=embedding, chroma_service=chroma)
        results = svc.search("test query", k=2)
        sources = {r.source for r in results}
        assert "a.pdf" in sources
        assert "b.pdf" in sources
