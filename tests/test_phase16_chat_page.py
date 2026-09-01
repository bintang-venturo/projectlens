from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse


class TestChatPageStructure(TestCase):
    """Tests for the chat page template structure."""

    def setUp(self):
        self.client = Client()
        self.url = reverse("ui:chat")

    def test_page_loads(self):
        resp = self.client.get(self.url)
        assert resp.status_code == 200

    def test_page_has_alpine_component(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "x-data" in content

    def test_page_has_csrf_token(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "csrfToken" in content

    def test_page_has_message_input(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "Ask a question about your documents" in content
        assert "<textarea" in content

    def test_page_has_send_button(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "sendMessage()" in content

    def test_page_has_empty_state(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "Ask a question about your documents" in content
        assert "Upload documents in the Document Library" in content

    def test_page_has_chat_history_sidebar(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "Chat History" in content

    def test_page_has_new_conversation_button(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "newConversation()" in content

    def test_page_has_session_management(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "sessionId" in content
        assert "session_id" in content

    def test_page_has_loading_indicator(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "Searching documents" in content

    def test_page_has_error_handling(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "error" in content
        assert "Network error" in content

    def test_page_has_citations_rendering(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "citations" in content
        assert "Sources" in content or "SOURCES" in content

    def test_page_has_keyboard_handler(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "handleKeydown" in content

    def test_page_has_auto_scroll(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "scrollToBottom" in content

    def test_page_title(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "<title>Chat — ProjectLens</title>" in content

    def test_page_has_projectlens_label(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "ProjectLens AI" in content


class TestChatAPIIntegration(TestCase):
    """Tests verifying the chat API still works for the frontend."""

    def setUp(self):
        self.client = Client()

    @patch("apps.chat.services.RAGService.ask")
    def test_chat_api_accepts_json(self, mock_ask):
        from apps.chat.services import Citation, RAGResult

        mock_ask.return_value = RAGResult(
            answer="Test answer",
            citations=[Citation(source="doc.pdf", page=1)],
        )

        resp = self.client.post(
            "/api/chat/",
            data={"question": "test question"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["answer"] == "Test answer"
        assert len(data["citations"]) == 1
        assert data["citations"][0]["source"] == "doc.pdf"
        assert data["citations"][0]["page"] == 1

    @patch("apps.chat.services.RAGService.ask")
    def test_chat_api_multi_turn(self, mock_ask):
        from apps.chat.services import RAGResult

        mock_ask.return_value = RAGResult(answer="First answer", citations=[])

        resp1 = self.client.post(
            "/api/chat/",
            data={"question": "first question"},
            content_type="application/json",
        )
        session_id = resp1.json()["session_id"]

        mock_ask.return_value = RAGResult(answer="Second answer", citations=[])

        resp2 = self.client.post(
            "/api/chat/",
            data={"question": "follow up", "session_id": session_id},
            content_type="application/json",
        )
        assert resp2.status_code == 200
        assert resp2.json()["session_id"] == session_id
        assert resp2.json()["answer"] == "Second answer"

    def test_chat_api_empty_question_rejected(self):
        resp = self.client.post(
            "/api/chat/",
            data={"question": ""},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_chat_api_missing_question_rejected(self):
        resp = self.client.post(
            "/api/chat/",
            data={},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_chat_api_invalid_session_returns_404(self):
        resp = self.client.post(
            "/api/chat/",
            data={
                "question": "test",
                "session_id": "00000000-0000-0000-0000-000000000000",
            },
            content_type="application/json",
        )
        assert resp.status_code == 404
