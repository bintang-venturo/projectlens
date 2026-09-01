import pytest
from django.test import Client
from django.urls import reverse


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
class TestUIRoutes:
    def test_chat_page_loads(self, client):
        response = client.get(reverse("ui:chat"))
        assert response.status_code == 200

    def test_documents_page_loads(self, client):
        response = client.get(reverse("ui:documents"))
        assert response.status_code == 200

    def test_settings_page_loads(self, client):
        response = client.get(reverse("ui:settings"))
        assert response.status_code == 200

    def test_root_url_is_chat(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert b"Chat History" in response.content

    def test_chat_page_has_nav(self, client):
        response = client.get(reverse("ui:chat"))
        content = response.content.decode()
        assert "Dashboard" in content
        assert "Chat" in content
        assert "Settings" in content

    def test_chat_page_has_branding(self, client):
        response = client.get(reverse("ui:chat"))
        content = response.content.decode()
        assert "ProjectLens" in content
        assert "logo.png" in content

    def test_documents_page_has_active_nav(self, client):
        response = client.get(reverse("ui:documents"))
        content = response.content.decode()
        assert "Document Library" in content

    def test_settings_page_has_sections(self, client):
        response = client.get(reverse("ui:settings"))
        content = response.content.decode()
        assert "AI Engine Configuration" in content
        assert "Embedding Strategy" in content

    def test_all_pages_load_tailwind(self, client):
        response = client.get(reverse("ui:chat"))
        content = response.content.decode()
        assert "cdn.tailwindcss.com" in content

    def test_all_pages_load_htmx(self, client):
        response = client.get(reverse("ui:chat"))
        content = response.content.decode()
        assert "htmx" in content

    def test_all_pages_load_alpinejs(self, client):
        response = client.get(reverse("ui:chat"))
        content = response.content.decode()
        assert "alpinejs" in content

    def test_engine_status_in_sidebar(self, client):
        response = client.get(reverse("ui:chat"))
        content = response.content.decode()
        assert "Engine Status" in content
        assert "Operational" in content

    def test_api_documents_still_works(self, client):
        response = client.get("/api/documents/")
        assert response.status_code == 200

    def test_url_names_resolve(self):
        assert reverse("ui:chat") == "/"
        assert reverse("ui:documents") == "/documents/"
        assert reverse("ui:settings") == "/settings/"
