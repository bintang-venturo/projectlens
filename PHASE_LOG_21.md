# PHASE 21 — Frontend: Project Map

| Section | Detail |
|---|---|
| **Phase** | 21 — Frontend: Project Map |
| **Status** | PASS |
| **Files changed** | **Modified (2):** `apps/ui/urls.py` (added project-map route), `apps/ui/templates/ui/base.html` (added Project Map nav link to sidebar). **New (2):** `apps/ui/views.py` (added `project_map_view`), `apps/ui/templates/ui/project_map.html` (full Project Map page with Cytoscape.js graph). **Tests (1):** `tests/test_phase21_project_map.py` (27 tests). |
| **Implementation** | **Route & View:** `GET /project-map/` renders `project_map.html` with `active_page="project-map"`. **Sidebar nav:** Project Map link added to `base.html` sidebar with map icon, active state highlighting via `active_page` context variable — visible on all pages. **Cytoscape.js graph:** Loads analysis data from `GET /api/project/analysis/latest/`, renders features as nodes (blue = normal, red = high/critical risk) and dependencies as directed edges (solid = explicit, dashed = inferred). Uses `cose` force-directed layout with animation. **Detail panel:** Right-side slide-out panel on node tap showing feature name, description, requirements (color-coded COVERED/MISSING), risks (severity badges), source document references, and dependency list (clickable to navigate graph). **Re-analyze button:** Triggers `POST /api/project/analyze/`, shows spinner, polls `GET /api/project/analysis/<id>/` every 3s until COMPLETED/FAILED, then reloads graph. Handles 409 (already in progress). **States:** Empty state (no analysis), loading spinner, error toast with dismiss. **Alpine.js** manages all reactive state (selectedFeature, loading, analyzing, polling). |
| **Tests executed** | 27 new Phase 21 tests + existing = all passing |
| **Test result** | 27/27 passed |
| **Known limitations** | Graph layout is non-deterministic (cose algorithm). No zoom controls UI (browser zoom/scroll works). No graph export/screenshot. Dark mode not implemented. |
| **Next phase** | Phase 22 |

## Test Breakdown

- **Route (4):** page loads 200, URL resolves to `/project-map/`, correct template used, extends base.html.
- **Content (9):** page title, Cytoscape loaded, Re-analyze button, graph container `#cy`, empty state message, detail panel (`selectedFeature`), dependency legend (Explicit/Inferred), htmx loaded, Alpine.js loaded.
- **Navigation (3):** sidebar has project-map link, active state on project-map page, link visible from other pages (chat, documents, settings).
- **API Integration (6):** latest analysis returns graph data (features, dependencies with from/to/inference_type/names), features include requirements with status, features include risks with severity, empty analysis returns 404, analysis detail by ID, dependency has inference_type (EXPLICIT/INFERRED).
- **Cytoscape Config (5):** uses cose layout, inferred edges dashed (`line-style: dashed`), graph fetches from `/api/project/analysis/latest/`, re-analyze posts to `/api/project/analyze/`, polling with `startPolling`/`setInterval`.
