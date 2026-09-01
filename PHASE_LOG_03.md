# PHASE 03 — Database Models

```
Phase:   03 — Database Models
Status:  COMPLETE
```

## Files changed

### Created

- `apps/documents/migrations/0001_initial.py` — Document + DocumentPage tables
- `apps/ingestion/migrations/0001_initial.py` — DocumentChunk table (depends on documents 0001)
- `apps/chat/migrations/0001_initial.py` — ChatSession + ChatMessage tables
- `tests/test_phase03_models.py` — 45 tests for all models

### Modified

- `apps/documents/models.py` — Document (UUID pk, status choices, file fields) and DocumentPage (unique document+page_number)
- `apps/documents/admin.py` — registered Document and DocumentPage
- `apps/ingestion/models.py` — DocumentChunk (FKs to Document/DocumentPage, unique constraints, deterministic chunk_id, JSON metadata)
- `apps/ingestion/admin.py` — registered DocumentChunk
- `apps/chat/models.py` — ChatSession (UUID pk) and ChatMessage (role choices USER/ASSISTANT, FK to session)
- `apps/chat/admin.py` — registered ChatSession and ChatMessage

## Implementation

### Document (apps.documents)
- UUID primary key
- FileField with `upload_to="documents/"`
- Status choices: PENDING, PROCESSING, COMPLETED, FAILED (default: PENDING)
- Fields: name, file, file_size, page_count, status, error_message, created_at, updated_at
- Ordering by `-created_at`

### DocumentPage (apps.documents)
- UUID primary key
- FK to Document (CASCADE, related_name="pages")
- UniqueConstraint on (document, page_number)
- Ordering by `page_number`

### DocumentChunk (apps.ingestion)
- UUID primary key
- FK to Document (CASCADE, related_name="chunks")
- FK to DocumentPage (CASCADE, related_name="chunks")
- Deterministic `chunk_id`: `{document.name}:{page.page_number}:{chunk_index}` — auto-generated in `save()` if not set
- `chunk_id` has unique=True
- UniqueConstraint on (document, page, chunk_index)
- JSON metadata field (default=dict)
- Ordering by `chunk_index`

### ChatSession (apps.chat)
- UUID primary key
- created_at, updated_at
- Ordering by `-created_at`

### ChatMessage (apps.chat)
- UUID primary key
- FK to ChatSession (CASCADE, related_name="messages")
- Role choices: USER, ASSISTANT
- Ordering by `created_at`

## Tests executed

| Check | Result |
|---|---|
| `uv run python manage.py check` | PASS — "System check identified no issues" |
| `uv run python manage.py makemigrations --check --dry-run` | PASS — "No changes detected" |
| `uv run pytest tests/test_phase03_models.py -v` | PASS — 45/45 passed |
| `uv run pytest tests/ -v` | PASS — 86/86 passed (0 regressions) |

Tests cover:
- Document: creation with defaults, UUID pk, status choices, status transitions, failed+error_message, str, ordering, file field, file_size, page_count
- DocumentPage: creation, unique(document, page_number) constraint, same page_number on different docs, cascade delete, related_name, ordering, str, empty content
- DocumentChunk: creation, deterministic chunk_id auto-generation, explicit chunk_id, chunk_id unique, unique(document, page, chunk_index), chunk_index resets per page, JSON metadata, cascade delete (document and page), related_names, str, ordering
- ChatSession: creation, UUID pk, str, ordering
- ChatMessage: USER/ASSISTANT creation, role choices, cascade delete, related_name, ordering, str
- Migration completeness: all fields exist on all 5 models

```
Test result: PASS
```

## Known limitations

- Models are defined but no views, serializers, or endpoints use them yet (Phase 04+)
- Migrations exist but have not been applied to a live database (no `migrate` run — requires PostgreSQL)
- `chunk_id` auto-generation in `save()` requires both `document` and `page` to be set; bulk_create bypasses `save()` and would need explicit `chunk_id`
- No content-change detection for chunks (MVP limitation per PRD §9)

## Next phase

PHASE 04 — Document Upload: POST /api/documents/ endpoint with PDF validation, Document serializer, and Celery task dispatch.
