import ast
from pathlib import Path

import pytest

from ctrlcoco import klik
from ctrlcoco.klik import AMBANG_SERET_PX, adalah_klik

TEKAN = (100, 100)


def geser(dx, dy):
    return (TEKAN[0] + dx, TEKAN[1] + dy)


def test_ambang_sama_dengan_bawaan_qt():
    assert AMBANG_SERET_PX == 10


def test_tanpa_gerak_adalah_klik():
    assert adalah_klik(TEKAN, TEKAN)


@pytest.mark.parametrize("dx, dy", [(3, 4), (9, 0), (0, -9), (-3, -2), (5, 4)])
def test_gerak_di_bawah_ambang_adalah_klik(dx, dy):
    assert adalah_klik(TEKAN, geser(dx, dy))


@pytest.mark.parametrize("dx, dy", [(10, 0), (0, -10), (6, 4), (-5, 5)])
def test_gerak_tepat_di_ambang_adalah_seret(dx, dy):
    # Jarak dihitung |dx| + |dy| (manhattan), sama seperti Qt.
    assert not adalah_klik(TEKAN, geser(dx, dy))


@pytest.mark.parametrize("dx, dy", [(15, 0), (50, 30), (-8, -8)])
def test_gerak_di_atas_ambang_adalah_seret(dx, dy):
    assert not adalah_klik(TEKAN, geser(dx, dy))


def test_ambang_bisa_diganti():
    assert adalah_klik(TEKAN, geser(3, 0), ambang=4)
    assert not adalah_klik(TEKAN, geser(4, 0), ambang=4)


def test_modul_klik_tidak_mengimpor_pyside6():
    pohon = ast.parse(Path(klik.__file__).read_text(encoding="utf-8"))
    modul = set()
    for node in ast.walk(pohon):
        if isinstance(node, ast.Import):
            modul.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modul.add(node.module.split(".")[0])
    assert "PySide6" not in modul
