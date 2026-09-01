from django.shortcuts import render

from apps.documents.models import Document


def chat_view(request):
    return render(request, "ui/chat.html", {"active_page": "chat"})


def documents_view(request):
    return render(request, "ui/documents.html", {"active_page": "documents"})


def document_rows_partial(request):
    documents = Document.objects.all()
    has_active = documents.filter(
        status__in=[Document.Status.PENDING, Document.Status.PROCESSING]
    ).exists()
    return render(request, "ui/_document_rows.html", {
        "documents": documents,
        "has_active": has_active,
    })


def settings_view(request):
    return render(request, "ui/settings.html", {"active_page": "settings"})
