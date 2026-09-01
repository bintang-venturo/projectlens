# PHASE 07 — Embedding

```
Phase:   07 — Embedding
Status:  COMPLETE
```

## Files changed

### Created

- `apps/ai/embedding.py` — `EmbeddingService`, `get_embedding_provider()` factory
- `tests/test_phase07_embedding.py` — 31 tests for provider abstraction, Gemini implementation, service, factory

### Modified

- `apps/ai/providers/base.py` — added `EmbeddingProvider` ABC alongside existing `AIProvider`
- `apps/ai/providers/gemini.py` — added `GeminiEmbeddingProvider`, refactored `GeminiProvider` to use Django settings

## Implementation

### EmbeddingProvider ABC

```python
class EmbeddingProvider(ABC):

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        ...
```

Separate from `AIProvider` (generation) — each has a single responsibility per PRD §8.

### GeminiEmbeddingProvider

- Uses `google-genai` SDK's `client.models.embed_content()` API
- Reads `EMBEDDING_API_KEY` and `EMBEDDING_MODEL` from Django settings
- `embed_documents()` passes texts as a list, returns `[e.values for e in response.embeddings]`
- `embed_query()` passes single text, returns `response.embeddings[0].values`

### EmbeddingService

```text
EmbeddingService
       │
       ▼
EmbeddingProvider (injected or from factory)
       │
       ▼
External Embedding API
```

- Accepts an optional `provider` parameter for dependency injection (testing)
- Falls back to `get_embedding_provider()` which reads `EMBEDDING_PROVIDER` setting
- Delegates `embed_documents()` and `embed_query()` to the provider
- Same provider instance used for both document and query embeddings

### Provider factory

```python
get_embedding_provider()
        │
        ▼
Read EMBEDDING_PROVIDER setting
        │
        ├── "gemini" → GeminiEmbeddingProvider()
        └── other   → ValueError
```

### Configuration (already in settings.py from Phase 01)

```env
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL=text-embedding-004
EMBEDDING_API_KEY=...
```

## Tests executed

| Check | Result |
|---|---|
| `uv run python manage.py check` | PASS — "System check identified no issues" |
| `uv run python manage.py makemigrations --check --dry-run` | PASS — "No changes detected" |
| `uv run pytest tests/test_phase07_embedding.py -v` | PASS — 31/31 passed |
| `uv run pytest tests/ -v` | PASS — 200/200 passed (0 regressions) |

Tests cover:
- **EmbeddingProvider ABC**: is abstract, both methods are abstract, separate from AIProvider, subclass validation
- **AIProvider regression**: still abstract, generate still abstract, GeminiProvider still subclass
- **GeminiEmbeddingProvider**: is EmbeddingProvider subclass, not AIProvider subclass, embed_documents returns correct values, passes model and texts to API, handles empty list, embed_query returns single vector, passes text to API, uses API key and model from settings
- **get_embedding_provider**: returns GeminiEmbeddingProvider for "gemini", raises on unknown provider, returns EmbeddingProvider instance
- **EmbeddingService**: injected provider, delegates embed_documents, delegates embed_query, returns correct types (list[list[float]] and list[float]), default provider from settings, same provider for documents and queries, preserves order, handles empty list

All tests mock the external API — no real API calls required.

```
Test result: PASS
```

## Known limitations

- Only Gemini embedding provider implemented (add more providers by subclassing `EmbeddingProvider`)
- `embed_documents()` sends all texts in a single API call — no batching for very large document sets
- No retry logic on API failures (can be added to the service layer later)
- Embedding is not yet integrated into the ingestion pipeline (Phase 08 — Vector Storage)

## Next phase

PHASE 08 — Vector Storage: ChromaDB integration, `projectlens_documents` collection, incremental synchronization, embedding + storage in ingestion pipeline.
