from django.urls import path

from apps.chat.views import ChatView, SessionListView

app_name = "chat"

urlpatterns = [
    path("", ChatView.as_view(), name="chat"),
    path("sessions/", SessionListView.as_view(), name="sessions"),
]
