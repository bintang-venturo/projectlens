from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chat.models import ChatMessage, ChatSession
from apps.chat.serializers import ChatRequestSerializer, ChatResponseSerializer
from apps.chat.services import RAGService


class ChatView(APIView):

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question = serializer.validated_data["question"]
        session_id = serializer.validated_data["session_id"]

        session = self._get_or_create_session(session_id)
        history = self._load_history(session)

        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content=question,
        )

        rag_service = RAGService()
        result = rag_service.ask(question, history=history)

        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=result.answer,
        )

        response_data = {
            "session_id": str(session.id),
            "answer": result.answer,
            "citations": [
                {"source": c.source, "page": c.page}
                for c in result.citations
            ],
        }
        response_serializer = ChatResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)

        return Response(response_serializer.validated_data, status=status.HTTP_200_OK)

    def _get_or_create_session(self, session_id):
        if session_id is None:
            return ChatSession.objects.create()
        try:
            return ChatSession.objects.get(id=session_id)
        except ChatSession.DoesNotExist:
            from rest_framework.exceptions import NotFound

            raise NotFound(f"Chat session {session_id} not found.")

    def _load_history(self, session):
        limit = settings.CHAT_HISTORY_LIMIT
        messages = list(
            ChatMessage.objects.filter(session=session)
            .order_by("-created_at")[:limit]
        )
        messages.reverse()
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
