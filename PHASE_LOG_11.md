# PHASE 11 — Citation

```
Phase:   11 — Citation
Status:  COMPLETE
```

## Files changed

### Created

- `tests/test_phase11_citation.py` — 15 tests for `build_citations` and RAGService citation integration

### Modified

- `apps/chat/services.py` — added `Citation` dataclass, `build_citations()` function, wired citations into `RAGResult` and `RAGService.ask()`

## Implementation

### Citation dataclass

```python
@dataclass
class Citation:
    source: str   # source filename from retrieval metadata
    page: int     # page number from retrieval metadata
```

### build_citations

```text
build_citations(retrieval_results)
        │
        ▼
Iterate results in order
        │
        ▼
Extract (source, page) pairs
        │
        ▼
Deduplicate (keep first occurrence)
        │
        ▼
list[Citation]
```

- Citations come from retrieval metadata only — the LLM does not invent them
- Duplicate (source, page) combinations are removed
- Original order (by retrieval relevance) is preserved
- First occurrence wins when duplicates exist

### RAGResult (updated)

```python
@dataclass
class RAGResult:
    answer: str
    citations: list[Citation]
    retrieval_results: list[RetrievalResult]
```

### RAGService.ask (updated)

```text
ask(question)
    │
    ├── RetrievalService.search(question) → results
    ├── _build_context(results)
    ├── _build_prompt(context, question)
    ├── AIProvider.generate(prompt) → answer
    ├── build_citations(results) → citations
    └── RAGResult(answer, citations, retrieval_results)
```

## Tests executed

| Check | Result |
|---|---|
| `uv run python manage.py check` | PASS — "System check identified no issues" |
| `uv run pytest tests/test_phase11_citation.py -v` | PASS — 15/15 passed |
| `uv run pytest tests/ -v` | PASS — 275/275 passed (0 regressions) |

Tests cover:
- **build_citations**: single result, duplicate source/page removed, different pages kept, different sources kept, empty results, order preserved, first occurrence kept, returns Citation dataclass, has source/page fields, metadata not invented
- **RAGService integration**: ask returns citations, deduplicates citations, empty retrieval → no citations, RAGResult has all fields, citations are structured data

All tests use fake providers — no external API calls.

```
Test result: PASS
```

## Known limitations

- No weighting or ranking of citations — order reflects retrieval relevance
- No citation linking to specific answer segments — citations cover the full answer

## Next phase

PHASE 12 — Chat API: REST endpoint `POST /api/chat/` wiring RAGService and returning JSON with answer and citations.
