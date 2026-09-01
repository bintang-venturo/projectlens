from dataclasses import dataclass

from django.conf import settings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from apps.ingestion.parsers import ParsedPage


@dataclass
class Chunk:
    content: str
    source: str
    page_number: int
    chunk_index: int
    chunk_id: str


def chunk_pages(
    parsed_pages: list[ParsedPage],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Chunk]:
    size = chunk_size if chunk_size is not None else settings.CHUNK_SIZE
    overlap = chunk_overlap if chunk_overlap is not None else settings.CHUNK_OVERLAP

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
    )

    chunks: list[Chunk] = []
    for page in parsed_pages:
        texts = splitter.split_text(page.content)
        for idx, text in enumerate(texts):
            chunk_id = f"{page.source}:{page.page_number}:{idx}"
            chunks.append(Chunk(
                content=text,
                source=page.source,
                page_number=page.page_number,
                chunk_index=idx,
                chunk_id=chunk_id,
            ))
    return chunks
