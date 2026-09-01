# PHASE 10 — RAG

```
Phase:   10 — RAG
Status:  COMPLETE
```

## Files changed

### Created

- `apps/ai/generation.py` — `get_generation_provider()` factory function for AI generation providers
- `apps/chat/services.py` — `RAGService` with `ask()` method; `RAGResult` dataclass for structured responses
- `tests/test_phase10_rag.py` — 17 tests for RAGService

### Modified

- `config/settings.py` — added `GENERATION_PROVIDER` and `GEMINI_MODEL` settings
- `apps/ai/providers/gemini.py` — `GeminiProvider` now reads model from `settings.GEMINI_MODEL`

## Implementation

### Generation provider factory

```text
get_generation_provider()
        │
        ▼
settings.GENERATION_PROVIDER
        │
        ├── "gemini" → GeminiProvider
        └── other   → ValueError
```

Mirrors the existing `get_embedding_provider()` pattern from `apps/ai/embedding.py`.

### RAGService

```text
RAGService(retrieval_service?, ai_provider?)
        │
        └── ask(question)
                │
                ▼
        RetrievalService.search(question)
                │
                ▼
        _build_context(results)
                │
                ▼
        _build_prompt(context, question)
                │
                ▼
        AIProvider.generate(prompt)
                │
                ▼
        RAGResult(answer, retrieval_results)
```

- Services are injectable for testing
- AI provider called through `AIProvider` abstraction, not a vendor client
- Does NOT call any vendor SDK directly

### Context construction

Each retrieval result becomes a labeled block:

```text
[Source: monopoly.pdf, Page: 4]
Each player starts with $1,500.

[Source: monopoly.pdf, Page: 5]
Players take turns rolling two dice.
```

Blocks are separated by double newlines.

### Prompt structure

```text
{SYSTEM_PROMPT}

Context:
{context}

Question:
{question}
```

System prompt instructs the model to:
- Answer using only the provided context
- Not invent facts
- Say information is unavailable when context is insufficient

### RAGResult

```python
@dataclass
class RAGResult:
    answer: str                          # Generated answer from AI provider
    retrieval_results: list[RetrievalResult]  # Source chunks used for context
```

## Tests executed

| Check | Result |
|---|---|
| `uv run python manage.py check` | PASS — "System check identified no issues" |
| `uv run pytest tests/test_phase10_rag.py -v` | PASS — 17/17 passed |
| `uv run pytest tests/ -v` | PASS — 260/260 passed (0 regressions) |

Tests cover:
- **RAGService.ask**: returns RAGResult, correct answer, includes retrieval results, AI provider called once
- **Prompt**: contains system instruction, question, context chunks, source metadata, "do not invent" instruction, "only use context" instruction
- **Empty results**: still calls provider, returns empty results list, empty context in prompt
- **Context building**: single result, multiple sources, blocks separated by double newlines
- **Abstraction**: uses AIProvider interface, provider is injectable

All tests use FakeAIProvider and FakeRetrievalService — no external API calls.

```
Test result: PASS
```

## Known limitations

- No streaming support — full response generated before returning
- No conversation history / multi-turn context — each `ask()` is stateless
- No token limit management for context window — all retrieved chunks are included regardless of total length

## Next phase

PHASE 11 — Citation: extract citation metadata from retrieval results, deduplicate source/page pairs, structure as JSON in the response.
