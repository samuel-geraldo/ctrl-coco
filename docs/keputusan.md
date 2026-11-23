# CtrlCoco: keputusan awal
- Bentuk: widget desktop pribadi, karakter Coco (anjing mirip golden retriever campuran)
- Stack: Python + PySide6 + SQLite
- Hanya untuk laptop pribadi; database tidak boleh masuk Git (.gitignore)
- Tidak ada data/detail pekerjaan kantor; magang cukup label umum
- Tabel MVP: area, task, daily_log
- Aturan streak: 1 hari valid jika ada aktivitas Claude Code DAN GitHub di hari yang sama; dicatat manual
- Ekspresi Coco (3 awal): waspada, senang, tidur; aturan dan urutannya ada di bagian "Prioritas kondisi Coco" di bawah
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

## Waktu tunggu kunci database: 1 detik (#47)

Bila database sedang dikunci proses lain, SQLite menunggu dulu sebelum menyerah dengan "database is locked". Bawaan `sqlite3` adalah 5 detik. Semua query widget berjalan di thread antarmuka, jadi selama menunggu widget beku (animasi berhenti, tidak bisa digeser); pada percobaan di #22, satu refresh saat terkunci menahan antarmuka sekitar 7,5 detik.

Keputusan: `db.connect` memakai waktu tunggu 1 detik (`WAKTU_TUNGGU_KUNCI` di `src/ctrlcoco/db.py`), untuk widget, ketiga form, startup, dan `scripts/seed_demo.py`.

Alasan:
- 1 detik masih cukup untuk kunci yang singkat, misalnya skrip yang sedang menulis beberapa baris.
- Bila kunci lebih lama, menunggu lebih lama tidak membantu: error-nya sudah ditangani di semua tempat (widget menampilkan "Data gagal dimuat" lalu mencoba lagi di refresh berikutnya; form menampilkan pesan dan tetap terbuka; startup menampilkan jendela error).
- Tes memeriksa nilai `PRAGMA busy_timeout` secara langsung, bukan mengukur lamanya menunggu, karena tes yang bergantung pada jam rapuh di CI.

## Analitik: kolom tanggal dan nilai kosong (#61)

Modul `src/ctrlcoco/analytics.py` (tanpa Qt) menjadi dasar jendela Ringkasan. Semua fungsinya menerima rentang `awal` dan `akhir` bertipe `date`, keduanya inklusif, dengan SQL berparameter (`?`).

- **Completion rate per area** menyaring task menurut tanggal `created_at`. Alasannya, penyebutnya memuat semua task (termasuk `todo`), dan hanya `created_at` yang selalu terisi. `deadline` boleh kosong dan `completed_at` hanya ada pada task `done`.
- Hasilnya `selesai / total`, angka 0 sampai 1 (bukan persen). Bila `total` 0, nilainya `None`, bukan 0, supaya "tidak ada task" tidak terbaca "0% selesai".
- Semua area dikembalikan, termasuk yang tanpa task di rentang (`rate = None`). Menyaringnya adalah urusan tampilan.
- Rentang terbalik (`awal > akhir`) tidak menjadi galat; hasilnya sama dengan rentang tanpa task.

## Analitik: on-time rate (#62)

- Pembilang: task `done` dengan `completed_at <= deadline` (selesai tepat pada deadline dihitung tepat waktu). Penyebut: task `done` yang punya deadline. Task tanpa deadline dan task `todo` tidak dihitung di keduanya.
- Rentang disaring menurut tanggal `completed_at` (inklusif), karena hanya task `done` yang dihitung dan kolom itu yang menunjukkan kapan task selesai.
- Satu angka gabungan semua area, 0 sampai 1. Bila penyebut 0, nilainya `None`, bukan 0, supaya "tidak ada data" tidak terbaca "semua terlambat".

## Analitik: streak terpanjang (#63)

- `longest_streak(conn, awal, akhir)` mengembalikan deretan hari valid berturut-turut terpanjang di dalam rentang (inklusif); 0 bila tidak ada hari valid. Beda dari `get_streak`, yang hanya menghitung streak yang sedang berjalan.
- Definisi hari valid satu sumber: konstanta `KONDISI_HARI_VALID` di `streak.py`, dipakai oleh `get_streak` dan `longest_streak`. `mood.py` dan `widget.py` tidak diubah; keduanya membaca satu baris log, bukan menyaring lewat SQL.
- Deretan yang melewati batas rentang hanya dihitung bagian di dalamnya.

## Jendela Ringkasan: rentang, data kosong, dan satu jendela (#64)

- **Rentang tetap** 12 minggu: 84 hari berakhir hari ini (inklusif). `rentang_ringkasan(today)` di `analytics.py` yang menghitungnya; jendela hanya menampilkannya sebagai label. Penyelarasan ke hari Senin untuk heatmap diputuskan di #65.
- **Ada data** berarti minimal satu baris di `task` atau `daily_log`, di seluruh database (bukan hanya di rentang). Area tanpa task belum dihitung. Log apa pun dihitung, termasuk yang bukan hari valid, dan kolom tanggal tidak diperiksa, jadi task tanpa deadline atau `completed_at` tetap terhitung. Bila tidak ada data, jendela menampilkan pesan "Belum ada data", bukan grafik kosong.
- **Satu jendela, tidak modal.** Coco tetap bisa diklik saat Ringkasan terbuka. Jika Ringkasan sudah terbuka dan dipilih lagi dari menu, jendela lama dibawa ke depan, tidak dibuat ganda. Jendela dihapus dari memori setelah ditutup, seperti form lain.
- Modul tampilan (`ringkasan.py`) tidak berisi SQL maupun hitungan metrik; semuanya lewat `analytics.py`.

## Heatmap kalender hari valid (#65)

- `hari_valid(conn, awal, akhir)` di `analytics.py` mengembalikan hari valid dalam rentang (inklusif), urut naik. Kuerinya memakai konstanta SQL yang sama dengan `longest_streak`, jadi aturan hari valid (`KONDISI_HARI_VALID`) tetap satu sumber.
- **Rentang tetap 84 hari** (keputusan #64 tidak diubah). Grid 7 baris (Senin sampai Minggu) kali 13 kolom; sel sebelum awal rentang dan sesudah hari ini dikosongkan, bukan digambar. Menjaga rentang tetap 84 hari lebih sederhana daripada memajukan awal ke hari Senin, yang membuat panjang rentang berubah antara 78 dan 84 hari.
- Heatmap dibuat dari `QLabel` kecil di `QGridLayout` (tanpa pustaka grafik, jadi ukuran .exe tidak bertambah). Tiap sel membawa properti `valid`, sehingga tes membaca sel yang ditandai tanpa membandingkan piksel.
- Warna: hari valid hijau `#3fa34d` (sama dengan warna lompat Coco), hari dalam rentang tanpa log valid abu terang. Belum ada label hari atau bulan di tepi grid.
- Bila database kosong, heatmap dan angka streak disembunyikan; yang tampil hanya pesan "Belum ada data". Bila database hanya punya task, heatmap tampil tanpa sel ditandai dan streak terpanjang 0.
