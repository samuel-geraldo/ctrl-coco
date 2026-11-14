import os

# Tes widget berjalan tanpa layar: Qt menggambar di memori saja.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from ctrlcoco import db


@pytest.fixture
def conn():
    """Database sementara di memori: bersih untuk tiap tes, hilang saat selesai."""
    c = db.connect(":memory:")
    db.init_db(c)
    yield c
    c.close()


@pytest.fixture(scope="session")
def app():
    """Satu QApplication untuk semua tes yang memakai Qt."""
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])
