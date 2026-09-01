from django.urls import path

from . import views

app_name = "ui"

urlpatterns = [
    path("", views.chat_view, name="chat"),
    path("documents/", views.documents_view, name="documents"),
    path("settings/", views.settings_view, name="settings"),
]
