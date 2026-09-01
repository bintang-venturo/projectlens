# PHASE 14 — Frontend Foundation

```
Phase:   14 — Frontend Foundation
Status:  COMPLETE
```

## Files changed

### Created

- `apps/ui/__init__.py` — empty init for new Django app
- `apps/ui/apps.py` — AppConfig for `apps.ui`
- `apps/ui/views.py` — 3 views: `chat_view`, `documents_view`, `settings_view`
- `apps/ui/urls.py` — URL routing under `ui:` namespace (chat `/`, documents `/documents/`, settings `/settings/`)
- `apps/ui/static/ui/images/logo.png` — branding asset (copied from `design/logo.png`)
- `apps/ui/templates/ui/base.html` — base layout with sidebar nav, top bar, content block
- `apps/ui/templates/ui/chat.html` — placeholder chat page
- `apps/ui/templates/ui/documents.html` — placeholder document library page
- `apps/ui/templates/ui/settings.html` — placeholder settings page
- `tests/test_phase14_frontend_foundation.py` — 14 tests for frontend foundation
- `design/chat-page.png` — Stitch design reference
- `design/document-library-page.png` — Stitch design reference
- `design/logo.png` — Stitch design reference
- `design/settings-age.png` — Stitch design reference

### Modified

- `config/settings.py` — added `"apps.ui"` to `INSTALLED_APPS`
- `config/urls.py` — added `path("", include("apps.ui.urls"))` for UI routes
- `BASE_UI_PRD.md` — UI implementation PRD (Phases 14–17)

## Implementation

### Architecture decisions

- **App location:** `apps/ui/` — follows existing `apps/` convention
- **Styling:** Tailwind CSS via play-CDN (`cdn.tailwindcss.com`) with inline config for brand colors
- **Interactivity:** htmx 2.0.4 + Alpine.js 3.14.8 via CDN (loaded in base template)
- **Typography:** Inter font via Google Fonts
- **Same-origin:** UI served from the same Django app as the REST API — no CORS issues

### Layout structure

```text
┌───────────────────────────────────────────────────┐
│  Sidebar (w-60)  │  Main Content Area             │
│                  │                                 │
│  ┌────────────┐  │  ┌──────────────────────────┐  │
│  │ Logo       │  │  │ Top Bar (search + user)  │  │
│  ├────────────┤  │  ├──────────────────────────┤  │
│  │ Dashboard  │  │  │                          │  │
│  │ Chat       │  │  │  {% block content %}     │  │
│  │ Settings   │  │  │                          │  │
│  ├────────────┤  │  │                          │  │
│  │ Engine     │  │  │                          │  │
│  │ Status     │  │  │                          │  │
│  └────────────┘  │  └──────────────────────────┘  │
└───────────────────────────────────────────────────┘
```

### Navigation

- Sidebar nav with 3 links: Dashboard (documents), Chat, Settings
- Active page highlighted with `bg-brand-500 text-white`
- `active_page` context variable drives highlight logic
- SVG icons for each nav item
- Engine Status indicator at sidebar bottom

### Styling foundation

| Token | Value | Usage |
|---|---|---|
| `brand-50` | `#eff6ff` | Subtle backgrounds |
| `brand-500` | `#3b82f6` | Primary / active nav |
| `brand-600` | `#2563eb` | Hover states |
| `brand-700` | `#1d4ed8` | Focus states |
| `navy` | `#0f172a` | Brand text |

### URL routing

| URL | View | Name |
|---|---|---|
| `/` | `chat_view` | `ui:chat` |
| `/documents/` | `documents_view` | `ui:documents` |
| `/settings/` | `settings_view` | `ui:settings` |

All existing `/api/*` routes remain unchanged and functional.

## Tests executed

| Check | Result |
|---|---|
| `uv run pytest tests/test_phase14_frontend_foundation.py -v` | PASS — 14/14 passed |
| `uv run pytest tests/ -v` | PASS — 318/318 passed (0 regressions) |

Tests cover:
- **Page loads**: all 3 pages return HTTP 200
- **Template content**: logo present, nav links present, page-specific content renders
- **Active nav state**: correct page highlighted in sidebar
- **Assets**: htmx and Alpine.js loaded in base template
- **Engine status**: sidebar shows "Engine Status" indicator
- **API coexistence**: `/api/documents/` still returns 200
- **URL resolution**: all named URLs resolve correctly

```
Test result: PASS
```

## Known limitations

- Search bar in top bar is disabled (placeholder only)
- Notification bell is disabled (placeholder only)
- User info is hardcoded ("User" / "ProjectLens")
- Engine Status is hardcoded "Operational" (not wired to health check)
- Tailwind via play-CDN — not suitable for production (acceptable for MVP)

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
