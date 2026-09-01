from django.contrib import admin

from .models import DocumentChunk


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ["chunk_id", "document", "page", "chunk_index", "created_at"]
    readonly_fields = ["id", "created_at"]
