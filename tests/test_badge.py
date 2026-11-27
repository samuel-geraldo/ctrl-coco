"""Tes badge cakupan (#126): pembuat SVG, job di CI, dan tautan di README."""
import importlib.util
import re
from pathlib import Path
from xml.etree import ElementTree

import pytest

REPO = Path(__file__).resolve().parents[1]
SVG = "{http://www.w3.org/2000/svg}"
URL_BADGE = "https://raw.githubusercontent.com/samuel-geraldo/ctrl-coco/badges/cakupan.svg"


def _muat():
    path = REPO / "scripts" / "badge_cakupan.py"
    spec = importlib.util.spec_from_file_location("badge_cakupan", path)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def teks_di(svg):
    akar = ElementTree.fromstring(svg)
    assert akar.tag == f"{SVG}svg"
    return [t.text for t in akar.iter(f"{SVG}text")]


@pytest.mark.parametrize("persen", [0, 7, 99, 100])
def test_svg_memuat_label_dan_angka(persen):
    svg = _muat().buat_svg(persen)
    assert teks_di(svg) == ["cakupan", f"{persen}%"]
    assert ElementTree.fromstring(svg).get("aria-label") == f"cakupan {persen}%"


def test_svg_tidak_memuat_tautan_ke_luar():
    svg = _muat().buat_svg(99)
    assert re.findall(r"https?://[^\"'<> ]+", svg) == ["http://www.w3.org/2000/svg"]


@pytest.mark.parametrize("persen", [-1, 101])
def test_angka_di_luar_0_sampai_100_ditolak(persen):
    with pytest.raises(ValueError):
        _muat().buat_svg(persen)


def test_main_menulis_berkas(tmp_path):
    badge = _muat()
    tujuan = tmp_path / "cakupan.svg"
    assert badge.main(["99", str(tujuan)]) == 0
    assert tujuan.read_text(encoding="utf-8") == badge.buat_svg(99)


@pytest.mark.parametrize("teks", ["", "99%", "banyak"])
def test_main_menolak_angka_yang_tidak_terbaca_tanpa_menulis(tmp_path, teks):
    tujuan = tmp_path / "cakupan.svg"
    with pytest.raises(SystemExit):
        _muat().main([teks, str(tujuan)])
    assert not tujuan.exists()


# --- workflow tests.yml ---

def workflow():
    return (REPO / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")


def job(nama):
    cocok = re.search(
        rf"^  {nama}:$(.*?)(?=^  \S|\Z)", workflow(), re.MULTILINE | re.DOTALL
    )
    assert cocok, f"job {nama!r} tidak ada"
    return cocok.group(1)


def test_job_pytest_meneruskan_angka_total():
    isi = job("pytest")
    assert "coverage report --format=total" in isi
    assert "total: ${{ steps.cakupan.outputs.total }}" in isi


def test_job_badge_hanya_sesudah_tes_lulus_pada_push_ke_main():
    isi = job("badge")
    assert "needs: pytest" in isi
    assert "if: github.event_name == 'push' && github.ref == 'refs/heads/main'" in isi
    assert "needs.pytest.outputs.total" in isi
    assert "scripts/badge_cakupan.py" in isi


def test_izin_tulis_hanya_di_job_badge():
    assert re.search(r"^permissions:\n  contents: read$", workflow(), re.MULTILINE)
    assert workflow().count("contents: write") == 1
    assert "contents: write" in job("badge")


def test_badge_disimpan_di_branch_badges_oleh_bot_tanpa_layanan_luar():
    isi = job("badge")
    assert 'git config user.name "github-actions[bot]"' in isi
    assert re.search(r"git push --force .*\bbadges$", isi, re.MULTILINE)
    semua = workflow().lower()
    assert "codecov" not in semua and "coveralls" not in semua and "shields.io" not in semua


# --- README ---

def test_readme_menampilkan_badge_dari_branch_badges():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert re.search(rf'<img src="{re.escape(URL_BADGE)}" alt="cakupan tes">', readme)
