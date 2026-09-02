# PHASE 19 — Extraction Pipeline (Backend, Celery)

| Section | Detail |
|---|---|
| **Phase** | 19 — Extraction Pipeline (Backend, Celery) |
| **Status** | PASS |
| **Files changed** | **Modified (5):** `apps/ai/providers/gemini.py`, `apps/ai/generation.py`, `config/settings.py`, `config/urls.py`, `PROJECT_INTELLIGENCE_PRD.md`. **New (12):** `apps/intelligence/services.py`, `apps/intelligence/tasks.py`, `apps/intelligence/views.py`, `apps/intelligence/urls.py`, `apps/intelligence/serializers.py`, `apps/intelligence/prompts.py`, `tests/test_phase19_extraction.py`. **Phase 18 carry-over (7):** `apps/intelligence/__init__.py`, `apps.py`, `models.py`, `admin.py`, `migrations/__init__.py`, `migrations/0001_initial.py`, `apps/intelligence/apps.py`. Total: **1,540 lines** across intelligence app + tests. |
| **Implementation** | **GeminiProvider** made configurable — accepts optional `max_output_tokens`, `temperature`, `response_mime_type` (backward-compatible, defaults from settings). **`get_extraction_provider()`** factory creates a provider with JSON mode, 16384 output tokens, 0.1 temperature. **Extraction prompt** (`prompts.py`) instructs the LLM to return a structured JSON with features (nested requirements, user flows + steps, risks), top-level dependencies (with inference_type EXPLICIT/INFERRED), and conflicts — all with source references (document name, page number, excerpt). **`ExtractionService`** gathers all COMPLETED document pages, validates content size (800K char threshold), calls the LLM, parses JSON, and saves all entities with proper FK relationships and document-name-to-ID resolution for source references. Uses `bulk_create` for SourceReference efficiency. Skips dependencies/conflicts referencing unknown features with warning logs. **Celery task** `run_project_analysis` manages PENDING→PROCESSING→COMPLETED/FAILED lifecycle, deletes previous completed analyses on success (full replace per PRD). `max_retries=0` — extraction is expensive, user re-triggers manually. **API endpoints:** `POST /api/project/analyze/` (triggers async, rejects if in-progress, returns 202), `GET /api/project/analysis/latest/` (fully nested serialization), `GET /api/project/analysis/<uuid>/` (specific analysis). **Settings:** `EXTRACTION_MAX_OUTPUT_TOKENS=16384`, `EXTRACTION_TEMPERATURE=0.1`, `EXTRACTION_MAX_CONTENT_LENGTH=800000`. |
| **Tests executed** | 31 new Phase 19 tests + 339 existing = 370 total (excluding 1 pre-existing Phase 08 failure) |
| **Test result** | 370/370 passed. Pre-existing failure: `test_phase08_vector.py::test_task_completes_without_real_services` (confirmed fails on clean main without Phase 19 changes). |
| **Known limitations** | Single-pass only (no multi-pass batching — content size check fails gracefully). Conflict requirement matching relies on exact description text. Dependencies/conflicts with unknown feature names are silently skipped. |
| **Next phase** | Phase 20 — Analysis Engine |

## Test Breakdown

- **ExtractionService (9):** creates features, requirements with status, user flows + ordered steps, dependencies with inference_type, risks with severity, source references with document mapping, verifies single LLM call, verifies prompt content.
- **Edge cases (6):** no completed docs → error, invalid JSON → error, content exceeds threshold → error, empty features array → no entities, unknown feature in dependency → skip, pending docs excluded.
- **API trigger (7):** returns 202, creates analysis, dispatches Celery task, rejects when PROCESSING/PENDING, allows after COMPLETED/FAILED.
- **API status (5):** 404 when empty, returns latest, returns by ID, 404 for nonexistent, includes nested features.
- **Celery task (4):** sets COMPLETED on success, sets FAILED on error, deletes previous analysis, ignores nonexistent ID.

## PRD Decisions Made

1. **Context window strategy: Single-pass.** Gemini 2.5 Flash has 1M token context window. ProjectLens's expected use case (5–20 documents, ~200 pages) totals ~100K–160K tokens — well within a single call. Content size check (800K char threshold) fails gracefully if exceeded.
2. **Entity resolution: Handled naturally by single-pass.** All document content enters one LLM context, so the model unifies features referenced by different names across documents.
3. **Conflict and Risk detection: Included in the extraction prompt.** The LLM identifies conflicts and risks during the same extraction pass — no separate LLM call needed.
