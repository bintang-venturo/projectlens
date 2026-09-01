# PHASE 05 — PDF Parser

```
Phase:   05 — PDF Parser
Status:  COMPLETE
```

## Files changed

### Created

- `apps/ingestion/parsers.py` — `DocumentParser` ABC, `ParsedPage` dataclass, `PDFParser` implementation (PyMuPDF)
- `apps/ingestion/services.py` — `get_parser()`, `save_parsed_pages()`, `ingest_document()` orchestration
- `tests/test_phase05_parser.py` — 24 tests for parser, service, and task integration

### Modified

- `apps/ingestion/tasks.py` — `process_document` now calls `ingest_document()` (parse + save pages)
- `tests/test_phase04_upload.py` — updated task test to use real PDF (PyMuPDF-generated) instead of fake `%PDF-` header

## Implementation

### DocumentParser interface

```python
class DocumentParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> list[ParsedPage]:
        ...
```

### ParsedPage dataclass

```python
@dataclass
class ParsedPage:
    content: str
    source: str
    page_number: int
```

### PDFParser (PyMuPDF)

- Opens PDF with `fitz.open(file_path)`
- Iterates each page, extracts text with `page.get_text()`
- Returns 1-indexed page numbers
- Preserves source filename from path
- Handles empty pages (returns empty string content)
- Raises on corrupt/missing files

### Ingestion service

```text
ingest_document(document)
        │
        ▼
get_parser() → PDFParser
        │
        ▼
parser.parse(file.path) → list[ParsedPage]
        │
        ▼
save_parsed_pages() → bulk_create DocumentPage records
        │
        ▼
document.page_count = len(parsed_pages)
```

### Celery task update

```text
process_document(document_id)
        │
        ▼
status = PROCESSING
        │
        ▼
ingest_document(doc)    ← NEW: parse PDF + save pages
        │
        ▼
status = COMPLETED
        │
        (on error)
        ▼
status = FAILED, error_message = str(exc)
```

## Tests executed

| Check | Result |
|---|---|
| `uv run python manage.py check` | PASS — "System check identified no issues" |
| `uv run python manage.py makemigrations --check --dry-run` | PASS — "No changes detected" |
| `uv run pytest tests/test_phase05_parser.py -v` | PASS — 24/24 passed |
| `uv run pytest tests/ -v` | PASS — 136/136 passed (0 regressions) |

Tests cover:
- **DocumentParser ABC**: cannot instantiate, parse is abstract, PDFParser is subclass
- **PDFParser**: single page, multi page, preserves source filename, preserves page numbers, handles empty pages, all-empty pages, returns ParsedPage dataclass, raises on invalid/corrupt file
- **ParsedPage**: field access
- **get_parser**: returns PDFParser instance
- **save_parsed_pages**: creates DocumentPage records, updates page_count, preserves content, saves empty pages
- **ingest_document**: parses and saves pages, raises on corrupt PDF
- **Celery task integration**: parses PDF and saves pages with COMPLETED status, sets FAILED on corrupt PDF with error_message, preserves page content and numbers

```
Test result: PASS
```

## Known limitations

- Only PDF format supported (future parsers for Markdown, CSV, HTML, DOCX per PRD §6)
- `get_parser()` returns `PDFParser` unconditionally — no format detection or registry yet
- No chunking, embedding, or vector storage in the ingestion pipeline yet (Phase 06+)
- `save_parsed_pages` uses `bulk_create` which is efficient but does not call `save()` on each page instance
- PyMuPDF warnings about SwigPyPacked/SwigPyObject are cosmetic (upstream deprecation notices)

## Next phase

PHASE 06 — Chunking: `RecursiveCharacterTextSplitter`, configurable chunk size/overlap, deterministic chunk IDs, chunk metadata preservation.
