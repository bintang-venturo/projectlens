# PHASE 15 — Document Library Page

```
Phase:   15 — Document Library Page
Status:  COMPLETE
```

## Files changed

### Created

- `apps/ui/templates/ui/_document_rows.html` — htmx partial template for document table body rows with conditional polling
- `tests/test_phase15_document_library.py` — 27 tests for document library page

### Modified

- `apps/ui/views.py` — added `document_rows_partial` view (queries Document model, computes `has_active` flag)
- `apps/ui/urls.py` — added `documents/partials/rows/` route (name: `document-rows`)
- `apps/ui/templates/ui/documents.html` — full rewrite with Alpine.js upload component + htmx table loading

## Implementation

### Architecture

- **Upload:** Alpine.js `x-data` component with `fetch()` POST to `/api/documents/` (drag-and-drop + file picker). CSRF token embedded via `{{ csrf_token }}`.
- **Document list:** htmx partial at `/documents/partials/rows/` — Django view queries `Document.objects.all()` and renders `_document_rows.html` (just `<tbody>` rows). Same partial serves initial load and polling refresh.
- **Status polling:** `hx-trigger="every 5s"` on `<tbody>`, conditionally included only when PENDING/PROCESSING documents exist. When all docs reach terminal status, the swapped-in `<tbody>` has no trigger and polling stops naturally.
- **Post-upload refresh:** Alpine calls `htmx.trigger('#document-table-body', 'refresh')` on success, which the table body listens for alongside `load`.

### Upload flow

```text
User clicks "Upload File" or drops PDF on drop zone
      │
      ▼
Alpine.js handleFiles() → upload(file)
      │
      ▼
fetch('/api/documents/', { method: 'POST', headers: {'X-CSRFToken': ...}, body: FormData })
      │
      ├── 201 → show success banner, trigger htmx refresh
      ├── 400 → parse error from data.file[0], show error banner
      └── catch → show "Network error" banner
      │
      ▼
htmx refresh → GET /documents/partials/rows/ → swap <tbody>
      │
      ▼
New doc appears with PENDING status → polling starts (every 5s)
      │
      ▼
Status transitions to COMPLETED/FAILED → polling stops when all terminal
```

### Status badge mapping

| Status | Dot Color | Text | Subtitle |
|---|---|---|---|
| COMPLETED | green | COMPLETED | `"{page_count} pages · Embedded"` |
| PENDING | orange | PENDING | `"In Queue"` |
| PROCESSING | yellow | PROCESSING | `"Processing…"` |
| FAILED | red | FAILED | `"{error_message}"` |

### Partial template polling mechanism

```text
GET /documents/partials/rows/
      │
      ▼
View queries Document.objects.all()
      │
      ▼
has_active = any PENDING or PROCESSING docs?
      │
      ├── Yes → <tbody hx-get="..." hx-trigger="every 5s" hx-swap="outerHTML">
      └── No  → <tbody id="document-table-body">  (no polling attributes)
```

The `hx-swap="outerHTML"` replaces the entire `<tbody>` element including its attributes, so removing the trigger from the response naturally stops polling.

### Error handling

| Error | Source | User sees |
|---|---|---|
| Non-PDF file | Backend 400: `"Only PDF files are accepted."` | Red error banner with message |
| Empty file | Backend 400: `"The uploaded file is empty."` | Red error banner with message |
| Oversized file | Backend 400: `"File size exceeds the maximum allowed size (50 MB)."` | Red error banner with message |
| Invalid PDF header | Backend 400: `"The file is not a valid PDF."` | Red error banner with message |
| No file submitted | Backend 400: `"No file was submitted."` | Red error banner with message |
| Network failure | fetch() catch | `"Network error. Please try again."` |

## Tests executed

| Check | Result |
|---|---|
| `uv run pytest tests/test_phase15_document_library.py -v` | PASS — 27/27 passed |
| `uv run pytest tests/ -v` | PASS — 345/345 passed (0 regressions) |

Tests cover:

- **Partial endpoint**: returns 200, empty state message, document names rendered, all 4 status badges (COMPLETED/PENDING/PROCESSING/FAILED), file size display, date formatting, error message for FAILED, singular/plural page count
- **Conditional polling**: `hx-trigger="every 5s"` present when active docs exist, absent when all terminal
- **Document ordering**: newest first
- **Page integration**: htmx trigger present, upload button not disabled, drop zone with drag events, CSRF token in page, Alpine x-data present, file input with accept filter, error/success areas, API regression check
- **Upload validation**: successful upload creates document with PENDING status, invalid file returns 400, empty file returns 400, missing file returns 400

```
Test result: PASS
```

## Known limitations

- Single file upload at a time (first file used if multiple dropped)
- Search bar on documents page is disabled (placeholder)
- No client-side file size pre-validation (relies on backend 400 response)
- No upload progress indicator (binary uploading/done state only)
- Polling interval fixed at 5 seconds (not configurable)

## Cumulative phase summary

| Phase | Description | Tests |
|---|---|---|
| 01 | Architecture | — |
| 02 | Django Apps | 35 |
| 03 | Database Models | 45 |
| 04 | Document Upload | 67 |
| 05 | PDF Parser | 78 |
| 06 | Chunking | 99 |
| 07 | Embedding | 121 |
| 08 | Vector Storage | 135 |
| 09 | Retrieval | 148 |
| 10 | RAG | 165 |
| 11 | Citation | 180 |
| 12 | Chat API | 288 |
| 13 | Conversation History | 304 |
| 14 | Frontend Foundation | 318 |
| 15 | Document Library | 345 |
