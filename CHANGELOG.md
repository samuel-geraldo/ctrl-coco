# Changelog

Semua perubahan penting pada CtrlCoco dicatat di berkas ini. Formatnya mengikuti [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Belum ada versi yang dirilis, jadi semua perubahan masih di bagian **Unreleased**. Judul versi, tanggal, dan tautan perbandingan antarversi ditambahkan saat rilis.

## [Unreleased]

### Added

- Rancangan data (ERD) dan user story (#1, PR #2).
- Inti data: SQLite untuk area, task, dan log harian, serta hitungan streak (#3, PR #4).
- Widget tanpa bingkai yang selalu di atas, berlatar tembus pandang, menampilkan streak dan task terdekat (#5 dan #7, PR #6 dan #8).
- Lokasi database di folder AppData dan skrip data contoh (#7, PR #8).
- Kondisi Coco (waspada, senang, tidur) dan animasi dengan sprite sementara (#9 dan #17, PR #10 dan #18).
- Form dari menu klik kanan: tambah task, log harian, dan selesaikan task (#37 dan #38, PR #51 dan #52).
- Validasi format tanggal, nama area, dan judul task (#13 dan #39, PR #14 dan #50).
- Coco lebih hidup: gelembung bicara, reaksi saat diklik, momen perayaan, form di samping Coco, dan tombol deadline cepat (#91 sampai #95, PR #99 sampai #102 dan #104).
- Jendela Ringkasan: heatmap hari valid, streak terpanjang, completion rate per area, dan on-time rate (#61 sampai #66, PR #106 sampai #111).
- Median waktu penyelesaian per area dan produktivitas per hari dalam seminggu di Ringkasan (#81 dan #82, PR #121 dan #122).
- Jendela Tinjauan mingguan untuk 7 hari terakhir (#80, PR #128).
- Membatalkan status selesai pada task (#55, PR #123).
- Mengisi log untuk tanggal lampau, sampai 30 hari ke belakang (#56, PR #124).
- Ekspor task dan log harian ke CSV (#43, PR #112).
- Data contoh 60 hari (#79, PR #105).
- Build `CtrlCoco.exe` dengan PyInstaller sebagai artifact di GitHub Actions (#75, PR #114).
- Skrip tangkapan layar untuk README (#88, PR #117).
- Panduan menggambar sprite (#70, PR #103).
- Lisensi MIT untuk kode, dengan nama, logo, dan karakter Coco dikecualikan (#87, PR #115).
- Tes otomatis, lint ruff, dan laporan cakupan tes di CI (#15, #67, dan #68, PR #16, #97, dan #125).

### Changed

- Waktu tunggu kunci database menjadi 1 detik supaya widget tidak lama membeku (#47, PR #89).
- Versi dependensi dikunci dan akhir baris diseragamkan lewat `.gitattributes` (#69, PR #96).
- Ketiga form memakai satu kelas dasar (#57, PR #118).
- Statistik task selesai dibaca lewat view `v_task_selesai`; skema database naik ke versi 3 (#83, PR #119).
- README disusun ulang, dengan logo dan peta jalan per milestone (#32 dan #77, PR #33, #116, dan #120).

### Fixed

- Tulis yang gagal tidak lagi meninggalkan transaksi terbuka yang mengunci database (#19 dan #31, PR #27 dan #35).
- Format tanggal dijaga database, sehingga baris bertanggal salah tidak lagi membuat widget gagal dijalankan (#21, PR #34).
- Mengisi ulang log tanpa catatan tidak lagi menghapus catatan lama (#24, PR #29).
- Skrip data contoh tidak lagi menimpa log harian asli (#20, PR #28).
- Error database saat startup dan refresh ditangani dan ditampilkan (#22, PR #48).
- Pesan muncul bila folder data tidak bisa dibuat (#54, PR #60).
- Daftar di form Selesaikan task dimuat ulang bila task tidak ditemukan (#53, PR #59).
- Aset ditemukan dengan benar saat berjalan dari `.exe` (#74, PR #113).
- Koneksi database ditutup saat aplikasi keluar dan di dalam tes (#127, PR #129).

### Removed

- `assets/coco.png`, karena lisensinya tidak jelas (#23, PR #36).
