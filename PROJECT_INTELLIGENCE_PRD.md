# ProjectLens — Project Intelligence PRD (Phase 18–23)

Lanjutan dari backend RAG (Phase 01–13) dan UI (Phase 14–17). Fitur ini menambah layer baru: dari "document QA" menjadi "structured project understanding" — Project Map, Feature & User Flow, dan analisis (missing requirements, conflict, dependency, risk, impact).

## Keputusan Arsitektur

- **Trigger analisis: manual.** User klik "Re-analyze Project". Tiap klik = **full re-extraction** (rebuild struktur dari nol berdasarkan semua dokumen COMPLETED saat ini), bukan incremental merge. Lebih simpel, dan cocok karena project understanding memang snapshot per titik waktu.
- **Dokumen: PDF saja**, reuse pipeline ingestion yang sudah ada (Phase 02–03). Tidak perlu parser baru.
- **Project Map: graph interaktif**, node bisa diklik untuk detail. Rekomendasi library: **Cytoscape.js** (vanilla JS, ringan, cocok dengan stack htmx/Alpine — tidak butuh React/build step berat). Klarifikasi/tantang pilihan ini boleh diajukan Claude saat propose plan kalau ada alasan kuat lain.
- **Storage: relasional (PostgreSQL)**, bukan graph DB terpisah (Neo4j dll) — cukup model dengan FK/self-referencing untuk dependency graph. Menghindari komponen infrastruktur baru yang tidak perlu.
- **Extraction: LLM dengan structured output** (JSON schema / function calling, provider Gemini yang sudah dipakai) — bukan prompt bebas yang di-parse manual dengan regex.

## Urutan Fase

### Phase 18 — Data Model (Structured Project Understanding)
Model baru untuk merepresentasikan pemahaman terstruktur:
- `ProjectAnalysis` — status (PENDING/PROCESSING/COMPLETED/FAILED), triggered_at, completed_at (satu "snapshot" analisis)
- `Feature` — nama, deskripsi, source document reference(s)
- `Requirement` — terikat ke Feature, status (covered/missing), source reference
- `UserFlow` + `UserFlowStep` — terikat ke Feature, urutan langkah, actor
- `Dependency` — relasi Feature-to-Feature (self-referencing, dengan tipe/arah)
- `Conflict` — dua Requirement yang bertentangan, referensi ke keduanya, deskripsi konflik
- `Risk` — terikat ke Feature/Requirement, severity, deskripsi

**Definition of Done:**
- Semua model + migration ada
- Terdaftar di Django admin untuk keperluan inspeksi manual selama development
- Belum ada logic ekstraksi — fase ini murni skema (pola sama seperti ChatSession/ChatMessage di Phase 03 dulu)

### Phase 19 — Extraction Pipeline (Backend, Celery)
Endpoint `POST /api/project/analyze/` yang trigger Celery task async. Task ini:
1. Ambil semua dokumen dengan status COMPLETED
2. Kirim konten ke LLM dengan prompt terstruktur untuk ekstrak Feature, Requirement, UserFlow — output dalam JSON schema yang jelas
3. Simpan hasil ke tabel-tabel Phase 18 (full replace — hapus hasil analisis sebelumnya, buat `ProjectAnalysis` baru)
4. Endpoint `GET /api/project/analysis/{id}/status/` atau `GET /api/project/analysis/latest/` untuk cek status/hasil

**Keputusan yang perlu di-propose Claude:**
- Berapa banyak dokumen/konten yang bisa masuk satu LLM call (context window limit) — apakah perlu multi-pass/batching untuk project dengan banyak dokumen
- Bagaimana menangani project besar yang melebihi context window (chunking strategy untuk ekstraksi, beda dengan chunking untuk embedding)

**Definition of Done:**
- Trigger manual dari API berjalan, task async tidak blocking
- Hasil ekstraksi tersimpan sesuai model Phase 18
- Test dengan AI provider yang di-mock (ikuti konvensi test yang sudah ada)

### Phase 20 — Analysis Engine
Logic analitik di atas data terstruktur Phase 18–19:
- **Missing requirements**: Feature tanpa Requirement terkait, atau UserFlow tanpa langkah lengkap
- **Conflict detection**: perbandingan semantik antar Requirement (bisa jadi bagian dari LLM call di Phase 19, atau pass terpisah — keputusan di-propose Claude)
- **Dependency graph**: query/traversal dari tabel Dependency
- **Risk**: severity + deskripsi per Feature/Requirement (dari hasil ekstraksi Phase 19, atau pass analisis tambahan)
- **Impact analysis**: given satu Feature, temukan Feature/Requirement lain yang terdampak (traversal Dependency graph) + narasi penjelasan (LLM call singkat)

**Definition of Done:**
- Endpoint(s) untuk tiap jenis analisis mengembalikan data terstruktur (JSON) siap dikonsumsi frontend
- Impact analysis bisa menerima input Feature tertentu dan mengembalikan daftar terdampak + penjelasan

### Phase 21 — Frontend: Project Map
Halaman baru menampilkan graph interaktif (Cytoscape.js) berdasarkan data Feature + Dependency dari Phase 18–20.
- Tombol "Re-analyze Project" (trigger Phase 19 endpoint, tampilkan status loading/progress)
- Node = Feature, edge = Dependency, klik node → panel detail (Requirement terkait, Risk, source document)

**Definition of Done:**
- Graph render dari data API, interaktif (klik node → detail)
- Tombol re-analyze berfungsi end-to-end dengan status yang jelas (PENDING/PROCESSING/COMPLETED/FAILED)

### Phase 22 — Frontend: Feature & User Flow Detail
Tampilan detail per Feature: Requirement terkait, User Flow (step-by-step), status coverage. Bisa berupa halaman/panel terpisah dari Project Map, diakses dari klik node atau list Feature.

**Definition of Done:**
- User bisa lihat detail satu Feature: requirement list, user flow steps berurutan, source document reference

### Phase 23 — Frontend: Analysis Dashboard
Halaman/tab menampilkan hasil Phase 20: Missing Requirements, Conflicts, Risks (list/card), plus tool Impact Analysis (pilih Feature → lihat dampak).

**Definition of Done:**
- Tiap jenis analisis tampil terstruktur dan bisa di-drill-down ke Feature/Requirement terkait
- Impact analysis interaktif: pilih Feature, dapat hasil + penjelasan

## Execution Rules

Sama seperti PRD sebelumnya — satu fase per sesi, propose plan dulu (terutama Phase 19 untuk strategi context window, dan Phase 20 untuk keputusan single-pass vs multi-pass analisis), tunggu approval, implement, report format standar (Phase/Status/Files changed/Implementation/Tests executed/Test result/Known limitations/Next phase), tidak commit otomatis.
