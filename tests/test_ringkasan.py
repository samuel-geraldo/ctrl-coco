"""Tes jendela Ringkasan tanpa layar."""
from datetime import date
from pathlib import Path

import shiboken6
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication

from ctrlcoco import analytics, data
from ctrlcoco import ringkasan as ringkasan_module
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
