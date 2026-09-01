from django.urls import path

from apps.documents.views import DocumentDetailView, DocumentListCreateView

app_name = "documents"

urlpatterns = [
    path("", DocumentListCreateView.as_view(), name="list-create"),
    path("<uuid:pk>/", DocumentDetailView.as_view(), name="detail"),
]
