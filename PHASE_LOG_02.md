# PHASE 02 — Django Apps

```
Phase:   02 — Django Apps
Status:  COMPLETE
```

## Files changed

### Created

- `apps/documents/apps.py` — DocumentsConfig (label="documents", name="apps.documents")
- `apps/documents/models.py` — empty placeholder (Phase 03)
- `apps/documents/views.py` — empty placeholder (Phase 04)
- `apps/documents/urls.py` — app_name="documents", empty urlpatterns
- `apps/documents/serializers.py` — empty placeholder (Phase 04)
- `apps/documents/admin.py` — admin import placeholder
- `apps/documents/migrations/__init__.py` — migrations package

- `apps/ingestion/apps.py` — IngestionConfig (label="ingestion", name="apps.ingestion")
- `apps/ingestion/models.py` — empty placeholder (Phase 03)
- `apps/ingestion/views.py` — empty placeholder
- `apps/ingestion/urls.py` — app_name="ingestion", empty urlpatterns
- `apps/ingestion/serializers.py` — empty placeholder
- `apps/ingestion/admin.py` — admin import placeholder
- `apps/ingestion/tasks.py` — empty placeholder (Phase 14 — Celery tasks)
- `apps/ingestion/migrations/__init__.py` — migrations package

- `apps/retrieval/apps.py` — RetrievalConfig (label="retrieval", name="apps.retrieval")
- `apps/retrieval/models.py` — empty placeholder
- `apps/retrieval/views.py` — empty placeholder
- `apps/retrieval/urls.py` — app_name="retrieval", empty urlpatterns
- `apps/retrieval/serializers.py` — empty placeholder
- `apps/retrieval/admin.py` — admin import placeholder
- `apps/retrieval/migrations/__init__.py` — migrations package

- `apps/chat/apps.py` — ChatConfig (label="chat", name="apps.chat")
- `apps/chat/models.py` — empty placeholder (Phase 03)
- `apps/chat/views.py` — empty placeholder (Phase 12)
- `apps/chat/urls.py` — app_name="chat", empty urlpatterns
- `apps/chat/serializers.py` — empty placeholder (Phase 12)
- `apps/chat/admin.py` — admin import placeholder
- `apps/chat/migrations/__init__.py` — migrations package

- `apps/ai/apps.py` — AIConfig (label="ai", name="apps.ai")
- `apps/ai/models.py` — empty placeholder
- `apps/ai/views.py` — empty placeholder
- `apps/ai/urls.py` — app_name="ai", empty urlpatterns
- `apps/ai/serializers.py` — empty placeholder
- `apps/ai/admin.py` — admin import placeholder
- `apps/ai/migrations/__init__.py` — migrations package

- `tests/test_phase02_apps.py` — 41 tests for app scaffolding

### Modified

- `config/settings.py` — added all 5 apps to INSTALLED_APPS
- `config/urls.py` — wired api/documents/ and api/chat/ includes

## Implementation

- Created proper Django app scaffolds for all 5 PRD apps: documents, ingestion, retrieval, chat, ai
- Each app has: apps.py (AppConfig), models.py, views.py, urls.py, serializers.py, admin.py, migrations/__init__.py
- Each AppConfig uses `name="apps.<label>"` and `label="<label>"` to avoid Django's app label collision with the `apps` package
- Ingestion app additionally includes `tasks.py` for future Celery tasks
- All 5 apps registered in `INSTALLED_APPS`
- Root URL conf wires `api/documents/` and `api/chat/` (the two PRD-required API prefixes)
- AI provider abstraction (`apps.ai.providers.base` / `apps.ai.providers.gemini`) preserved unchanged

## Tests executed

| Check                             | Result |
|-----------------------------------|--------|
| `uv run python manage.py check`  | PASS — "System check identified no issues" |
| `uv run python manage.py makemigrations --check --dry-run` | PASS — "No changes detected" |
| `uv run pytest tests/test_phase02_apps.py -v` | PASS — 41/41 passed |

Tests cover:
- All 5 apps registered in Django app registry
- All 5 apps have migrations packages
- All 5 apps have required modules (models, views, urls, serializers, admin)
- documents and chat URL confs have app_name and urlpatterns
- ingestion has tasks module
- AI providers base/gemini preserved and importable
- Root URL conf includes api/documents/ and api/chat/

```
Test result: PASS
```

## Known limitations

- All models.py, views.py, serializers.py are empty — models come in Phase 03, endpoints in Phase 04+
- urlpatterns are empty lists — routes added when views are implemented
- `core/` app still exists but is not in INSTALLED_APPS (unchanged from Phase 01)
- `EmbeddingProvider` ABC not yet defined (Phase 07)

## Next phase

PHASE 03 — Database Models: Define Document, DocumentPage, DocumentChunk, ChatSession, and ChatMessage models with constraints and status choices per the PRD.
