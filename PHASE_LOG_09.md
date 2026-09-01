# PHASE 09 — Retrieval

```
Phase:   09 — Retrieval
Status:  COMPLETE
```

## Files changed

### Created

- `apps/retrieval/services.py` — `RetrievalService` with `search()` method; `RetrievalResult` dataclass for normalized results
- `tests/test_phase09_retrieval.py` — 16 tests for ChromaService.query and RetrievalService

### Modified

- `core/chroma.py` — added `query()` method to `ChromaService`

## Implementation

### ChromaService.query

```text
ChromaService.query(query_embedding, n_results=5)
        │
        ▼
collection.query(
    query_embeddings=[query_embedding],
    n_results=n_results,
    include=["documents", "metadatas", "distances"]
)
```

Returns raw ChromaDB result dict with documents, metadatas, and distances.

### RetrievalService

```text
RetrievalService(embedding_service?, chroma_service?)
        │
        └── search(query, k=None)
                │
                ▼
        Embed query (EmbeddingService.embed_query)
                │
                ▼
        Query ChromaDB (ChromaService.query)
                │
                ▼
        Normalize results → list[RetrievalResult]
```

- Default `k` from `settings.RETRIEVAL_K` (default 5)
- Custom `k` parameter overrides settings
- Services are injectable for testing
- Does NOT generate answers — returns raw content only

### RetrievalResult

```python
@dataclass
class RetrievalResult:
    content: str   # chunk text from ChromaDB
    source: str    # source filename from metadata
    page: int      # page number from metadata
    score: float   # similarity score (1.0 - distance), rounded to 4 decimals
```

### Score normalization

ChromaDB returns L2 distances (lower = closer). Converted to similarity score: `score = 1.0 - distance`, rounded to 4 decimal places. Results come back ordered by relevance (highest score first).

## Tests executed

| Check | Result |
|---|---|
| `uv run python manage.py check` | PASS — "System check identified no issues" |
| `uv run pytest tests/test_phase09_retrieval.py -v` | PASS — 16/16 passed |
| `uv run pytest tests/ -v` | PASS — 243/243 passed (0 regressions) |

Tests cover:
- **ChromaService.query**: returns documents/metadatas/distances, respects n_results, returns fewer when collection smaller, empty collection returns empty
- **RetrievalService.search**: returns RetrievalResult list, correct content/source/page/score, default K from settings, custom K overrides, empty collection returns empty, score bounded at 1.0, results ordered by relevance
- **Boundary**: returns raw content not generated answer, no AI provider used
- **Normalization**: page is int, score rounded to 4 decimals, multiple sources

All tests use in-memory ChromaDB client and fake embedding provider — no external services required.

```
Test result: PASS
```

## Known limitations

- Score formula `1.0 - distance` assumes ChromaDB default L2 distance metric; other metrics would need different conversion
- No minimum score threshold filtering — all top-K results are returned regardless of relevance
- No document-scoped retrieval (searches across all documents in the collection)

## Next phase

PHASE 10 — RAG: context construction, prompt building, AI provider generation, answer grounded in retrieved context.
