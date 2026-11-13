# CtrlCoco: user story

Format: "Sebagai pengguna, saya ingin ..., supaya ...", diikuti kriteria selesai.

## Tahap 2: Inti data

1. Sebagai pengguna, saya ingin database dan tabel dibuat otomatis saat aplikasi pertama kali jalan, supaya saya tidak perlu menyiapkannya sendiri.
   - File database dibuat jika belum ada, berisi tabel `area`, `task`, `daily_log` sesuai `docs/erd.md`.
   - File database tidak ikut ter-commit (sudah diabaikan `.gitignore`).

2. Sebagai pengguna, saya ingin menambah dan melihat area, supaya task bisa dikelompokkan.
   - Bisa menambah area dengan nama unik; nama yang sama ditolak.

3. Sebagai pengguna, saya ingin menambah task dengan area dan deadline, lalu menandainya selesai, supaya saya tahu apa yang masih harus dikerjakan.
   - Task wajib punya area; deadline boleh kosong.
   - Menandai selesai mengubah `status` jadi `done` dan mengisi `completed_at`.

4. Sebagai pengguna, saya ingin mencatat log harian (Claude Code dan GitHub), supaya streak bisa dihitung.
   - Satu tanggal hanya satu baris; mengisi ulang tanggal yang sama memperbarui baris itu.

5. Sebagai pengguna, saya ingin melihat angka streak saya, supaya saya tahu konsistensi saya.
   - Streak dihitung dari `daily_log` sesuai aturan di `docs/erd.md`, dan diuji dengan beberapa contoh tanggal (berturut-turut, ada yang bolong, hari ini belum diisi).

## Tahap 3: Widget kosong

6. Sebagai pengguna, saya ingin widget kecil muncul di desktop, supaya status hari ini terlihat tanpa membuka aplikasi lain.
   - Jendela kecil tanpa bingkai, bisa digeser, selalu di atas jendela lain.
   - Menampilkan gambar Coco statis, angka streak, dan task dengan deadline terdekat.

## Tahap 4: Animasi

7. Sebagai pengguna, saya ingin ekspresi Coco berubah sesuai kondisi, supaya saya langsung tahu keadaan hari ini.
   - Senang: hari ini valid (Claude Code dan GitHub tercatat).
   - Waspada: ada task `todo` dengan deadline kurang dari 24 jam lagi.
   - Tidur: belum ada log hari ini.
   - Urutan prioritas jika lebih dari satu kondisi berlaku diputuskan di awal Tahap 4.

## Tahap 5: Input cepat

8. Sebagai pengguna, saya ingin menambah task langsung dari widget, supaya mencatat pekerjaan baru tidak memutus fokus.
   - Form singkat: judul, area, deadline (opsional); task langsung tersimpan.

9. Sebagai pengguna, saya ingin mencentang Claude Code dan GitHub hari ini dari widget, supaya log harian cepat diisi.
   - Dua centang di widget langsung memperbarui `daily_log` hari ini, dan ekspresi Coco ikut berubah.
