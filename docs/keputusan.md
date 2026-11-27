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

## Grafik completion rate per area dan on-time rate (#66)

- Tidak ada fungsi analitik baru: grafik memakai `completion_rate_per_area` (#61) dan teks on-time memakai `on_time_rate` (#62), keduanya dengan rentang 84 hari yang sama dengan heatmap.
- Satu baris per area, urutan sama dengan hasil fungsi analitik: nama, batang, dan teks "67% (2/3)". Batang adalah `QLabel` dengan lebar sebanding `rate` (tanpa pustaka grafik, jadi ukuran .exe tidak bertambah). Tiap batang membawa properti `rate` dan `kosong`, supaya tes membaca nilainya tanpa membandingkan piksel.
- **Penyebut nol dibedakan dari 0%.** Area tanpa task di rentang (`rate = None`) tidak punya batang dan teksnya abu "belum ada task". Area yang punya task tapi belum ada yang selesai tampil "0% (0/N)" dengan batang kosong. Hal yang sama untuk on-time rate: tanpa task selesai berdeadline, teksnya "belum ada task selesai dengan deadline", bukan 0%.
- Persen ditampilkan bulat, setengah dibulatkan ke atas (12,5 menjadi 13), dan selalu ditemani "(selesai/total)" supaya angka aslinya terlihat.
- Belum ada scroll: jendela memanjang mengikuti jumlah area. Cukup untuk v0.1.0; ditinjau lagi bila area banyak.
- Bila database kosong, grafik dan on-time disembunyikan; yang tampil hanya "Belum ada data".

## Analitik: median waktu penyelesaian per area (#81)

- `median_penyelesaian_per_area(conn, awal, akhir)` di `analytics.py` mengembalikan median waktu dari `created_at` sampai `completed_at` tiap area, hanya task `done`.
- **Satuan: jam** (pecahan). Di Ringkasan ditampilkan satu angka di belakang koma, misalnya "62,0 jam".
- **Median dihitung di Python** (`statistics.median`) dari hasil SQL, karena SQLite tidak punya fungsi median bawaan dan versi fungsi jendela lebih panjang untuk dibaca. Untuk jumlah genap, hasilnya rata-rata dua nilai tengah.
- Task masuk rentang menurut tanggal `completed_at` (inklusif), sama dengan on-time rate.
- Area tanpa task selesai di rentang bernilai `None`, bukan 0, dan tampil "belum ada task selesai". Bila database kosong, teks median disembunyikan.

## Analitik: produktivitas per hari dalam seminggu (#82)

- `produktivitas_per_hari(conn, awal, akhir)` di `analytics.py` mengembalikan selalu 7 baris, Senin sampai Minggu, berisi jumlah task selesai dan jumlah hari valid. Hari tanpa data bernilai 0.
- Task dihitung menurut tanggal `completed_at` (inklusif). `strftime('%w')` di SQLite memberi 0 untuk Minggu, jadi angkanya digeser `(w + 6) % 7` supaya 0 berarti Senin.
- Hari valid diambil dari `hari_valid`, jadi aturannya tetap satu sumber.
- Di Ringkasan tampil sebagai teks tujuh baris, misalnya "Senin: 3 task selesai, 2 hari valid". Bila database kosong, teksnya disembunyikan.

## Batalkan status selesai (#55)

- `batalkan_selesai(conn, task_id)` di `data.py` mengubah task `done` menjadi `todo` dan mengosongkan `completed_at` dalam satu transaksi. Task `todo` dibiarkan; id yang tidak ada menghasilkan `ValueError`.
- Jalan masuknya menu **Batalkan selesai…**, dengan form terpisah (`form_batalkan.py`). Daftar diurutkan dari yang terakhir diselesaikan, karena salah klik biasanya baru terjadi.
- Tombol utamanya "Kembalikan", supaya tidak tertukar dengan tombol "Batal".
- Tidak ada perayaan dan tidak ada riwayat perubahan status.

## Ekspor CSV (#43)

- `ekspor_csv(conn, folder)` di `export.py` (tanpa Qt) menulis dua file bernama tetap ke folder yang dipilih: `task.csv` dan `daily_log.csv`. File lama dengan nama itu ditimpa.
- **Header `task.csv`:** `area, judul, tenggat, status, dibuat, selesai`. Kolom `area` berisi nama area (lewat `JOIN`), bukan `area_id`. Baris urut menurut id task.
- **Header `daily_log.csv`:** `tanggal, claude_code, github, catatan`. Baris urut menurut tanggal.
- **Header berbahasa Indonesia dan nilai diterjemahkan:** status `belum`/`selesai` (di database `todo`/`done`), centang `ya`/`tidak` (di database 1/0). Tujuannya supaya file langsung terbaca di spreadsheet tanpa kamus. Konsekuensinya, file ini bukan salinan mentah tabel dan belum bisa diimpor kembali (impor di luar cakupan).
- **Nilai kosong (`NULL`) menjadi sel kosong**, bukan teks "None".
- **UTF-8 dengan BOM** (`utf-8-sig`): Excel di Windows membaca file UTF-8 tanpa BOM sebagai ANSI, sehingga huruf non-ASCII rusak. `csv.DictReader` dengan `utf-8-sig` membuang BOM, jadi nama kolom pertama tidak tercemar. File ditulis dengan `newline=""` agar baris baru di dalam sel tidak rusak. Koma, kutip, dan baris baru di-escape oleh modul `csv`.
- **Menimpa: tanya dulu.** `file_yang_sudah_ada(folder)` menyebut file yang akan tertimpa; menu menampilkan pertanyaan dengan jawaban bawaan "Tidak". Folder tanpa file lama langsung ditulis tanpa bertanya.
- **Kegagalan:** hanya `OSError` (folder hilang, izin ditolak, disk penuh) yang ditangkap menu dan ditampilkan dengan lokasi serta penyebab; aplikasi tidak keluar. Error lain adalah bug dan dibiarkan terlihat. Tes memakai folder yang tidak ada untuk memicu `OSError`, karena folder tanpa izin tidak bisa disimulasikan andal di Windows; jalur kodenya sama.
- Dialog pilih folder memakai `QFileDialog` bawaan dan hanya memilih folder; nama file tetap, tidak ditanyakan.

## Lokasi folder aset untuk .exe (#74)

- `aset.py` punya satu fungsi lokasi: `folder_aset()` (dan `folder_sprite()` untuk `assets/sprites`). `sprites.py` dan `widget.py` memakainya; konstanta `SPRITE_DIR` yang dihitung dari `__file__` dihapus.
- **Mode .exe** dikenali dari `sys.frozen` bersama `sys._MEIPASS`, yang dipasang PyInstaller; lokasinya `<_MEIPASS>/assets`. Bila `frozen` ada tapi `_MEIPASS` tidak, dipakai lokasi sumber, bukan error. Build di #75 harus menaruh isi `assets/` di folder `assets` dalam paket, supaya lokasi ini cocok.
- **Dihitung setiap dipanggil, bukan saat impor**, dan `load_frames` serta `CocoWidget` menerima `sprite_dir=None` sebagai "pakai lokasi bawaan". Dengan begitu mode beku bisa disimulasikan di tes lewat `monkeypatch`; konstanta yang dihitung saat impor tidak ikut berubah.
- Tes mode beku memakai `monkeypatch` pada `sys.frozen` dan `sys._MEIPASS`; berjalan tidak benar-benar di dalam .exe. Pemeriksaan di .exe sungguhan (sprite dimuat dari paket) ada di #75.

## Build .exe dengan PyInstaller (#75)

- **Satu berkas (onefile), tanpa konsol.** `packaging/ctrlcoco.spec` menghasilkan `dist/CtrlCoco.exe`. Aplikasi ini jendela, dan kesalahan sudah ditampilkan lewat `QMessageBox`, jadi konsol tidak perlu. Onefile lebih lambat saat start (mengurai paket ke folder sementara) tetapi memenuhi kriteria "satu .exe" dan paling mudah dibagikan.
- **`assets/` ikut seluruhnya** dan mendarat di `<paket>/assets`, tempat `aset.folder_aset()` mencarinya (#74). Sprite yang ditambahkan nanti (#71-#73) otomatis ikut tanpa mengubah spec.
- **Titik masuk `packaging/entry.py`**, bukan `python -m ctrlcoco`: PyInstaller butuh skrip. Kodenya hanya memanggil `main()` yang sama, jadi perilaku .exe dan versi sumber sama, termasuk `default_db_path()`.
- **Dependensi build terpisah** di `requirements-build.txt` (PyInstaller terkunci versinya), supaya CI tes dan pengembang biasa tidak memasangnya.
- **Berkas `.spec` perlu pengecualian di `.gitignore`** (`!packaging/ctrlcoco.spec`), karena `*.spec` diabaikan secara umum. Tes menjaganya agar tidak hilang diam-diam.
- **Modul Qt yang tidak dipakai dikecualikan** (WebEngine, Pdf, Qml, Quick, 3D, Multimedia, Charts) agar ukuran tidak membengkak.
- **Belum ada ikon `.exe`.** Logo 608x688 tidak persegi; ikon yang layak butuh berkas `.ico` yang digambar tersendiri. Ditunda, bukan bagian kriteria #75.
- **Workflow `build-exe`** (runner Windows) membangun .exe, memastikan `dist/` hanya berisi `CtrlCoco.exe`, menjalankannya sepuluh detik dengan database sementara (harus tetap hidup dan membuat database), lalu mengunggahnya sebagai artifact. Dijalankan manual dan pada pull request yang menyentuh `src/`, `assets/`, atau `packaging/`. Pemeriksaan di Windows tanpa Python dan sprite yang dimuat dari paket tetap manual di laptop pribadi (kriteria #75); build ini belum membuktikannya.

## Susunan README dan peta jalan (#77)

- Urutan bagian mengikuti #77: ringkasan dan badge, Fitur, Privasi, Cara instal, FAQ, Cara build dan tes, lalu Lisensi. Bagian yang bukan pengguna akhir (Sprite, Struktur proyek, Pilihan desain, Alur kerja) dikumpulkan di "Untuk pengembang", sesudah Cara build dan tes.
- **Peta jalan diletakkan sebelum Lisensi**, sesudah "Untuk pengembang": pembaca yang hanya ingin memakai aplikasi sudah selesai sebelum sampai ke sana, dan rencana ke depan menutup README tepat di atas lisensi dan penulis.
- Peta jalan dibagi per milestone (v0.1.0 dan v0.2.0) dan ditulis per kelompok pekerjaan, bukan satu baris per issue, supaya tidak ikut usang tiap kali issue kecil selesai. Tahap 6 (tinjauan mingguan) pindah ke v0.2.0 sesuai milestone di GitHub; penanda "(opsional)" dihapus karena sudah diganti milestone.
- Kalimat Privasi memuat "semua data lokal, tanpa akun dan jaringan" persis, karena itu kriteria #77 dan dijaga tes.
- Tes `test_readme.py` menolak gambar yang berkas tujuannya belum ada. Tangkapan layar (#88) dan sprite asli (#71-#73) belum ada, jadi gambar itu baru ditambahkan bersama berkasnya, bukan lebih dulu.

## Isi log untuk tanggal selain hari ini (#56)

- **Tanggal masa depan ditolak, mundur paling jauh 30 hari** (hari ini - 30 masih boleh), bawaannya hari ini. Batasnya dipasang sebagai rentang `QDateEdit`, jadi nilai form tidak pernah keluar dari rentang. `set_daily_log` tidak ikut membatasi: aturan ini milik form, dan fungsi data tetap menerima tanggal apa pun yang formatnya benar (dipakai juga oleh data demo).
- **Mengganti tanggal memuat ulang isian** dari `get_daily_log`; perubahan yang belum disimpan dibuang tanpa konfirmasi. Isian dikosongkan lebih dulu, dan bila log gagal dibaca tombol Simpan dinonaktifkan, supaya isi tanggal lain tidak tertulis ke tanggal terpilih.
- **Judul jendela** "Log hari ini (tanggal)" untuk hari ini dan "Log tanggal (tanggal)" untuk hari lain. Label menu klik kanan tidak diubah.
- **Perayaan tidak berubah:** hanya log hari ini yang baru menjadi valid yang dirayakan. Mengisi tanggal lampau tidak membuat Coco melompat, walaupun streak melewati tonggak.

## Cakupan tes di CI (#68)

- **`pytest-cov` dikunci di `requirements.txt`**; `coverage`, dependensinya, tidak dikunci tersendiri.
- **CI menjalankan `pytest --cov=ctrlcoco --cov-report=term-missing`**, jadi persentase per berkas dan baris yang belum dites terlihat di log job. Tanpa Codecov atau layanan luar lain.
- **Tanpa ambang minimum:** cakupan tidak menggagalkan CI. Ambang bisa menyusul setelah angka awal diketahui.
- **Badge cakupan belum dikerjakan**, jadi #68 tetap terbuka. Badge buatan workflow sendiri butuh branch tambahan dan izin tulis untuk `GITHUB_TOKEN`; untuk sekarang itu tidak diambil.

## Tinjauan mingguan (#80)

- **Rentang:** 7 hari terakhir sampai hari ini, inklusif. Rentang lain di luar cakupan.
- **Terlambat:** deadline jatuh dalam rentang dan tidak dipenuhi, yaitu `done` dengan `completed_at > deadline`, atau `todo` dengan deadline lebih kecil dari waktu sekarang. Selesai tepat pada deadline dihitung tepat waktu, sama dengan on-time rate. Todo yang deadline-nya sama dengan menit sekarang belum terlambat (gelembung Coco sudah menyebutnya terlambat pada menit itu). Tunggakan dengan deadline sebelum rentang tidak dihitung, supaya semua angka task memakai rentang yang sama.
- **Streak:** `get_streak`, sama dengan gelembung Coco. Bisa lebih dari 7, jadi satu-satunya angka yang melihat data di luar rentang.
- **Catatan refleksi mingguan tidak dibuat:** tidak diminta kriteria selesai, dan menyimpannya butuh tabel baru serta migrasi skema. Catatan harian sudah ada.
- **Pesan kosong** hanya bila database belum punya task atau log (`ada_data`, sama dengan Ringkasan). Bila hanya 7 hari terakhir yang kosong, angka 0 ditampilkan.
- **Jendela** tidak modal dan hanya satu sekaligus, seperti Ringkasan (keduanya memakai `_buka_jendela_tunggal`). Angka dibaca saat jendela dibuka, tanpa refresh otomatis.
