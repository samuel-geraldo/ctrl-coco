import importlib.util
from datetime import date, datetime
from pathlib import Path

from ctrlcoco import data
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
