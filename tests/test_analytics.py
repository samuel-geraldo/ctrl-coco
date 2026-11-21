import re
from datetime import date, datetime
from pathlib import Path

from ctrlcoco import analytics, data

AWAL = date(2026, 3, 1)
AKHIR = date(2026, 3, 31)


def _task(conn, area_id, dibuat, selesai=False):
    """Task dengan created_at tertentu; selesai=True menandainya done."""
    t = datetime.strptime(dibuat, "%Y-%m-%d %H:%M")
    task_id = data.add_task(conn, area_id, "t", now=t)
    if selesai:
        data.complete_task(conn, task_id, now=t)
    return task_id


def test_tanpa_area(conn):
    assert analytics.completion_rate_per_area(conn, AWAL, AKHIR) == []


def test_angka_beberapa_area(conn):
    kuliah = data.add_area(conn, "Kuliah")
    magang = data.add_area(conn, "Magang")
    pribadi = data.add_area(conn, "Pribadi")
    for selesai in (True, True, False, False):
        _task(conn, kuliah, "2026-03-05 09:00", selesai)
    _task(conn, magang, "2026-03-06 09:00", True)
    for _ in range(3):
        _task(conn, pribadi, "2026-03-07 09:00")

    hasil = {r.nama: r for r in analytics.completion_rate_per_area(conn, AWAL, AKHIR)}

    assert (hasil["Kuliah"].selesai, hasil["Kuliah"].total, hasil["Kuliah"].rate) == (2, 4, 0.5)
    assert (hasil["Magang"].selesai, hasil["Magang"].total, hasil["Magang"].rate) == (1, 1, 1.0)
    assert (hasil["Pribadi"].selesai, hasil["Pribadi"].total, hasil["Pribadi"].rate) == (0, 3, 0.0)


def test_area_tanpa_task_penyebut_nol(conn):
    data.add_area(conn, "Kosong")
    [r] = analytics.completion_rate_per_area(conn, AWAL, AKHIR)
    assert (r.nama, r.selesai, r.total, r.rate) == ("Kosong", 0, 0, None)


def test_task_di_luar_rentang_diabaikan(conn):
    area = data.add_area(conn, "Kuliah")
    _task(conn, area, "2026-02-28 23:59", True)
    _task(conn, area, "2026-04-01 00:00", True)
    _task(conn, area, "2026-03-15 12:00", False)

    [r] = analytics.completion_rate_per_area(conn, AWAL, AKHIR)
    assert (r.selesai, r.total, r.rate) == (0, 1, 0.0)


def test_area_hanya_punya_task_di_luar_rentang_penyebut_nol(conn):
    area = data.add_area(conn, "Kuliah")
    _task(conn, area, "2026-01-10 10:00", True)
    [r] = analytics.completion_rate_per_area(conn, AWAL, AKHIR)
    assert (r.total, r.rate) == (0, None)


def test_batas_rentang_inklusif(conn):
    area = data.add_area(conn, "Kuliah")
    _task(conn, area, "2026-03-01 00:00", True)  # hari awal, jam paling awal
    _task(conn, area, "2026-03-31 23:59", False)  # hari akhir, jam paling akhir
    [r] = analytics.completion_rate_per_area(conn, AWAL, AKHIR)
    assert (r.selesai, r.total) == (1, 2)


def test_awal_sama_dengan_akhir(conn):
    area = data.add_area(conn, "Kuliah")
    _task(conn, area, "2026-03-10 08:00", True)
    _task(conn, area, "2026-03-11 08:00", True)
    [r] = analytics.completion_rate_per_area(conn, date(2026, 3, 10), date(2026, 3, 10))
    assert (r.selesai, r.total) == (1, 1)


def test_rentang_terbalik_kosong_bukan_galat(conn):
    area = data.add_area(conn, "Kuliah")
    _task(conn, area, "2026-03-10 08:00", True)
    [r] = analytics.completion_rate_per_area(conn, AKHIR, AWAL)
    assert (r.total, r.rate) == (0, None)


def test_urutan_area_tanpa_beda_huruf(conn):
    for nama in ("Pribadi", "magang", "Kuliah"):
        data.add_area(conn, nama)
    nama = [r.nama for r in analytics.completion_rate_per_area(conn, AWAL, AKHIR)]
    assert nama == ["Kuliah", "magang", "Pribadi"]


def test_nama_area_dengan_tanda_kutip_aman(conn):
    # Nama berisi karakter SQL tidak mengganggu kueri berparameter.
    data.add_area(conn, "Robert'); DROP TABLE task;--")
    [r] = analytics.completion_rate_per_area(conn, AWAL, AKHIR)
    assert r.nama == "Robert'); DROP TABLE task;--"
    assert conn.execute("SELECT COUNT(*) FROM task").fetchone()[0] == 0


def _sumber():
    return Path(analytics.__file__).read_text(encoding="utf-8")


def test_tanpa_impor_qt():
    assert not re.search(r"^\s*(import|from)\s+(PySide6|PyQt)", _sumber(), re.M)


def test_kueri_tanpa_f_string():
    # SQL disusun dari konstanta biasa, nilai masukan hanya lewat parameter "?".
    assert not re.search(r"""\bf["']""", _sumber())
