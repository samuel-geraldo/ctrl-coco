# Panduan sprite Coco

Panduan ini berisi aturan menggambar sprite Coco supaya semua kondisi konsisten dan terbaca oleh widget. Sprite digambar di [Piskel](https://www.piskelapp.com/).

## Ringkasan aturan

| Hal | Aturan |
|---|---|
| Ukuran | 64×64 piksel |
| Format | PNG dengan latar transparan |
| Folder | `assets/sprites/` |
| Nama berkas | `<kondisi>_<n>.png`, huruf kecil, nomor mulai dari 1 |
| Berkas sumber | `<kondisi>.piskel` di folder yang sama |
| Tampilan di widget | diperbesar 3× menjadi 192×192, tanpa penghalusan |

## Ukuran dan format

- Kanvas **64×64 piksel**. Semua frame berukuran sama.
- Simpan sebagai **PNG** dengan **latar transparan**: bagian di luar badan Coco dibiarkan kosong, jangan diberi warna latar. Widget punya latar tembus pandang, jadi warna latar akan terlihat sebagai kotak di desktop.
- Widget memperbesar gambar **3×** (64 → 192 piksel) dengan cara *nearest neighbor*: setiap piksel menjadi kotak 3×3 yang tajam, tidak buram. Karena perbesarannya bilangan bulat, semua piksel tampil sama besar.

## Nama berkas dan folder

Widget (`src/ctrlcoco/sprites.py`) membaca frame dari folder `assets/sprites/` dengan pola `<kondisi>_<n>.png`. Frame diurutkan menurut nomornya.

- Pakai huruf kecil: `senang_1.png`, bukan `Senang_1.PNG`.
- Nomor mulai dari 1 dan berurutan tanpa loncat: `senang_1.png`, `senang_2.png`. Jangan `senang_0.png` atau `senang_01.png`.
- Berkas sumber Piskel disimpan di folder yang sama dengan nama `<kondisi>.piskel`, misalnya `senang.piskel`. Widget hanya membaca berkas `.png`, jadi berkas `.piskel` tidak mengganggu.
- Jangan menaruh berkas lain di folder ini. Tes `tests/test_aset_sprite.py` memeriksa nama, ukuran, dan latar setiap berkas.

Contoh isi folder:

```text
assets/sprites/
  senang_1.png
  senang_2.png
  senang.piskel
  waspada_1.png
  waspada_2.png
  waspada.piskel
  tidur_1.png
  tidur_2.png
  tidur.piskel
  lompat_1.png
  lompat_2.png
  lompat_3.png
  lompat.piskel
```

Kondisi yang belum punya berkas memakai gambar sementara (lingkaran berwarna), jadi sprite boleh ditambahkan satu kondisi demi satu kondisi.

## Jumlah frame per kondisi

| Kondisi | Jumlah frame | Berkas | Kapan tampil |
|---|---|---|---|
| `senang` | 2 | `senang_1.png`, `senang_2.png` | log hari ini lengkap |
| `waspada` | 2 | `waspada_1.png`, `waspada_2.png` | ada deadline kurang dari 24 jam atau sudah lewat |
| `tidur` | 2 | `tidur_1.png`, `tidur_2.png` | selain itu |
| `lompat` | 3 | `lompat_1.png` sampai `lompat_3.png` | perayaan (#93) |

- Dua frame cukup untuk gerak sederhana, misalnya berkedip atau bernapas. Frame 2 sebaiknya hanya sedikit berbeda dari frame 1, supaya gerakannya halus.
- `senang` boleh ditambah sampai 4 frame nanti. Bila jumlahnya diubah, perbarui tabel ini dan tes jumlah frame di #71.
- Frame `lompat` baru dipakai setelah perayaan (#93) selesai dibuat; sebelum itu widget belum membacanya.

## Kecepatan animasi

- Biasa: frame berganti setiap **500 ms**. Dengan 2 frame, satu putaran animasi = 1 detik.
- Saat Coco diklik (reaksi): frame kondisi yang sama diputar lebih cepat, setiap **120 ms**, selama 1 detik.

Gambarlah dengan kecepatan ini dalam pikiran: di Piskel, atur pratinjau ke 2 FPS (frame per detik) untuk melihat kecepatan biasa.

## Palet warna Coco

Warna diambil dari logo Coco (`assets/logo.svg`), yang juga pixel art. Pakai warna dari daftar ini supaya sprite cocok dengan logo. Angka di kolom terakhir menunjukkan seberapa sering warna itu muncul di logo.

| Kelompok | Kode hex | Jumlah di logo |
|---|---|---|
| Gelap (garis) | `#2a1a10` | 9 |
| Gelap (garis) | `#4a3220` | 79 |
| Gelap | `#76491a` | 15 |
| Gelap | `#8a5a20` | 40 |
| Cokelat | `#a8702a` | 26 |
| Cokelat | `#b97d2e` | 43 |
| Cokelat | `#b9822f` | 3 |
| Cokelat | `#d1923a` | 99 |
| Cokelat | `#e3a448` | 83 |
| Terang | `#f4c26c` | 21 |
| Terang | `#e3c88e` | 18 |
| Terang | `#f3dcaa` | 31 |
| Terang | `#faebc6` | 11 |
| Kuning | `#ffb703` | 5 |
| Kuning | `#ffd23f` | 8 |
| Kuning | `#fff3b0` | 1 |
| Abu-abu | `#7b8794` | 14 |
| Abu-abu | `#dfe6ee` | 17 |

Tips di Piskel: buka panel palet, buat palet baru, lalu masukkan kode hex di atas satu per satu.

## Langkah menggambar di Piskel

1. Buka [piskelapp.com](https://www.piskelapp.com/) dan pilih **Create Sprite**.
2. Buka panel **Resize** di sisi kanan, ubah ukuran kanvas menjadi **64 × 64**, lalu terapkan.
3. Gambar frame pertama. Biarkan latar kosong (transparan); jangan memakai alat isi warna pada latar.
4. Tambah frame berikutnya lewat **Add new frame**, atau gandakan frame pertama (**Duplicate**) lalu ubah sedikit.
5. Periksa gerakan di jendela pratinjau (kanan atas) dengan kecepatan 2 FPS.
6. Simpan berkas sumber: buka panel **Save** dan simpan sebagai berkas `.piskel` di komputer. Beri nama sesuai kondisinya, misalnya `senang.piskel`.
7. Ekspor PNG per frame: buka panel **Export**, pilih ekspor ke **ZIP** (setiap frame menjadi satu PNG), dengan skala **1×** supaya ukurannya tetap 64×64.
8. Buka berkas ZIP, lalu ganti nama setiap PNG sesuai pola: `senang_1.png`, `senang_2.png`, dan seterusnya, menurut urutan frame. Nama bawaan dari Piskel bisa berbeda (misalnya mulai dari 0), jadi selalu ganti namanya.
9. Salin PNG dan berkas `.piskel` ke folder `assets/sprites/`.

## Cara mencoba di laptop pribadi

Coba sprite dengan database contoh (`demo.db`), bukan database harian.

1. Pastikan berkas sudah ada di `assets/sprites/` sesuai aturan di atas.
2. Periksa aturan dengan tes:

   ```bat
   python -m pytest tests/test_aset_sprite.py
   ```

3. Bila `demo.db` belum ada, buat dulu:

   ```bat
   set PYTHONPATH=src
   python scripts/seed_demo.py
   ```

4. Buka widget dengan database contoh:

   ```bat
   set PYTHONPATH=src
   python -m ctrlcoco --db "%APPDATA%\CtrlCoco\demo.db"
   ```

5. Lihat tiap kondisi:
   - `tidur`: tampil bila log hari ini belum lengkap.
   - `senang`: klik dua kali Coco, centang kedua kotak, lalu simpan.
   - `waspada`: klik kanan → **Tambah task…**, pilih **Hari ini 23:59**, lalu simpan.
6. Periksa: latar tembus pandang (tidak ada kotak), tepi piksel tajam, ukuran piksel rata, dan gerakan terlihat wajar. Klik Coco sekali untuk melihat animasi reaksi yang cepat.
7. Widget memuat sprite sekali saat dibuka. Setelah mengganti gambar, tutup widget (klik kanan → **Keluar**) lalu buka lagi.

## Lisensi aset

- Sprite Coco digambar sendiri di Piskel. Jangan menyalin atau menjiplak gambar dari sumber lain, supaya asal-usul dan lisensinya jelas.
- Kode CtrlCoco akan berlisensi MIT, tetapi nama CtrlCoco, logo, dan karakter Coco beserta sprite-nya (`assets/sprites/`) **tidak** termasuk lisensi itu dan tidak boleh dipakai ulang tanpa izin. Rinciannya diatur di issue #87 (berkas `LICENSE` dan `assets/LICENSE-ASSETS.md`).
