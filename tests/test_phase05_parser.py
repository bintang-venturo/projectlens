import tempfile
from pathlib import Path

import fitz
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.documents.models import Document, DocumentPage
from apps.ingestion.parsers import DocumentParser, ParsedPage, PDFParser
from apps.ingestion.services import get_parser, ingest_document, save_parsed_pages


# ---------------------------------------------------------------------------
# Helpers — create real PDFs with PyMuPDF
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


@pytest.fixture
def single_page_pdf(tmp_path):
    return _create_pdf(["Hello from page one."], str(tmp_path / "single.pdf"))


@pytest.fixture
def multi_page_pdf(tmp_path):
    return _create_pdf(
        ["Page one content.", "Page two content.", "Page three content."],
        str(tmp_path / "multi.pdf"),
    )


@pytest.fixture
def empty_page_pdf(tmp_path):
    return _create_pdf(["Content here.", "", "More content."], str(tmp_path / "empty_page.pdf"))


@pytest.fixture
def all_empty_pdf(tmp_path):
    return _create_pdf(["", ""], str(tmp_path / "all_empty.pdf"))


def _make_document(file_path: str, **kwargs) -> Document:
    path = Path(file_path)
    with open(file_path, "rb") as f:
        content = f.read()
    defaults = {
        "name": path.name,
        "file": SimpleUploadedFile(path.name, content, content_type="application/pdf"),
        "file_size": len(content),
    }
    defaults.update(kwargs)
    return Document.objects.create(**defaults)


# ===========================================================================
# DocumentParser ABC
# ===========================================================================


class TestDocumentParserABC:

    def test_is_abstract(self):
        with pytest.raises(TypeError):
            DocumentParser()

    def test_parse_is_abstract_method(self):
        assert hasattr(DocumentParser.parse, "__isabstractmethod__")

    def test_pdf_parser_is_subclass(self):
        assert issubclass(PDFParser, DocumentParser)


# ===========================================================================
# PDFParser
# ===========================================================================


class TestPDFParser:

    def test_parse_single_page(self, single_page_pdf):
        parser = PDFParser()
        pages = parser.parse(single_page_pdf)
        assert len(pages) == 1
        assert pages[0].page_number == 1
        assert "Hello from page one" in pages[0].content
        assert pages[0].source == "single.pdf"

    def test_parse_multi_page(self, multi_page_pdf):
        parser = PDFParser()
        pages = parser.parse(multi_page_pdf)
        assert len(pages) == 3
        assert [p.page_number for p in pages] == [1, 2, 3]
        assert "Page one" in pages[0].content
        assert "Page two" in pages[1].content
        assert "Page three" in pages[2].content

    def test_preserves_source_filename(self, multi_page_pdf):
        parser = PDFParser()
        pages = parser.parse(multi_page_pdf)
        for page in pages:
            assert page.source == "multi.pdf"

    def test_preserves_page_numbers(self, multi_page_pdf):
        parser = PDFParser()
        pages = parser.parse(multi_page_pdf)
        assert pages[0].page_number == 1
        assert pages[1].page_number == 2
        assert pages[2].page_number == 3

    def test_handles_empty_pages(self, empty_page_pdf):
        parser = PDFParser()
        pages = parser.parse(empty_page_pdf)
        assert len(pages) == 3
        assert pages[0].content.strip() != ""
        assert pages[1].content.strip() == ""
        assert pages[2].content.strip() != ""

    def test_all_empty_pages(self, all_empty_pdf):
        parser = PDFParser()
        pages = parser.parse(all_empty_pdf)
        assert len(pages) == 2
        for page in pages:
            assert page.content.strip() == ""

    def test_returns_parsed_page_dataclass(self, single_page_pdf):
        parser = PDFParser()
        pages = parser.parse(single_page_pdf)
        assert isinstance(pages[0], ParsedPage)

    def test_raises_on_invalid_file(self, tmp_path):
        bad_path = str(tmp_path / "nonexistent.pdf")
        parser = PDFParser()
        with pytest.raises(Exception):
            parser.parse(bad_path)

    def test_raises_on_corrupt_file(self, tmp_path):
        corrupt = tmp_path / "corrupt.pdf"
        corrupt.write_bytes(b"NOT-A-PDF-AT-ALL")
        parser = PDFParser()
        with pytest.raises(Exception):
            parser.parse(str(corrupt))


# ===========================================================================
# ParsedPage dataclass
# ===========================================================================


class TestParsedPage:

    def test_fields(self):
        pp = ParsedPage(content="hello", source="test.pdf", page_number=1)
        assert pp.content == "hello"
        assert pp.source == "test.pdf"
        assert pp.page_number == 1


# ===========================================================================
# get_parser
# ===========================================================================


class TestGetParser:

    def test_returns_pdf_parser(self):
        parser = get_parser()
        assert isinstance(parser, PDFParser)


# ===========================================================================
# save_parsed_pages service
# ===========================================================================


@pytest.mark.django_db
class TestSaveParsedPages:

    def test_creates_document_pages(self, multi_page_pdf):
        doc = _make_document(multi_page_pdf)
        parsed = PDFParser().parse(multi_page_pdf)
        save_parsed_pages(doc, parsed)

        assert doc.pages.count() == 3
        page_numbers = list(doc.pages.values_list("page_number", flat=True))
        assert sorted(page_numbers) == [1, 2, 3]

    def test_updates_page_count(self, multi_page_pdf):
        doc = _make_document(multi_page_pdf)
        parsed = PDFParser().parse(multi_page_pdf)
        save_parsed_pages(doc, parsed)

        doc.refresh_from_db()
        assert doc.page_count == 3

    def test_preserves_content(self, single_page_pdf):
        doc = _make_document(single_page_pdf)
        parsed = PDFParser().parse(single_page_pdf)
        save_parsed_pages(doc, parsed)

        page = doc.pages.first()
        assert "Hello from page one" in page.content

    def test_empty_pages_saved(self, empty_page_pdf):
        doc = _make_document(empty_page_pdf)
        parsed = PDFParser().parse(empty_page_pdf)
        save_parsed_pages(doc, parsed)

        assert doc.pages.count() == 3
        page2 = doc.pages.get(page_number=2)
        assert page2.content.strip() == ""


# ===========================================================================
# ingest_document service
# ===========================================================================


@pytest.mark.django_db
class TestIngestDocument:

    def test_parses_and_saves_pages(self, multi_page_pdf):
        doc = _make_document(multi_page_pdf)
        ingest_document(doc)

        doc.refresh_from_db()
        assert doc.page_count == 3
        assert doc.pages.count() == 3

    def test_raises_on_corrupt_pdf(self, tmp_path):
        corrupt = tmp_path / "corrupt.pdf"
        corrupt.write_bytes(b"NOT-A-PDF")
        doc = _make_document(str(corrupt))
        with pytest.raises(Exception):
            ingest_document(doc)


# ===========================================================================
# Celery task integration
# ===========================================================================


@pytest.mark.django_db
class TestProcessDocumentTaskParsing:

    def test_task_parses_pdf_and_saves_pages(self, multi_page_pdf):
        from apps.ingestion.tasks import process_document

        doc = _make_document(multi_page_pdf)
        process_document(str(doc.pk))

        doc.refresh_from_db()
        assert doc.status == Document.Status.COMPLETED
        assert doc.page_count == 3
        assert doc.pages.count() == 3

    def test_task_sets_failed_on_corrupt_pdf(self, tmp_path):
        from apps.ingestion.tasks import process_document

        corrupt = tmp_path / "corrupt.pdf"
        corrupt.write_bytes(b"NOT-A-PDF")
        doc = _make_document(str(corrupt))

        with pytest.raises(Exception):
            process_document(str(doc.pk))

        doc.refresh_from_db()
        assert doc.status == Document.Status.FAILED
        assert doc.error_message != ""

    def test_task_preserves_page_content(self, single_page_pdf):
        from apps.ingestion.tasks import process_document

        doc = _make_document(single_page_pdf)
        process_document(str(doc.pk))

        doc.refresh_from_db()
        page = doc.pages.first()
        assert "Hello from page one" in page.content

    def test_task_preserves_page_numbers(self, multi_page_pdf):
        from apps.ingestion.tasks import process_document

        doc = _make_document(multi_page_pdf)
        process_document(str(doc.pk))

        page_numbers = list(doc.pages.values_list("page_number", flat=True))
        assert sorted(page_numbers) == [1, 2, 3]
