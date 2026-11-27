"""Tes jendela Tinjauan mingguan tanpa layar."""
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import shiboken6
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication

from ctrlcoco import analytics, data
from ctrlcoco import tinjauan as tinjauan_module
from ctrlcoco.tinjauan import JendelaTinjauan

SEKARANG = datetime(2026, 3, 10, 15, 0)  # 7 hari: 04/03 sampai 10/03


@pytest.fixture
def jendela_dibuat(app):
    """Membuat jendela dan menutupnya setelah tes, jika Qt belum menghapusnya."""
    dibuat = []

    def buat(conn):
        j = JendelaTinjauan(conn, SEKARANG)
        j.show()  # offscreen, jadi tidak ada jendela sungguhan
        dibuat.append(j)
        return j

    yield buat
    for j in dibuat:
        if shiboken6.isValid(j):
            j.close()


def label_angka(j):
    return (j.selesai_label, j.terlambat_label, j.hari_valid_label, j.streak_label)


def isi_data(conn):
    """2 task selesai (1 telat), 1 todo lewat deadline, 3 hari valid beruntun sampai hari ini."""
    area = data.add_area(conn, "Kuliah")
    dibuat = datetime(2026, 1, 1, 8, 0)
    tepat = data.add_task(conn, area, "tepat", deadline="2026-03-09 10:00", now=dibuat)
    data.complete_task(conn, tepat, now=datetime(2026, 3, 8, 10, 0))
    telat = data.add_task(conn, area, "telat", deadline="2026-03-05 10:00", now=dibuat)
    data.complete_task(conn, telat, now=datetime(2026, 3, 6, 10, 0))
    data.add_task(conn, area, "lewat", deadline="2026-03-07 10:00", now=dibuat)
    for n in range(3):
        data.set_daily_log(conn, (SEKARANG - timedelta(days=n)).date().isoformat(), True, True)


def test_judul_dan_label_rentang(conn, jendela_dibuat):
    j = jendela_dibuat(conn)
    assert j.windowTitle() == "Tinjauan mingguan"
    teks = j.rentang_label.text()
    assert "7 hari terakhir" in teks
    assert "04/03/2026" in teks and "10/03/2026" in teks


def test_angka_sama_dengan_fungsi_analitik(conn, jendela_dibuat):
    isi_data(conn)
    hasil = analytics.tinjauan_mingguan(conn, SEKARANG)
    assert (
        hasil.task_selesai, hasil.task_terlambat, hasil.jumlah_hari_valid, hasil.streak
    ) == (2, 2, 3, 3)

    j = jendela_dibuat(conn)

    assert [label.text() for label in label_angka(j)] == [
        "Task selesai: 2",
        "Task terlambat: 2",
        "Hari valid: 3 dari 7",
        "Streak saat ini: 3 hari",
    ]
    assert j.kosong_label.isHidden()
    assert not any(label.isHidden() for label in label_angka(j))


def test_jendela_hanya_menggambar_hasil_analitik(conn, jendela_dibuat, monkeypatch):
    data.set_daily_log(conn, "2026-03-10", True, True)
    palsu = analytics.Tinjauan(
        SEKARANG.date() - timedelta(days=6), SEKARANG.date(), 11, 12, 5, 40
    )
    panggilan = []

    def tiruan(koneksi, now):
        panggilan.append((koneksi, now))
        return palsu

    monkeypatch.setattr(tinjauan_module, "tinjauan_mingguan", tiruan)
    j = jendela_dibuat(conn)

    assert panggilan == [(conn, SEKARANG)]
    assert [label.text() for label in label_angka(j)] == [
        "Task selesai: 11",
        "Task terlambat: 12",
        "Hari valid: 5 dari 7",
        "Streak saat ini: 40 hari",
    ]


def test_database_kosong_menampilkan_pesan(conn, jendela_dibuat):
    j = jendela_dibuat(conn)
    assert not j.kosong_label.isHidden()
    assert "belum ada data" in j.kosong_label.text().lower()
    assert all(label.isHidden() for label in label_angka(j))


def test_data_lama_saja_menampilkan_angka_nol(conn, jendela_dibuat):
    data.set_daily_log(conn, "2026-01-05", True, True)
    j = jendela_dibuat(conn)
    assert j.kosong_label.isHidden()
    assert [label.text() for label in label_angka(j)] == [
        "Task selesai: 0",
        "Task terlambat: 0",
        "Hari valid: 0 dari 7",
        "Streak saat ini: 0 hari",
    ]


def test_tanpa_now_memakai_waktu_sekarang(app, conn):
    j = JendelaTinjauan(conn)
    assert datetime.now().strftime("%d/%m/%Y") in j.rentang_label.text()
    j.close()


def test_jendela_dihapus_dari_memori_setelah_ditutup(conn, jendela_dibuat):
    j = jendela_dibuat(conn)
    j.close()
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    assert not shiboken6.isValid(j)


def test_modul_tampilan_tanpa_sql_dan_tanpa_hitungan_metrik():
    sumber = Path(tinjauan_module.__file__).read_text(encoding="utf-8")
    assert "execute" not in sumber and "SELECT" not in sumber
    assert "get_streak" not in sumber and "hari_valid(" not in sumber
