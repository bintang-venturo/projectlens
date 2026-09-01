# PHASE 13 — Conversation History

```
Phase:   13 — Conversation History
Status:  COMPLETE
```

## Files changed

### Created

- `tests/test_phase13_conversation_history.py` — 16 tests for conversation history

### Modified

- `apps/chat/serializers.py` — added optional `session_id` to request, `session_id` to response
- `apps/chat/services.py` — `RAGService.ask()` accepts `history` param, includes it in prompt
- `apps/chat/views.py` — session create/lookup, message persistence, history loading
- `config/settings.py` — added `CHAT_HISTORY_LIMIT` setting
- `.env.example` — added `CHAT_HISTORY_LIMIT` entry
- `tests/test_phase12_chat_api.py` — updated 2 assertions for new `session_id` field and `history` kwarg

## Implementation

### Request/Response contract

Request:

```json
{
  "question": "How much money does each player start with?",
  "session_id": null
}
```

- `session_id` is optional (nullable UUID)
- Omitted or `null` → creates a new `ChatSession`
- Provided → looks up existing session (404 if not found, 400 if malformed)

Response:

```json
{
  "session_id": "a1b2c3d4-...",
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
ChatRequestSerializer (validate question + optional session_id)
      │
      ▼
Create or lookup ChatSession
      │
      ▼
Load prior history (last N messages)
      │
      ▼
Save user ChatMessage (role=USER)
      │
      ▼
RAGService.ask(question, history=history)
      │
      ├── RetrievalService.search()
      ├── _build_context()
      ├── _build_prompt() — includes conversation history block
      ├── AIProvider.generate()
      └── build_citations()
      │
      ▼
Save assistant ChatMessage (role=ASSISTANT)
      │
      ▼
ChatResponseSerializer (validate response)
      │
      ▼
JSON Response (HTTP 200)
```

### Prompt structure with history

```text
{SYSTEM_PROMPT}

Conversation history:
User: ...
Assistant: ...

Context:
[Source: file.pdf, Page: 4]
chunk text...

Question:
{current question}
```

History is inserted between the system prompt and retrieved-chunks context. When history is empty, the block is omitted entirely (backward compatible with Phase 12 prompt).

### Configuration

| Variable | Default | Description |
|---|---|---|
| `CHAT_HISTORY_LIMIT` | `10` | Maximum number of prior messages loaded into the prompt (10 messages = 5 user/assistant turns) |

### Backward compatibility

- Requests without `session_id` continue to work (new session created silently)
- Response adds `session_id` — additive, non-breaking
- `RAGService.ask()` without `history` produces the same prompt as before

## Tests executed

| Check | Result |
|---|---|
| `uv run pytest tests/test_phase12_chat_api.py -v` | PASS — 13/13 passed |
| `uv run pytest tests/test_phase13_conversation_history.py -v` | PASS — 16/16 passed |
| `uv run pytest tests/ -v` | PASS — 304/304 passed (0 regressions) |

Tests cover:
- **Session lifecycle**: no session_id creates new, null creates new, valid reuses, nonexistent → 404, malformed → 400
- **Message persistence**: user + assistant messages saved, messages accumulate across requests
- **History passed to RAG**: first message has empty history, second message includes prior pair, limit respected
- **Prompt construction**: no history → original prompt, empty history → original prompt, history includes conversation block, correct ordering (system → history → context → question)
- **Backward compatibility**: requests without session_id → 200, response still has answer + citations

All tests mock RAGService or AI provider — no external API calls.

```
Test result: PASS
```

## Known limitations

- No token-based history truncation — uses a fixed message count limit
- History is loaded as full message content (no summarization of older turns)
- No session expiry/cleanup mechanism
- Retrieval is per-question only — prior conversation context is not used to reformulate the search query

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
