# PHASE 04 — Document Upload

```
Phase:   04 — Document Upload
Status:  COMPLETE
```

## Files changed

### Created

- `apps/documents/services.py` — `validate_pdf()` and `create_document()` business logic
- `tests/test_phase04_upload.py` — 26 tests for validation, service, endpoints, and Celery task

### Modified

- `apps/documents/serializers.py` — `DocumentSerializer` (read response) and `DocumentUploadSerializer` (upload file field)
- `apps/documents/views.py` — `DocumentListCreateView` (POST + GET list) and `DocumentDetailView` (GET single)
- `apps/documents/urls.py` — wired `POST/GET /api/documents/` and `GET /api/documents/{id}/`
- `apps/ingestion/tasks.py` — `process_document` Celery task (PENDING → PROCESSING → COMPLETED stub)
- `config/settings.py` — added `MAX_UPLOAD_SIZE` setting (env-configurable, default 50 MB)

## Implementation

### Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/documents/` | Upload a PDF file (multipart/form-data) |
| GET | `/api/documents/` | List all documents |
| GET | `/api/documents/{id}/` | Retrieve a single document |

### Upload flow

```text
POST /api/documents/ (multipart/form-data, file=<pdf>)
        │
        ▼
DocumentUploadSerializer validates file field present
        │
        ▼
validate_pdf() — reject empty, oversized, non-PDF content type, invalid PDF header
        │
        ▼
Document.objects.create(name, file, file_size, status=PENDING)
        │
        ▼
process_document.delay(document_id) — Celery task dispatched
        │
        ▼
Return HTTP 201 { id, name, status: "PENDING", ... }
```

### Validation rules

- Empty files → 400
- Files exceeding `MAX_UPLOAD_SIZE` → 400
- Non-`application/pdf` content type → 400
- Files without `%PDF-` magic header → 400
- Missing file field → 400

### Architecture

- Business logic (`validate_pdf`, `create_document`) lives in `services.py`, not in views or serializers (per PRD rule #14)
- Celery task `process_document` is a placeholder: sets PROCESSING then COMPLETED (actual parsing deferred to Phase 05)
- Celery task handles failures by setting `status=FAILED` with `error_message`

### Response structure

```json
{
  "id": "uuid",
  "name": "monopoly.pdf",
  "file_size": 12345,
  "page_count": 0,
  "status": "PENDING",
  "error_message": "",
  "created_at": "2026-09-02T...",
  "updated_at": "2026-09-02T..."
}
```

## Tests executed

| Check | Result |
|---|---|
| `uv run python manage.py check` | PASS — "System check identified no issues" |
| `uv run python manage.py makemigrations --check --dry-run` | PASS — "No changes detected" |
| `uv run pytest tests/test_phase04_upload.py -v` | PASS — 26/26 passed |
| `uv run pytest tests/ -v` | PASS — 112/112 passed (0 regressions) |

Tests cover:
- **validate_pdf**: empty file, oversized file, non-PDF content type, invalid PDF header, valid PDF
- **create_document service**: creates doc with PENDING status, dispatches Celery task, rejects invalid file
- **POST /api/documents/**: success 201, stores in DB, dispatches Celery, rejects non-PDF, empty, oversized, corrupt, missing file, response fields
- **GET /api/documents/**: empty list, returns documents, ordered by created_at desc
- **GET /api/documents/{id}/**: success, 404, response fields
- **process_document task**: PENDING → PROCESSING → COMPLETED, handles missing document, task registration

```
Test result: PASS
```

## Known limitations

- `process_document` Celery task is a stub — it immediately marks COMPLETED without actually parsing the PDF (Phase 05)
- No pagination on the document list endpoint
- `MAX_UPLOAD_SIZE` validation happens at the service level after the full file is received; Django's `DATA_UPLOAD_MAX_MEMORY_SIZE` could add an earlier boundary but is not configured
- File storage uses local filesystem (`MEDIA_ROOT`); no S3 or cloud storage configured

## Next phase

PHASE 05 — PDF Parser: implement `DocumentParser` interface, `PDFParser` using PyMuPDF, page-level extraction with preserved metadata.
