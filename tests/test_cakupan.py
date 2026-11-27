"""Penjaga laporan cakupan tes (#68): versi terkunci, perintah di CI, dan cara cek lokal."""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PERINTAH = "pytest --cov=ctrlcoco --cov-report=term-missing"


def baca(nama):
    return (REPO / nama).read_text(encoding="utf-8")


def test_pytest_cov_terkunci_di_requirements():
    baris = baca("requirements.txt").splitlines()
    assert any(re.fullmatch(r"pytest-cov==\d+\.\d+\.\d+", b) for b in baris)


def test_ci_menjalankan_pytest_dengan_cakupan():
    workflow = baca(".github/workflows/tests.yml")
    assert re.search(rf"^\s*- run: {re.escape(PERINTAH)}$", workflow, re.MULTILINE)


def test_readme_memuat_cara_cek_cakupan_lokal():
    bagian = re.search(
        r"^## Cara build dan tes$(.*?)(?=^## )", baca("README.md"), re.MULTILINE | re.DOTALL
    )
    assert bagian
    assert f"python -m {PERINTAH}" in bagian.group(1)
