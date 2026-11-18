import importlib.util
from datetime import date, datetime
from pathlib import Path

import pytest

from ctrlcoco import data, db
from ctrlcoco.streak import get_streak

_spec = importlib.util.spec_from_file_location(
    "seed_demo", Path(__file__).resolve().parents[1] / "scripts" / "seed_demo.py"
)
seed_demo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed_demo)


def test_seed_mengisi_area_task_dan_streak(conn):
    assert seed_demo.seed(conn, today=datetime(2026, 11, 14, 9, 0)) is True
    assert [a["name"] for a in data.list_areas(conn)] == ["Kuliah", "Portofolio"]
    assert data.get_nearest_task(conn)["title"] == "Laporan praktikum basis data"
    assert get_streak(conn, today=date(2026, 11, 14)) == 5


def test_seed_tidak_menimpa_database_berisi(conn):
    data.add_area(conn, "Milik saya")
    assert seed_demo.seed(conn) is False
    assert [a["name"] for a in data.list_areas(conn)] == ["Milik saya"]


def test_seed_tidak_menimpa_database_yang_hanya_berisi_log(conn):
    # Streak bisa dicatat tanpa pernah membuat area; log seperti ini tidak boleh tertimpa.
    data.set_daily_log(conn, "2026-11-14", True, True, note="catatan asli")
    assert seed_demo.seed(conn, today=datetime(2026, 11, 14, 9, 0)) is False
    assert data.get_daily_log(conn, "2026-11-14")["note"] == "catatan asli"
    assert data.list_areas(conn) == []


# --- konfirmasi sebelum menulis ke database harian ---

@pytest.fixture
def folder_appdata(tmp_path, monkeypatch):
    """APPDATA dan folder kerja dialihkan ke tmp_path, supaya database harian asli
    tidak tersentuh dan tidak ada demo.db yang tercipta di folder repo."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    return tmp_path / "CtrlCoco"


def ganti_input(monkeypatch, jawaban):
    """Ganti input(): langsung menjawab `jawaban` dan mencatat setiap pertanyaan."""
    ditanya = []

    def input_tiruan(prompt=""):
        ditanya.append(prompt)
        return jawaban

    monkeypatch.setattr("builtins.input", input_tiruan)
    return ditanya


def nama_area_di(path):
    c = db.connect(path)
    nama = [a["name"] for a in data.list_areas(c)]
    c.close()
    return nama


def test_seed_demo_jawab_n_tidak_menulis_apa_pun(folder_appdata, monkeypatch):
    harian = folder_appdata / "ctrlcoco.db"
    ditanya = ganti_input(monkeypatch, "n")
    assert seed_demo.main(["--db", str(harian)]) == 1
    assert len(ditanya) == 1
    assert not harian.exists()


def test_seed_demo_jawab_y_menulis_data(folder_appdata, monkeypatch):
    harian = folder_appdata / "ctrlcoco.db"
    ditanya = ganti_input(monkeypatch, "y")
    assert seed_demo.main(["--db", str(harian)]) == 0
    assert len(ditanya) == 1
    assert nama_area_di(harian) == ["Kuliah", "Portofolio"]


def test_seed_demo_tanpa_db_tidak_bertanya(folder_appdata, monkeypatch):
    ditanya = ganti_input(monkeypatch, "y")
    assert seed_demo.main([]) == 0
    assert ditanya == []
    assert nama_area_di(folder_appdata / "demo.db") == ["Kuliah", "Portofolio"]
    assert not (folder_appdata / "ctrlcoco.db").exists()
