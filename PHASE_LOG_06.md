# PHASE 06 — Chunking

```
Phase:   06 — Chunking
Status:  COMPLETE
```

## Files changed

### Created

- `apps/ingestion/chunkers.py` — `Chunk` dataclass, `chunk_pages()` function using `RecursiveCharacterTextSplitter`
- `tests/test_phase06_chunking.py` — 33 tests for chunker, save_chunks, ingestion integration, and Celery task

### Modified

- `apps/ingestion/services.py` — added `save_chunks()`, updated `ingest_document()` to call `chunk_pages()` + `save_chunks()`
- `apps/ingestion/tasks.py` — updated comment to reflect Phase 06 completion

## Implementation

### Chunk dataclass

```python
@dataclass
class Chunk:
    content: str
    source: str
    page_number: int
    chunk_index: int
    chunk_id: str
```

### chunk_pages function

- Uses `RecursiveCharacterTextSplitter` from `langchain_text_splitters`
- Reads `CHUNK_SIZE` and `CHUNK_OVERLAP` from Django settings (env-configurable)
- Accepts optional `chunk_size` / `chunk_overlap` overrides for testing
- Iterates each `ParsedPage`, splits text, assigns sequential `chunk_index` (resets to 0 per page)
- Generates deterministic `chunk_id`: `{source}:{page_number}:{chunk_index}`
- Empty pages naturally produce no chunks (splitter returns `[]` for empty text)

### save_chunks service

```text
save_chunks(document, chunks)
        │
        ▼
Build page_map {page_number → DocumentPage}
        │
        ▼
Create DocumentChunk objects with:
  - document, page, chunk_index, chunk_id
  - content, metadata (source, page, chunk_index)
        │
        ▼
bulk_create all chunks
```

### Updated ingestion pipeline

```text
ingest_document(document)
        │
        ▼
parse(file.path) → list[ParsedPage]
        │
        ▼
save_parsed_pages()
        │
        ▼
chunk_pages(parsed_pages) → list[Chunk]    ← NEW
        │
        ▼
save_chunks(document, chunks)               ← NEW
```

## Tests executed

| Check | Result |
|---|---|
| `uv run python manage.py check` | PASS — "System check identified no issues" |
| `uv run python manage.py makemigrations --check --dry-run` | PASS — "No changes detected" |
| `uv run pytest tests/test_phase06_chunking.py -v` | PASS — 33/33 passed |
| `uv run pytest tests/ -v` | PASS — 169/169 passed (0 regressions) |

Tests cover:
- **Chunk dataclass**: field access
- **chunk_pages — basic**: short content single chunk, returns Chunk instances, multi-page preserves all pages, long content produces multiple chunks, empty page produces no chunks, all-empty pages, no pages
- **Deterministic IDs**: format `source:page:index`, includes all components, resets per page, deterministic across calls, unique across pages
- **Metadata preservation**: source preserved, page number preserved, chunk index sequential
- **Configurable chunking**: custom chunk_size, custom chunk_overlap, uses settings defaults
- **save_chunks**: creates DocumentChunk records, preserves chunk_id/content/metadata, links to correct page, links to document
- **Ingestion integration**: creates chunks, correct document linkage, deterministic IDs, metadata present, empty pages skipped
- **Celery task integration**: task creates chunks, chunk IDs deterministic, metadata complete

```
Test result: PASS
```

## Known limitations

- No embedding or vector storage yet — chunks are saved to PostgreSQL only (Phase 07+)
- Empty pages produce no chunks (no text to split) — this is correct behavior, not a limitation
- `chunk_pages` does not deduplicate overlapping content between pages (per PRD MVP limitation)
- `save_chunks` uses `bulk_create` which does not call model `save()` — chunk_id is generated in the service, not the model

## Next phase

PHASE 07 — Embedding: `EmbeddingProvider` abstraction, `EmbeddingService`, external embedding API integration.
