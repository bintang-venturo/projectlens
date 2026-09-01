# PHASE 16 — Chat Page

```
Phase:   16 — Chat Page
Status:  COMPLETE
```

## Files changed

### Created

- `tests/test_phase16_chat_page.py` — 21 tests for chat page structure and API integration

### Modified

- `apps/ui/templates/ui/chat.html` — full rewrite with Alpine.js chat component (send messages, multi-turn sessions, citations, chat history sidebar)

## Implementation

### Architecture decisions

- **Session persistence:** Alpine.js client-side state. The `session_id` returned from the first API call is stored in the Alpine component; subsequent messages send it back. State resets on page reload (expected per PRD).
- **Message rendering:** Alpine.js reactive `messages[]` array rendered with `x-for`. No htmx needed — chat is a purely client-driven interaction.
- **Chat history sidebar:** Client-side only. Sessions tracked in Alpine `sessions[]` during page lifetime. Each session titled by its first user question.
- **No backend changes.** The frontend calls the existing `POST /api/chat/` endpoint via `fetch()`.

### Send message flow

```text
User types question → Enter or click Send
      │
      ▼
sendMessage(): push {role: 'user', content} to messages[]
      │
      ▼
fetch('/api/chat/', {
  method: 'POST',
  headers: {'Content-Type': 'application/json', 'X-CSRFToken': ...},
  body: JSON.stringify({question, session_id})
})
      │
      ├── 200 → store session_id, push {role: 'assistant', content, citations} to messages[]
      ├── 4xx → parse error message, show error banner
      └── catch → show "Network error" banner
      │
      ▼
Auto-scroll to bottom
```

### Alpine.js component data

```text
sessionId: null              — current chat session UUID (null until first response)
messages: []                 — [{role, content, citations}] for current conversation
sessions: []                 — [{sessionId, title, messages}] saved conversations
activeSessionIndex: -1       — which session is active in sidebar (-1 = new unsaved)
question: ''                 — textarea binding
sending: false               — loading state
error: ''                    — error message
csrfToken: '{{ csrf_token }}'
```

### Message UI

| Element | Style |
|---|---|
| User message | Right-aligned, `bg-gray-800 text-white rounded-2xl rounded-tr-md`, "You" label + avatar |
| Assistant message | Left-aligned, `border-l-[3px] border-brand-500` accent, ProjectLens logo + label |
| Citations | "SOURCES" header, pills with document icon + filename + `Page N` |
| Loading | Animated bouncing dots + "Searching documents..." |
| Empty state | Centered icon + "Ask a question about your documents" |
| Error | Red banner below messages area with dismiss button |

### Chat history sidebar

- "+" button creates new conversation (saves current to `sessions[]`, resets state)
- Click session in sidebar to switch (`switchSession(index)`)
- Active session highlighted with `bg-brand-50 border-l-[3px] border-brand-500`
- Session title = first user message (truncated to 40 chars)
- Message count shown for inactive sessions

### Input area

- `<textarea>` with auto-resize (`field-sizing: content`, max 120px)
- Enter to send, Shift+Enter for newline
- Send button disabled when empty or sending
- Input cleared after send

### Session lifecycle

```text
Page load → sessionId: null, messages: []
      │
      ▼
First message sent → POST /api/chat/ (no session_id)
      │
      ▼
Response returns session_id → stored in Alpine state
      │
      ▼
Subsequent messages → POST /api/chat/ (with session_id) → multi-turn history
      │
      ▼
"New Conversation" clicked → current saved to sessions[], state reset
      │
      ▼
Click saved session → load its messages + sessionId
      │
      ▼
Page reload → all state lost (by design)
```

## Tests executed

| Check | Result |
|---|---|
| `uv run pytest tests/test_phase16_chat_page.py -v` | PASS — 21/21 passed |
| `uv run pytest tests/ -v` | PASS — 366/366 passed (0 regressions) |

Tests cover:

- **Page structure (16)**: loads at 200, Alpine x-data present, CSRF token embedded, textarea input, send button wired, empty state content, chat history sidebar, new conversation button, session management variables, loading indicator, error handling, citations rendering, keyboard handler, auto-scroll, page title, ProjectLens AI label
- **API integration (5)**: JSON POST returns 200 with answer + citations + session_id, multi-turn with session_id reuse, empty question rejected (400), missing question rejected (400), invalid session_id returns 404

```
Test result: PASS
```

## Known limitations

- Chat history is client-side only — lost on page reload (no backend session listing endpoint)
- No streaming responses — full answer rendered after complete API response
- Single-session per browser tab (no cross-tab session sharing)
- No message editing or deletion
- No markdown rendering in assistant responses (plain text with `whitespace-pre-wrap`)
- Conversation title is first user message only (not AI-generated summary)

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
| 16 | Chat Page | 366 |
