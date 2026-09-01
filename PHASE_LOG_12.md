# PHASE 12 — Chat API

```
Phase:   12 — Chat API
Status:  COMPLETE
```

## Files changed

### Created

- `tests/test_phase12_chat_api.py` — 13 tests for the chat endpoint

### Modified

- `apps/chat/views.py` — `ChatView` (APIView) handling `POST /api/chat/`
- `apps/chat/serializers.py` — `ChatRequestSerializer`, `CitationSerializer`, `ChatResponseSerializer`
- `apps/chat/urls.py` — wired `ChatView` to root path

## Implementation

### Endpoint

```text
POST /api/chat/
```

Request:

```json
{
  "question": "How much money does each player start with?"
}
```

Response:

```json
{
  "answer": "Each player starts with $1,500.",
  "citations": [
    {
      "source": "monopoly.pdf",
      "page": 4
    }
  ]
}
```

### Flow

```text
POST /api/chat/
      │
      ▼
ChatRequestSerializer (validate question)
      │
      ▼
RAGService.ask(question)
      │
      ├── RetrievalService.search()
      ├── _build_context()
      ├── _build_prompt()
      ├── AIProvider.generate()
      └── build_citations()
      │
      ▼
ChatResponseSerializer (validate response)
      │
      ▼
JSON Response (HTTP 200)
```

### Validation

- Missing `question` → HTTP 400
- Empty `question` → HTTP 400
- No request body → HTTP 400

### Response structure

- `answer` (string) — generated answer from AI provider
- `citations` (array) — each with `source` (string) and `page` (integer)
- No extra fields exposed

## All API endpoints (PRD complete)

```text
POST   /api/documents/       — Upload PDF
GET    /api/documents/        — List documents
GET    /api/documents/{id}/   — Document detail
POST   /api/chat/             — Question answering with citations
```

## Tests executed

| Check | Result |
|---|---|
| `uv run python manage.py check` | PASS — "System check identified no issues" |
| `uv run pytest tests/test_phase12_chat_api.py -v` | PASS — 13/13 passed |
| `uv run pytest tests/ -v` | PASS — 288/288 passed (0 regressions) |

Tests cover:
- **Happy path**: returns 200, response has answer, response has citations, JSON structure, multiple citations, empty citations
- **Service wiring**: RAGService called with question
- **Validation**: missing question → 400, empty question → 400, no body → 400
- **Consistency**: content type is JSON, response keys only answer/citations, citation keys only source/page

All tests mock RAGService — no external API calls.

```
Test result: PASS
```

## Known limitations

- No authentication or rate limiting
- No conversation history / session tracking (stateless per request)
- No streaming response

## Implementation complete

All 12 phases of the PRD have been implemented:

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
