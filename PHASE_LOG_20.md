# PHASE 20 — Analysis Engine

| Section | Detail |
|---|---|
| **Phase** | 20 — Analysis Engine |
| **Status** | NOT STARTED |
| **PRD scope** | Analytic logic on top of Phase 18–19 structured data: **Missing requirements** (features without requirements, user flows without complete steps), **Conflict detection** (semantic comparison between requirements — already partially handled in Phase 19 extraction), **Dependency graph** (query/traversal of Dependency table), **Risk aggregation** (severity + description per feature/requirement), **Impact analysis** (given one feature, find affected features/requirements via dependency graph traversal + LLM-generated narrative explanation). |
| **Definition of Done** | Endpoints for each analysis type returning structured JSON ready for frontend consumption. Impact analysis accepts a specific feature and returns affected list + explanation. |
| **PRD decisions needed** | Whether conflict detection needs a separate LLM pass (Phase 19 already extracts conflicts during extraction — Phase 20 may add additional semantic comparison). Whether risk analysis needs an additional LLM pass or can use Phase 19 extraction results as-is. |
| **Dependencies** | Phase 18 (data model) ✅, Phase 19 (extraction pipeline) ✅ |
| **Expected endpoints** | `GET /api/project/analysis/latest/missing-requirements/`, `GET /api/project/analysis/latest/conflicts/`, `GET /api/project/analysis/latest/risks/`, `GET /api/project/analysis/latest/dependencies/`, `POST /api/project/analysis/latest/impact/` (accepts feature ID, returns affected graph + narrative) |
