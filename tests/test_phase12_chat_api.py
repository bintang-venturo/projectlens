from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.ai.providers.base import AIProvider
from apps.chat.services import Citation, RAGResult
from apps.retrieval.services import RetrievalResult


class FakeAIProvider(AIProvider):
    def generate(self, prompt: str) -> str:
        return "Each player starts with $1,500."


_DEFAULT_CITATIONS = [Citation(source="monopoly.pdf", page=4)]
_DEFAULT_RETRIEVAL = [
    RetrievalResult(
        content="Each player starts with $1,500.",
        source="monopoly.pdf",
        page=4,
        score=0.95,
    ),
]


def _make_rag_result(
    answer="Each player starts with $1,500.",
    citations=None,
    retrieval_results=None,
):
    return RAGResult(
        answer=answer,
        citations=_DEFAULT_CITATIONS if citations is None else citations,
        retrieval_results=_DEFAULT_RETRIEVAL if retrieval_results is None else retrieval_results,
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestChatEndpoint:

    def test_returns_200(self, api_client):
        with patch("apps.chat.views.RAGService") as mock_cls:
            mock_cls.return_value.ask.return_value = _make_rag_result()
            response = api_client.post(
                "/api/chat/",
                {"question": "How much money do players start with?"},
                format="json",
            )
        assert response.status_code == 200

    def test_response_has_answer(self, api_client):
        with patch("apps.chat.views.RAGService") as mock_cls:
            mock_cls.return_value.ask.return_value = _make_rag_result()
            response = api_client.post(
                "/api/chat/",
                {"question": "How much money?"},
                format="json",
            )
        assert response.data["answer"] == "Each player starts with $1,500."

    def test_response_has_citations(self, api_client):
        with patch("apps.chat.views.RAGService") as mock_cls:
            mock_cls.return_value.ask.return_value = _make_rag_result()
            response = api_client.post(
                "/api/chat/",
                {"question": "How much money?"},
                format="json",
            )
        citations = response.data["citations"]
        assert len(citations) == 1
        assert citations[0]["source"] == "monopoly.pdf"
        assert citations[0]["page"] == 4

    def test_response_json_structure(self, api_client):
        with patch("apps.chat.views.RAGService") as mock_cls:
            mock_cls.return_value.ask.return_value = _make_rag_result()
            response = api_client.post(
                "/api/chat/",
                {"question": "question"},
                format="json",
            )
        assert "answer" in response.data
        assert "citations" in response.data
        assert isinstance(response.data["citations"], list)

    def test_multiple_citations(self, api_client):
        result = _make_rag_result(
            citations=[
                Citation(source="monopoly.pdf", page=4),
                Citation(source="monopoly.pdf", page=5),
            ],
        )
        with patch("apps.chat.views.RAGService") as mock_cls:
            mock_cls.return_value.ask.return_value = result
            response = api_client.post(
                "/api/chat/",
                {"question": "question"},
                format="json",
            )
        assert len(response.data["citations"]) == 2

    def test_empty_citations(self, api_client):
        result = _make_rag_result(
            answer="Information not available.",
            citations=[],
            retrieval_results=[],
        )
        with patch("apps.chat.views.RAGService") as mock_cls:
            mock_cls.return_value.ask.return_value = result
            response = api_client.post(
                "/api/chat/",
                {"question": "question"},
                format="json",
            )
        assert response.status_code == 200
        assert response.data["citations"] == []

    def test_calls_rag_service_with_question(self, api_client):
        with patch("apps.chat.views.RAGService") as mock_cls:
            mock_cls.return_value.ask.return_value = _make_rag_result()
            api_client.post(
                "/api/chat/",
                {"question": "How much money?"},
                format="json",
            )
            mock_cls.return_value.ask.assert_called_once_with(
                "How much money?", history=[]
            )


@pytest.mark.django_db
class TestChatEndpointValidation:

    def test_missing_question_returns_400(self, api_client):
        response = api_client.post("/api/chat/", {}, format="json")
        assert response.status_code == 400

    def test_empty_question_returns_400(self, api_client):
        response = api_client.post(
            "/api/chat/", {"question": ""}, format="json"
        )
        assert response.status_code == 400

    def test_no_body_returns_400(self, api_client):
        response = api_client.post(
            "/api/chat/", None, format="json", content_type="application/json"
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestChatEndpointConsistency:

    def test_content_type_is_json(self, api_client):
        with patch("apps.chat.views.RAGService") as mock_cls:
            mock_cls.return_value.ask.return_value = _make_rag_result()
            response = api_client.post(
                "/api/chat/",
                {"question": "question"},
                format="json",
            )
        assert response["Content-Type"] == "application/json"

    def test_response_keys(self, api_client):
        with patch("apps.chat.views.RAGService") as mock_cls:
            mock_cls.return_value.ask.return_value = _make_rag_result()
            response = api_client.post(
                "/api/chat/",
                {"question": "question"},
                format="json",
            )
        assert set(response.data.keys()) == {"session_id", "answer", "citations"}

    def test_citation_keys_only_source_and_page(self, api_client):
        with patch("apps.chat.views.RAGService") as mock_cls:
            mock_cls.return_value.ask.return_value = _make_rag_result()
            response = api_client.post(
                "/api/chat/",
                {"question": "question"},
                format="json",
            )
        citation = response.data["citations"][0]
        assert set(citation.keys()) == {"source", "page"}
