# CtrlCoco

*Ctrl your day, with Coco.*

CtrlCoco adalah widget desktop pribadi dengan karakter Coco, anjing saya, untuk memantau task, deadline, dan streak harian. Coco berubah ekspresi sesuai kondisi hari itu, jadi status pekerjaan terlihat sekilas tanpa membuka aplikasi lain.

**Status:** work in progress (Tahap 3b: widget dilengkapi)

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

Klik kiri dan seret untuk menggeser, klik kanan lalu "Keluar" untuk menutup. Taruh foto Coco di `assets/coco.png` (opsional); tanpa itu widget menampilkan tulisan "Coco".

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
