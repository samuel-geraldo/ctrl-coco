"""Penjaga berkas build .exe (#75): yang bisa dicek tanpa membangun .exe sungguhan."""
import subprocess
from pathlib import Path

from ctrlcoco import aset

REPO = Path(__file__).resolve().parents[1]
SPEC = REPO / "packaging" / "ctrlcoco.spec"


def test_berkas_build_ada_di_repo():
    assert SPEC.is_file()
    assert (REPO / "packaging" / "entry.py").is_file()
    assert (REPO / "requirements-build.txt").is_file()


def test_spec_tidak_diabaikan_git():
    # .gitignore mengabaikan *.spec; spec ini harus punya pengecualian, atau tidak ikut commit.
    hasil = subprocess.run(
        ["git", "check-ignore", "--quiet", str(SPEC)], cwd=REPO, capture_output=True
    )
    assert hasil.returncode == 1  # 1 = tidak diabaikan


def test_spec_menaruh_assets_di_tempat_yang_dicari_folder_aset():
    # aset.folder_aset() mencari <paket>/assets; spec harus menaruh folder itu di sana.
    isi = SPEC.read_text(encoding="utf-8")
    assert f'"{aset.folder_aset().name}")]' in isi  # datas=[(<sumber>, "assets")]


def test_dependensi_build_memakai_versi_terkunci_dan_tidak_masuk_requirements_utama():
    build = (REPO / "requirements-build.txt").read_text(encoding="utf-8")
    utama = (REPO / "requirements.txt").read_text(encoding="utf-8")
    assert "pyinstaller==" in build
    assert "-r requirements.txt" in build
    assert "pyinstaller" not in utama.lower()  # CI tes tidak perlu memasangnya
