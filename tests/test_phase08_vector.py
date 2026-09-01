from pathlib import Path
from unittest.mock import MagicMock

import chromadb
import fitz
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.ai.embedding import EmbeddingService
from apps.ai.providers.base import EmbeddingProvider
from apps.documents.models import Document
from apps.ingestion.chunkers import Chunk, chunk_pages
from apps.ingestion.parsers import PDFParser
from apps.ingestion.services import embed_and_store_chunks, ingest_document
from core.chroma import COLLECTION_NAME, ChromaService

pytestmark = pytest.mark.no_embed_mock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeEmbeddingProvider(EmbeddingProvider):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(i)] * 3 for i in range(len(texts))]

    def embed_query(self, text: str) -> list[float]:
        return [0.0, 0.0, 0.0]


def _fake_embedding_service():
    return EmbeddingService(provider=FakeEmbeddingProvider())


def _chroma_service():
    client = chromadb.Client()
    return ChromaService(client=client)


def _create_pdf(pages: list[str], path: str) -> str:
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        if text:
            page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()
    return path


def _make_document(file_path: str) -> Document:
    path = Path(file_path)
    with open(file_path, "rb") as f:
        content = f.read()
    return Document.objects.create(
        name=path.name,
        file=SimpleUploadedFile(path.name, content, content_type="application/pdf"),
        file_size=len(content),
    )


def _sample_chunks(source="test.pdf", doc_pages=None):
    if doc_pages is None:
        doc_pages = [(1, "Page one content."), (2, "Page two content.")]
    chunks = []
    for page_num, text in doc_pages:
        chunks.append(Chunk(
            content=text,
            source=source,
            page_number=page_num,
            chunk_index=0,
            chunk_id=f"{source}:{page_num}:0",
        ))
    return chunks


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def chroma():
    svc = _chroma_service()
    yield svc
    try:
        svc.client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass


@pytest.fixture
def embed_svc():
    return _fake_embedding_service()


@pytest.fixture
def multi_page_pdf(tmp_path):
    return _create_pdf(
        ["Page one content.", "Page two content.", "Page three content."],
        str(tmp_path / "multi.pdf"),
    )


@pytest.fixture
def single_page_pdf(tmp_path):
    return _create_pdf(["Short content."], str(tmp_path / "single.pdf"))


# ===========================================================================
# ChromaService — collection
# ===========================================================================


class TestChromaServiceCollection:

    def test_get_collection_creates(self, chroma):
        col = chroma.get_collection()
        assert col.name == COLLECTION_NAME

    def test_get_collection_idempotent(self, chroma):
        col1 = chroma.get_collection()
        col2 = chroma.get_collection()
        assert col1.name == col2.name

    def test_collection_name_constant(self):
        assert COLLECTION_NAME == "projectlens_documents"


# ===========================================================================
# ChromaService — get_existing_ids
# ===========================================================================


class TestChromaServiceGetExistingIds:

    def test_empty_ids_returns_empty_set(self, chroma):
        result = chroma.get_existing_ids([])
        assert result == set()

    def test_no_existing_returns_empty(self, chroma):
        chroma.get_collection()
        result = chroma.get_existing_ids(["nonexistent:1:0"])
        assert result == set()

    def test_returns_existing_ids(self, chroma):
        col = chroma.get_collection()
        col.upsert(
            ids=["a:1:0", "a:2:0"],
            embeddings=[[0.1], [0.2]],
            documents=["doc1", "doc2"],
            metadatas=[{"source": "a"}, {"source": "a"}],
        )
        result = chroma.get_existing_ids(["a:1:0", "a:2:0", "a:3:0"])
        assert result == {"a:1:0", "a:2:0"}

    def test_returns_set_type(self, chroma):
        result = chroma.get_existing_ids([])
        assert isinstance(result, set)


# ===========================================================================
# ChromaService — upsert
# ===========================================================================


class TestChromaServiceUpsert:

    def test_upsert_stores_data(self, chroma):
        chroma.upsert(
            ids=["test:1:0"],
            embeddings=[[0.1, 0.2]],
            documents=["hello"],
            metadatas=[{"source": "test.pdf", "page": 1}],
        )
        col = chroma.get_collection()
        result = col.get(ids=["test:1:0"], include=["documents", "metadatas"])
        assert result["ids"] == ["test:1:0"]
        assert result["documents"] == ["hello"]
        assert result["metadatas"][0]["source"] == "test.pdf"

    def test_upsert_empty_list_noop(self, chroma):
        chroma.upsert(ids=[], embeddings=[], documents=[], metadatas=[])
        col = chroma.get_collection()
        result = col.get(include=[])
        assert result["ids"] == []

    def test_upsert_multiple(self, chroma):
        chroma.upsert(
            ids=["a:1:0", "a:2:0"],
            embeddings=[[0.1], [0.2]],
            documents=["doc1", "doc2"],
            metadatas=[{"page": 1}, {"page": 2}],
        )
        existing = chroma.get_existing_ids(["a:1:0", "a:2:0"])
        assert existing == {"a:1:0", "a:2:0"}

    def test_upsert_overwrites_existing(self, chroma):
        chroma.upsert(
            ids=["a:1:0"],
            embeddings=[[0.1]],
            documents=["old"],
            metadatas=[{"v": "1"}],
        )
        chroma.upsert(
            ids=["a:1:0"],
            embeddings=[[0.9]],
            documents=["new"],
            metadatas=[{"v": "2"}],
        )
        col = chroma.get_collection()
        result = col.get(ids=["a:1:0"], include=["documents", "metadatas"])
        assert result["documents"] == ["new"]
        assert result["metadatas"][0]["v"] == "2"


# ===========================================================================
# ChromaService — delete_by_document
# ===========================================================================


class TestChromaServiceDelete:

    def test_delete_by_document_removes_records(self, chroma):
        chroma.upsert(
            ids=["a:1:0", "a:2:0", "b:1:0"],
            embeddings=[[0.1], [0.2], [0.3]],
            documents=["d1", "d2", "d3"],
            metadatas=[
                {"document_id": "doc-a"},
                {"document_id": "doc-a"},
                {"document_id": "doc-b"},
            ],
        )
        chroma.delete_by_document("doc-a")
        existing = chroma.get_existing_ids(["a:1:0", "a:2:0", "b:1:0"])
        assert existing == {"b:1:0"}

    def test_delete_nonexistent_document_noop(self, chroma):
        chroma.get_collection()
        chroma.delete_by_document("nonexistent")


# ===========================================================================
# ChromaService — injectable client
# ===========================================================================


class TestChromaServiceInjection:

    def test_accepts_injected_client(self):
        client = chromadb.Client()
        svc = ChromaService(client=client)
        assert svc.client is client

    def test_lazy_client_property(self):
        svc = ChromaService()
        assert svc._client is None


# ===========================================================================
# embed_and_store_chunks — incremental sync
# ===========================================================================


@pytest.mark.django_db
class TestEmbedAndStoreChunks:

    def test_stores_new_chunks(self, chroma, embed_svc, single_page_pdf):
        doc = _make_document(single_page_pdf)
        chunks = _sample_chunks()
        embed_and_store_chunks(doc, chunks, embed_svc, chroma)

        existing = chroma.get_existing_ids([c.chunk_id for c in chunks])
        assert len(existing) == len(chunks)

    def test_skips_existing_chunks(self, chroma, embed_svc, single_page_pdf):
        doc = _make_document(single_page_pdf)
        chunks = _sample_chunks()

        chroma.upsert(
            ids=[chunks[0].chunk_id],
            embeddings=[[0.5, 0.5, 0.5]],
            documents=[chunks[0].content],
            metadatas=[{"source": chunks[0].source}],
        )

        spy_provider = MagicMock(spec=EmbeddingProvider)
        spy_provider.embed_documents.return_value = [[0.1, 0.2, 0.3]]
        spy_svc = EmbeddingService(provider=spy_provider)

        embed_and_store_chunks(doc, chunks, spy_svc, chroma)

        texts_embedded = spy_provider.embed_documents.call_args[0][0]
        assert len(texts_embedded) == 1
        assert texts_embedded[0] == chunks[1].content

    def test_all_existing_skips_embedding(self, chroma, single_page_pdf):
        doc = _make_document(single_page_pdf)
        chunks = _sample_chunks()

        chroma.upsert(
            ids=[c.chunk_id for c in chunks],
            embeddings=[[0.1]] * len(chunks),
            documents=[c.content for c in chunks],
            metadatas=[{"source": c.source} for c in chunks],
        )

        spy_provider = MagicMock(spec=EmbeddingProvider)
        spy_svc = EmbeddingService(provider=spy_provider)

        embed_and_store_chunks(doc, chunks, spy_svc, chroma)

        spy_provider.embed_documents.assert_not_called()

    def test_empty_chunks_noop(self, chroma, embed_svc, single_page_pdf):
        doc = _make_document(single_page_pdf)
        embed_and_store_chunks(doc, [], embed_svc, chroma)

    def test_metadata_structure(self, chroma, embed_svc, single_page_pdf):
        doc = _make_document(single_page_pdf)
        chunks = _sample_chunks()
        embed_and_store_chunks(doc, chunks, embed_svc, chroma)

        col = chroma.get_collection()
        result = col.get(ids=[chunks[0].chunk_id], include=["metadatas"])
        meta = result["metadatas"][0]
        assert meta["document_id"] == str(doc.pk)
        assert meta["source"] == "test.pdf"
        assert meta["page"] == 1
        assert meta["chunk_index"] == 0

    def test_stores_document_text(self, chroma, embed_svc, single_page_pdf):
        doc = _make_document(single_page_pdf)
        chunks = _sample_chunks()
        embed_and_store_chunks(doc, chunks, embed_svc, chroma)

        col = chroma.get_collection()
        result = col.get(ids=[chunks[0].chunk_id], include=["documents"])
        assert result["documents"][0] == chunks[0].content

    def test_calls_embed_documents_with_texts(self, chroma, single_page_pdf):
        doc = _make_document(single_page_pdf)
        chunks = _sample_chunks()

        spy_provider = MagicMock(spec=EmbeddingProvider)
        spy_provider.embed_documents.return_value = [[0.1]] * len(chunks)
        spy_svc = EmbeddingService(provider=spy_provider)

        embed_and_store_chunks(doc, chunks, spy_svc, chroma)

        texts = spy_provider.embed_documents.call_args[0][0]
        assert texts == [c.content for c in chunks]


# ===========================================================================
# ingest_document — full pipeline with vectors
# ===========================================================================


@pytest.mark.django_db
class TestIngestDocumentVectors:

    def test_stores_vectors_in_chroma(self, chroma, embed_svc, multi_page_pdf):
        doc = _make_document(multi_page_pdf)
        ingest_document(doc, embed_svc, chroma)

        chunk_ids = list(doc.chunks.values_list("chunk_id", flat=True))
        existing = chroma.get_existing_ids(chunk_ids)
        assert existing == set(chunk_ids)

    def test_pages_and_chunks_still_saved(self, chroma, embed_svc, multi_page_pdf):
        doc = _make_document(multi_page_pdf)
        ingest_document(doc, embed_svc, chroma)

        doc.refresh_from_db()
        assert doc.page_count == 3
        assert doc.pages.count() == 3
        assert doc.chunks.count() > 0

    def test_chroma_metadata_matches_db(self, chroma, embed_svc, single_page_pdf):
        doc = _make_document(single_page_pdf)
        ingest_document(doc, embed_svc, chroma)

        db_chunk = doc.chunks.first()
        col = chroma.get_collection()
        result = col.get(ids=[db_chunk.chunk_id], include=["metadatas"])
        meta = result["metadatas"][0]
        assert meta["document_id"] == str(doc.pk)
        assert meta["source"] == db_chunk.metadata["source"]
        assert meta["page"] == db_chunk.metadata["page"]
        assert meta["chunk_index"] == db_chunk.metadata["chunk_index"]

    def test_incremental_second_ingest_skips_embedding(self, chroma, multi_page_pdf):
        doc = _make_document(multi_page_pdf)

        embed_svc1 = _fake_embedding_service()
        ingest_document(doc, embed_svc1, chroma)

        chunk_ids = list(doc.chunks.values_list("chunk_id", flat=True))

        spy_provider = MagicMock(spec=EmbeddingProvider)
        spy_svc = EmbeddingService(provider=spy_provider)

        chunks_from_db = [
            Chunk(
                content=c.content,
                source=c.metadata["source"],
                page_number=c.metadata["page"],
                chunk_index=c.metadata["chunk_index"],
                chunk_id=c.chunk_id,
            )
            for c in doc.chunks.all()
        ]
        embed_and_store_chunks(doc, chunks_from_db, spy_svc, chroma)

        spy_provider.embed_documents.assert_not_called()


# ===========================================================================
# Celery task integration
# ===========================================================================


@pytest.mark.django_db
class TestProcessDocumentTaskVectors:

    def test_task_completes_without_real_services(self, multi_page_pdf):
        from apps.ingestion.tasks import process_document

        doc = _make_document(multi_page_pdf)

        with pytest.raises(Exception):
            process_document(str(doc.pk))

        doc.refresh_from_db()
        assert doc.pages.count() == 3
        assert doc.chunks.count() > 0
