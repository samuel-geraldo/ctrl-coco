"""Penjaga koneksi database (#127): test_db.py harus menutup setiap koneksi yang dibukanya."""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_test_db_tidak_meninggalkan_koneksi_terbuka():
    # Proses terpisah, karena peringatan baru muncul saat Python membersihkan koneksi,
    # sering kali di tes lain. Tanpa -W, Python mengabaikan ResourceWarning.
    perintah = [
        sys.executable, "-m", "pytest", "tests/test_db.py", "-q",
        "-p", "no:cacheprovider", "-W", "default::ResourceWarning",
    ]
    hasil = subprocess.run(perintah, cwd=REPO, capture_output=True, text=True, errors="replace")
    assert hasil.returncode == 0, hasil.stdout + hasil.stderr
    jumlah = (hasil.stdout + hasil.stderr).count("unclosed database")
    assert jumlah == 0, f"{jumlah} peringatan 'unclosed database' dari tests/test_db.py"
