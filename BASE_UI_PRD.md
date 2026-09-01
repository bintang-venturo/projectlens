# ProjectLens — UI Implementation PRD (Phase 14–17)

Lanjutan dari `PROJECTLENS_IMPLEMENTATION_PRD.md` (Phase 01–13, backend, sudah selesai). Dokumen ini scope-nya khusus frontend.

## Stack & Keputusan Teknis

- **Stack:** Django templates + htmx + Alpine.js. Tidak ada SPA terpisah, tidak ada build step JS yang berat (htmx/Alpine via CDN atau vendored, bukan bundler seperti Vite/Webpack kecuali memang dibutuhkan untuk Tailwind).
- **Lokasi:** Folder `frontend/` di repo yang sama. Karena ini Django templates (bukan SPA statis), `frontend/` berisi: Django app baru (misal `apps/ui/`) untuk views + templates, plus `static/` untuk CSS/JS/asset desain (logo, dsb dari Google Stitch).
- **Same-origin:** Karena disajikan dari Django app yang sama dengan REST API, **tidak ada isu CORS**. Views di `apps/ui/` bisa call service layer langsung (reuse `RAGService`, dsb) atau tetap lewat REST API internal — ini salah satu keputusan yang perlu di-propose Claude di Phase 14.
- **Styling:** Bebas, senada dengan vibe desain Stitch (bukan pixel-perfect clone). Tailwind direkomendasikan untuk kecepatan, tapi keputusan akhir di tangan Claude saat propose plan.
- **Referensi desain:** `design/logo.png`, `design/chat-page.png`, `design/document-library-page.png`, `design/settings-page.png` (hasil Google Stitch).

## Urutan Fase

### Phase 14 — Frontend Foundation
Setup app baru, base template/layout, navigasi antar 3 halaman, branding (logo), styling foundation (Tailwind config kalau dipakai). Tidak ada fungsionalitas chat/document/settings yang riil di fase ini — cuma shell + nav yang bisa diklik antar halaman (boleh dummy/placeholder content).

**Definition of Done:**
- App `apps/ui/` (atau nama lain hasil kesepakatan) berjalan, bisa diakses via browser
- Base layout dengan nav ke 3 halaman (Chat, Document Library, Settings) sudah ada
- Logo & branding dari `design/logo.png` sudah terpasang
- Styling foundation established (bisa dilihat konsisten di base layout)

### Phase 15 — Document Library Page
Halaman untuk upload PDF, lihat daftar dokumen beserta status (`PENDING`/`PROCESSING`/`COMPLETED`/`FAILED`), sesuai desain `design/document-library-page.png`.

**Definition of Done:**
- Upload form berfungsi (POST ke `/api/documents/` atau setara)
- List dokumen tampil dengan status masing-masing
- Status ter-update tanpa perlu manual refresh penuh (htmx polling, atau setidaknya refresh button — detail ditentukan di plan)
- Error handling untuk validasi upload (non-PDF, file kosong, dll — sesuai error response yang sudah ada di backend)

### Phase 16 — Chat Page
Halaman chat sesuai `design/chat-page.png`, terhubung ke `/api/chat/` yang sudah session-aware (Phase 13).

**Definition of Done:**
- User bisa kirim pertanyaan, dapat jawaban + citations (source file + page)
- Percakapan multi-turn berjalan (session_id ter-maintain otomatis antar request — mekanisme persis-nya, misal via Django session server-side vs client-side, ditentukan Claude saat propose plan)
- History percakapan tampil di UI selama halaman belum di-reload/session belum direset
- Ada cara untuk mulai percakapan baru (reset session)

### Phase 17 — Settings Page (placeholder, prioritas rendah)
Halaman ini **tidak punya backend/API pendukung** dan tidak wajib fungsional penuh. Cukup tampilkan layout sesuai `design/settings-page.png` sebagai placeholder — boleh dikerjakan terakhir, atau di-skip dulu sampai ada kebutuhan konkret.

**Definition of Done:**
- Halaman bisa diakses dari nav, layout sesuai desain
- Tidak perlu wired ke data/API apapun — static/placeholder content cukup

## Execution Rules (sama seperti PRD backend)

1. Satu fase per sesi. Jangan lompat ke fase berikutnya tanpa approval.
2. **Selalu propose plan dulu, tunggu approval, baru implement** — terutama di Phase 14 (keputusan struktur app + styling approach) dan Phase 16 (mekanisme session_id persistence).
3. Inspect struktur project yang ada sebelum ubah kode.
4. Reference gambar desain (`design/*.png`) langsung saat propose plan dan implementasi — jangan minta Claude menebak layout dari deskripsi teks saja.
5. Jalankan test yang relevan (kalau ada test convention untuk views/templates di project ini, ikuti; kalau belum ada, boleh diusulkan di Phase 14).
6. Tutup tiap fase dengan laporan format standar: Phase / Status / Files changed / Implementation / Tests executed / Test result / Known limitations / Next phase.
7. Tidak commit otomatis — commit dilakukan manual oleh user setelah review.

## Next Steps

1. Taruh 4 file desain Stitch di folder `design/` di root repo (kalau belum)
2. Mulai Phase 14 dengan prompt propose-plan (lihat pola di `phase13_prompt.md` sebagai referensi format)
3. Simpan laporan tiap fase ke `PHASE_LOG_14.md` dst