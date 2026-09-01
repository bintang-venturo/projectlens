import uuid

from django.db import models

from apps.documents.models import Document, DocumentPage


class DocumentChunk(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    page = models.ForeignKey(
        DocumentPage,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_index = models.PositiveIntegerField()
    chunk_id = models.CharField(max_length=512, unique=True)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "page", "chunk_index"],
                name="unique_document_page_chunk",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.chunk_id:
            self.chunk_id = (
                f"{self.document.name}:{self.page.page_number}:{self.chunk_index}"
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.chunk_id
