# CtrlCoco: keputusan awal
- Bentuk: widget desktop pribadi, karakter Coco (anjing mirip golden retriever campuran)
- Stack: Python + PySide6 + SQLite
- Hanya untuk laptop pribadi; database tidak boleh masuk Git (.gitignore)
- Tidak ada data/detail pekerjaan kantor; magang cukup label umum
- Tabel MVP: area, task, daily_log
- Aturan streak: 1 hari valid jika ada aktivitas Claude Code DAN GitHub di hari yang sama; dicatat manual
- Ekspresi Coco (3 awal): senang (streak valid), waspada (deadline <24 jam), tidur (belum ada log hari ini)
- Alur kerja: 1 fitur = 1 issue = 1 PR; per tahap ada recap pemahaman
- Tahap: 1 ERD+user story, 2 inti data, 3 widget kosong, 4 animasi, 5 input cepat

## Prioritas kondisi Coco (diputuskan di awal Tahap 4)

Coco hanya punya satu kondisi pada satu waktu. Aturan diperiksa berurutan dari atas, dan yang pertama cocok menang:

1. **waspada**: ada task `todo` yang deadline-nya sudah lewat atau kurang dari 24 jam dari sekarang.
2. **senang**: hari ini valid (`claude_code = 1` dan `github = 1`).
3. **tidur**: selain itu (belum ada log hari ini, atau log ada tapi baru satu aktivitas).

Catatan:
- Waspada menang atas senang: deadline yang mepet lebih mendesak daripada log yang sudah lengkap.
- Deadline tepat 24 jam lagi belum waspada (aturannya "kurang dari").
- Task tanpa deadline dan task berstatus `done` tidak pernah memicu waspada.
- Logikanya ada di `get_mood(conn, now)` di `src/ctrlcoco/mood.py`, terpisah dari tampilan widget.
