import uuid
from io import BytesIO
from unittest.mock import patch

import fitz
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient

from apps.documents.models import Document
from apps.documents.services import create_document, validate_pdf
from rest_framework.exceptions import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pdf_bytes(content: bytes = b"test content") -> bytes:
    return b"%PDF-1.4 " + content


def _pdf_file(name: str = "test.pdf", content: bytes = b"test content") -> SimpleUploadedFile:
    return SimpleUploadedFile(
        name,
        _pdf_bytes(content),
        content_type="application/pdf",
    )


@pytest.fixture
def api_client():
    return APIClient()


# ===========================================================================
# validate_pdf service
# ===========================================================================


class TestValidatePdf:

    def test_rejects_empty_file(self):
        f = SimpleUploadedFile("empty.pdf", b"", content_type="application/pdf")
        with pytest.raises(ValidationError, match="empty"):
            validate_pdf(f)

    @override_settings(MAX_UPLOAD_SIZE=10)
    def test_rejects_oversized_file(self):
        f = _pdf_file(content=b"x" * 100)
        with pytest.raises(ValidationError, match="exceeds"):
            validate_pdf(f)

    def test_rejects_non_pdf_content_type(self):
        f = SimpleUploadedFile("test.txt", b"%PDF-1.4 data", content_type="text/plain")
        with pytest.raises(ValidationError, match="Only PDF"):
            validate_pdf(f)

    def test_rejects_invalid_pdf_header(self):
        f = SimpleUploadedFile("fake.pdf", b"NOT-A-PDF", content_type="application/pdf")
        with pytest.raises(ValidationError, match="not a valid PDF"):
            validate_pdf(f)

    def test_accepts_valid_pdf(self):
        f = _pdf_file()
        validate_pdf(f)


# ===========================================================================
# create_document service
# ===========================================================================


@pytest.mark.django_db
class TestCreateDocument:

    @patch("apps.documents.services.process_document")
    def test_creates_document_with_pending_status(self, mock_task):
        mock_task.delay.return_value = None
        f = _pdf_file(name="monopoly.pdf")
        doc = create_document(f)
        assert doc.pk is not None
        assert doc.name == "monopoly.pdf"
        assert doc.status == Document.Status.PENDING
        assert doc.file_size > 0

    @patch("apps.documents.services.process_document")
    def test_dispatches_celery_task(self, mock_task):
        mock_task.delay.return_value = None
        f = _pdf_file()
        doc = create_document(f)
        mock_task.delay.assert_called_once_with(str(doc.pk))

    def test_rejects_invalid_file(self):
        f = SimpleUploadedFile("bad.txt", b"hello", content_type="text/plain")
        with pytest.raises(ValidationError):
            create_document(f)


# ===========================================================================
# POST /api/documents/ — Upload
# ===========================================================================


@pytest.mark.django_db
class TestDocumentUploadEndpoint:

    @patch("apps.documents.services.process_document")
    def test_upload_success(self, mock_task, api_client):
        mock_task.delay.return_value = None
        f = _pdf_file(name="monopoly.pdf")
        resp = api_client.post("/api/documents/", {"file": f}, format="multipart")
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "monopoly.pdf"
        assert data["status"] == "PENDING"
        assert "id" in data
        uuid.UUID(data["id"])

    @patch("apps.documents.services.process_document")
    def test_upload_stores_document_in_db(self, mock_task, api_client):
        mock_task.delay.return_value = None
        f = _pdf_file()
        resp = api_client.post("/api/documents/", {"file": f}, format="multipart")
        assert resp.status_code == 201
        assert Document.objects.count() == 1

    @patch("apps.documents.services.process_document")
    def test_upload_dispatches_celery(self, mock_task, api_client):
        mock_task.delay.return_value = None
        f = _pdf_file()
        api_client.post("/api/documents/", {"file": f}, format="multipart")
        mock_task.delay.assert_called_once()

    def test_upload_rejects_non_pdf(self, api_client):
        f = SimpleUploadedFile("test.txt", b"hello", content_type="text/plain")
        resp = api_client.post("/api/documents/", {"file": f}, format="multipart")
        assert resp.status_code == 400

    def test_upload_rejects_empty_file(self, api_client):
        f = SimpleUploadedFile("empty.pdf", b"", content_type="application/pdf")
        resp = api_client.post("/api/documents/", {"file": f}, format="multipart")
        assert resp.status_code == 400

    @override_settings(MAX_UPLOAD_SIZE=10)
    def test_upload_rejects_oversized_file(self, api_client):
        f = _pdf_file(content=b"x" * 100)
        resp = api_client.post("/api/documents/", {"file": f}, format="multipart")
        assert resp.status_code == 400

    def test_upload_rejects_corrupt_pdf(self, api_client):
        f = SimpleUploadedFile("corrupt.pdf", b"NOT-A-PDF", content_type="application/pdf")
        resp = api_client.post("/api/documents/", {"file": f}, format="multipart")
        assert resp.status_code == 400

    def test_upload_no_file(self, api_client):
        resp = api_client.post("/api/documents/", {}, format="multipart")
        assert resp.status_code == 400

    @patch("apps.documents.services.process_document")
    def test_upload_response_fields(self, mock_task, api_client):
        mock_task.delay.return_value = None
        f = _pdf_file(name="report.pdf")
        resp = api_client.post("/api/documents/", {"file": f}, format="multipart")
        data = resp.json()
        expected_keys = {"id", "name", "file_size", "page_count", "status", "error_message", "created_at", "updated_at"}
        assert expected_keys == set(data.keys())


# ===========================================================================
# GET /api/documents/ — List
# ===========================================================================


@pytest.mark.django_db
class TestDocumentListEndpoint:

    def test_list_empty(self, api_client):
        resp = api_client.get("/api/documents/")
        assert resp.status_code == 200
        assert resp.json() == []

    @patch("apps.documents.services.process_document")
    def test_list_returns_documents(self, mock_task, api_client):
        mock_task.delay.return_value = None
        create_document(_pdf_file(name="a.pdf"))
        create_document(_pdf_file(name="b.pdf"))
        resp = api_client.get("/api/documents/")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @patch("apps.documents.services.process_document")
    def test_list_ordered_by_created_desc(self, mock_task, api_client):
        mock_task.delay.return_value = None
        create_document(_pdf_file(name="first.pdf"))
        create_document(_pdf_file(name="second.pdf"))
        resp = api_client.get("/api/documents/")
        names = [d["name"] for d in resp.json()]
        assert names[0] == "second.pdf"


# ===========================================================================
# GET /api/documents/{id}/ — Detail
# ===========================================================================


@pytest.mark.django_db
class TestDocumentDetailEndpoint:

    @patch("apps.documents.services.process_document")
    def test_detail_success(self, mock_task, api_client):
        mock_task.delay.return_value = None
        doc = create_document(_pdf_file(name="monopoly.pdf"))
        resp = api_client.get(f"/api/documents/{doc.pk}/")
        assert resp.status_code == 200
        assert resp.json()["name"] == "monopoly.pdf"

    def test_detail_not_found(self, api_client):
        fake_id = uuid.uuid4()
        resp = api_client.get(f"/api/documents/{fake_id}/")
        assert resp.status_code == 404

    @patch("apps.documents.services.process_document")
    def test_detail_response_fields(self, mock_task, api_client):
        mock_task.delay.return_value = None
        doc = create_document(_pdf_file())
        resp = api_client.get(f"/api/documents/{doc.pk}/")
        data = resp.json()
        expected_keys = {"id", "name", "file_size", "page_count", "status", "error_message", "created_at", "updated_at"}
        assert expected_keys == set(data.keys())


# ===========================================================================
# Celery task (unit)
# ===========================================================================


@pytest.mark.django_db
class TestProcessDocumentTask:

    def test_task_sets_processing_then_completed(self):
        from apps.ingestion.tasks import process_document

        pdf_doc = fitz.open()
        pdf_doc.new_page()
        pdf_bytes = pdf_doc.tobytes()
        pdf_doc.close()

        doc = Document.objects.create(
            name="test.pdf",
            file=SimpleUploadedFile("test.pdf", pdf_bytes, content_type="application/pdf"),
            file_size=len(pdf_bytes),
        )
        assert doc.status == Document.Status.PENDING

        process_document(str(doc.pk))

        doc.refresh_from_db()
        assert doc.status == Document.Status.COMPLETED

    def test_task_handles_missing_document(self):
        from apps.ingestion.tasks import process_document

        process_document(str(uuid.uuid4()))

    def test_task_is_registered(self):
        from apps.ingestion.tasks import process_document

        assert process_document.name == "apps.ingestion.tasks.process_document"
