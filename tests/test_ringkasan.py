"""Tes jendela Ringkasan tanpa layar."""
from datetime import date
from pathlib import Path

import shiboken6
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication

from ctrlcoco import data
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
