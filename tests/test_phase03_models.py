import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError

from apps.chat.models import ChatMessage, ChatSession
from apps.documents.models import Document, DocumentPage
from apps.ingestion.models import DocumentChunk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_document(**kwargs):
    defaults = {
        "name": "test.pdf",
        "file": SimpleUploadedFile("test.pdf", b"%PDF-1.4 test"),
        "file_size": 1024,
    }
    defaults.update(kwargs)
    return Document.objects.create(**defaults)


def _make_page(document, page_number=1, content="page text"):
    return DocumentPage.objects.create(
        document=document,
        page_number=page_number,
        content=content,
    )


# ===========================================================================
# Document model
# ===========================================================================

@pytest.mark.django_db
class TestDocumentModel:

    def test_create_document_defaults(self):
        doc = _make_document()
        assert doc.pk is not None
        assert isinstance(doc.pk, uuid.UUID)
        assert doc.status == Document.Status.PENDING
        assert doc.error_message == ""
        assert doc.page_count == 0
        assert doc.created_at is not None
        assert doc.updated_at is not None

    def test_status_choices(self):
        choices = {c.value for c in Document.Status}
        assert choices == {"PENDING", "PROCESSING", "COMPLETED", "FAILED"}

    def test_status_transitions(self):
        doc = _make_document()
        for status in (Document.Status.PROCESSING, Document.Status.COMPLETED):
            doc.status = status
            doc.save()
            doc.refresh_from_db()
            assert doc.status == status

    def test_failed_status_with_error_message(self):
        doc = _make_document()
        doc.status = Document.Status.FAILED
        doc.error_message = "corrupt PDF"
        doc.save()
        doc.refresh_from_db()
        assert doc.status == Document.Status.FAILED
        assert doc.error_message == "corrupt PDF"

    def test_str(self):
        doc = _make_document(name="monopoly.pdf")
        assert str(doc) == "monopoly.pdf"

    def test_ordering(self):
        d1 = _make_document(name="first.pdf")
        d2 = _make_document(name="second.pdf")
        docs = list(Document.objects.all())
        assert docs[0].pk == d2.pk

    def test_uuid_primary_key(self):
        doc = _make_document()
        assert isinstance(doc.id, uuid.UUID)

    def test_file_field(self):
        doc = _make_document()
        assert doc.file.name.startswith("documents/")

    def test_file_size_field(self):
        doc = _make_document(file_size=5000)
        doc.refresh_from_db()
        assert doc.file_size == 5000

    def test_page_count_field(self):
        doc = _make_document(page_count=10)
        doc.refresh_from_db()
        assert doc.page_count == 10


# ===========================================================================
# DocumentPage model
# ===========================================================================

@pytest.mark.django_db
class TestDocumentPageModel:

    def test_create_page(self):
        doc = _make_document()
        page = _make_page(doc, page_number=1, content="Hello")
        assert page.pk is not None
        assert isinstance(page.pk, uuid.UUID)
        assert page.page_number == 1
        assert page.content == "Hello"

    def test_unique_document_page_constraint(self):
        doc = _make_document()
        _make_page(doc, page_number=1)
        with pytest.raises(IntegrityError):
            _make_page(doc, page_number=1)

    def test_same_page_number_different_documents(self):
        d1 = _make_document(name="a.pdf")
        d2 = _make_document(name="b.pdf")
        p1 = _make_page(d1, page_number=1)
        p2 = _make_page(d2, page_number=1)
        assert p1.pk != p2.pk

    def test_cascade_delete(self):
        doc = _make_document()
        _make_page(doc, page_number=1)
        doc.delete()
        assert DocumentPage.objects.count() == 0

    def test_related_name(self):
        doc = _make_document()
        _make_page(doc, page_number=1)
        _make_page(doc, page_number=2)
        assert doc.pages.count() == 2

    def test_ordering(self):
        doc = _make_document()
        _make_page(doc, page_number=3)
        _make_page(doc, page_number=1)
        _make_page(doc, page_number=2)
        pages = list(doc.pages.all())
        assert [p.page_number for p in pages] == [1, 2, 3]

    def test_str(self):
        doc = _make_document(name="monopoly.pdf")
        page = _make_page(doc, page_number=4)
        assert str(page) == "monopoly.pdf — Page 4"

    def test_empty_content_allowed(self):
        doc = _make_document()
        page = _make_page(doc, page_number=1, content="")
        page.refresh_from_db()
        assert page.content == ""


# ===========================================================================
# DocumentChunk model
# ===========================================================================

@pytest.mark.django_db
class TestDocumentChunkModel:

    def test_create_chunk(self):
        doc = _make_document(name="monopoly.pdf")
        page = _make_page(doc, page_number=4)
        chunk = DocumentChunk.objects.create(
            document=doc,
            page=page,
            chunk_index=0,
            chunk_id="monopoly.pdf:4:0",
            content="chunk text",
            metadata={"source": "monopoly.pdf", "page": 4, "chunk_index": 0},
        )
        assert chunk.pk is not None
        assert isinstance(chunk.pk, uuid.UUID)

    def test_deterministic_chunk_id_auto(self):
        doc = _make_document(name="monopoly.pdf")
        page = _make_page(doc, page_number=4)
        chunk = DocumentChunk(
            document=doc,
            page=page,
            chunk_index=0,
            content="chunk text",
        )
        chunk.save()
        assert chunk.chunk_id == "monopoly.pdf:4:0"

    def test_deterministic_chunk_id_explicit(self):
        doc = _make_document(name="monopoly.pdf")
        page = _make_page(doc, page_number=5)
        chunk = DocumentChunk.objects.create(
            document=doc,
            page=page,
            chunk_index=1,
            chunk_id="monopoly.pdf:5:1",
            content="text",
        )
        assert chunk.chunk_id == "monopoly.pdf:5:1"

    def test_chunk_id_unique(self):
        doc = _make_document(name="test.pdf")
        page = _make_page(doc, page_number=1)
        DocumentChunk.objects.create(
            document=doc, page=page, chunk_index=0,
            chunk_id="test.pdf:1:0", content="a",
        )
        with pytest.raises(IntegrityError):
            DocumentChunk.objects.create(
                document=doc, page=page, chunk_index=1,
                chunk_id="test.pdf:1:0", content="b",
            )

    def test_unique_document_page_chunk_constraint(self):
        doc = _make_document(name="test.pdf")
        page = _make_page(doc, page_number=1)
        DocumentChunk.objects.create(
            document=doc, page=page, chunk_index=0,
            chunk_id="test.pdf:1:0", content="a",
        )
        with pytest.raises(IntegrityError):
            DocumentChunk.objects.create(
                document=doc, page=page, chunk_index=0,
                chunk_id="test.pdf:1:0-dup", content="b",
            )

    def test_chunk_index_resets_per_page(self):
        doc = _make_document(name="test.pdf")
        p1 = _make_page(doc, page_number=1)
        p2 = _make_page(doc, page_number=2)
        c1 = DocumentChunk.objects.create(
            document=doc, page=p1, chunk_index=0,
            chunk_id="test.pdf:1:0", content="a",
        )
        c2 = DocumentChunk.objects.create(
            document=doc, page=p2, chunk_index=0,
            chunk_id="test.pdf:2:0", content="b",
        )
        assert c1.chunk_index == 0
        assert c2.chunk_index == 0

    def test_metadata_json_field(self):
        doc = _make_document(name="test.pdf")
        page = _make_page(doc, page_number=1)
        meta = {"source": "test.pdf", "page": 1, "chunk_index": 0}
        chunk = DocumentChunk.objects.create(
            document=doc, page=page, chunk_index=0,
            chunk_id="test.pdf:1:0", content="text", metadata=meta,
        )
        chunk.refresh_from_db()
        assert chunk.metadata == meta

    def test_cascade_delete_document(self):
        doc = _make_document()
        page = _make_page(doc, page_number=1)
        DocumentChunk.objects.create(
            document=doc, page=page, chunk_index=0,
            chunk_id="x:1:0", content="a",
        )
        doc.delete()
        assert DocumentChunk.objects.count() == 0

    def test_cascade_delete_page(self):
        doc = _make_document()
        page = _make_page(doc, page_number=1)
        DocumentChunk.objects.create(
            document=doc, page=page, chunk_index=0,
            chunk_id="x:1:0", content="a",
        )
        page.delete()
        assert DocumentChunk.objects.count() == 0

    def test_related_names(self):
        doc = _make_document(name="test.pdf")
        page = _make_page(doc, page_number=1)
        DocumentChunk.objects.create(
            document=doc, page=page, chunk_index=0,
            chunk_id="test.pdf:1:0", content="a",
        )
        assert doc.chunks.count() == 1
        assert page.chunks.count() == 1

    def test_str(self):
        doc = _make_document(name="test.pdf")
        page = _make_page(doc, page_number=1)
        chunk = DocumentChunk.objects.create(
            document=doc, page=page, chunk_index=0,
            chunk_id="test.pdf:1:0", content="a",
        )
        assert str(chunk) == "test.pdf:1:0"

    def test_ordering(self):
        doc = _make_document(name="test.pdf")
        page = _make_page(doc, page_number=1)
        DocumentChunk.objects.create(
            document=doc, page=page, chunk_index=2,
            chunk_id="test.pdf:1:2", content="c",
        )
        DocumentChunk.objects.create(
            document=doc, page=page, chunk_index=0,
            chunk_id="test.pdf:1:0", content="a",
        )
        DocumentChunk.objects.create(
            document=doc, page=page, chunk_index=1,
            chunk_id="test.pdf:1:1", content="b",
        )
        chunks = list(page.chunks.all())
        assert [c.chunk_index for c in chunks] == [0, 1, 2]


# ===========================================================================
# ChatSession model
# ===========================================================================

@pytest.mark.django_db
class TestChatSessionModel:

    def test_create_session(self):
        session = ChatSession.objects.create()
        assert session.pk is not None
        assert isinstance(session.pk, uuid.UUID)
        assert session.created_at is not None
        assert session.updated_at is not None

    def test_str(self):
        session = ChatSession.objects.create()
        assert str(session) == f"ChatSession {session.id}"

    def test_ordering(self):
        s1 = ChatSession.objects.create()
        s2 = ChatSession.objects.create()
        sessions = list(ChatSession.objects.all())
        assert sessions[0].pk == s2.pk


# ===========================================================================
# ChatMessage model
# ===========================================================================

@pytest.mark.django_db
class TestChatMessageModel:

    def test_create_user_message(self):
        session = ChatSession.objects.create()
        msg = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content="How much money?",
        )
        assert msg.pk is not None
        assert isinstance(msg.pk, uuid.UUID)
        assert msg.role == "USER"

    def test_create_assistant_message(self):
        session = ChatSession.objects.create()
        msg = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content="$1500",
        )
        assert msg.role == "ASSISTANT"

    def test_role_choices(self):
        choices = {c.value for c in ChatMessage.Role}
        assert choices == {"USER", "ASSISTANT"}

    def test_cascade_delete(self):
        session = ChatSession.objects.create()
        ChatMessage.objects.create(
            session=session, role=ChatMessage.Role.USER, content="hi",
        )
        session.delete()
        assert ChatMessage.objects.count() == 0

    def test_related_name(self):
        session = ChatSession.objects.create()
        ChatMessage.objects.create(
            session=session, role=ChatMessage.Role.USER, content="q",
        )
        ChatMessage.objects.create(
            session=session, role=ChatMessage.Role.ASSISTANT, content="a",
        )
        assert session.messages.count() == 2

    def test_ordering(self):
        session = ChatSession.objects.create()
        m1 = ChatMessage.objects.create(
            session=session, role=ChatMessage.Role.USER, content="first",
        )
        m2 = ChatMessage.objects.create(
            session=session, role=ChatMessage.Role.ASSISTANT, content="second",
        )
        messages = list(session.messages.all())
        assert messages[0].pk == m1.pk
        assert messages[1].pk == m2.pk

    def test_str(self):
        session = ChatSession.objects.create()
        msg = ChatMessage.objects.create(
            session=session, role=ChatMessage.Role.USER, content="q",
        )
        assert "USER" in str(msg)


# ===========================================================================
# Migration completeness
# ===========================================================================

@pytest.mark.django_db
class TestMigrations:

    def test_document_model_fields(self):
        field_names = {f.name for f in Document._meta.get_fields()}
        expected = {
            "id", "name", "file", "file_size", "page_count",
            "status", "error_message", "created_at", "updated_at",
            "pages", "chunks",
        }
        assert expected.issubset(field_names)

    def test_document_page_fields(self):
        field_names = {f.name for f in DocumentPage._meta.get_fields()}
        expected = {"id", "document", "page_number", "content", "created_at", "chunks"}
        assert expected.issubset(field_names)

    def test_document_chunk_fields(self):
        field_names = {f.name for f in DocumentChunk._meta.get_fields()}
        expected = {
            "id", "document", "page", "chunk_index",
            "chunk_id", "content", "metadata", "created_at",
        }
        assert expected.issubset(field_names)

    def test_chat_session_fields(self):
        field_names = {f.name for f in ChatSession._meta.get_fields()}
        expected = {"id", "created_at", "updated_at", "messages"}
        assert expected.issubset(field_names)

    def test_chat_message_fields(self):
        field_names = {f.name for f in ChatMessage._meta.get_fields()}
        expected = {"id", "session", "role", "content", "created_at"}
        assert expected.issubset(field_names)
