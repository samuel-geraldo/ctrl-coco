# CtrlCoco

*Ctrl your day, with Coco.*

CtrlCoco adalah widget desktop pribadi dengan karakter Coco, anjing saya, untuk memantau task, deadline, dan streak harian. Coco berubah ekspresi sesuai kondisi hari itu, jadi status pekerjaan terlihat sekilas tanpa membuka aplikasi lain.

**Status:** work in progress (Tahap 2: inti data, belum ada tampilan)

## Cara menjalankan

Butuh Python 3.10 atau lebih baru. Dari folder proyek (PowerShell):

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest
```

Kode ada di `src/ctrlcoco/`, tes di `tests/`. File database (`*.db`) dibuat otomatis dan tidak ikut Git.
