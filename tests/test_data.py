from datetime import datetime

import pytest

from ctrlcoco import data

NOW = datetime(2026, 3, 10, 9, 30)


# --- area ---

def test_add_area_dan_list_areas(conn):
    data.add_area(conn, "Kuliah")
    data.add_area(conn, "Pribadi")
    assert [a["name"] for a in data.list_areas(conn)] == ["Kuliah", "Pribadi"]


def test_add_area_nama_kembar_ditolak(conn):
    data.add_area(conn, "Kuliah")
    with pytest.raises(ValueError):
        data.add_area(conn, "Kuliah")
    assert len(data.list_areas(conn)) == 1


def test_list_areas_kosong(conn):
    assert data.list_areas(conn) == []


def test_nama_dengan_tanda_kutip_aman(conn):
    nama = "x'); DROP TABLE area; --"
    data.add_area(conn, nama)
    assert data.list_areas(conn)[0]["name"] == nama


# --- task ---

def test_add_task_tanpa_deadline(conn):
    area_id = data.add_area(conn, "Kuliah")
    task_id = data.add_task(conn, area_id, "Baca bab 1", now=NOW)
    task = data.list_tasks(conn)[0]
    assert task["id"] == task_id
    assert task["area_id"] == area_id
    assert task["title"] == "Baca bab 1"
    assert task["deadline"] is None
    assert task["status"] == "todo"
    assert task["created_at"] == "2026-03-10 09:30"
    assert task["completed_at"] is None


def test_add_task_dengan_deadline(conn):
    area_id = data.add_area(conn, "Kuliah")
    data.add_task(conn, area_id, "Laporan", deadline="2026-03-12 23:59", now=NOW)
    assert data.list_tasks(conn)[0]["deadline"] == "2026-03-12 23:59"


def test_add_task_area_tidak_ada_ditolak(conn):
    with pytest.raises(ValueError):
        data.add_task(conn, 999, "Tanpa area", now=NOW)
    assert data.list_tasks(conn) == []


def test_list_tasks_filter_status(conn):
    area_id = data.add_area(conn, "Kuliah")
    t1 = data.add_task(conn, area_id, "A", now=NOW)
    data.add_task(conn, area_id, "B", now=NOW)
    data.complete_task(conn, t1, now=NOW)
    assert [t["title"] for t in data.list_tasks(conn, status="todo")] == ["B"]
    assert [t["title"] for t in data.list_tasks(conn, status="done")] == ["A"]
    assert len(data.list_tasks(conn)) == 2


def test_complete_task_mengisi_status_dan_completed_at(conn):
    area_id = data.add_area(conn, "Kuliah")
    task_id = data.add_task(conn, area_id, "A", now=NOW)
    data.complete_task(conn, task_id, now=datetime(2026, 3, 11, 14, 5))
    task = data.list_tasks(conn)[0]
    assert task["status"] == "done"
    assert task["completed_at"] == "2026-03-11 14:05"


def test_complete_task_dua_kali_tidak_mengubah_completed_at(conn):
    area_id = data.add_area(conn, "Kuliah")
    task_id = data.add_task(conn, area_id, "A", now=NOW)
    data.complete_task(conn, task_id, now=datetime(2026, 3, 11, 14, 5))
    data.complete_task(conn, task_id, now=datetime(2026, 3, 12, 8, 0))
    assert data.list_tasks(conn)[0]["completed_at"] == "2026-03-11 14:05"


def test_complete_task_tidak_ada_ditolak(conn):
    with pytest.raises(ValueError):
        data.complete_task(conn, 999)


# --- daily_log ---

def test_set_daily_log_baru(conn):
    data.set_daily_log(conn, "2026-03-10", True, False, note="hari biasa")
    log = data.get_daily_log(conn, "2026-03-10")
    assert log["claude_code"] == 1
    assert log["github"] == 0
    assert log["note"] == "hari biasa"


def test_set_daily_log_tanggal_sama_memperbarui(conn):
    data.set_daily_log(conn, "2026-03-10", True, False)
    data.set_daily_log(conn, "2026-03-10", True, True, note="lengkap")
    rows = conn.execute("SELECT * FROM daily_log").fetchall()
    assert len(rows) == 1
    assert rows[0]["github"] == 1
    assert rows[0]["note"] == "lengkap"


def test_get_daily_log_tidak_ada(conn):
    assert data.get_daily_log(conn, "2026-03-10") is None
