import inspect
import re
import sqlite3
from datetime import datetime

import pytest

from ctrlcoco import data, db

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


KOSONG = ["", "   ", "\t", " \n "]


def test_add_area_membuang_spasi_di_awal_dan_akhir(conn):
    data.add_area(conn, " Kuliah ")
    assert [a["name"] for a in data.list_areas(conn)] == ["Kuliah"]


@pytest.mark.parametrize("nama", KOSONG)
def test_add_area_nama_kosong_ditolak(conn, nama):
    with pytest.raises(ValueError, match="Nama area wajib diisi"):
        data.add_area(conn, nama)
    assert data.list_areas(conn) == []
    assert not conn.in_transaction


@pytest.mark.parametrize("nama", ["kuliah", "KULIAH", " KULIAH "])
def test_add_area_kembar_beda_huruf_ditolak_dengan_nama_yang_sudah_ada(conn, nama):
    data.add_area(conn, "Kuliah")
    with pytest.raises(ValueError, match="^Area sudah ada: Kuliah$"):
        data.add_area(conn, nama)
    assert [a["name"] for a in data.list_areas(conn)] == ["Kuliah"]
    assert not conn.in_transaction


def test_list_areas_mengembalikan_nama_seperti_disimpan(conn):
    for nama in ("Pribadi", "magang", "Kuliah"):
        data.add_area(conn, nama)
    assert [a["name"] for a in data.list_areas(conn)] == ["Kuliah", "magang", "Pribadi"]


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


def test_add_task_membuang_spasi_di_awal_dan_akhir_judul(conn):
    area_id = data.add_area(conn, "Kuliah")
    data.add_task(conn, area_id, "  Baca bab 1\t", now=NOW)
    assert data.list_tasks(conn)[0]["title"] == "Baca bab 1"


@pytest.mark.parametrize("judul", KOSONG)
def test_add_task_judul_kosong_ditolak(conn, judul):
    area_id = data.add_area(conn, "Kuliah")
    with pytest.raises(ValueError, match="Judul task wajib diisi"):
        data.add_task(conn, area_id, judul, now=NOW)
    assert data.list_tasks(conn) == []
    assert not conn.in_transaction


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
        " 2026-03-12 23:59 ",   # spasi hanya dibuang di simpan_task_baru, bukan di add_task
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


# --- tulis yang gagal ---

@pytest.mark.parametrize(
    "tulis_gagal",
    [
        lambda conn: data.add_area(conn, "Kuliah"),       # nama kembar
        lambda conn: data.add_task(conn, 999, "Tanpa area", now=NOW),
        lambda conn: data.complete_task(conn, 999),       # task tidak ada
    ],
    ids=["add_area", "add_task", "complete_task"],
)
def test_tulis_gagal_tidak_meninggalkan_transaksi_terbuka(conn, tulis_gagal):
    data.add_area(conn, "Kuliah")
    with pytest.raises(ValueError):
        tulis_gagal(conn)
    assert not conn.in_transaction


def test_tulis_gagal_tidak_mengunci_koneksi_lain(tmp_path):
    path = tmp_path / "coba.db"
    pertama = db.connect(path)
    db.init_db(pertama)
    data.add_area(pertama, "Kuliah")
    with pytest.raises(ValueError):
        data.add_area(pertama, "Kuliah")

    # Koneksi kedua berperan sebagai proses lain. timeout=0: langsung gagal jika terkunci.
    kedua = sqlite3.connect(path, timeout=0)
    kedua.execute("INSERT INTO area (name) VALUES ('Lain')")
    kedua.commit()
    kedua.close()
    pertama.close()


# --- pesan error sesuai penyebab ---

def test_add_task_pesan_error_sesuai_penyebab(conn):
    area_id = data.add_area(conn, "Kuliah")
    with pytest.raises(ValueError, match="Area tidak ditemukan: 999"):
        data.add_task(conn, 999, "Tugas", now=NOW)
    with pytest.raises(ValueError, match="Judul task wajib diisi"):
        data.add_task(conn, area_id, None, now=NOW)
    # Penyebab yang tidak dikenal (area_id kosong) tidak boleh disamarkan jadi "area tidak ditemukan".
    with pytest.raises(sqlite3.IntegrityError):
        data.add_task(conn, None, "Tugas", now=NOW)
    assert data.list_tasks(conn) == []
    assert not conn.in_transaction


def test_add_area_pesan_error_sesuai_penyebab(conn):
    data.add_area(conn, "Kuliah")
    with pytest.raises(ValueError, match="Area sudah ada: Kuliah"):
        data.add_area(conn, "Kuliah")
    with pytest.raises(ValueError, match="Nama area wajib diisi"):
        data.add_area(conn, None)
    assert [a["name"] for a in data.list_areas(conn)] == ["Kuliah"]


def test_pelanggaran_check_tidak_disamarkan_jadi_pesan_area(conn):
    """Sejak ada CHECK di skema, jenis pelanggaran baru bisa muncul; pesannya harus jujur."""
    area_id = data.add_area(conn, "Kuliah")
    with pytest.raises(sqlite3.IntegrityError) as err:
        with conn:
            conn.execute(
                "INSERT INTO task (area_id, title, status, created_at) VALUES (?, 'x', 'selesai', 'x')",
                (area_id,),
            )
    assert err.value.sqlite_errorname == "SQLITE_CONSTRAINT_CHECK"


# Tiap fungsi yang menulis ke database, dipanggil dengan argumen yang valid.
PENULIS = {
    "add_area": lambda c: data.add_area(c, "Baru"),
    "add_task": lambda c: data.add_task(c, 1, "Tugas baru", now=NOW),
    "complete_task": lambda c: data.complete_task(c, 1, now=NOW),
    "set_daily_log": lambda c: data.set_daily_log(c, "2026-03-10", True, True),
    "simpan_task_baru": lambda c: data.simpan_task_baru(c, "Area baru", "Tugas baru", "", now=NOW),
}


@pytest.mark.parametrize("nama", sorted(PENULIS))
def test_tulis_saat_database_terkunci_tidak_meninggalkan_transaksi(tmp_path, nama):
    path = tmp_path / "kunci.db"
    c = db.connect(path)
    db.init_db(c)
    area_id = data.add_area(c, "Kuliah")
    data.add_task(c, area_id, "Tugas", now=NOW)
    c.execute("PRAGMA busy_timeout = 0")  # langsung gagal jika terkunci, jangan menunggu

    # Koneksi lain berperan sebagai proses lain yang sedang menulis ke database yang sama.
    lain = sqlite3.connect(path, isolation_level=None)
    lain.execute("BEGIN EXCLUSIVE")
    try:
        with pytest.raises(sqlite3.OperationalError):
            PENULIS[nama](c)
        assert not c.in_transaction
    finally:
        lain.rollback()
        lain.close()
        c.close()


def test_semua_fungsi_tulis_di_data_py_ikut_dites_saat_terkunci():
    """Penjaga: fungsi tulis baru di data.py harus ditambahkan ke PENULIS di atas."""
    fungsi_data = {
        nama: inspect.getsource(fungsi)
        for nama, fungsi in inspect.getmembers(data, inspect.isfunction)
        if fungsi.__module__ == data.__name__
    }
    # Pembantu berawalan _ yang menulis sengaja tidak commit; ia selalu dipanggil di
    # dalam `with conn:` milik fungsi publik, jadi yang dites cukup fungsi publiknya.
    # Fungsi publik dianggap menulis jika berisi SQL tulis, atau memanggil pembantu itu.
    pola_tulis = r"\b(INSERT|UPDATE|DELETE)\b"
    pembantu_tulis = [
        nama for nama, src in fungsi_data.items()
        if nama.startswith("_") and re.search(pola_tulis, src)
    ]
    if pembantu_tulis:
        pola_tulis += r"|\b(" + "|".join(pembantu_tulis) + r")\("
    penulis = {
        nama for nama, src in fungsi_data.items()
        if not nama.startswith("_") and re.search(pola_tulis, src)
    }
    assert penulis == set(PENULIS), (
        "Fungsi tulis di data.py tidak sama dengan daftar PENULIS di tes ini. "
        "Tambahkan fungsi baru ke PENULIS, dan pakai `with conn:` di dalamnya."
    )


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


def test_set_daily_log_tanpa_note_mempertahankan_note_lama(conn):
    data.set_daily_log(conn, "2026-03-10", True, False, note="pagi: belajar QTimer")
    data.set_daily_log(conn, "2026-03-10", True, True)  # centang GitHub menyusul, tanpa note
    log = data.get_daily_log(conn, "2026-03-10")
    assert log["github"] == 1
    assert log["note"] == "pagi: belajar QTimer"


def test_set_daily_log_note_kosong_mengosongkan_note(conn):
    data.set_daily_log(conn, "2026-03-10", True, False, note="salah tulis")
    data.set_daily_log(conn, "2026-03-10", True, False, note="")
    assert data.get_daily_log(conn, "2026-03-10")["note"] == ""


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


# --- simpan_task_baru: logika form tambah task, semua atau tidak sama sekali ---

def _jumlah(conn, tabel):
    return conn.execute(f"SELECT COUNT(*) FROM {tabel}").fetchone()[0]


def test_simpan_task_baru_ke_area_lama(conn):
    kuliah = data.add_area(conn, "Kuliah")
    task_id = data.simpan_task_baru(conn, "Kuliah", "Laporan", "2026-03-12 23:59", now=NOW)
    task = data.list_tasks(conn)[0]
    assert task["id"] == task_id
    assert task["area_id"] == kuliah
    assert task["title"] == "Laporan"
    assert task["deadline"] == "2026-03-12 23:59"
    assert task["created_at"] == "2026-03-10 09:30"
    assert _jumlah(conn, "area") == 1
    assert not conn.in_transaction


def test_simpan_task_baru_membuat_area_baru(conn):
    data.add_area(conn, "Kuliah")
    data.simpan_task_baru(conn, "Organisasi", "Rapat", "", now=NOW)
    areas = {a["name"]: a["id"] for a in data.list_areas(conn)}
    assert set(areas) == {"Kuliah", "Organisasi"}
    assert data.list_tasks(conn)[0]["area_id"] == areas["Organisasi"]


@pytest.mark.parametrize("teks_area", ["kuliah", " KULIAH ", "Kuliah\t"])
def test_simpan_task_baru_area_beda_huruf_memakai_area_lama(conn, teks_area):
    kuliah = data.add_area(conn, "Kuliah")
    data.simpan_task_baru(conn, teks_area, "Laporan", "", now=NOW)
    assert [a["name"] for a in data.list_areas(conn)] == ["Kuliah"]
    assert data.list_tasks(conn)[0]["area_id"] == kuliah


@pytest.mark.parametrize("teks_deadline", ["", "   ", "\t", None])
def test_simpan_task_baru_deadline_kosong_jadi_none(conn, teks_deadline):
    data.simpan_task_baru(conn, "Kuliah", "Laporan", teks_deadline, now=NOW)
    assert data.list_tasks(conn)[0]["deadline"] is None


def test_simpan_task_baru_membuang_spasi_di_sekitar_deadline(conn):
    data.simpan_task_baru(conn, "Kuliah", "Laporan", " 2026-03-12 23:59 ", now=NOW)
    assert data.list_tasks(conn)[0]["deadline"] == "2026-03-12 23:59"


@pytest.mark.parametrize(
    "teks_area, judul, teks_deadline, pesan",
    [
        ("Organisasi", "Rapat", "2026-3-12 9:00", "YYYY-MM-DD HH:MM"),
        ("Organisasi", "Rapat", "2026-02-30 10:00", "YYYY-MM-DD HH:MM"),
        ("Organisasi", "   ", "", "Judul task wajib diisi"),
        ("   ", "Rapat", "", "Nama area wajib diisi"),
    ],
    ids=["deadline_format_salah", "deadline_mustahil", "judul_kosong", "area_kosong"],
)
def test_simpan_task_baru_gagal_validasi_tidak_meninggalkan_apa_pun(
    conn, teks_area, judul, teks_deadline, pesan
):
    data.add_area(conn, "Kuliah")
    with pytest.raises(ValueError, match=pesan):
        data.simpan_task_baru(conn, teks_area, judul, teks_deadline, now=NOW)
    assert [a["name"] for a in data.list_areas(conn)] == ["Kuliah"]
    assert _jumlah(conn, "task") == 0
    assert not conn.in_transaction


def test_simpan_task_baru_error_database_membatalkan_area_baru(conn):
    """Area baru sudah disisipkan, lalu INSERT task gagal di database: area ikut dibatalkan."""
    data.add_area(conn, "Kuliah")
    conn.execute(
        "CREATE TEMP TRIGGER tolak_task BEFORE INSERT ON task"
        " BEGIN SELECT RAISE(ABORT, 'task ditolak'); END"
    )
    with pytest.raises(sqlite3.Error, match="task ditolak"):
        data.simpan_task_baru(conn, "Organisasi", "Rapat", "2026-03-12 23:59", now=NOW)
    assert [a["name"] for a in data.list_areas(conn)] == ["Kuliah"]
    assert _jumlah(conn, "task") == 0
    assert not conn.in_transaction


# --- list_todo_untuk_selesai: daftar untuk form "Selesaikan task" ---

def test_list_todo_untuk_selesai_urutan_deadline_lalu_tanpa_deadline(conn):
    kuliah = data.add_area(conn, "Kuliah")
    magang = data.add_area(conn, "Magang")
    data.add_task(conn, kuliah, "Tanpa deadline 1", now=NOW)                        # id 1
    data.add_task(conn, magang, "Paling akhir", "2026-03-20 10:00", now=NOW)       # id 2
    data.add_task(conn, kuliah, "Kembar B", "2026-03-12 08:00", now=NOW)           # id 3
    data.add_task(conn, magang, "Paling awal", "2026-03-11 23:59", now=NOW)        # id 4
    data.add_task(conn, kuliah, "Kembar A", "2026-03-12 08:00", now=NOW)           # id 5
    data.add_task(conn, magang, "Tanpa deadline 2", now=NOW)                        # id 6

    hasil = [tuple(r) for r in data.list_todo_untuk_selesai(conn)]
    assert hasil == [
        (4, "Paling awal", "Magang", "2026-03-11 23:59"),
        (3, "Kembar B", "Kuliah", "2026-03-12 08:00"),   # deadline sama: menurut id
        (5, "Kembar A", "Kuliah", "2026-03-12 08:00"),
        (2, "Paling akhir", "Magang", "2026-03-20 10:00"),
        (1, "Tanpa deadline 1", "Kuliah", None),          # tanpa deadline paling bawah
        (6, "Tanpa deadline 2", "Magang", None),
    ]


def test_list_todo_untuk_selesai_tanpa_task_done(conn):
    area_id = data.add_area(conn, "Kuliah")
    selesai = data.add_task(conn, area_id, "Sudah", "2026-03-11 10:00", now=NOW)
    data.add_task(conn, area_id, "Belum", "2026-03-12 10:00", now=NOW)
    data.complete_task(conn, selesai, now=NOW)
    hasil = data.list_todo_untuk_selesai(conn)
    assert [(r["title"], r["area"]) for r in hasil] == [("Belum", "Kuliah")]


def test_list_todo_untuk_selesai_kosong(conn):
    assert data.list_todo_untuk_selesai(conn) == []
