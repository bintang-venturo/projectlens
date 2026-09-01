from apps.documents.models import Document, DocumentPage
from apps.ingestion.chunkers import Chunk, chunk_pages
from apps.ingestion.models import DocumentChunk
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


def save_chunks(document: Document, chunks: list[Chunk]) -> None:
    page_map = {p.page_number: p for p in document.pages.all()}
    chunk_objects = [
        DocumentChunk(
            document=document,
            page=page_map[chunk.page_number],
            chunk_index=chunk.chunk_index,
            chunk_id=chunk.chunk_id,
            content=chunk.content,
            metadata={
                "source": chunk.source,
                "page": chunk.page_number,
                "chunk_index": chunk.chunk_index,
            },
        )
        for chunk in chunks
    ]
    DocumentChunk.objects.bulk_create(chunk_objects)


def ingest_document(document: Document) -> None:
    parser = get_parser()
    parsed_pages = parser.parse(document.file.path)
    save_parsed_pages(document, parsed_pages)
    chunks = chunk_pages(parsed_pages)
    save_chunks(document, chunks)
