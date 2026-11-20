import ast
from pathlib import Path

import pytest

from ctrlcoco import perayaan
from ctrlcoco.perayaan import TONGGAK_STREAK, Perayaan, jenis_perayaan_log, perlu_rayakan


def test_tonggak_streak():
    assert TONGGAK_STREAK == (3, 7, 14, 30)


# --- perlu_rayakan: tonggak streak ---

@pytest.mark.parametrize(
    "sebelum, sesudah, tonggak",
    [(2, 3, 3), (6, 7, 7), (13, 14, 14), (13, 15, 14), (29, 30, 30)],
)
def test_baru_mencapai_tonggak(sebelum, sesudah, tonggak):
    assert perlu_rayakan(sebelum, sesudah) == tonggak


@pytest.mark.parametrize(
    "sebelum, sesudah",
    [(3, 3), (7, 7), (0, 1), (1, 2), (4, 5), (30, 31), (31, 32), (3, 0), (8, 2)],
)
def test_tidak_mencapai_tonggak_baru(sebelum, sesudah):
    assert perlu_rayakan(sebelum, sesudah) is None


@pytest.mark.parametrize("sebelum, sesudah, tonggak", [(2, 7, 7), (0, 30, 30), (0, 10, 7)])
def test_beberapa_tonggak_sekaligus_pilih_terbesar(sebelum, sesudah, tonggak):
    assert perlu_rayakan(sebelum, sesudah) == tonggak


def test_streak_putus_lalu_naik_lagi_ke_3_dirayakan_lagi():
    urutan = [(2, 3), (3, 0), (0, 1), (1, 2), (2, 3)]
    assert [perlu_rayakan(a, b) for a, b in urutan] == [3, None, None, None, 3]


# --- jenis_perayaan_log ---

def test_log_baru_valid_mencapai_tonggak():
    assert jenis_perayaan_log(False, True, 2, 3) == Perayaan("tonggak", 3)


def test_log_baru_valid_tanpa_tonggak_perayaan_biasa():
    assert jenis_perayaan_log(False, True, 0, 1) == Perayaan("log")
    assert jenis_perayaan_log(False, True, 3, 4) == Perayaan("log")


def test_tonggak_lebih_utama_daripada_log_biasa():
    assert jenis_perayaan_log(False, True, 6, 7).jenis == "tonggak"


@pytest.mark.parametrize(
    "valid_sebelum, valid_sesudah, streak_sebelum, streak_sesudah",
    [
        (True, True, 3, 3),    # simpan ulang log yang sudah valid
        (True, True, 2, 3),    # walau angka streak terlihat naik
        (False, False, 2, 2),  # log masih belum lengkap
        (True, False, 3, 2),   # log dibuat tidak valid lagi
    ],
)
def test_log_tidak_baru_valid_tidak_merayakan(
    valid_sebelum, valid_sesudah, streak_sebelum, streak_sesudah
):
    assert jenis_perayaan_log(valid_sebelum, valid_sesudah, streak_sebelum, streak_sesudah) is None


def test_perayaan_task():
    assert Perayaan("task", judul="Laporan") == Perayaan("task", None, "Laporan")


# --- modul murni ---

def test_modul_perayaan_tidak_mengimpor_pyside6():
    pohon = ast.parse(Path(perayaan.__file__).read_text(encoding="utf-8"))
    modul = set()
    for node in ast.walk(pohon):
        if isinstance(node, ast.Import):
            modul.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modul.add(node.module.split(".")[0])
    assert "PySide6" not in modul
