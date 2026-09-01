from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.documents.models import Document


def _pdf_bytes():
    return b"%PDF-1.4 test content"


def _pdf_file(name="test.pdf"):
    return SimpleUploadedFile(name, _pdf_bytes(), content_type="application/pdf")


def _create_doc(name="report.pdf", status=Document.Status.PENDING, **kwargs):
    return Document.objects.create(
        name=name,
        file=_pdf_file(name),
        file_size=kwargs.pop("file_size", 2_500_000),
        page_count=kwargs.pop("page_count", 0),
        status=status,
        error_message=kwargs.pop("error_message", ""),
        **kwargs,
    )


class TestDocumentRowsPartial(TestCase):
    """Tests for the htmx partial at /documents/partials/rows/."""

    def setUp(self):
        self.client = Client()
        self.url = reverse("ui:document-rows")

    def test_partial_returns_200(self):
        resp = self.client.get(self.url)
        assert resp.status_code == 200

    def test_partial_empty_state(self):
        resp = self.client.get(self.url)
        assert b"No documents uploaded yet" in resp.content

    def test_partial_shows_documents(self):
        _create_doc(name="alpha.pdf")
        _create_doc(name="beta.pdf")
        resp = self.client.get(self.url)
        assert b"alpha.pdf" in resp.content
        assert b"beta.pdf" in resp.content

    def test_partial_shows_completed_status(self):
        _create_doc(status=Document.Status.COMPLETED, page_count=10)
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "COMPLETED" in content
        assert "10 pages" in content

    def test_partial_shows_pending_status(self):
        _create_doc(status=Document.Status.PENDING)
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "PENDING" in content
        assert "In Queue" in content

    def test_partial_shows_processing_status(self):
        _create_doc(status=Document.Status.PROCESSING)
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "PROCESSING" in content

    def test_partial_shows_failed_status_with_error(self):
        _create_doc(
            status=Document.Status.FAILED,
            error_message="Corrupt PDF structure",
        )
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "FAILED" in content
        assert "Corrupt PDF structure" in content

    def test_partial_shows_file_size(self):
        _create_doc(file_size=2_516_582)
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "MB" in content

    def test_partial_shows_date(self):
        doc = _create_doc()
        resp = self.client.get(self.url)
        expected_date = doc.created_at.strftime("%b").lstrip("0")
        assert expected_date.encode() in resp.content

    def test_partial_has_polling_when_active_docs(self):
        _create_doc(status=Document.Status.PENDING)
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert 'hx-trigger="every 5s"' in content
        assert "hx-get" in content

    def test_partial_no_polling_when_all_terminal(self):
        _create_doc(status=Document.Status.COMPLETED)
        _create_doc(status=Document.Status.FAILED, error_message="err")
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "every 5s" not in content

    def test_partial_ordered_by_newest_first(self):
        doc_old = _create_doc(name="old.pdf")
        doc_new = _create_doc(name="new.pdf")
        resp = self.client.get(self.url)
        content = resp.content.decode()
        pos_new = content.index("new.pdf")
        pos_old = content.index("old.pdf")
        assert pos_new < pos_old

    def test_partial_page_count_singular(self):
        _create_doc(status=Document.Status.COMPLETED, page_count=1)
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "1 page" in content
        assert "1 pages" not in content


class TestDocumentsPageIntegration(TestCase):
    """Tests for the full documents page at /documents/."""

    def setUp(self):
        self.client = Client()
        self.url = reverse("ui:documents")

    def test_page_loads(self):
        resp = self.client.get(self.url)
        assert resp.status_code == 200

    def test_page_has_htmx_trigger(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "hx-get" in content
        assert "hx-trigger" in content
        assert "document-rows" in content or "partials/rows" in content

    def test_page_has_upload_button(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "Upload File" in content
        assert 'disabled=""' not in content.split("Upload File")[0].split("<button")[-1]

    def test_page_has_drop_zone(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "Drag and drop documents here" in content
        assert "@drop.prevent" in content

    def test_page_has_csrf_token(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "csrfToken" in content

    def test_page_has_alpine_component(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "x-data" in content

    def test_page_has_file_input(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert 'type="file"' in content
        assert "accept=" in content

    def test_page_has_error_area(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "uploadError" in content

    def test_page_has_success_area(self):
        resp = self.client.get(self.url)
        content = resp.content.decode()
        assert "uploadSuccess" in content

    def test_existing_api_still_works(self):
        resp = self.client.get("/api/documents/")
        assert resp.status_code == 200


@override_settings(MEDIA_ROOT="/tmp/projectlens_test_media")
class TestUploadViaAPI(TestCase):
    """Tests verifying upload still works with CSRF token from browser context."""

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    @patch("apps.ingestion.tasks.process_document.delay")
    def test_upload_creates_document(self, mock_delay):
        resp = self.client.post(
            "/api/documents/",
            {"file": _pdf_file("upload_test.pdf")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "upload_test.pdf"
        assert data["status"] == "PENDING"
        mock_delay.assert_called_once()

    @patch("apps.ingestion.tasks.process_document.delay")
    def test_upload_invalid_file_returns_400(self, mock_delay):
        bad_file = SimpleUploadedFile("test.txt", b"not a pdf", content_type="text/plain")
        resp = self.client.post("/api/documents/", {"file": bad_file})
        assert resp.status_code == 400
        assert "file" in resp.json()
        mock_delay.assert_not_called()

    def test_upload_empty_file_returns_400(self):
        empty_file = SimpleUploadedFile("empty.pdf", b"", content_type="application/pdf")
        resp = self.client.post("/api/documents/", {"file": empty_file})
        assert resp.status_code == 400

    def test_upload_no_file_returns_400(self):
        resp = self.client.post("/api/documents/", {})
        assert resp.status_code == 400
