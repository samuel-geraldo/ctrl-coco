"""Penjaga lisensi (#87): kode MIT murni; nama, logo, dan karakter Coco dikecualikan."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PEMEGANG = "Copyright (c) 2026 Samuel Geraldo Tobia Lumika"


def baca(*bagian):
    return REPO.joinpath(*bagian).read_text(encoding="utf-8")


def test_license_adalah_teks_mit_murni_dengan_tahun_dan_nama():
    isi = baca("LICENSE")
    assert isi.startswith("MIT License\n")
    assert PEMEGANG in isi
    assert "Permission is hereby granted, free of charge" in isi
    assert 'THE SOFTWARE IS PROVIDED "AS IS"' in isi


def test_license_tanpa_tambahan_di_luar_teks_mit():
    # GitHub hanya mengenali MIT bila teksnya murni; catatan pengecualian ada di berkas lain.
    isi = baca("LICENSE").lower()
    for kata in ("logo", "maskot", "sprite", "ctrlcoco", "coco"):
        assert kata not in isi


def test_lisensi_aset_menyebut_pengecualian():
    isi = baca("assets", "LICENSE-ASSETS.md")
    for hal in ("CtrlCoco", "logo", "karakter Coco", "sprite"):
        assert hal in isi
    assert "tanpa izin" in isi


def test_readme_punya_bagian_lisensi_yang_menautkan_kedua_berkas():
    readme = baca("README.md")
    assert "## Lisensi" in readme
    bagian = readme.split("## Lisensi", 1)[1].split("\n## ", 1)[0]
    assert "(LICENSE)" in bagian
    assert "(assets/LICENSE-ASSETS.md)" in bagian
    for hal in ("CtrlCoco", "assets/logo", "assets/sprites"):
        assert hal in bagian
