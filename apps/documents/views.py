from rest_framework import generics, parsers, status
from rest_framework.response import Response

from apps.documents.models import Document
from apps.documents.serializers import DocumentSerializer, DocumentUploadSerializer
from apps.documents.services import create_document


class DocumentListCreateView(generics.ListCreateAPIView):
    queryset = Document.objects.all()
    parser_classes = [parsers.MultiPartParser, parsers.JSONParser]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DocumentUploadSerializer
        return DocumentSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc = create_document(serializer.validated_data["file"])
        return Response(
            DocumentSerializer(doc).data,
            status=status.HTTP_201_CREATED,
        )


class DocumentDetailView(generics.RetrieveAPIView):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
