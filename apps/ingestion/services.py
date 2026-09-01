from apps.ai.embedding import EmbeddingService
from apps.ai.providers.base import EmbeddingProvider
from apps.documents.models import Document, DocumentPage
from apps.ingestion.chunkers import Chunk, chunk_pages
from apps.ingestion.models import DocumentChunk
from apps.ingestion.parsers import ParsedPage, PDFParser
from core.chroma import ChromaService


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


def embed_and_store_chunks(
    document: Document,
    chunks: list[Chunk],
    embedding_service: EmbeddingService | None = None,
    chroma_service: ChromaService | None = None,
) -> None:
    if not chunks:
        return

    embedding_service = embedding_service or EmbeddingService()
    chroma_service = chroma_service or ChromaService()

    chunk_ids = [c.chunk_id for c in chunks]
    existing_ids = chroma_service.get_existing_ids(chunk_ids)
    new_chunks = [c for c in chunks if c.chunk_id not in existing_ids]

    if not new_chunks:
        return

    texts = [c.content for c in new_chunks]
    embeddings = embedding_service.embed_documents(texts)

    new_ids = [c.chunk_id for c in new_chunks]
    metadatas = [
        {
            "document_id": str(document.pk),
            "source": c.source,
            "page": c.page_number,
            "chunk_index": c.chunk_index,
        }
        for c in new_chunks
    ]

    chroma_service.upsert(
        ids=new_ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )


def ingest_document(
    document: Document,
    embedding_service: EmbeddingService | None = None,
    chroma_service: ChromaService | None = None,
) -> None:
    parser = get_parser()
    parsed_pages = parser.parse(document.file.path)
    save_parsed_pages(document, parsed_pages)
    chunks = chunk_pages(parsed_pages)
    save_chunks(document, chunks)
    embed_and_store_chunks(document, chunks, embedding_service, chroma_service)
