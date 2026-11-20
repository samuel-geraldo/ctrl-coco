import ast
from datetime import datetime
from pathlib import Path

import pytest

from ctrlcoco import deadline
from ctrlcoco.deadline import PILIHAN_CEPAT, deadline_cepat

NOW = datetime(2026, 3, 10, 9, 30)


def test_daftar_pilihan():
    assert PILIHAN_CEPAT == ("hari_ini", "besok", "minggu_depan")


@pytest.mark.parametrize(
    "now",
    [NOW, datetime(2026, 3, 10, 0, 0), datetime(2026, 3, 10, 23, 59, 30)],
    ids=["pagi", "tengah_malam", "23_59_30"],
)
def test_hari_ini_pukul_23_59(now):
    assert deadline_cepat("hari_ini", now) == datetime(2026, 3, 10, 23, 59)


def test_besok_pukul_23_59():
    assert deadline_cepat("besok", NOW) == datetime(2026, 3, 11, 23, 59)


def test_minggu_depan_7_hari_pukul_23_59():
    assert deadline_cepat("minggu_depan", NOW) == datetime(2026, 3, 17, 23, 59)


@pytest.mark.parametrize("pilihan", PILIHAN_CEPAT)
def test_detik_selalu_nol(pilihan):
    hasil = deadline_cepat(pilihan, datetime(2026, 3, 10, 9, 30, 45, 123))
    assert (hasil.second, hasil.microsecond) == (0, 0)


@pytest.mark.parametrize(
    "pilihan, now, harapan",
    [
        ("besok", datetime(2026, 1, 31, 10, 0), datetime(2026, 2, 1, 23, 59)),
        ("besok", datetime(2026, 2, 28, 10, 0), datetime(2026, 3, 1, 23, 59)),
        ("minggu_depan", datetime(2026, 2, 25, 10, 0), datetime(2026, 3, 4, 23, 59)),
        ("besok", datetime(2026, 12, 31, 10, 0), datetime(2027, 1, 1, 23, 59)),
        ("minggu_depan", datetime(2026, 12, 28, 10, 0), datetime(2027, 1, 4, 23, 59)),
        ("besok", datetime(2028, 2, 28, 10, 0), datetime(2028, 2, 29, 23, 59)),
    ],
    ids=[
        "31_jan_besok",
        "28_feb_besok",
        "25_feb_minggu_depan",
        "31_des_besok",
        "28_des_minggu_depan",
        "kabisat_28_feb_besok",
    ],
)
def test_pergantian_bulan_dan_tahun(pilihan, now, harapan):
    assert deadline_cepat(pilihan, now) == harapan


def test_pilihan_tidak_dikenal_ditolak():
    with pytest.raises(ValueError):
        deadline_cepat("lusa", NOW)


def test_modul_deadline_tidak_mengimpor_pyside6():
    pohon = ast.parse(Path(deadline.__file__).read_text(encoding="utf-8"))
    modul = set()
    for node in ast.walk(pohon):
        if isinstance(node, ast.Import):
            modul.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modul.add(node.module.split(".")[0])
    assert "PySide6" not in modul
