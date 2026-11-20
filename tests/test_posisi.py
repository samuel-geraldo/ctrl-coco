import ast
from pathlib import Path

import pytest

from ctrlcoco import posisi
from ctrlcoco.posisi import JARAK_FORM_PX, posisi_form

LAYAR = (0, 0, 1920, 1040)
LEBAR_COCO, TINGGI_COCO = 200, 260
FORM = (0, 0, 300, 400)  # hanya lebar dan tinggi yang dipakai


def coco(x, y):
    return (x, y, LEBAR_COCO, TINGGI_COCO)


def kotak_form(x, y, form=FORM):
    return (x, y, form[2], form[3])


def bertumpuk(a, b):
    """True bila dua persegi (x, y, lebar, tinggi) saling menimpa."""
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def di_dalam(dalam, luar):
    return (
        dalam[0] >= luar[0]
        and dalam[1] >= luar[1]
        and dalam[0] + dalam[2] <= luar[0] + luar[2]
        and dalam[1] + dalam[3] <= luar[1] + luar[3]
    )


def test_jarak_bawaan():
    assert JARAK_FORM_PX == 8


# --- kanan, lalu kiri ---

def test_coco_di_tengah_form_di_kanan():
    assert posisi_form(coco(800, 300), FORM, LAYAR) == (800 + 200 + 8, 300)


def test_coco_di_tepi_kanan_form_di_kiri():
    assert posisi_form(coco(1720, 300), FORM, LAYAR) == (1720 - 8 - 300, 300)


def test_coco_di_tepi_kiri_form_di_kanan():
    assert posisi_form(coco(0, 300), FORM, LAYAR) == (208, 300)


def test_ruang_kanan_pas_selebar_form_tetap_di_kanan():
    # Kanan Coco 1612, + jarak 8 = 1620, + lebar form 300 = 1920 (tepi layar).
    assert posisi_form(coco(1412, 300), FORM, LAYAR) == (1620, 300)


def test_ruang_kanan_kurang_1_px_pindah_ke_kiri():
    assert posisi_form(coco(1413, 300), FORM, LAYAR) == (1413 - 8 - 300, 300)


def test_jarak_bisa_diganti():
    assert posisi_form(coco(800, 300), FORM, LAYAR, jarak=20) == (1020, 300)


# --- vertikal ---

def test_coco_di_dekat_tepi_bawah_form_digeser_naik():
    assert posisi_form(coco(800, 900), FORM, LAYAR) == (1008, 1040 - 400)


def test_coco_melewati_tepi_atas_form_di_atas_layar():
    assert posisi_form(coco(800, -50), FORM, LAYAR) == (1008, 0)


# --- kanan dan kiri sama-sama tidak muat ---

def test_dua_sisi_tidak_muat_ruang_kiri_lebih_besar():
    layar = (0, 0, 600, 1040)
    # Ruang kanan 600 - 450 - 8 = 142, ruang kiri 250 - 8 = 242: pilih kiri, lalu dijepit.
    x, y = posisi_form(coco(250, 300), FORM, layar)
    assert (x, y) == (0, 300)
    assert di_dalam(kotak_form(x, y), layar)


def test_dua_sisi_tidak_muat_ruang_sama_pilih_kanan():
    layar = (0, 0, 700, 1040)
    # Ruang kanan 700 - 450 - 8 = 242, ruang kiri 250 - 8 = 242: kanan, lalu dijepit.
    x, y = posisi_form(coco(250, 300), FORM, layar)
    assert (x, y) == (700 - 300, 300)
    assert di_dalam(kotak_form(x, y), layar)


def test_layar_lebih_kecil_dari_form_form_di_pojok_kiri_atas():
    layar = (0, 0, 250, 300)
    assert posisi_form((20, 20, 100, 100), FORM, layar) == (0, 0)


# --- monitor kedua ---

def test_monitor_kedua_di_kanan():
    layar = (1920, 0, 1280, 1000)
    x, y = posisi_form(coco(3200 - 200, 100), FORM, layar)
    assert (x, y) == (3000 - 8 - 300, 100)
    assert x >= 1920


def test_monitor_kedua_berkoordinat_negatif():
    layar = (-1280, 0, 1280, 1000)
    # Coco di tepi kiri layar ini: form di kanan.
    assert posisi_form(coco(-1280, 300), FORM, layar) == (-1280 + 208, 300)
    # Coco lebar 900: ruang kanan 142, ruang kiri 222, dua-duanya tidak muat. Pilih
    # kiri (-1358), lalu dijepit ke tepi kiri layar ini (-1280), bukan ke 0.
    x, _ = posisi_form((-1050, 300, 900, 260), FORM, layar)
    assert x == -1280


# --- sifat umum ---

@pytest.mark.parametrize("x", range(0, 1920 - LEBAR_COCO + 1, 40))
@pytest.mark.parametrize("y", [0, 200, 500, 780])
def test_form_tidak_menimpa_coco_dan_utuh_di_layar(x, y):
    hasil = posisi_form(coco(x, y), FORM, LAYAR)
    form = kotak_form(*hasil)
    assert not bertumpuk(form, coco(x, y))
    assert di_dalam(form, LAYAR)


def test_modul_posisi_tidak_mengimpor_pyside6():
    pohon = ast.parse(Path(posisi.__file__).read_text(encoding="utf-8"))
    modul = set()
    for node in ast.walk(pohon):
        if isinstance(node, ast.Import):
            modul.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modul.add(node.module.split(".")[0])
    assert "PySide6" not in modul
