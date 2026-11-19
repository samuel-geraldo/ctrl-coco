import os
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


def test_connect_tanpa_argumen_memakai_folder_appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    c = db.connect()
    # Tanya SQLite sendiri file mana yang dibuka koneksi ini.
    dibuka = c.execute("PRAGMA database_list").fetchone()["file"]
    c.close()
    assert os.path.samefile(dibuka, tmp_path / "CtrlCoco" / "ctrlcoco.db")


# --- CHECK pada kolom tanggal: database menolak teks berformat salah dari jalur mana pun ---

LOG_DATE_SALAH = [
    "2026-11-5",          # tanpa nol di depan
    "14-11-2026",         # urutan terbalik
    "",                   # kosong
    "2026-02-30",         # tidak ada di kalender
    "2026-11-14 10:00",   # ada jamnya
    "0000-01-01",         # tahun 0: diterima SQLite, ditolak Python
]
DEADLINE_SALAH = [
    "2026-11-20",           # tanpa jam
    "2026-11-20 23:59:00",  # ada detik
    "",
    "2026-3-5 09:00",
    "2026-02-30 09:00",
    "2026-11-20 24:00",     # jam 24: diterima SQLite, ditolak Python
    "0000-01-01 00:00",
]


def _tambah_area(conn):
    conn.execute("INSERT INTO area (name) VALUES ('Kuliah')")


@pytest.mark.parametrize("nilai", LOG_DATE_SALAH)
def test_database_menolak_log_date_salah(conn, nilai):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO daily_log VALUES (?, 1, 1, NULL)", (nilai,))


@pytest.mark.parametrize("nilai", DEADLINE_SALAH)
def test_database_menolak_deadline_salah(conn, nilai):
    _tambah_area(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO task (area_id, title, deadline, created_at) VALUES (1, 'x', ?, '2026-01-01 00:00')",
            (nilai,),
        )


def test_database_menerima_tanggal_dan_deadline_yang_benar(conn):
    _tambah_area(conn)
    conn.execute("INSERT INTO daily_log VALUES ('2024-02-29', 1, 1, NULL)")  # tahun kabisat
    conn.execute("INSERT INTO task (area_id, title, deadline, created_at) VALUES (1, 'a', '2026-11-20 23:59', 'x')")
    conn.execute("INSERT INTO task (area_id, title, deadline, created_at) VALUES (1, 'b', NULL, 'x')")  # tanpa deadline


def test_update_ke_format_salah_juga_ditolak(conn):
    _tambah_area(conn)
    conn.execute("INSERT INTO task (area_id, title, deadline, created_at) VALUES (1, 'a', '2026-11-20 23:59', 'x')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE task SET deadline = '2026-11-20' WHERE id = 1")
    conn.execute("INSERT INTO daily_log VALUES ('2026-11-14', 1, 1, NULL)")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE daily_log SET log_date = '2026-11-5'")


def _kombinasi_tanggal():
    for tahun in (0, 1, 1900, 2023, 2024, 2100, 9999):
        for bulan in (0, 1, 2, 12, 13):
            for hari in (0, 1, 28, 29, 30, 31, 32):
                yield f"{tahun:04d}-{bulan:02d}-{hari:02d}"


def test_check_database_sama_dengan_validasi_python(conn):
    """Aturan di SQLite dan di Python (data._check_format) tidak boleh berbeda."""
    from ctrlcoco import data

    def python_menerima(teks, fmt):
        try:
            data._check_format(teks, fmt, "x", "x")
            return True
        except ValueError:
            return False

    _tambah_area(conn)
    for teks in _kombinasi_tanggal():
        try:
            conn.execute("INSERT INTO daily_log VALUES (?, 1, 1, NULL)", (teks,))
            sqlite_menerima = True
        except sqlite3.IntegrityError:
            sqlite_menerima = False
        assert sqlite_menerima == python_menerima(teks, data.DATE_FORMAT), teks

    for tanggal in ("0000-01-01", "0001-01-01", "2024-02-29", "2026-11-20"):
        for jam in (0, 23, 24, 25):
            for menit in (0, 59, 60):
                teks = f"{tanggal} {jam:02d}:{menit:02d}"
                try:
                    conn.execute(
                        "INSERT INTO task (area_id, title, deadline, created_at) VALUES (1, 'x', ?, 'x')",
                        (teks,),
                    )
                    sqlite_menerima = True
                except sqlite3.IntegrityError:
                    sqlite_menerima = False
                assert sqlite_menerima == python_menerima(teks, data.TIME_FORMAT), teks


# --- CHECK nama: area.name dan task.title tidak boleh kosong, nama area unik tanpa beda huruf ---

NAMA_KOSONG = ["", " ", "   ", "\t", "\n", "\r\n", " \t\r\n "]


@pytest.mark.parametrize("nilai", NAMA_KOSONG)
def test_database_menolak_nama_area_kosong(conn, nilai):
    with pytest.raises(sqlite3.IntegrityError) as err:
        conn.execute("INSERT INTO area (name) VALUES (?)", (nilai,))
    assert err.value.sqlite_errorname == "SQLITE_CONSTRAINT_CHECK"


@pytest.mark.parametrize("nilai", NAMA_KOSONG)
def test_database_menolak_judul_task_kosong(conn, nilai):
    _tambah_area(conn)
    with pytest.raises(sqlite3.IntegrityError) as err:
        conn.execute(
            "INSERT INTO task (area_id, title, created_at) VALUES (1, ?, '2026-01-01 00:00')", (nilai,)
        )
    assert err.value.sqlite_errorname == "SQLITE_CONSTRAINT_CHECK"


@pytest.mark.parametrize("nilai", ["Kuliah", "kuliah", "KULIAH", "kUlIaH"])
def test_database_menolak_nama_area_kembar_beda_huruf(conn, nilai):
    _tambah_area(conn)
    with pytest.raises(sqlite3.IntegrityError) as err:
        conn.execute("INSERT INTO area (name) VALUES (?)", (nilai,))
    assert err.value.sqlite_errorname == "SQLITE_CONSTRAINT_UNIQUE"


def test_database_menyimpan_nama_area_apa_adanya(conn):
    conn.execute("INSERT INTO area (name) VALUES ('magang')")
    conn.execute("INSERT INTO area (name) VALUES ('Pribadi')")
    _tambah_area(conn)
    # Urutan tanpa beda huruf besar-kecil; tulisan aslinya tidak diubah.
    names = [r["name"] for r in conn.execute("SELECT name FROM area ORDER BY name")]
    assert names == ["Kuliah", "magang", "Pribadi"]


def test_update_ke_nama_kosong_atau_kembar_juga_ditolak(conn):
    _tambah_area(conn)
    conn.execute("INSERT INTO area (name) VALUES ('Magang')")
    conn.execute("INSERT INTO task (area_id, title, created_at) VALUES (1, 'a', 'x')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE area SET name = '  ' WHERE id = 2")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE area SET name = 'kuliah' WHERE id = 2")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE task SET title = '\t' WHERE id = 1")


# --- migrasi database lama (tanpa CHECK) ---

SKEMA_LAMA = """
CREATE TABLE area (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE);
CREATE TABLE task (
    id INTEGER PRIMARY KEY AUTOINCREMENT, area_id INTEGER NOT NULL REFERENCES area(id),
    title TEXT NOT NULL, deadline TEXT,
    status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'done')),
    created_at TEXT NOT NULL, completed_at TEXT
);
CREATE TABLE daily_log (
    log_date TEXT PRIMARY KEY,
    claude_code INTEGER NOT NULL CHECK (claude_code IN (0, 1)),
    github INTEGER NOT NULL CHECK (github IN (0, 1)),
    note TEXT
);
"""


def _database_lama(tmp_path):
    c = db.connect(str(tmp_path / "lama.db"))
    c.executescript(SKEMA_LAMA)
    c.execute("INSERT INTO area (name) VALUES ('Kuliah')")
    c.execute("INSERT INTO task (area_id, title, deadline, created_at) VALUES (1, 'Laporan', '2026-11-20 23:59', '2026-11-10 08:00')")
    c.execute("INSERT INTO task (area_id, title, deadline, status, created_at, completed_at) VALUES (1, 'Selesai', NULL, 'done', '2026-11-01 08:00', '2026-11-02 09:00')")
    c.execute("INSERT INTO daily_log VALUES ('2026-11-14', 1, 1, 'catatan')")
    c.commit()
    return c


def test_migrasi_mempertahankan_data_dan_menyalakan_check(tmp_path):
    c = _database_lama(tmp_path)
    assert c.execute("PRAGMA user_version").fetchone()[0] == 0

    db.init_db(c)

    assert c.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION
    tasks = c.execute("SELECT id, title, deadline, status, completed_at FROM task ORDER BY id").fetchall()
    assert [tuple(t) for t in tasks] == [
        (1, "Laporan", "2026-11-20 23:59", "todo", None),
        (2, "Selesai", None, "done", "2026-11-02 09:00"),
    ]
    assert tuple(c.execute("SELECT * FROM daily_log").fetchone()) == ("2026-11-14", 1, 1, "catatan")
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO daily_log VALUES ('2026-11-5', 1, 1, NULL)")
    names = {r["name"] for r in c.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert not any(n.endswith("_baru") for n in names)
    # v0 langsung naik ke v2: aturan nama ikut aktif.
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO area (name) VALUES ('kuliah')")
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO task (area_id, title, created_at) VALUES (1, ' ', 'x')")
    assert c.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_migrasi_tidak_dijalankan_dua_kali(tmp_path):
    c = _database_lama(tmp_path)
    db.init_db(c)
    db.init_db(c)
    assert c.execute("SELECT COUNT(*) FROM task").fetchone()[0] == 2


def test_migrasi_berhenti_jika_ada_baris_rusak_dan_tidak_mengubah_apa_pun(tmp_path):
    c = _database_lama(tmp_path)
    c.execute("INSERT INTO daily_log VALUES ('2026-11-5', 1, 1, NULL)")
    c.execute("INSERT INTO task (area_id, title, deadline, created_at) VALUES (1, 'Rusak', '2026-11-20', 'x')")
    c.commit()

    with pytest.raises(ValueError) as err:
        db.init_db(c)

    pesan = str(err.value)
    assert "daily_log.log_date='2026-11-5'" in pesan
    assert "task.id=3" in pesan and "'2026-11-20'" in pesan
    assert c.execute("PRAGMA user_version").fetchone()[0] == 0
    assert c.execute("SELECT COUNT(*) FROM daily_log").fetchone()[0] == 2  # baris rusak masih di tempatnya
    c.execute("INSERT INTO daily_log VALUES ('2026-12-1', 1, 1, NULL)")    # tabel lama utuh (tanpa CHECK)


def test_database_baru_langsung_berversi_terbaru(conn):
    assert conn.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION


# --- migrasi v1 ke v2: aturan nama (CHECK tidak kosong, UNIQUE tanpa beda huruf) ---

SKEMA_V1 = f"""
CREATE TABLE area (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE);
CREATE TABLE task (
    id INTEGER PRIMARY KEY AUTOINCREMENT, area_id INTEGER NOT NULL REFERENCES area(id),
    title TEXT NOT NULL,
    deadline TEXT CHECK (deadline IS NULL OR ({db.CEK_WAKTU.format(kolom="deadline")})),
    status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'done')),
    created_at TEXT NOT NULL, completed_at TEXT
);
CREATE TABLE daily_log (
    log_date TEXT PRIMARY KEY CHECK ({db.CEK_TANGGAL.format(kolom="log_date")}),
    claude_code INTEGER NOT NULL CHECK (claude_code IN (0, 1)),
    github INTEGER NOT NULL CHECK (github IN (0, 1)),
    note TEXT
);
PRAGMA user_version = 1;
"""


def _database_v1(tmp_path):
    c = db.connect(str(tmp_path / "v1.db"))
    c.executescript(SKEMA_V1)
    c.executemany("INSERT INTO area (name) VALUES (?)", [("Kuliah",), ("Magang",), ("Pribadi",)])
    c.execute("INSERT INTO task (area_id, title, deadline, created_at) VALUES (1, 'Laporan', '2026-11-20 23:59', '2026-11-10 08:00')")
    c.execute("INSERT INTO task (area_id, title, deadline, created_at) VALUES (2, 'Presentasi', NULL, '2026-11-11 08:00')")
    c.execute("INSERT INTO daily_log VALUES ('2026-11-14', 1, 0, 'catatan')")
    c.commit()
    return c


def _isi(c):
    """Seluruh isi database sebagai teks SQL, untuk memastikan tidak ada yang berubah."""
    return list(c.iterdump())


def test_migrasi_v1_ke_v2_data_utuh_dan_aturan_nama_aktif(tmp_path):
    c = _database_v1(tmp_path)
    c.execute("DELETE FROM area WHERE id = 3")  # id 3 pernah dipakai; tidak boleh dipakai ulang
    c.commit()

    db.init_db(c)

    assert c.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION == 2
    assert [tuple(r) for r in c.execute("SELECT id, name FROM area ORDER BY id")] == [
        (1, "Kuliah"), (2, "Magang"),
    ]
    relasi = c.execute(
        "SELECT task.id, task.title, area.name FROM task JOIN area ON area.id = task.area_id ORDER BY task.id"
    ).fetchall()
    assert [tuple(r) for r in relasi] == [(1, "Laporan", "Kuliah"), (2, "Presentasi", "Magang")]
    assert tuple(c.execute("SELECT * FROM daily_log").fetchone()) == ("2026-11-14", 1, 0, "catatan")

    assert c.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO area (name) VALUES ('kuliah')")
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO task (area_id, title, created_at) VALUES (1, '  ', 'x')")
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO task (area_id, title, created_at) VALUES (99, 'x', 'x')")
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO daily_log VALUES ('2026-11-5', 1, 1, NULL)")  # CHECK tanggal tetap ada

    assert c.execute("INSERT INTO area (name) VALUES ('Organisasi')").lastrowid == 4
    names = {r["name"] for r in c.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert not any(n.endswith("_baru") for n in names)


def test_migrasi_v1_dua_kali_tidak_mengubah_apa_pun(tmp_path):
    c = _database_v1(tmp_path)
    db.init_db(c)
    sesudah_pertama = _isi(c)
    db.init_db(c)
    assert _isi(c) == sesudah_pertama


def test_migrasi_v1_berhenti_jika_nama_area_bentrok(tmp_path):
    c = _database_v1(tmp_path)
    c.execute("INSERT INTO area (name) VALUES ('kuliah')")  # id 4; v1 masih membedakan huruf
    c.commit()
    sebelum = _isi(c)

    with pytest.raises(ValueError) as err:
        db.init_db(c)

    assert "area.id=1 name='Kuliah' bentrok dengan area.id=4 name='kuliah'" in str(err.value)
    assert c.execute("PRAGMA user_version").fetchone()[0] == 1
    assert _isi(c) == sebelum
    assert not c.in_transaction
    assert c.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_migrasi_v1_berhenti_jika_ada_nama_atau_judul_kosong(tmp_path):
    c = _database_v1(tmp_path)
    nama, judul = "  ", "\t"
    c.execute("INSERT INTO area (name) VALUES (?)", (nama,))  # id 4
    c.execute("INSERT INTO task (area_id, title, created_at) VALUES (1, ?, 'x')", (judul,))  # id 3
    c.commit()
    sebelum = _isi(c)

    with pytest.raises(ValueError) as err:
        db.init_db(c)

    pesan = str(err.value)
    assert f"area.id=4 name={nama!r}" in pesan
    assert f"task.id=3 title={judul!r}" in pesan
    assert c.execute("PRAGMA user_version").fetchone()[0] == 1
    assert _isi(c) == sebelum


def test_migrasi_v0_dengan_tanggal_rusak_dan_nama_bentrok_satu_pesan(tmp_path):
    c = _database_lama(tmp_path)
    c.execute("INSERT INTO area (name) VALUES ('KULIAH')")  # id 2
    c.execute("INSERT INTO daily_log VALUES ('2026-11-5', 1, 1, NULL)")
    c.commit()
    sebelum = _isi(c)

    with pytest.raises(ValueError) as err:
        db.init_db(c)

    pesan = str(err.value)
    assert "daily_log.log_date='2026-11-5'" in pesan
    assert "area.id=1 name='Kuliah' bentrok dengan area.id=2 name='KULIAH'" in pesan
    # Tidak berhenti di tengah jalan (v1): tetap v0 dan isinya sama persis.
    assert c.execute("PRAGMA user_version").fetchone()[0] == 0
    assert _isi(c) == sebelum


def test_migrasi_membuang_spasi_di_awal_dan_akhir_nama_lama(tmp_path):
    c = _database_v1(tmp_path)
    c.execute("UPDATE area SET name = ' Kuliah\t' WHERE id = 1")
    c.execute("UPDATE task SET title = '  Laporan\r\n' WHERE id = 1")
    c.commit()

    db.init_db(c)

    assert c.execute("SELECT name FROM area WHERE id = 1").fetchone()[0] == "Kuliah"
    assert c.execute("SELECT title FROM task WHERE id = 1").fetchone()[0] == "Laporan"


def test_migrasi_nama_bentrok_setelah_spasi_dibuang(tmp_path):
    c = _database_v1(tmp_path)
    c.execute("INSERT INTO area (name) VALUES (' kuliah')")  # id 4
    c.commit()
    sebelum = _isi(c)

    with pytest.raises(ValueError) as err:
        db.init_db(c)

    assert "area.id=1 name='Kuliah' bentrok dengan area.id=4 name=' kuliah'" in str(err.value)
    assert c.execute("PRAGMA user_version").fetchone()[0] == 1
    assert _isi(c) == sebelum


def test_migrasi_dibatalkan_jika_ada_task_tanpa_area(tmp_path):
    c = _database_v1(tmp_path)
    c.execute("PRAGMA foreign_keys = OFF")  # meniru edit manual yang melewati kunci tamu
    c.execute("INSERT INTO task (area_id, title, created_at) VALUES (99, 'Yatim', 'x')")  # id 3
    c.commit()
    c.execute("PRAGMA foreign_keys = ON")
    sebelum = _isi(c)

    with pytest.raises(ValueError) as err:
        db.init_db(c)

    assert "task.id=3" in str(err.value)
    assert c.execute("PRAGMA user_version").fetchone()[0] == 1
    assert _isi(c) == sebelum
    assert not c.in_transaction
    assert c.execute("PRAGMA foreign_keys").fetchone()[0] == 1
