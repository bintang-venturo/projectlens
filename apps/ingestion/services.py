from apps.documents.models import Document, DocumentPage
from apps.ingestion.parsers import ParsedPage, PDFParser


def get_parser():
    return PDFParser()


def save_parsed_pages(document: Document, parsed_pages: list[ParsedPage]) -> None:
    pages = [
        DocumentPage(
            document=document,
            page_number=pp.page_number,
            content=pp.content,
        )
        for pp in parsed_pages
    ]
    DocumentPage.objects.bulk_create(pages)

    document.page_count = len(parsed_pages)
    document.save(update_fields=["page_count", "updated_at"])


def ingest_document(document: Document) -> None:
    parser = get_parser()
    parsed_pages = parser.parse(document.file.path)
    save_parsed_pages(document, parsed_pages)
