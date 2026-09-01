Read `PROJECTLENS_IMPLEMENTATION_PRD.md`.

## A. Status Fase Sebelumnya

Phase [NOMOR FASE SEBELUMNYA] telah selesai. Berikut laporan resminya:

---
Phase: [tempel dari laporan Claude sebelumnya]
Status: [tempel]

Files changed:
[tempel]

Implementation:
[tempel]

Tests executed:
[tempel]

Test result: [tempel]

Known limitations:
[tempel]

Next phase: [tempel]
---

## B. Verifikasi

Sebelum melanjutkan:
1. Inspect current repo state.
2. Verifikasi laporan di atas masih akurat terhadap kondisi repo saat ini (file benar-benar ada, test masih pass, tidak ada perubahan manual yang belum tercatat).
3. Jika ada ketidaksesuaian antara laporan dan kondisi repo aktual, laporkan sebelum lanjut — jangan asumsikan laporan lama selalu benar.

## C. Instruksi Fase Berikutnya

Lanjutkan ke PHASE [NOMOR FASE BERIKUTNYA] sesuai urutan di Section 18 PRD.

Ikuti semua aturan di Section 19 (Claude Code Execution Rules), termasuk:
- Implementasi satu fase ini saja, jangan lompat ke fase setelahnya.
- Inspect struktur project yang ada sebelum ubah kode.
- Jangan overwrite konfigurasi yang sudah jalan kecuali memang perlu.
- Jalankan test yang relevan setelah fase ini selesai.
- Jangan lanjut jika fase ini masih broken.
- Jika ada perubahan arsitektur yang bertentangan dengan PRD, jelaskan alasannya dulu sebelum eksekusi.

Jangan modifikasi file apa pun sampai saya approve plan untuk fase ini.

Setelah saya approve, kerjakan fase ini dan tutup dengan laporan sesuai format Section 19 (Phase / Status / Files changed / Implementation / Tests executed / Test result / Known limitations / Next phase).