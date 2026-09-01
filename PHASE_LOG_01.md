# PHASE 01 — Architecture

```
Phase:   01 — Architecture
Status:  COMPLETE
```

## Files changed

### Created

- `apps/__init__.py` — apps package root
- `apps/documents/__init__.py` — documents app placeholder
- `apps/ingestion/__init__.py` — ingestion app placeholder
- `apps/retrieval/__init__.py` — retrieval app placeholder
- `apps/chat/__init__.py` — chat app placeholder
- `apps/ai/__init__.py` — ai app placeholder
- `apps/ai/providers/__init__.py` — providers sub-package
- `apps/ai/providers/base.py` — AIProvider ABC (relocated from `ai/`)
- `apps/ai/providers/gemini.py` — GeminiProvider (relocated from `ai/`)
- `tests/__init__.py` — test package
- `tests/conftest.py` — pytest-django configuration
- `data/.gitkeep` — upload directory placeholder

### Modified

- `config/settings.py` — SECRET_KEY/DEBUG from env, DEFAULT_AUTO_FIELD, ChromaDB/chunking/embedding/retrieval settings, MEDIA_ROOT
- `.env` — added CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_*, RETRIEVAL_K
- `pyproject.toml` — added langchain-text-splitters, pytest config with testpaths, switched build backend from uv_build to hatchling
- `.gitignore` — added data/* exclusion with .gitkeep exception

### Deleted

- `ai/` (entire directory) — relocated to `apps/ai/`
- `db.sqlite3` — stale SQLite file
- `127.0.0.1:0:` — junk file
- `src/projectlens/` — unused uv_build scaffold

## Implementation

- Directory structure now matches the PRD: `apps/`, `tests/`, `data/`, `config/`, `core/`, `scripts/`
- All five PRD apps exist as packages under `apps/` (documents, ingestion, retrieval, chat, ai)
- AI provider abstraction preserved at new path `apps.ai.providers`
- All settings driven by environment variables (no hardcoded secrets)
- All PRD-required config vars defined (ChromaDB, chunking, embedding, retrieval)
- `langchain-text-splitters` dependency available for Phase 06
- Build system switched from `uv_build` (which required `src/projectlens/`) to `hatchling` (which packages `config`, `apps`, `core` directly)

## Tests executed

| Check                                              | Result |
|----------------------------------------------------|--------|
| `uv sync`                                          | PASS — all deps installed including langchain-text-splitters |
| `uv run python manage.py check`                    | PASS — "System check identified no issues" |
| `uv run pytest`                                    | PASS — no errors, 0 tests (exit code 5 = no tests collected, expected) |
| `docker compose config`                            | PASS — valid config, no changes |
| `from apps.ai.providers.base import AIProvider`    | PASS |
| `from apps.ai.providers.gemini import GeminiProvider` | PASS |
| GeminiProvider.generate() live call                 | PASS — response received from gemini-3.6-flash |

```
Test result: PASS
```

## Known limitations

- App packages under `apps/` are empty placeholders — no `apps.py`, models, views, urls, or serializers yet (Phase 02)
- `core/` app still exists but is not registered in `INSTALLED_APPS` (unchanged from pre-existing state)
- `EmbeddingProvider` ABC not yet defined (Phase 07)
- No API endpoints registered (Phase 04+)

## Next phase

PHASE 02 — Django Apps: Create proper Django app scaffolds (apps.py, models.py, views.py, urls.py, serializers.py, admin, migrations) for each app under `apps/` and register them in `INSTALLED_APPS`.
