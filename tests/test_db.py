import sqlite3

import pytest

from ctrlcoco import db


def test_init_db_membuat_tiga_tabel(conn):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    names = {r["name"] for r in rows}
    assert {"area", "task", "daily_log"} <= names


def test_init_db_aman_dipanggil_berulang(conn):
    conn.execute("INSERT INTO area (name) VALUES ('Kuliah')")
    db.init_db(conn)
    assert conn.execute("SELECT COUNT(*) FROM area").fetchone()[0] == 1


def test_foreign_keys_menyala(conn):
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_task_dengan_area_tidak_ada_ditolak(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO task (area_id, title, created_at) VALUES (999, 'x', '2026-01-01 00:00')"
        )


def test_connect_membuat_file_jika_belum_ada(tmp_path):
    path = tmp_path / "baru.db"
    assert not path.exists()
    c = db.connect(str(path))
    db.init_db(c)
    c.close()
    assert path.exists()


def test_default_db_path_di_appdata_dan_folder_dibuat(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    path = db.default_db_path()
    assert path == tmp_path / "CtrlCoco" / "ctrlcoco.db"
    assert path.parent.is_dir()


def test_default_db_path_di_appdata_dan_folder_dibuat(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    path = db.default_db_path()
    assert path == tmp_path / "CtrlCoco" / "ctrlcoco.db"
    assert path.parent.is_dir()
