import re
from datetime import date, datetime, timedelta
from pathlib import Path

from ctrlcoco import analytics, data, streak

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


# --- on-time rate (#62) ---


def _selesai(conn, area_id, selesai, deadline=None):
    """Task done dengan completed_at dan deadline tertentu (format 'YYYY-MM-DD HH:MM')."""
    t = datetime.strptime(selesai, "%Y-%m-%d %H:%M")
    task_id = data.add_task(conn, area_id, "t", deadline=deadline, now=t)
    data.complete_task(conn, task_id, now=t)
    return task_id


def test_on_time_tanpa_data(conn):
    assert analytics.on_time_rate(conn, AWAL, AKHIR) is None


def test_on_time_angka_diketahui(conn):
    area = data.add_area(conn, "Kuliah")
    _selesai(conn, area, "2026-03-05 09:00", "2026-03-05 17:00")  # tepat waktu
    _selesai(conn, area, "2026-03-06 09:00", "2026-03-10 17:00")  # tepat waktu
    _selesai(conn, area, "2026-03-07 18:00", "2026-03-07 17:00")  # terlambat
    _selesai(conn, area, "2026-03-08 09:00", "2026-03-09 09:00")  # tepat waktu
    assert analytics.on_time_rate(conn, AWAL, AKHIR) == 0.75


def test_on_time_semua_terlambat_nol_bukan_none(conn):
    area = data.add_area(conn, "Kuliah")
    _selesai(conn, area, "2026-03-07 18:00", "2026-03-07 17:00")
    assert analytics.on_time_rate(conn, AWAL, AKHIR) == 0.0


def test_on_time_selesai_tepat_pada_deadline_tepat_waktu(conn):
    area = data.add_area(conn, "Kuliah")
    _selesai(conn, area, "2026-03-05 17:00", "2026-03-05 17:00")
    assert analytics.on_time_rate(conn, AWAL, AKHIR) == 1.0


def test_on_time_telat_satu_menit_terlambat(conn):
    area = data.add_area(conn, "Kuliah")
    _selesai(conn, area, "2026-03-05 17:01", "2026-03-05 17:00")
    assert analytics.on_time_rate(conn, AWAL, AKHIR) == 0.0


def test_on_time_task_tanpa_deadline_tidak_dihitung(conn):
    area = data.add_area(conn, "Kuliah")
    _selesai(conn, area, "2026-03-05 09:00", "2026-03-05 17:00")  # tepat waktu
    _selesai(conn, area, "2026-03-06 18:00", "2026-03-06 17:00")  # terlambat
    angka_awal = analytics.on_time_rate(conn, AWAL, AKHIR)
    for hari in (7, 8, 9):  # tanpa deadline: tidak boleh mengubah pembilang maupun penyebut
        _selesai(conn, area, f"2026-03-0{hari} 09:00")
    assert angka_awal == 0.5
    assert analytics.on_time_rate(conn, AWAL, AKHIR) == 0.5


def test_on_time_hanya_task_tanpa_deadline_penyebut_nol(conn):
    area = data.add_area(conn, "Kuliah")
    _selesai(conn, area, "2026-03-05 09:00")
    assert analytics.on_time_rate(conn, AWAL, AKHIR) is None


def test_on_time_task_todo_berdeadline_tidak_dihitung(conn):
    area = data.add_area(conn, "Kuliah")
    data.add_task(conn, area, "belum", deadline="2026-03-05 17:00",
                  now=datetime(2026, 3, 1, 8, 0))
    assert analytics.on_time_rate(conn, AWAL, AKHIR) is None
    _selesai(conn, area, "2026-03-05 09:00", "2026-03-05 17:00")
    assert analytics.on_time_rate(conn, AWAL, AKHIR) == 1.0


def test_on_time_disaring_menurut_completed_at(conn):
    area = data.add_area(conn, "Kuliah")
    _selesai(conn, area, "2026-02-28 23:59", "2026-02-28 12:00")  # terlambat, sebelum rentang
    _selesai(conn, area, "2026-04-01 00:00", "2026-04-02 12:00")  # tepat waktu, setelah rentang
    _selesai(conn, area, "2026-03-15 10:00", "2026-03-15 12:00")  # di dalam rentang
    assert analytics.on_time_rate(conn, AWAL, AKHIR) == 1.0


def test_on_time_batas_rentang_inklusif(conn):
    area = data.add_area(conn, "Kuliah")
    _selesai(conn, area, "2026-03-01 00:00", "2026-03-01 08:00")  # hari awal, tepat waktu
    _selesai(conn, area, "2026-03-31 23:59", "2026-03-31 12:00")  # hari akhir, terlambat
    assert analytics.on_time_rate(conn, AWAL, AKHIR) == 0.5


def test_on_time_gabungan_semua_area(conn):
    kuliah = data.add_area(conn, "Kuliah")
    magang = data.add_area(conn, "Magang")
    _selesai(conn, kuliah, "2026-03-05 09:00", "2026-03-05 17:00")
    _selesai(conn, magang, "2026-03-06 18:00", "2026-03-06 17:00")
    assert analytics.on_time_rate(conn, AWAL, AKHIR) == 0.5


# --- streak terpanjang (#63) ---



def _hari_valid(conn, awal, jumlah):
    """`jumlah` hari valid berturut-turut mulai dari `awal`."""
    for i in range(jumlah):
        data.set_daily_log(conn, (awal + timedelta(days=i)).isoformat(), True, True)


def test_streak_terpanjang_tanpa_data(conn):
    assert analytics.longest_streak(conn, AWAL, AKHIR) == 0


def test_streak_terpanjang_satu_hari(conn):
    data.set_daily_log(conn, "2026-03-10", True, True)
    assert analytics.longest_streak(conn, AWAL, AKHIR) == 1


def test_streak_terpanjang_pilih_deretan_terpanjang(conn):
    _hari_valid(conn, date(2026, 3, 2), 2)
    _hari_valid(conn, date(2026, 3, 10), 5)
    _hari_valid(conn, date(2026, 3, 20), 3)
    assert analytics.longest_streak(conn, AWAL, AKHIR) == 5


def test_streak_terpanjang_hari_tidak_lengkap_memutus(conn):
    _hari_valid(conn, date(2026, 3, 1), 3)
    data.set_daily_log(conn, "2026-03-04", True, False)  # hanya Claude Code
    data.set_daily_log(conn, "2026-03-05", False, True)  # hanya GitHub
    _hari_valid(conn, date(2026, 3, 6), 2)
    assert analytics.longest_streak(conn, AWAL, AKHIR) == 3


def test_streak_terpanjang_hari_tidak_tercatat_memutus(conn):
    _hari_valid(conn, date(2026, 3, 1), 2)
    _hari_valid(conn, date(2026, 3, 4), 2)  # 3 Maret tidak tercatat
    assert analytics.longest_streak(conn, AWAL, AKHIR) == 2


def test_streak_terpanjang_di_luar_rentang_diabaikan(conn):
    _hari_valid(conn, date(2026, 2, 1), 10)  # sebelum rentang
    _hari_valid(conn, date(2026, 4, 1), 10)  # setelah rentang
    _hari_valid(conn, date(2026, 3, 10), 2)
    assert analytics.longest_streak(conn, AWAL, AKHIR) == 2


def test_streak_terpanjang_deretan_terpotong_batas_rentang(conn):
    # Deretan 27 Feb sampai 3 Mar: hanya bagian di dalam rentang (1 sampai 3 Maret) dihitung.
    _hari_valid(conn, date(2026, 2, 27), 5)
    assert analytics.longest_streak(conn, AWAL, AKHIR) == 3


def test_streak_terpanjang_batas_rentang_inklusif(conn):
    _hari_valid(conn, date(2026, 3, 30), 2)  # 30 dan 31 Maret
    assert analytics.longest_streak(conn, AWAL, AKHIR) == 2
    assert analytics.longest_streak(conn, date(2026, 3, 31), date(2026, 3, 31)) == 1


def test_streak_terpanjang_rentang_terbalik_nol(conn):
    _hari_valid(conn, date(2026, 3, 10), 3)
    assert analytics.longest_streak(conn, AKHIR, AWAL) == 0


def test_streak_terpanjang_sama_dengan_get_streak_bila_sedang_berjalan(conn):
    hari_ini = date(2026, 3, 10)
    _hari_valid(conn, date(2026, 3, 6), 5)  # 6 sampai 10 Maret, berakhir hari ini
    assert streak.get_streak(conn, today=hari_ini) == 5
    assert analytics.longest_streak(conn, AWAL, hari_ini) == 5


def test_streak_lama_lebih_panjang_dari_streak_berjalan(conn):
    hari_ini = date(2026, 3, 20)
    _hari_valid(conn, date(2026, 3, 1), 10)  # 1 sampai 10 Maret
    # 11 sampai 17 Maret putus
    _hari_valid(conn, date(2026, 3, 18), 3)  # 18 sampai 20 Maret, sampai hari ini
    assert streak.get_streak(conn, today=hari_ini) == 3
    assert analytics.longest_streak(conn, AWAL, hari_ini) == 10


def test_streak_terpanjang_memakai_definisi_hari_valid_streak_py(conn):
    # Aturan hari valid satu sumber: konstanta di streak.py, dipakai kedua modul.
    sumber_analytics = _sumber()
    assert "KONDISI_HARI_VALID" in sumber_analytics
    assert "claude_code" not in sumber_analytics
    assert "KONDISI_HARI_VALID" in Path(streak.__file__).read_text(encoding="utf-8")


# --- jendela Ringkasan (#64): rentang tetap dan pemeriksaan ada data ---


def test_rentang_ringkasan_12_minggu_berakhir_hari_ini():
    awal, akhir = analytics.rentang_ringkasan(date(2026, 3, 10))
    assert analytics.RENTANG_MINGGU == 12
    assert akhir == date(2026, 3, 10)
    assert awal == date(2025, 12, 17)
    assert (akhir - awal).days + 1 == 84  # awal dan akhir sama-sama dihitung


def test_rentang_ringkasan_melewati_pergantian_tahun():
    awal, akhir = analytics.rentang_ringkasan(date(2026, 1, 5))
    assert (awal, akhir) == (date(2025, 10, 14), date(2026, 1, 5))


def test_ada_data_database_kosong_false(conn):
    assert analytics.ada_data(conn) is False


def test_ada_data_area_saja_belum_dihitung(conn):
    data.add_area(conn, "Kuliah")
    assert analytics.ada_data(conn) is False


def test_ada_data_satu_task_true_walau_kolom_tanggal_kosong(conn):
    # Task todo tanpa deadline: deadline dan completed_at sama-sama NULL.
    area_id = data.add_area(conn, "Kuliah")
    data.add_task(conn, area_id, "Laporan")
    assert analytics.ada_data(conn) is True


def test_ada_data_satu_log_true_walau_catatan_kosong(conn):
    data.set_daily_log(conn, "2026-03-10", False, False)  # note NULL, bukan hari valid
    assert analytics.ada_data(conn) is True


def test_ada_data_seluruh_database_bukan_hanya_rentang(conn):
    # Task jauh sebelum rentang 12 minggu tetap membuat database tidak kosong.
    area_id = data.add_area(conn, "Kuliah")
    data.add_task(conn, area_id, "Lama", now=datetime(2020, 1, 1, 8, 0))
    awal, akhir = analytics.rentang_ringkasan(date(2026, 3, 10))
    assert analytics.completion_rate_per_area(conn, awal, akhir)[0].total == 0
    assert analytics.ada_data(conn) is True
