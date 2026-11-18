import sqlite3

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from ctrlcoco import __main__ as titik_masuk
from ctrlcoco import db


@pytest.fixture
def pesan(monkeypatch):
    """Ganti QMessageBox.critical: hanya mencatat panggilannya, tanpa menunggu klik."""
    dicatat = []
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *args: dicatat.append(args)))
    return dicatat


@pytest.fixture
def exec_dipanggil(monkeypatch):
    """Ganti QApplication.exec: catat panggilannya, jangan masuk event loop."""
    dipanggil = []
    monkeypatch.setattr(QApplication, "exec", staticmethod(lambda *args: dipanggil.append(True) or 0))
    return dipanggil


@pytest.fixture
def koneksi_dibuka(monkeypatch):
    """Catat setiap koneksi yang dibuka main, supaya bisa dicek sudah ditutup."""
    dibuka = []
    connect_asli = db.connect

    def connect(path=None):
        conn = connect_asli(path)
        dibuka.append(conn)
        return conn

    monkeypatch.setattr(db, "connect", connect)
    return dibuka


def jalankan_dan_harus_gagal(path, pesan, exec_dipanggil):
    """Jalankan main dengan --db path; pastikan gagal dengan pesan, lalu kembalikan teks pesannya."""
    kode = titik_masuk.main(["--db", str(path)])
    assert kode != 0
    assert not exec_dipanggil
    assert len(pesan) == 1
    teks = pesan[0][2]  # QMessageBox.critical(parent, judul, teks)
    assert str(path) in teks
    return teks


def sudah_ditutup(conn):
    try:
        conn.execute("SELECT 1")
    except sqlite3.ProgrammingError:
        return True
    return False


def test_startup_file_bukan_database(app, tmp_path, pesan, exec_dipanggil, koneksi_dibuka):
    path = tmp_path / "rusak.db"
    path.write_text("ini bukan database")
    teks = jalankan_dan_harus_gagal(path, pesan, exec_dipanggil)
    assert "file is not a database" in teks
    assert all(sudah_ditutup(c) for c in koneksi_dibuka)


def test_startup_database_lama_bertanggal_rusak(app, tmp_path, pesan, exec_dipanggil, koneksi_dibuka):
    # Database lama (user_version 0) tanpa CHECK, berisi tanggal berformat salah:
    # migrasi di init_db menolaknya dengan ValueError.
    path = tmp_path / "lama.db"
    lama = sqlite3.connect(path)
    lama.execute(
        "CREATE TABLE daily_log (log_date TEXT PRIMARY KEY, claude_code INTEGER NOT NULL,"
        " github INTEGER NOT NULL, note TEXT)"
    )
    lama.execute("INSERT INTO daily_log VALUES ('10-03-2026', 1, 1, NULL)")
    lama.commit()
    lama.close()

    teks = jalankan_dan_harus_gagal(path, pesan, exec_dipanggil)
    assert "10-03-2026" in teks
    assert len(koneksi_dibuka) == 1
    assert sudah_ditutup(koneksi_dibuka[0])


def test_startup_database_terkunci(app, tmp_path, monkeypatch, pesan, exec_dipanggil, koneksi_dibuka):
    # Kunci sungguhan (BEGIN EXCLUSIVE) membuat tes menunggu timeout; cukup tiru errornya.
    def init_db_terkunci(conn):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(db, "init_db", init_db_terkunci)
    teks = jalankan_dan_harus_gagal(tmp_path / "ctrlcoco.db", pesan, exec_dipanggil)
    assert "database is locked" in teks
    assert len(koneksi_dibuka) == 1
    assert sudah_ditutup(koneksi_dibuka[0])
