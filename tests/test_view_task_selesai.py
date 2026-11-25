"""Tes view v_task_selesai dan migrasi skema v3 (#83)."""
from datetime import datetime

import pytest

from ctrlcoco import data, db

KOLOM_VIEW = [
    "task_id", "area_id", "area_nama", "judul", "deadline", "dibuat", "selesai", "tepat_waktu",
]
DIBUAT = datetime(2026, 11, 1, 8, 0)


def nama_view(conn):
    return [
        r[0]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'view' ORDER BY name")
    ]


def isi_data(conn):
    """Dua area, lima task: tepat waktu, terlambat, tanpa deadline, todo, tepat pada deadline."""
    kuliah = data.add_area(conn, "Kuliah")
    magang = data.add_area(conn, "Magang")
    rencana = [  # (area, judul, deadline, selesai atau None)
        (kuliah, "Tepat waktu", "2026-11-20 23:59", datetime(2026, 11, 20, 10, 0)),
        (kuliah, "Terlambat", "2026-11-20 23:59", datetime(2026, 11, 21, 8, 0)),
        (magang, "Tanpa deadline", None, datetime(2026, 11, 22, 9, 0)),
        (magang, "Masih todo", "2026-11-30 23:59", None),
        (magang, "Tepat pada deadline", "2026-11-25 12:00", datetime(2026, 11, 25, 12, 0)),
    ]
    for area, judul, deadline, selesai in rencana:
        task_id = data.add_task(conn, area, judul, deadline, now=DIBUAT)
        if selesai is not None:
            data.complete_task(conn, task_id, now=selesai)


def database_v2(tmp_path):
    """Database versi 2 yang sungguhan: skema terbaru dikurangi view, berisi data."""
    c = db.connect(tmp_path / "v2.db")
    db.init_db(c)
    isi_data(c)
    c.execute("DROP VIEW v_task_selesai")
    c.execute("PRAGMA user_version = 2")
    c.commit()
    return c


def isi_tabel(conn):
    return [
        [tuple(r) for r in conn.execute(f"SELECT * FROM {tabel} ORDER BY 1")]
        for tabel in ("area", "task", "daily_log")
    ]


def test_view_ada_di_database_baru(conn):
    assert nama_view(conn) == ["v_task_selesai"]


def test_view_ada_setelah_database_v2_dinaikkan(tmp_path):
    c = database_v2(tmp_path)
    assert nama_view(c) == []
    assert c.execute("PRAGMA user_version").fetchone()[0] == 2

    db.init_db(c)

    assert nama_view(c) == ["v_task_selesai"]
    assert c.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION == 3
    c.close()


def test_kolom_view(conn):
    kursor = conn.execute("SELECT * FROM v_task_selesai")
    assert [k[0] for k in kursor.description] == KOLOM_VIEW


def test_isi_view_sesuai_data_yang_diketahui(conn):
    isi_data(conn)

    baris = [tuple(r) for r in conn.execute("SELECT * FROM v_task_selesai ORDER BY task_id")]

    # Task "Masih todo" (id 4) tidak ikut: view hanya memuat task yang selesai.
    assert baris == [
        (1, 1, "Kuliah", "Tepat waktu", "2026-11-20 23:59", "2026-11-01 08:00",
         "2026-11-20 10:00", 1),
        (2, 1, "Kuliah", "Terlambat", "2026-11-20 23:59", "2026-11-01 08:00",
         "2026-11-21 08:00", 0),
        (3, 2, "Magang", "Tanpa deadline", None, "2026-11-01 08:00",
         "2026-11-22 09:00", None),
        (5, 2, "Magang", "Tepat pada deadline", "2026-11-25 12:00", "2026-11-01 08:00",
         "2026-11-25 12:00", 1),
    ]


def test_view_kosong_bila_belum_ada_task_selesai(conn):
    area = data.add_area(conn, "Kuliah")
    data.add_task(conn, area, "Belum selesai", now=DIBUAT)
    assert conn.execute("SELECT COUNT(*) FROM v_task_selesai").fetchone()[0] == 0


def test_init_db_dua_kali_tidak_error_dan_tidak_mengubah_apa_pun(conn):
    isi_data(conn)
    sebelum = isi_tabel(conn)
    isi_view = [tuple(r) for r in conn.execute("SELECT * FROM v_task_selesai")]

    db.init_db(conn)
    db.init_db(conn)

    assert isi_tabel(conn) == sebelum
    assert [tuple(r) for r in conn.execute("SELECT * FROM v_task_selesai")] == isi_view
    assert nama_view(conn) == ["v_task_selesai"]


def test_naik_dari_v2_tidak_mengubah_data_lama(tmp_path):
    c = database_v2(tmp_path)
    sebelum = isi_tabel(c)

    db.init_db(c)
    db.init_db(c)  # idempoten: kedua kalinya tidak error

    assert isi_tabel(c) == sebelum
    c.close()


def test_definisi_view_lama_diganti_saat_naik_ke_v3(tmp_path):
    c = database_v2(tmp_path)
    c.execute("CREATE VIEW v_task_selesai AS SELECT 1 AS usang")  # sisa definisi lama
    c.commit()

    db.init_db(c)

    assert [k[0] for k in c.execute("SELECT * FROM v_task_selesai").description] == KOLOM_VIEW
    c.close()


@pytest.mark.parametrize("versi_awal", [0, 1])
def test_database_lama_v0_v1_tetap_berakhir_di_versi_terbaru_dengan_view(tmp_path, versi_awal):
    c = db.connect(tmp_path / "lama.db")
    c.execute(f"PRAGMA user_version = {versi_awal}")  # tanpa tabel sama sekali
    c.commit()

    db.init_db(c)

    assert c.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION
    assert nama_view(c) == ["v_task_selesai"]
    c.close()
