from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/documents/", include("apps.documents.urls")),
    path("api/chat/", include("apps.chat.urls")),
    path("", include("apps.ui.urls")),
]
