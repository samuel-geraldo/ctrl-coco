# CtrlCoco

[![tests](https://github.com/samuel-geraldo/ctrl-coco/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/samuel-geraldo/ctrl-coco/actions/workflows/tests.yml)

*Ctrl your day, with Coco.*

CtrlCoco adalah widget desktop pribadi dengan karakter Coco, anjing saya, untuk memantau task, deadline, dan streak harian. Coco berubah ekspresi sesuai kondisi hari itu, jadi status pekerjaan terlihat sekilas tanpa membuka aplikasi lain.

**Status:** work in progress (Tahap 4b: mesin animasi dengan sprite sementara)

## Cara menjalankan

Butuh Python 3.10 atau lebih baru. Dari folder proyek (perintahnya sama di PowerShell dan CMD):

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest
```

Kode ada di `src/ctrlcoco/`, tes di `tests/`. File database (`*.db`) dibuat otomatis dan tidak ikut Git.

## Menjalankan widget

PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m ctrlcoco
```

CMD:

```bat
set PYTHONPATH=src
python -m ctrlcoco
```

Klik kiri dan seret untuk menggeser, klik kanan lalu "Keluar" untuk menutup.

Gambar Coco mengikuti kondisi saat itu: `waspada`, `senang`, atau `tidur` (aturannya di `docs/keputusan.md`). Frame animasi dibaca dari `assets/sprites/<kondisi>_<n>.png`, misalnya `senang_1.png` dan `senang_2.png`, lalu ditampilkan bergantian menurut nomornya. Kondisi yang belum punya file sprite memakai gambar sementara: lingkaran merah-oranye (waspada), kuning (senang), atau biru keabu-abuan (tidur). Data dibaca ulang dari database tiap 60 detik.

## Lokasi data dan data contoh

Database harian disimpan di `%APPDATA%\CtrlCoco\ctrlcoco.db` (folder dibuat otomatis), jadi tidak bergantung pada folder tempat widget dijalankan.

Untuk mencoba widget dengan data contoh (kuliah, portofolio) tanpa menyentuh database harian.

PowerShell:

```powershell
$env:PYTHONPATH = "src"
python scripts/seed_demo.py
python -m ctrlcoco --db "$env:APPDATA\CtrlCoco\demo.db"
```

CMD:

```bat
set PYTHONPATH=src
python scripts/seed_demo.py
python -m ctrlcoco --db "%APPDATA%\CtrlCoco\demo.db"
```
