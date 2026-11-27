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
    monkeypatch.setattr(
        QApplication, "exec", staticmethod(lambda *args: dipanggil.append(True) or 0)
    )
    return dipanggil


@pytest.fixture
def koneksi_dibuka(monkeypatch):
    """Catat setiap koneksi yang dibuka main, supaya bisa dicek sudah ditutup.
    Setelah tes selesai semuanya ditutup, supaya file di tmp_path bisa dihapus."""
    dibuka = []
    connect_asli = db.connect

    def connect(path=None):
        conn = connect_asli(path)
        dibuka.append(conn)
        return conn

    monkeypatch.setattr(db, "connect", connect)
    yield dibuka
    for conn in dibuka:
        conn.close()


def tabel_di(path):
    """Nama tabel buatan aplikasi di file database `path`."""
    c = sqlite3.connect(path)
    nama = {r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    )}
    c.close()
    return nama


# --- jalur normal ---

def test_main_membuat_database_baru_dengan_tiga_tabel(app, tmp_path, monkeypatch, pesan,
                                                      exec_dipanggil, koneksi_dibuka):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))  # pagar: jangan sentuh AppData asli
    path = tmp_path / "baru.db"
    assert titik_masuk.main(["--db", str(path)]) == 0
    assert exec_dipanggil == [True]
    assert pesan == []
    assert tabel_di(path) == {"area", "task", "daily_log"}
    assert not (tmp_path / "appdata" / "CtrlCoco" / "ctrlcoco.db").exists()


def test_main_tanpa_db_memakai_folder_appdata(app, tmp_path, monkeypatch, pesan,
                                             exec_dipanggil, koneksi_dibuka):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert titik_masuk.main([]) == 0
    assert exec_dipanggil == [True]
    assert pesan == []
    assert tabel_di(tmp_path / "CtrlCoco" / "ctrlcoco.db") == {"area", "task", "daily_log"}


def test_main_menutup_koneksi_saat_keluar_normal(app, tmp_path, pesan, exec_dipanggil,
                                                 koneksi_dibuka):
    assert titik_masuk.main(["--db", str(tmp_path / "baru.db")]) == 0
    assert len(koneksi_dibuka) == 1
    assert sudah_ditutup(koneksi_dibuka[0])


# --- jalur gagal ---


def jalankan_dan_harus_gagal(path, pesan, exec_dipanggil):
    """Jalankan main dengan --db path; pastikan gagal dengan pesan.

    Lalu kembalikan teks pesannya.
    """
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


def test_startup_database_lama_bertanggal_rusak(
    app, tmp_path, pesan, exec_dipanggil, koneksi_dibuka
):
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


def test_startup_database_terkunci(
    app, tmp_path, monkeypatch, pesan, exec_dipanggil, koneksi_dibuka
):
    # Kunci sungguhan (BEGIN EXCLUSIVE) membuat tes menunggu timeout; cukup tiru errornya.
    def init_db_terkunci(conn):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(db, "init_db", init_db_terkunci)
    teks = jalankan_dan_harus_gagal(tmp_path / "ctrlcoco.db", pesan, exec_dipanggil)
    assert "database is locked" in teks
    assert len(koneksi_dibuka) == 1
    assert sudah_ditutup(koneksi_dibuka[0])


# --- folder data gagal dibuat ---

FOLDER_DATA = r"C:\Users\contoh\AppData\Roaming\CtrlCoco"


def folder_gagal(error):
    """Tiruan default_db_path yang gagal membuat folder (tanpa mengubah izin folder sungguhan)."""
    def default_db_path():
        raise error
    return default_db_path


def test_startup_folder_data_tidak_bisa_dibuat(app, monkeypatch, pesan, exec_dipanggil,
                                               koneksi_dibuka):
    # Bentuk error sama seperti yang dilempar Path.mkdir: errno, sebab, dan path folder.
    monkeypatch.setattr(db, "default_db_path",
                        folder_gagal(PermissionError(13, "Access is denied", FOLDER_DATA)))
    assert titik_masuk.main([]) == 1
    assert not exec_dipanggil
    assert koneksi_dibuka == []  # database tidak dicoba dibuka
    assert len(pesan) == 1
    _, judul, teks = pesan[0]
    assert judul == "CtrlCoco"
    assert "Folder data tidak bisa dibuat" in teks
    assert FOLDER_DATA in teks
    assert "Access is denied" in teks


def test_startup_folder_data_gagal_tanpa_path(app, monkeypatch, pesan, exec_dipanggil,
                                              koneksi_dibuka):
    # OSError tanpa path: pesan tetap tampil dengan penyebabnya.
    monkeypatch.setattr(db, "default_db_path", folder_gagal(OSError("disk penuh")))
    assert titik_masuk.main([]) == 1
    assert not exec_dipanggil
    teks = pesan[0][2]
    assert "Folder data tidak bisa dibuat" in teks
    assert "disk penuh" in teks
    assert "None" not in teks


def test_dengan_db_folder_data_tidak_disentuh(app, tmp_path, monkeypatch, pesan,
                                              exec_dipanggil, koneksi_dibuka):
    dipanggil = []

    def default_db_path():
        dipanggil.append(True)
        raise PermissionError(13, "Access is denied", FOLDER_DATA)

    monkeypatch.setattr(db, "default_db_path", default_db_path)
    assert titik_masuk.main(["--db", str(tmp_path / "x.db")]) == 0
    assert dipanggil == []
    assert pesan == []
    assert exec_dipanggil == [True]


def test_error_lain_dari_folder_data_tidak_ditelan(app, monkeypatch, pesan, exec_dipanggil):
    monkeypatch.setattr(db, "default_db_path", folder_gagal(RuntimeError("bug lain")))
    with pytest.raises(RuntimeError, match="bug lain"):
        titik_masuk.main([])
    assert pesan == []
    assert not exec_dipanggil
