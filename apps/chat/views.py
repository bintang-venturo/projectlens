from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chat.serializers import ChatRequestSerializer, ChatResponseSerializer
from apps.chat.services import RAGService


class ChatView(APIView):

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question = serializer.validated_data["question"]
        rag_service = RAGService()
        result = rag_service.ask(question)

        response_data = {
            "answer": result.answer,
            "citations": [
                {"source": c.source, "page": c.page}
                for c in result.citations
            ],
        }
        response_serializer = ChatResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)

        return Response(response_serializer.validated_data, status=status.HTTP_200_OK)
