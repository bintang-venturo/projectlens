from pathlib import Path

import fitz
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.documents.models import Document, DocumentPage
from apps.ingestion.chunkers import Chunk, chunk_pages
from apps.ingestion.models import DocumentChunk
from apps.ingestion.parsers import ParsedPage, PDFParser
from apps.ingestion.services import ingest_document, save_chunks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def single_page_pdf(tmp_path):
    return _create_pdf(["Short content."], str(tmp_path / "single.pdf"))


@pytest.fixture
def multi_page_pdf(tmp_path):
    return _create_pdf(
        ["Page one content.", "Page two content.", "Page three content."],
        str(tmp_path / "multi.pdf"),
    )


@pytest.fixture
def long_content_pdf(tmp_path):
    long_text = "Word " * 500
    return _create_pdf([long_text], str(tmp_path / "long.pdf"))


@pytest.fixture
def empty_page_pdf(tmp_path):
    return _create_pdf(["Content here.", "", "More content."], str(tmp_path / "empty_page.pdf"))


@pytest.fixture
def parsed_single():
    return [ParsedPage(content="Short content.", source="test.pdf", page_number=1)]


@pytest.fixture
def parsed_multi():
    return [
        ParsedPage(content="Page one content.", source="doc.pdf", page_number=1),
        ParsedPage(content="Page two content.", source="doc.pdf", page_number=2),
        ParsedPage(content="Page three content.", source="doc.pdf", page_number=3),
    ]


@pytest.fixture
def parsed_long():
    long_text = "Word " * 500
    return [ParsedPage(content=long_text, source="long.pdf", page_number=1)]


@pytest.fixture
def parsed_with_empty():
    return [
        ParsedPage(content="Content.", source="doc.pdf", page_number=1),
        ParsedPage(content="", source="doc.pdf", page_number=2),
        ParsedPage(content="More.", source="doc.pdf", page_number=3),
    ]


# ===========================================================================
# Chunk dataclass
# ===========================================================================


class TestChunkDataclass:

    def test_fields(self):
        c = Chunk(
            content="hello",
            source="test.pdf",
            page_number=1,
            chunk_index=0,
            chunk_id="test.pdf:1:0",
        )
        assert c.content == "hello"
        assert c.source == "test.pdf"
        assert c.page_number == 1
        assert c.chunk_index == 0
        assert c.chunk_id == "test.pdf:1:0"


# ===========================================================================
# chunk_pages — basic behavior
# ===========================================================================


class TestChunkPages:

    def test_short_content_single_chunk(self, parsed_single):
        chunks = chunk_pages(parsed_single)
        assert len(chunks) == 1
        assert chunks[0].content == "Short content."

    def test_returns_chunk_instances(self, parsed_single):
        chunks = chunk_pages(parsed_single)
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_multi_page_preserves_all_pages(self, parsed_multi):
        chunks = chunk_pages(parsed_multi)
        page_numbers = {c.page_number for c in chunks}
        assert page_numbers == {1, 2, 3}

    def test_long_content_produces_multiple_chunks(self, parsed_long):
        chunks = chunk_pages(parsed_long, chunk_size=200, chunk_overlap=20)
        assert len(chunks) > 1

    def test_empty_page_produces_no_chunks(self, parsed_with_empty):
        chunks = chunk_pages(parsed_with_empty)
        page_numbers = {c.page_number for c in chunks}
        assert 2 not in page_numbers

    def test_all_empty_pages(self):
        pages = [
            ParsedPage(content="", source="empty.pdf", page_number=1),
            ParsedPage(content="", source="empty.pdf", page_number=2),
        ]
        chunks = chunk_pages(pages)
        assert chunks == []

    def test_no_pages(self):
        chunks = chunk_pages([])
        assert chunks == []


# ===========================================================================
# chunk_pages — deterministic IDs
# ===========================================================================


class TestDeterministicIDs:

    def test_id_format(self, parsed_single):
        chunks = chunk_pages(parsed_single)
        assert chunks[0].chunk_id == "test.pdf:1:0"

    def test_id_includes_source_page_index(self, parsed_multi):
        chunks = chunk_pages(parsed_multi)
        for chunk in chunks:
            expected = f"{chunk.source}:{chunk.page_number}:{chunk.chunk_index}"
            assert chunk.chunk_id == expected

    def test_chunk_index_resets_per_page(self, parsed_long):
        pages = [
            ParsedPage(content="Word " * 500, source="doc.pdf", page_number=1),
            ParsedPage(content="Word " * 500, source="doc.pdf", page_number=2),
        ]
        chunks = chunk_pages(pages, chunk_size=200, chunk_overlap=20)
        page1_indices = [c.chunk_index for c in chunks if c.page_number == 1]
        page2_indices = [c.chunk_index for c in chunks if c.page_number == 2]
        assert page1_indices[0] == 0
        assert page2_indices[0] == 0
        assert page1_indices == page2_indices

    def test_deterministic_across_calls(self, parsed_multi):
        chunks1 = chunk_pages(parsed_multi)
        chunks2 = chunk_pages(parsed_multi)
        ids1 = [c.chunk_id for c in chunks1]
        ids2 = [c.chunk_id for c in chunks2]
        assert ids1 == ids2

    def test_ids_are_unique(self):
        pages = [
            ParsedPage(content="Word " * 500, source="doc.pdf", page_number=1),
            ParsedPage(content="Word " * 500, source="doc.pdf", page_number=2),
        ]
        chunks = chunk_pages(pages, chunk_size=200, chunk_overlap=20)
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))


# ===========================================================================
# chunk_pages — metadata preservation
# ===========================================================================


class TestChunkMetadata:

    def test_source_preserved(self, parsed_multi):
        chunks = chunk_pages(parsed_multi)
        for chunk in chunks:
            assert chunk.source == "doc.pdf"

    def test_page_number_preserved(self, parsed_multi):
        chunks = chunk_pages(parsed_multi)
        for chunk in chunks:
            assert chunk.page_number in {1, 2, 3}

    def test_chunk_index_sequential(self):
        pages = [ParsedPage(content="Word " * 500, source="test.pdf", page_number=1)]
        chunks = chunk_pages(pages, chunk_size=200, chunk_overlap=20)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))


# ===========================================================================
# chunk_pages — configurable size/overlap
# ===========================================================================


class TestConfigurableChunking:

    def test_custom_chunk_size(self):
        pages = [ParsedPage(content="Word " * 500, source="test.pdf", page_number=1)]
        small = chunk_pages(pages, chunk_size=100, chunk_overlap=10)
        large = chunk_pages(pages, chunk_size=2000, chunk_overlap=10)
        assert len(small) > len(large)

    def test_custom_chunk_overlap(self):
        pages = [ParsedPage(content="Word " * 500, source="test.pdf", page_number=1)]
        no_overlap = chunk_pages(pages, chunk_size=200, chunk_overlap=0)
        with_overlap = chunk_pages(pages, chunk_size=200, chunk_overlap=50)
        assert len(with_overlap) >= len(no_overlap)

    def test_uses_settings_defaults(self, parsed_single, settings):
        settings.CHUNK_SIZE = 1000
        settings.CHUNK_OVERLAP = 150
        chunks = chunk_pages(parsed_single)
        assert len(chunks) == 1


# ===========================================================================
# save_chunks service
# ===========================================================================


@pytest.mark.django_db
class TestSaveChunks:

    def test_creates_document_chunks(self, multi_page_pdf):
        doc = _make_document(multi_page_pdf)
        parsed = PDFParser().parse(multi_page_pdf)
        from apps.ingestion.services import save_parsed_pages
        save_parsed_pages(doc, parsed)

        chunks = chunk_pages(parsed)
        save_chunks(doc, chunks)

        assert doc.chunks.count() == len(chunks)

    def test_preserves_chunk_id(self, single_page_pdf):
        doc = _make_document(single_page_pdf)
        parsed = PDFParser().parse(single_page_pdf)
        from apps.ingestion.services import save_parsed_pages
        save_parsed_pages(doc, parsed)

        chunks = chunk_pages(parsed)
        save_chunks(doc, chunks)

        db_chunk = doc.chunks.first()
        assert db_chunk.chunk_id == chunks[0].chunk_id

    def test_preserves_content(self, single_page_pdf):
        doc = _make_document(single_page_pdf)
        parsed = PDFParser().parse(single_page_pdf)
        from apps.ingestion.services import save_parsed_pages
        save_parsed_pages(doc, parsed)

        chunks = chunk_pages(parsed)
        save_chunks(doc, chunks)

        db_chunk = doc.chunks.first()
        assert db_chunk.content == chunks[0].content

    def test_preserves_metadata(self, single_page_pdf):
        doc = _make_document(single_page_pdf)
        parsed = PDFParser().parse(single_page_pdf)
        from apps.ingestion.services import save_parsed_pages
        save_parsed_pages(doc, parsed)

        chunks = chunk_pages(parsed)
        save_chunks(doc, chunks)

        db_chunk = doc.chunks.first()
        assert db_chunk.metadata["source"] == chunks[0].source
        assert db_chunk.metadata["page"] == chunks[0].page_number
        assert db_chunk.metadata["chunk_index"] == chunks[0].chunk_index

    def test_links_to_correct_page(self, multi_page_pdf):
        doc = _make_document(multi_page_pdf)
        parsed = PDFParser().parse(multi_page_pdf)
        from apps.ingestion.services import save_parsed_pages
        save_parsed_pages(doc, parsed)

        chunks = chunk_pages(parsed)
        save_chunks(doc, chunks)

        for db_chunk in doc.chunks.all():
            assert db_chunk.page.page_number == db_chunk.metadata["page"]

    def test_links_to_document(self, single_page_pdf):
        doc = _make_document(single_page_pdf)
        parsed = PDFParser().parse(single_page_pdf)
        from apps.ingestion.services import save_parsed_pages
        save_parsed_pages(doc, parsed)

        chunks = chunk_pages(parsed)
        save_chunks(doc, chunks)

        for db_chunk in doc.chunks.all():
            assert db_chunk.document == doc


# ===========================================================================
# ingest_document — chunking integration
# ===========================================================================


@pytest.mark.django_db
class TestIngestDocumentChunking:

    def test_creates_chunks(self, multi_page_pdf):
        doc = _make_document(multi_page_pdf)
        ingest_document(doc)

        assert doc.chunks.count() > 0

    def test_chunks_have_correct_document(self, single_page_pdf):
        doc = _make_document(single_page_pdf)
        ingest_document(doc)

        for chunk in doc.chunks.all():
            assert chunk.document == doc

    def test_chunks_have_deterministic_ids(self, multi_page_pdf):
        doc = _make_document(multi_page_pdf)
        ingest_document(doc)

        file_source = Path(doc.file.path).name
        for chunk in doc.chunks.all():
            expected = f"{file_source}:{chunk.page.page_number}:{chunk.chunk_index}"
            assert chunk.chunk_id == expected

    def test_chunks_have_metadata(self, single_page_pdf):
        doc = _make_document(single_page_pdf)
        ingest_document(doc)

        chunk = doc.chunks.first()
        assert "source" in chunk.metadata
        assert "page" in chunk.metadata
        assert "chunk_index" in chunk.metadata

    def test_empty_pages_skipped(self, empty_page_pdf):
        doc = _make_document(empty_page_pdf)
        ingest_document(doc)

        chunk_pages_set = {c.page.page_number for c in doc.chunks.all()}
        assert 2 not in chunk_pages_set


# ===========================================================================
# Celery task integration
# ===========================================================================


@pytest.mark.django_db
class TestProcessDocumentTaskChunking:

    def test_task_creates_chunks(self, multi_page_pdf):
        from apps.ingestion.tasks import process_document

        doc = _make_document(multi_page_pdf)
        process_document(str(doc.pk))

        doc.refresh_from_db()
        assert doc.status == Document.Status.COMPLETED
        assert doc.chunks.count() > 0

    def test_task_chunk_ids_are_deterministic(self, single_page_pdf):
        from apps.ingestion.tasks import process_document

        doc = _make_document(single_page_pdf)
        process_document(str(doc.pk))

        file_source = Path(doc.file.path).name
        chunk = doc.chunks.first()
        assert chunk.chunk_id == f"{file_source}:1:0"

    def test_task_chunk_metadata_complete(self, multi_page_pdf):
        from apps.ingestion.tasks import process_document

        doc = _make_document(multi_page_pdf)
        process_document(str(doc.pk))

        file_source = Path(doc.file.path).name
        for chunk in doc.chunks.all():
            assert chunk.metadata["source"] == file_source
            assert chunk.metadata["page"] == chunk.page.page_number
            assert chunk.metadata["chunk_index"] == chunk.chunk_index
