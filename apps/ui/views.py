from django.shortcuts import render


def chat_view(request):
    return render(request, "ui/chat.html", {"active_page": "chat"})


def documents_view(request):
    return render(request, "ui/documents.html", {"active_page": "documents"})


def settings_view(request):
    return render(request, "ui/settings.html", {"active_page": "settings"})
