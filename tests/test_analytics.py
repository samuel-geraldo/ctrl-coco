import re
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

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


# --- heatmap kalender (#65): daftar hari valid dalam rentang ---


def _log(conn, hari, claude_code, github, note=None):
    data.set_daily_log(conn, hari.isoformat(), claude_code, github, note)


def test_hari_valid_tanpa_data(conn):
    assert analytics.hari_valid(conn, AWAL, AKHIR) == []


def test_hari_valid_sesuai_data_contoh_dan_urut_naik(conn):
    _log(conn, date(2026, 3, 20), True, True)
    _log(conn, date(2026, 3, 5), True, True, note="rapat")
    _log(conn, date(2026, 3, 6), True, True)
    assert analytics.hari_valid(conn, AWAL, AKHIR) == [
        date(2026, 3, 5),
        date(2026, 3, 6),
        date(2026, 3, 20),
    ]


def test_hari_valid_hari_di_luar_rentang_tidak_ikut(conn):
    _log(conn, date(2026, 2, 28), True, True)
    _log(conn, date(2026, 3, 15), True, True)
    _log(conn, date(2026, 4, 1), True, True)
    assert analytics.hari_valid(conn, AWAL, AKHIR) == [date(2026, 3, 15)]


def test_hari_valid_batas_rentang_inklusif(conn):
    _log(conn, AWAL, True, True)
    _log(conn, AKHIR, True, True)
    assert analytics.hari_valid(conn, AWAL, AKHIR) == [AWAL, AKHIR]


def test_hari_valid_hari_tidak_valid_tidak_ikut(conn):
    _log(conn, date(2026, 3, 1), True, False)   # hanya Claude Code
    _log(conn, date(2026, 3, 2), False, True)   # hanya GitHub
    _log(conn, date(2026, 3, 3), False, False)  # keduanya kosong
    assert analytics.hari_valid(conn, AWAL, AKHIR) == []


def test_hari_valid_rentang_terbalik_kosong(conn):
    _log(conn, date(2026, 3, 10), True, True)
    assert analytics.hari_valid(conn, AKHIR, AWAL) == []


def test_hari_valid_task_tanpa_tanggal_tidak_memengaruhi(conn):
    # Task todo tanpa deadline dan tanpa completed_at tidak membuat hari menjadi valid.
    area_id = data.add_area(conn, "Kuliah")
    data.add_task(conn, area_id, "Laporan")
    _log(conn, date(2026, 3, 10), True, True)
    assert analytics.hari_valid(conn, AWAL, AKHIR) == [date(2026, 3, 10)]


def test_hari_valid_konsisten_dengan_streak_terpanjang(conn):
    _hari_valid(conn, date(2026, 3, 10), 4)
    hari = analytics.hari_valid(conn, AWAL, AKHIR)
    assert len(hari) == 4
    assert analytics.longest_streak(conn, AWAL, AKHIR) == 4


def _durasi(conn, area_id, dibuat, selesai):
    """Task done dengan created_at dan completed_at tertentu."""
    task_id = _task(conn, area_id, dibuat)
    data.complete_task(conn, task_id, now=datetime.strptime(selesai, "%Y-%m-%d %H:%M"))


def _median(conn, awal=AWAL, akhir=AKHIR):
    return {r.nama: r.jam for r in analytics.median_penyelesaian_per_area(conn, awal, akhir)}


def test_median_jumlah_ganjil(conn):
    area = data.add_area(conn, "Kuliah")
    _durasi(conn, area, "2026-03-05 08:00", "2026-03-05 09:00")  # 1 jam
    _durasi(conn, area, "2026-03-05 08:00", "2026-03-05 10:00")  # 2 jam
    _durasi(conn, area, "2026-03-05 08:00", "2026-03-09 12:00")  # 100 jam
    assert _median(conn) == {"Kuliah": 2.0}


def test_median_jumlah_genap(conn):
    area = data.add_area(conn, "Kuliah")
    for selesai in ("09:00", "10:00", "11:30", "18:00"):  # 1, 2, 3.5, 10 jam
        _durasi(conn, area, "2026-03-05 08:00", f"2026-03-05 {selesai}")
    assert _median(conn) == {"Kuliah": 2.75}


def test_median_dipisah_per_area_dan_urut_nama(conn):
    olahraga = data.add_area(conn, "Olahraga")
    kuliah = data.add_area(conn, "kuliah")
    _durasi(conn, olahraga, "2026-03-05 08:00", "2026-03-05 08:30")
    _durasi(conn, kuliah, "2026-03-05 08:00", "2026-03-06 08:00")
    hasil = analytics.median_penyelesaian_per_area(conn, AWAL, AKHIR)
    assert [(r.nama, r.jam) for r in hasil] == [("kuliah", 24.0), ("Olahraga", 0.5)]


def test_median_area_tanpa_task_selesai_none(conn):
    data.add_area(conn, "Kosong")
    area = data.add_area(conn, "Todo")
    _task(conn, area, "2026-03-05 08:00")
    assert _median(conn) == {"Kosong": None, "Todo": None}


def test_median_task_todo_diabaikan(conn):
    area = data.add_area(conn, "Kuliah")
    _durasi(conn, area, "2026-03-05 08:00", "2026-03-05 12:00")
    _task(conn, area, "2026-03-05 08:00")
    assert _median(conn) == {"Kuliah": 4.0}


def test_median_rentang_menurut_tanggal_selesai_inklusif(conn):
    area = data.add_area(conn, "Kuliah")
    _durasi(conn, area, "2026-02-27 23:59", "2026-02-28 23:59")  # sebelum rentang
    _durasi(conn, area, "2026-02-28 00:00", "2026-03-01 00:00")  # hari awal: 24 jam
    _durasi(conn, area, "2026-03-31 21:59", "2026-03-31 23:59")  # hari akhir: 2 jam
    _durasi(conn, area, "2026-03-31 00:00", "2026-04-01 00:00")  # sesudah rentang
    assert _median(conn) == {"Kuliah": 13.0}


def test_median_tanpa_area(conn):
    assert analytics.median_penyelesaian_per_area(conn, AWAL, AKHIR) == []


NAMA_HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def _per_hari(conn, awal=AWAL, akhir=AKHIR):
    """{nama hari: (task selesai, hari valid)}, hanya hari yang tidak nol."""
    return {
        r.nama: (r.task_selesai, r.hari_valid)
        for r in analytics.produktivitas_per_hari(conn, awal, akhir)
        if r.task_selesai or r.hari_valid
    }


def test_per_hari_database_kosong_tujuh_baris_nol(conn):
    hasil = analytics.produktivitas_per_hari(conn, AWAL, AKHIR)
    assert [(r.nama, r.task_selesai, r.hari_valid) for r in hasil] == [
        (nama, 0, 0) for nama in NAMA_HARI
    ]


def test_per_hari_angka_diketahui(conn):
    area = data.add_area(conn, "Kuliah")
    # 2026-03-02 dan 2026-03-09 hari Senin; 2026-03-04 hari Rabu.
    for selesai in ("2026-03-02 09:00", "2026-03-09 23:59", "2026-03-04 00:00"):
        _task(conn, area, selesai, True)
    for tanggal in ("2026-03-02", "2026-03-06", "2026-03-13"):  # Senin, Jumat, Jumat
        data.set_daily_log(conn, tanggal, True, True)
    assert _per_hari(conn) == {"Senin": (2, 1), "Rabu": (1, 0), "Jumat": (0, 2)}


def test_per_hari_minggu_tidak_tertukar_dengan_senin(conn):
    area = data.add_area(conn, "Kuliah")
    _task(conn, area, "2026-03-08 12:00", True)  # Minggu
    data.set_daily_log(conn, "2026-03-08", True, True)
    hasil = analytics.produktivitas_per_hari(conn, AWAL, AKHIR)
    assert (hasil[0].nama, hasil[0].task_selesai, hasil[0].hari_valid) == ("Senin", 0, 0)
    assert (hasil[6].nama, hasil[6].task_selesai, hasil[6].hari_valid) == ("Minggu", 1, 1)


def test_per_hari_menurut_completed_at_bukan_created_at(conn):
    area = data.add_area(conn, "Kuliah")
    _durasi(conn, area, "2026-03-02 08:00", "2026-03-03 08:00")  # dibuat Senin, selesai Selasa
    assert _per_hari(conn) == {"Selasa": (1, 0)}


def test_per_hari_todo_dan_log_tidak_valid_diabaikan(conn):
    area = data.add_area(conn, "Kuliah")
    _task(conn, area, "2026-03-02 09:00")
    data.set_daily_log(conn, "2026-03-02", True, False)
    assert _per_hari(conn) == {}


def test_per_hari_di_luar_rentang_diabaikan_batas_inklusif(conn):
    area = data.add_area(conn, "Kuliah")
    # AWAL 2026-03-01 hari Minggu, AKHIR 2026-03-31 hari Selasa.
    for selesai in (
        "2026-02-28 23:59",
        "2026-03-01 00:00",
        "2026-03-31 23:59",
        "2026-04-01 00:00",
    ):
        _task(conn, area, selesai, True)
    for tanggal in ("2026-02-28", "2026-03-01", "2026-03-31", "2026-04-01"):
        data.set_daily_log(conn, tanggal, True, True)
    assert _per_hari(conn) == {"Selasa": (1, 1), "Minggu": (1, 1)}


# --- tinjauan mingguan: 7 hari terakhir sampai hari ini (#80) ---

SEKARANG = datetime(2026, 3, 10, 15, 0)  # 7 hari: 04/03 sampai 10/03
AWAL_MINGGU = date(2026, 3, 4)


def _task_tinjauan(conn, area_id, deadline=None, selesai=None):
    """Task dengan deadline dan waktu selesai tertentu; selesai=None berarti masih todo."""
    dibuat = datetime(2026, 1, 1, 8, 0)
    task_id = data.add_task(conn, area_id, "t", deadline=deadline, now=dibuat)
    if selesai is not None:
        data.complete_task(conn, task_id, now=datetime.strptime(selesai, "%Y-%m-%d %H:%M"))
    return task_id


def test_rentang_tinjauan_tujuh_hari_berakhir_hari_ini():
    awal, akhir = analytics.rentang_tinjauan(SEKARANG.date())
    assert (awal, akhir) == (AWAL_MINGGU, SEKARANG.date())
    assert (akhir - awal).days + 1 == analytics.RENTANG_TINJAUAN_HARI == 7


def test_tinjauan_database_kosong(conn):
    hasil = analytics.tinjauan_mingguan(conn, SEKARANG)
    assert hasil == analytics.Tinjauan(AWAL_MINGGU, SEKARANG.date(), 0, 0, 0, 0)


def test_tinjauan_task_selesai_batas_hari_pertama_dan_terakhir(conn):
    area = data.add_area(conn, "Kuliah")
    for selesai in (
        "2026-03-03 23:59",  # sehari sebelum rentang
        "2026-03-04 00:00",
        "2026-03-07 12:00",
        "2026-03-10 23:59",
        "2026-03-11 00:00",  # sesudah rentang
    ):
        _task_tinjauan(conn, area, selesai=selesai)
    _task_tinjauan(conn, area)  # todo tidak dihitung
    assert analytics.tinjauan_mingguan(conn, SEKARANG).task_selesai == 3


@pytest.mark.parametrize(
    "deadline, selesai, terlambat",
    [
        ("2026-03-05 10:00", "2026-03-05 10:01", 1),  # selesai sesudah deadline
        ("2026-03-05 10:00", "2026-03-05 10:00", 0),  # tepat pada deadline
        ("2026-03-05 10:00", "2026-03-05 09:00", 0),  # sebelum deadline
        ("2026-03-05 10:00", None, 1),                # todo, deadline lewat
        ("2026-03-10 14:59", None, 1),                # lewat semenit
        ("2026-03-10 15:00", None, 0),                # tepat sekarang: belum lewat
        ("2026-03-10 18:00", None, 0),                # nanti sore
        ("2026-03-04 00:00", None, 1),                # batas awal rentang
        ("2026-03-03 23:59", None, 0),                # deadline di luar rentang
        ("2026-03-03 23:59", "2026-03-05 10:00", 0),  # telat, tapi deadline di luar rentang
        ("2026-03-11 09:00", None, 0),                # deadline sesudah rentang
        (None, None, 0),                              # tanpa deadline
        (None, "2026-03-05 10:00", 0),
    ],
)
def test_tinjauan_definisi_terlambat(conn, deadline, selesai, terlambat):
    area = data.add_area(conn, "Kuliah")
    _task_tinjauan(conn, area, deadline, selesai)
    assert analytics.tinjauan_mingguan(conn, SEKARANG).task_terlambat == terlambat


def test_tinjauan_terlambat_menjumlahkan_selesai_telat_dan_todo_lewat(conn):
    area = data.add_area(conn, "Kuliah")
    _task_tinjauan(conn, area, "2026-03-05 10:00", "2026-03-06 10:00")
    _task_tinjauan(conn, area, "2026-03-08 10:00")
    _task_tinjauan(conn, area, "2026-03-09 10:00", "2026-03-09 08:00")
    assert analytics.tinjauan_mingguan(conn, SEKARANG).task_terlambat == 2


def test_tinjauan_hari_valid_hanya_di_dalam_rentang(conn):
    for tanggal in ("2026-03-03", "2026-03-04", "2026-03-07", "2026-03-10", "2026-03-11"):
        data.set_daily_log(conn, tanggal, True, True)
    data.set_daily_log(conn, "2026-03-05", True, False)  # tidak valid
    assert analytics.tinjauan_mingguan(conn, SEKARANG).jumlah_hari_valid == 3


def test_tinjauan_streak_berjalan_boleh_lebih_dari_tujuh(conn):
    for n in range(10):  # 01/03 sampai 10/03
        data.set_daily_log(conn, (date(2026, 3, 10) - timedelta(days=n)).isoformat(), True, True)
    hasil = analytics.tinjauan_mingguan(conn, SEKARANG)
    assert hasil.streak == 10 == streak.get_streak(conn, SEKARANG.date())
    assert hasil.jumlah_hari_valid == 7


def test_tinjauan_streak_dari_kemarin_bila_hari_ini_belum_valid(conn):
    for tanggal in ("2026-03-08", "2026-03-09"):
        data.set_daily_log(conn, tanggal, True, True)
    assert analytics.tinjauan_mingguan(conn, SEKARANG).streak == 2
