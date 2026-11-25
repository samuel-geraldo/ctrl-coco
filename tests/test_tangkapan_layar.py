"""Tes skrip tangkapan layar (#88): semua gambar ditulis ke tmp_path, bukan ke docs/gambar."""
import importlib.util
from datetime import datetime
from pathlib import Path

import pytest
from PySide6.QtGui import QImage

from ctrlcoco import db
from ctrlcoco.mood import MOODS, get_mood

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _muat(nama):
    spec = importlib.util.spec_from_file_location(nama, SCRIPTS / f"{nama}.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


seed_demo = _muat("seed_demo")
tangkapan_layar = _muat("tangkapan_layar")

TODAY = datetime(2026, 11, 14, 9, 0)


@pytest.fixture
def demo_db(tmp_path):
    """demo.db sementara yang diisi seed_demo, seperti yang dibuat pengguna."""
    path = tmp_path / "demo.db"
    conn = db.connect(path)
    db.init_db(conn)
    assert seed_demo.seed(conn, today=TODAY) is True
    conn.close()
    return path


def test_menghasilkan_png_tidak_kosong_untuk_widget_dan_ringkasan(app, demo_db, tmp_path):
    folder = tmp_path / "gambar"
    hasil = tangkapan_layar.render_semua(demo_db, folder, TODAY.date())

    assert [p.name for p in hasil] == [
        "widget_waspada.png",
        "widget_senang.png",
        "widget_tidur.png",
        "ringkasan.png",
    ]
    for path in hasil:
        assert path.parent == folder
        assert path.stat().st_size > 0
        gambar = QImage(str(path))
        assert not gambar.isNull()
        assert gambar.width() > 0
        assert gambar.height() > 0


@pytest.mark.parametrize("kondisi", MOODS)
def test_db_kondisi_menghasilkan_mood_yang_dimaksud(kondisi):
    conn = tangkapan_layar.buat_db_kondisi(kondisi, TODAY)
    try:
        assert get_mood(conn, TODAY) == kondisi
    finally:
        conn.close()


def test_kondisi_tidak_dikenal_ditolak():
    with pytest.raises(ValueError, match="Kondisi tidak dikenal"):
        tangkapan_layar.buat_db_kondisi("marah", TODAY)


def test_menolak_database_harian_tanpa_membuka_atau_mengubahnya(monkeypatch, tmp_path, capsys):
    harian = tmp_path / "ctrlcoco.db"
    harian.write_bytes(b"data harian")
    monkeypatch.setattr(db, "default_db_path", lambda: harian)

    def dilarang(*args, **kwargs):
        raise AssertionError("database harian tidak boleh dibuka")

    monkeypatch.setattr(db, "connect", dilarang)
    folder = tmp_path / "gambar"

    kode = tangkapan_layar.main(["--db", str(harian), "--out", str(folder)])

    assert kode == 1
    assert "database harian" in capsys.readouterr().out
    assert harian.read_bytes() == b"data harian"
    assert not folder.exists()


def test_database_yang_tidak_ada_tidak_dibuat(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(db, "default_db_path", lambda: tmp_path / "ctrlcoco.db")
    hilang = tmp_path / "demo.db"

    kode = tangkapan_layar.main(["--db", str(hilang), "--out", str(tmp_path / "gambar")])

    assert kode == 1
    assert "seed_demo" in capsys.readouterr().out
    assert not hilang.exists()
