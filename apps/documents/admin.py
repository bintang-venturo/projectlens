from django.contrib import admin

from .models import Document, DocumentPage


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["name", "status", "file_size", "page_count", "created_at"]
    list_filter = ["status"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(DocumentPage)
class DocumentPageAdmin(admin.ModelAdmin):
    list_display = ["document", "page_number", "created_at"]
    readonly_fields = ["id", "created_at"]
