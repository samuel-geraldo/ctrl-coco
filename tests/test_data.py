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


@pytest.mark.parametrize("deadline", ["2026-03-12 00:00", "2026-03-12 23:59", "2028-02-29 10:00"])
def test_add_task_deadline_format_benar_diterima(conn, deadline):
    area_id = data.add_area(conn, "Kuliah")
    data.add_task(conn, area_id, "Laporan", deadline=deadline, now=NOW)
    assert data.list_tasks(conn)[0]["deadline"] == deadline


@pytest.mark.parametrize(
    "deadline",
    [
        "2026-03-12",           # tanpa jam
        "2026-03-12 23:59:00",  # ada detik
        "2026-03-12T23:59",     # pemisah T
        "12-03-2026 23:59",     # urutan hari-bulan-tahun
        "2026/03/12 23:59",     # garis miring
        "2026-3-12 9:00",       # tanpa nol di depan
        "besok",
        "",
    ],
)
def test_add_task_deadline_format_salah_ditolak(conn, deadline):
    area_id = data.add_area(conn, "Kuliah")
    with pytest.raises(ValueError, match="YYYY-MM-DD HH:MM"):
        data.add_task(conn, area_id, "Laporan", deadline=deadline, now=NOW)
    assert data.list_tasks(conn) == []


@pytest.mark.parametrize(
    "deadline",
    [
        "2026-02-30 10:00",  # Februari tidak punya tanggal 30
        "2027-02-29 10:00",  # 2027 bukan tahun kabisat
        "2026-13-01 10:00",  # bulan 13
        "2026-03-12 24:00",  # jam 24
        "2026-03-12 10:60",  # menit 60
    ],
)
def test_add_task_deadline_mustahil_ditolak(conn, deadline):
    area_id = data.add_area(conn, "Kuliah")
    with pytest.raises(ValueError, match="deadline"):
        data.add_task(conn, area_id, "Laporan", deadline=deadline, now=NOW)
    assert data.list_tasks(conn) == []


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


@pytest.mark.parametrize("log_date", ["2026-03-10", "2026-12-31", "2028-02-29"])
def test_set_daily_log_format_benar_diterima(conn, log_date):
    data.set_daily_log(conn, log_date, True, True)
    assert data.get_daily_log(conn, log_date) is not None


@pytest.mark.parametrize(
    "log_date",
    [
        "10-03-2026",        # urutan hari-bulan-tahun
        "2026/03/10",        # garis miring
        "2026-3-5",          # tanpa nol di depan
        "20260310",          # tanpa pemisah
        "2026-03-10 09:30",  # ada jam
        " 2026-03-10",       # ada spasi
        "kemarin",
        "",
    ],
)
def test_set_daily_log_format_salah_ditolak(conn, log_date):
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        data.set_daily_log(conn, log_date, True, True)
    assert conn.execute("SELECT COUNT(*) FROM daily_log").fetchone()[0] == 0


@pytest.mark.parametrize(
    "log_date",
    [
        "2026-02-30",  # Februari tidak punya tanggal 30
        "2027-02-29",  # 2027 bukan tahun kabisat
        "2026-04-31",  # April hanya 30 hari
        "2026-13-01",  # bulan 13
        "2026-00-10",  # bulan 0
    ],
)
def test_set_daily_log_tanggal_mustahil_ditolak(conn, log_date):
    with pytest.raises(ValueError, match="log_date"):
        data.set_daily_log(conn, log_date, True, True)
    assert conn.execute("SELECT COUNT(*) FROM daily_log").fetchone()[0] == 0


def test_get_daily_log_tidak_ada(conn):
    assert data.get_daily_log(conn, "2026-03-10") is None


# --- task terdekat ---

def test_get_nearest_task_memilih_deadline_paling_awal(conn):
    area_id = data.add_area(conn, "Kuliah")
    data.add_task(conn, area_id, "Lusa", deadline="2026-03-12 10:00", now=NOW)
    data.add_task(conn, area_id, "Besok", deadline="2026-03-11 10:00", now=NOW)
    assert data.get_nearest_task(conn)["title"] == "Besok"


def test_get_nearest_task_abaikan_done_dan_tanpa_deadline(conn):
    area_id = data.add_area(conn, "Kuliah")
    selesai = data.add_task(conn, area_id, "Selesai", deadline="2026-03-11 10:00", now=NOW)
    data.complete_task(conn, selesai, now=NOW)
    data.add_task(conn, area_id, "Tanpa deadline", now=NOW)
    data.add_task(conn, area_id, "Aktif", deadline="2026-03-15 10:00", now=NOW)
    assert data.get_nearest_task(conn)["title"] == "Aktif"


def test_get_nearest_task_kosong(conn):
    assert data.get_nearest_task(conn) is None
