import uuid
from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.ai.providers.base import AIProvider
from apps.chat.models import ChatMessage, ChatSession
from apps.chat.services import Citation, RAGResult, RAGService, SYSTEM_PROMPT
from apps.retrieval.services import RetrievalResult


class FakeAIProvider(AIProvider):
    def __init__(self):
        self.last_prompt = None

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return "Fake answer."


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


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSessionLifecycle:

    def test_no_session_id_creates_new_session(self, api_client):
        with patch("apps.chat.views.RAGService") as mock_cls:
            mock_cls.return_value.ask.return_value = _make_rag_result()
            response = api_client.post(
                "/api/chat/", {"question": "hi"}, format="json"
            )
        assert response.status_code == 200
        assert "session_id" in response.data
        assert ChatSession.objects.filter(id=response.data["session_id"]).exists()

    def test_null_session_id_creates_new_session(self, api_client):
        with patch("apps.chat.views.RAGService") as mock_cls:
            mock_cls.return_value.ask.return_value = _make_rag_result()
            response = api_client.post(
                "/api/chat/",
                {"question": "hi", "session_id": None},
                format="json",
            )
        assert response.status_code == 200
        assert "session_id" in response.data

    def test_valid_session_id_reuses_session(self, api_client):
        session = ChatSession.objects.create()
        with patch("apps.chat.views.RAGService") as mock_cls:
            mock_cls.return_value.ask.return_value = _make_rag_result()
            response = api_client.post(
                "/api/chat/",
                {"question": "hi", "session_id": str(session.id)},
                format="json",
            )
        assert response.status_code == 200
        assert str(response.data["session_id"]) == str(session.id)
        assert ChatSession.objects.count() == 1

    def test_nonexistent_session_id_returns_404(self, api_client):
        fake_id = str(uuid.uuid4())
        response = api_client.post(
            "/api/chat/",
            {"question": "hi", "session_id": fake_id},
            format="json",
        )
        assert response.status_code == 404

    def test_invalid_session_id_format_returns_400(self, api_client):
        response = api_client.post(
            "/api/chat/",
            {"question": "hi", "session_id": "not-a-uuid"},
            format="json",
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Message persistence
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMessagePersistence:

    def test_saves_user_and_assistant_messages(self, api_client):
        with patch("apps.chat.views.RAGService") as mock_cls:
            mock_cls.return_value.ask.return_value = _make_rag_result(
                answer="Test answer."
            )
            response = api_client.post(
                "/api/chat/", {"question": "Test question"}, format="json"
            )
        session_id = response.data["session_id"]
        messages = ChatMessage.objects.filter(session_id=session_id).order_by(
            "created_at"
        )
        assert messages.count() == 2
        assert messages[0].role == ChatMessage.Role.USER
        assert messages[0].content == "Test question"
        assert messages[1].role == ChatMessage.Role.ASSISTANT
        assert messages[1].content == "Test answer."

    def test_messages_accumulate_across_requests(self, api_client):
        session = ChatSession.objects.create()
        with patch("apps.chat.views.RAGService") as mock_cls:
            mock_cls.return_value.ask.return_value = _make_rag_result(answer="A1")
            api_client.post(
                "/api/chat/",
                {"question": "Q1", "session_id": str(session.id)},
                format="json",
            )
            mock_cls.return_value.ask.return_value = _make_rag_result(answer="A2")
            api_client.post(
                "/api/chat/",
                {"question": "Q2", "session_id": str(session.id)},
                format="json",
            )
        messages = ChatMessage.objects.filter(session=session).order_by("created_at")
        assert messages.count() == 4
        assert [m.role for m in messages] == [
            ChatMessage.Role.USER,
            ChatMessage.Role.ASSISTANT,
            ChatMessage.Role.USER,
            ChatMessage.Role.ASSISTANT,
        ]


# ---------------------------------------------------------------------------
# History passed to RAGService
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestHistoryPassedToRAG:

    def test_first_message_has_empty_history(self, api_client):
        with patch("apps.chat.views.RAGService") as mock_cls:
            mock_cls.return_value.ask.return_value = _make_rag_result()
            api_client.post(
                "/api/chat/", {"question": "Q1"}, format="json"
            )
            mock_cls.return_value.ask.assert_called_once_with("Q1", history=[])

    def test_second_message_includes_prior_history(self, api_client):
        session = ChatSession.objects.create()
        with patch("apps.chat.views.RAGService") as mock_cls:
            mock_cls.return_value.ask.return_value = _make_rag_result(answer="A1")
            api_client.post(
                "/api/chat/",
                {"question": "Q1", "session_id": str(session.id)},
                format="json",
            )
            mock_cls.return_value.ask.return_value = _make_rag_result(answer="A2")
            api_client.post(
                "/api/chat/",
                {"question": "Q2", "session_id": str(session.id)},
                format="json",
            )
            _, second_call = mock_cls.return_value.ask.call_args_list
            assert second_call.args == ("Q2",)
            history = second_call.kwargs["history"]
            assert len(history) == 2
            assert history[0] == {"role": "USER", "content": "Q1"}
            assert history[1] == {"role": "ASSISTANT", "content": "A1"}

    @override_settings(CHAT_HISTORY_LIMIT=2)
    def test_history_respects_limit(self, api_client):
        session = ChatSession.objects.create()
        with patch("apps.chat.views.RAGService") as mock_cls:
            for i in range(1, 4):
                mock_cls.return_value.ask.return_value = _make_rag_result(
                    answer=f"A{i}"
                )
                api_client.post(
                    "/api/chat/",
                    {"question": f"Q{i}", "session_id": str(session.id)},
                    format="json",
                )
            last_call = mock_cls.return_value.ask.call_args_list[-1]
            history = last_call.kwargs["history"]
            assert len(history) == 2


# ---------------------------------------------------------------------------
# RAGService prompt construction with history
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRAGServiceHistory:

    def _make_service(self, ai_provider):
        from unittest.mock import MagicMock

        retrieval = MagicMock()
        retrieval.search.return_value = [
            RetrievalResult(
                content="chunk text", source="doc.pdf", page=1, score=0.9
            )
        ]
        return RAGService(retrieval_service=retrieval, ai_provider=ai_provider)

    def test_ask_with_no_history_produces_original_prompt(self):
        provider = FakeAIProvider()
        service = self._make_service(provider)
        service.ask("What is X?")
        assert "Conversation history:" not in provider.last_prompt
        assert "Question:\nWhat is X?" in provider.last_prompt

    def test_ask_with_empty_history_produces_original_prompt(self):
        provider = FakeAIProvider()
        service = self._make_service(provider)
        service.ask("What is X?", history=[])
        assert "Conversation history:" not in provider.last_prompt

    def test_ask_with_history_includes_conversation_block(self):
        provider = FakeAIProvider()
        service = self._make_service(provider)
        history = [
            {"role": "USER", "content": "Hello"},
            {"role": "ASSISTANT", "content": "Hi there"},
        ]
        service.ask("Follow up?", history=history)
        prompt = provider.last_prompt
        assert "Conversation history:" in prompt
        assert "User: Hello" in prompt
        assert "Assistant: Hi there" in prompt

    def test_history_appears_between_system_and_context(self):
        provider = FakeAIProvider()
        service = self._make_service(provider)
        history = [{"role": "USER", "content": "prev"}]
        service.ask("current?", history=history)
        prompt = provider.last_prompt
        sys_pos = prompt.index(SYSTEM_PROMPT)
        hist_pos = prompt.index("Conversation history:")
        ctx_pos = prompt.index("Context:")
        q_pos = prompt.index("Question:")
        assert sys_pos < hist_pos < ctx_pos < q_pos


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBackwardCompatibility:

    def test_request_without_session_id_returns_200(self, api_client):
        with patch("apps.chat.views.RAGService") as mock_cls:
            mock_cls.return_value.ask.return_value = _make_rag_result()
            response = api_client.post(
                "/api/chat/", {"question": "hi"}, format="json"
            )
        assert response.status_code == 200

    def test_response_still_has_answer_and_citations(self, api_client):
        with patch("apps.chat.views.RAGService") as mock_cls:
            mock_cls.return_value.ask.return_value = _make_rag_result()
            response = api_client.post(
                "/api/chat/", {"question": "hi"}, format="json"
            )
        assert "answer" in response.data
        assert "citations" in response.data
        assert "session_id" in response.data
