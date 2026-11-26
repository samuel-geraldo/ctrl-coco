"""Tes jendela Ringkasan tanpa layar."""
from datetime import date, datetime
from pathlib import Path

import shiboken6
from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QApplication

from ctrlcoco import analytics, data
from ctrlcoco import ringkasan as ringkasan_module
from ctrlcoco.grafik_area import teks_median, teks_on_time, teks_per_hari
from ctrlcoco.ringkasan import JendelaRingkasan

HARI_INI = date(2026, 3, 10)


def buat_jendela(conn):
    j = JendelaRingkasan(conn, HARI_INI)
    j.show()  # offscreen, jadi tidak ada jendela sungguhan
    return j


def test_label_rentang_menyebut_12_minggu_dan_tanggalnya(app, conn):
    j = buat_jendela(conn)
    teks = j.rentang_label.text()
    assert "12 minggu terakhir" in teks
    assert "17/12/2025" in teks and "10/03/2026" in teks
    j.close()


def test_database_kosong_menampilkan_belum_ada_data(app, conn):
    j = buat_jendela(conn)
    assert not j.kosong_label.isHidden()
    assert "belum ada data" in j.kosong_label.text().lower()
    j.close()


def test_ada_data_menyembunyikan_pesan_kosong(app, conn):
    area_id = data.add_area(conn, "Kuliah")
    data.add_task(conn, area_id, "Laporan")  # tanpa deadline dan tanpa tanggal selesai
    j = buat_jendela(conn)
    assert j.kosong_label.isHidden()
    j.close()


def test_jendela_dihapus_dari_memori_setelah_ditutup(app, conn):
    j = buat_jendela(conn)
    j.close()
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    assert not shiboken6.isValid(j)


def test_modul_tampilan_tanpa_sql_dan_tanpa_hitungan_metrik():
    sumber = Path(ringkasan_module.__file__).read_text(encoding="utf-8")
    assert "execute" not in sumber and "SELECT" not in sumber


def isi_log(conn):
    """Log di sekitar HARI_INI: dua deretan 3 hari valid, satu tidak valid, satu di luar rentang."""
    valid = ("2026-03-01", "2026-03-02", "2026-03-03", "2026-03-08", "2026-03-09", "2026-03-10")
    for tanggal in valid:
        data.set_daily_log(conn, tanggal, True, True)
    data.set_daily_log(conn, "2026-03-05", True, False)   # bukan hari valid
    data.set_daily_log(conn, "2025-12-01", True, True)    # valid, tapi sebelum rentang


def test_heatmap_dan_streak_sama_dengan_fungsi_analitik(app, conn):
    isi_log(conn)
    j = buat_jendela(conn)
    awal, akhir = analytics.rentang_ringkasan(HARI_INI)
    valid = analytics.hari_valid(conn, awal, akhir)
    ditandai = {h for h, sel in j.heatmap.sel.items() if sel.property("valid")}
    assert ditandai == set(valid) and len(valid) == 6
    streak = analytics.longest_streak(conn, awal, akhir)
    assert j.streak_label.text() == f"Streak terpanjang: {streak} hari"
    assert streak == 3
    assert j.kosong_label.isHidden()
    j.close()


def test_database_kosong_menyembunyikan_heatmap_dan_streak(app, conn):
    j = buat_jendela(conn)
    assert j.heatmap.isHidden() and j.streak_label.isHidden()
    assert not j.kosong_label.isHidden()
    j.close()


def test_hanya_task_heatmap_tampil_tanpa_sel_ditandai_dan_streak_nol(app, conn):
    area_id = data.add_area(conn, "Kuliah")
    data.add_task(conn, area_id, "Laporan")
    j = buat_jendela(conn)
    assert not j.heatmap.isHidden() and not j.streak_label.isHidden()
    assert not any(sel.property("valid") for sel in j.heatmap.sel.values())
    assert j.streak_label.text() == "Streak terpanjang: 0 hari"
    j.close()


def isi_task(conn):
    """Kuliah: 2 selesai (satu tepat waktu, satu terlambat) dari 3. Olahraga: 0 dari 1."""
    kuliah = data.add_area(conn, "Kuliah")
    olahraga = data.add_area(conn, "Olahraga")
    dibuat = datetime(2026, 3, 5, 8, 0)
    tepat = data.add_task(conn, kuliah, "Kuis", deadline="2026-03-07 10:00", now=dibuat)
    telat = data.add_task(conn, kuliah, "Laporan", deadline="2026-03-08 10:00", now=dibuat)
    data.add_task(conn, kuliah, "Tugas", now=dibuat)
    data.add_task(conn, olahraga, "Lari", now=dibuat)
    data.complete_task(conn, tepat, now=datetime(2026, 3, 6, 10, 0))
    data.complete_task(conn, telat, now=datetime(2026, 3, 9, 10, 0))


def test_grafik_dan_on_time_sama_dengan_fungsi_analitik(app, conn):
    isi_task(conn)
    j = buat_jendela(conn)
    awal, akhir = analytics.rentang_ringkasan(HARI_INI)
    rates = analytics.completion_rate_per_area(conn, awal, akhir)
    assert [b.batang.property("rate") for b in j.grafik.baris] == [r.rate for r in rates]
    assert [r.rate for r in rates] == [2 / 3, 0.0]
    on_time = analytics.on_time_rate(conn, awal, akhir)
    assert on_time == 0.5
    assert j.on_time_label.text() == teks_on_time(on_time) == "On-time rate: 50%"
    assert j.kosong_label.isHidden()
    j.close()


def test_database_kosong_menyembunyikan_grafik_dan_on_time(app, conn):
    j = buat_jendela(conn)
    assert j.grafik.isHidden() and j.on_time_label.isHidden()
    assert not j.kosong_label.isHidden()
    j.close()


def test_hanya_log_grafik_tanpa_baris_dan_on_time_belum_ada(app, conn):
    data.set_daily_log(conn, "2026-03-10", True, True)
    j = buat_jendela(conn)
    assert not j.grafik.isHidden() and j.grafik.baris == []
    assert j.on_time_label.text() == teks_on_time(None)
    j.close()


def test_hanya_task_belum_selesai_nol_persen_dan_on_time_belum_ada(app, conn):
    area_id = data.add_area(conn, "Kuliah")
    data.add_task(conn, area_id, "Laporan", now=datetime(2026, 3, 5, 8, 0))
    j = buat_jendela(conn)
    assert len(j.grafik.baris) == 1
    assert j.grafik.baris[0].teks.text() == "0% (0/1)"
    assert j.on_time_label.text() == teks_on_time(None)
    j.close()


def test_median_di_ringkasan_sama_dengan_fungsi_analitik(app, conn):
    isi_task(conn)  # Kuliah: 26 jam dan 98 jam, median 62. Olahraga: belum ada yang selesai
    j = buat_jendela(conn)
    awal, akhir = analytics.rentang_ringkasan(HARI_INI)
    hasil = analytics.median_penyelesaian_per_area(conn, awal, akhir)
    assert [r.jam for r in hasil] == [62.0, None]
    assert j.median_label.text() == teks_median(hasil)
    assert not j.median_label.isHidden()
    j.close()


def test_teks_median():
    hasil = [
        analytics.MedianArea(1, "Kuliah", 62.26),
        analytics.MedianArea(2, "Olahraga", None),
    ]
    assert teks_median(hasil) == (
        "Median waktu selesai:\n"
        "Kuliah: 62,3 jam\n"
        "Olahraga: belum ada task selesai"
    )


def test_teks_median_tanpa_area():
    assert teks_median([]) == "Median waktu selesai: belum ada area"


def test_median_label_teks_polos(app, conn):
    # Nama area diketik pengguna: tag HTML harus tampil apa adanya.
    data.add_area(conn, "<b>Kuliah</b>")
    j = buat_jendela(conn)
    assert j.median_label.textFormat() == Qt.PlainText
    j.close()


def test_database_kosong_menyembunyikan_median(app, conn):
    j = buat_jendela(conn)
    assert j.median_label.isHidden()
    j.close()


def test_per_hari_di_ringkasan_sama_dengan_fungsi_analitik(app, conn):
    isi_task(conn)  # selesai Jumat 06/03 dan Senin 09/03
    data.set_daily_log(conn, "2026-03-09", True, True)
    j = buat_jendela(conn)
    awal, akhir = analytics.rentang_ringkasan(HARI_INI)
    hasil = analytics.produktivitas_per_hari(conn, awal, akhir)
    assert (hasil[0].task_selesai, hasil[0].hari_valid) == (1, 1)
    assert (hasil[4].task_selesai, hasil[4].hari_valid) == (1, 0)
    assert j.per_hari_label.text() == teks_per_hari(hasil)
    assert not j.per_hari_label.isHidden()
    j.close()


def test_teks_per_hari():
    hasil = [
        analytics.ProduktivitasHari("Senin", 3, 2),
        analytics.ProduktivitasHari("Selasa", 0, 0),
    ]
    assert teks_per_hari(hasil) == (
        "Produktivitas per hari:\n"
        "Senin: 3 task selesai, 2 hari valid\n"
        "Selasa: 0 task selesai, 0 hari valid"
    )


def test_database_kosong_menyembunyikan_per_hari(app, conn):
    j = buat_jendela(conn)
    assert j.per_hari_label.isHidden()
    j.close()
