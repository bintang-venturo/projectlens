# PHASE 08 — Vector Storage

```
Phase:   08 — Vector Storage
Status:  COMPLETE
```

## Files changed

### Created

- `core/chroma.py` — `ChromaService` wrapper: collection management, `get_existing_ids`, `upsert`, `delete_by_document`
- `tests/test_phase08_vector.py` — 27 tests for ChromaService, incremental sync, ingestion integration

### Modified

- `apps/ingestion/services.py` — added `embed_and_store_chunks()` with incremental sync, updated `ingest_document()` to accept injectable services
- `apps/ingestion/tasks.py` — updated comment
- `tests/conftest.py` — added auto-use fixture to mock `embed_and_store_chunks` for earlier phase tests (prevents real API calls)
- `pyproject.toml` — registered `no_embed_mock` pytest marker

## Implementation

### ChromaService

```text
ChromaService(client=None)
        │
        ├── get_collection()     → get_or_create "projectlens_documents"
        ├── get_existing_ids()   → set of IDs already in ChromaDB
        ├── upsert()             → store/update vectors with metadata
        └── delete_by_document() → remove all vectors for a document
```

- Lazy client initialization (connects to `CHROMA_HOST:CHROMA_PORT` on first use)
- Injectable client for testing (in-memory `chromadb.Client()`)
- Handles empty ID lists safely (no-op instead of ChromaDB validation error)
- Collection name: `projectlens_documents` (module-level constant)

### Incremental synchronization

```text
embed_and_store_chunks(document, chunks, embedding_service, chroma_service)
        │
        ▼
Generate deterministic IDs from chunks
        │
        ▼
Get existing IDs from ChromaDB
        │
        ▼
Filter to new chunks only
        │
        ▼
Embed new chunks (EmbeddingService)
        │
        ▼
Upsert into ChromaDB with metadata:
  - document_id (UUID)
  - source (filename)
  - page (page number)
  - chunk_index
```

Skips embedding entirely when all chunks already exist — no unnecessary API calls.

### Updated ingestion pipeline

```text
ingest_document(document, embedding_service?, chroma_service?)
        │
        ▼
parse → save_parsed_pages → chunk_pages → save_chunks
        │
        ▼
embed_and_store_chunks    ← NEW (Phase 08)
  ├── check existing IDs
  ├── embed new only
  └── upsert to ChromaDB
```

Services are injectable for testing; defaults create real connections.

### Test isolation

Added `conftest.py` auto-use fixture that patches `embed_and_store_chunks` as a no-op for all tests. Phase 08 tests opt out with `pytest.mark.no_embed_mock` and inject their own in-memory ChromaDB + fake embedding provider.

## Tests executed

| Check | Result |
|---|---|
| `uv run python manage.py check` | PASS — "System check identified no issues" |
| `uv run python manage.py makemigrations --check --dry-run` | PASS — "No changes detected" |
| `uv run pytest tests/test_phase08_vector.py -v` | PASS — 27/27 passed |
| `uv run pytest tests/ -v` | PASS — 227/227 passed (0 regressions) |

Tests cover:
- **ChromaService — collection**: creates collection, idempotent, correct name constant
- **ChromaService — get_existing_ids**: empty IDs returns empty set, no existing returns empty, returns existing only, returns set type
- **ChromaService — upsert**: stores data with metadata, empty list no-op, multiple records, overwrites existing
- **ChromaService — delete**: removes by document_id, nonexistent document no-op
- **ChromaService — injection**: accepts injected client, lazy client property
- **embed_and_store_chunks**: stores new chunks, skips existing (verifies embedding not called for existing), all-existing skips embedding entirely, empty chunks no-op, correct metadata structure, stores document text, passes correct texts to embedding
- **Ingestion integration**: stores vectors in ChromaDB, pages/chunks still saved to DB, ChromaDB metadata matches DB, second ingest skips embedding (incremental)
- **Celery task**: completes pipeline (pages + chunks created, embedding fails without real API but data is persisted)

All tests use in-memory ChromaDB client and fake embedding provider — no external services required.

```
Test result: PASS
```

## Known limitations

- No content-change detection (per PRD MVP limitation) — same source:page:chunk_index is considered unchanged
- No batching for large embedding requests (single API call for all new chunks)
- `delete_by_document` uses ChromaDB `where` filter — requires `document_id` in metadata
- Celery task uses default services (real API) — integration tests for the full Celery→API flow require a running ChromaDB server and valid embedding API key

## Next phase

PHASE 09 — Retrieval: query embedding, ChromaDB vector search, top-K results, retrieval result normalization.
