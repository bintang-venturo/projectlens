from django.urls import path

from . import views

app_name = "ui"

urlpatterns = [
    path("", views.chat_view, name="chat"),
    path("documents/partials/rows/", views.document_rows_partial, name="document-rows"),
    path("documents/", views.documents_view, name="documents"),
    path("project-map/", views.project_map_view, name="project-map"),
    path("settings/", views.settings_view, name="settings"),
]
