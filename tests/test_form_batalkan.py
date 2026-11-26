"""Tes form Batalkan selesai (#55) tanpa layar: pilih dan klik lewat kode."""
import sqlite3
from datetime import datetime

import pytest
import shiboken6
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from ctrlcoco import data
from ctrlcoco import form_batalkan as form_module
from ctrlcoco.form_batalkan import FormBatalkanSelesai
from ctrlcoco.form_dasar import FormDasar


@pytest.fixture
def form_dibuat(app):
    dibuat = []

    def buat(conn):
        f = FormBatalkanSelesai(conn)
        f.show()  # offscreen, jadi tidak ada jendela sungguhan
        dibuat.append(f)
        return f

    yield buat
    for f in dibuat:
        if shiboken6.isValid(f):
            f.close()


@pytest.fixture
def dua_selesai(conn):
    area = data.add_area(conn, "Kuliah")
    kuis = data.add_task(conn, area, "Kuis", now=datetime(2026, 3, 1, 8, 0))  # id 1
    laporan = data.add_task(conn, area, "Laporan", now=datetime(2026, 3, 1, 8, 0))  # id 2
    data.add_task(conn, area, "Belum", now=datetime(2026, 3, 1, 8, 0))  # id 3, todo
    data.complete_task(conn, kuis, now=datetime(2026, 3, 5, 9, 0))
    data.complete_task(conn, laporan, now=datetime(2026, 3, 6, 9, 0))
    return conn


def teks_daftar(form):
    return [form.daftar.item(i).text() for i in range(form.daftar.count())]


def status(conn, task_id):
    return conn.execute("SELECT status FROM task WHERE id = ?", (task_id,)).fetchone()[0]


def test_hanya_task_done_yang_tampil(dua_selesai, form_dibuat):
    form = form_dibuat(dua_selesai)
    assert isinstance(form, FormDasar)
    assert teks_daftar(form) == [
        "Laporan · Kuliah · selesai 2026-03-06 09:00",
        "Kuis · Kuliah · selesai 2026-03-05 09:00",
    ]
    assert form.tombol_kembalikan.text() == "Kembalikan"
    assert not form.tombol_kembalikan.isEnabled()
    assert not form.kosong_label.isVisible()


def test_tanpa_task_done_tampil_teks_kosong(conn, form_dibuat):
    form = form_dibuat(conn)
    assert form.kosong_label.text() == "Tidak ada task yang sudah selesai"
    assert form.kosong_label.isVisible()
    assert not form.daftar.isVisible()


def test_kembalikan_mengubah_status_dan_menutup_form(dua_selesai, form_dibuat):
    form = form_dibuat(dua_selesai)
    form.daftar.setCurrentRow(1)  # Kuis, id 1
    assert form.daftar.item(1).data(Qt.UserRole) == 1
    form.tombol_kembalikan.click()
    assert (status(dua_selesai, 1), status(dua_selesai, 2)) == ("todo", "done")
    assert form.result() == QDialog.Accepted
    assert not form.isVisible()


def test_task_sudah_dihapus_pesan_tampil_dan_daftar_dimuat_ulang(dua_selesai, form_dibuat):
    form = form_dibuat(dua_selesai)
    form.daftar.setCurrentRow(0)  # Laporan, id 2
    with dua_selesai:
        dua_selesai.execute("DELETE FROM task WHERE id = 2")
    form.tombol_kembalikan.click()
    assert "Task tidak ditemukan: 2" in form.error_label.text()
    assert teks_daftar(form) == ["Kuis · Kuliah · selesai 2026-03-05 09:00"]
    assert not form.tombol_kembalikan.isEnabled()
    assert form.isVisible()


def test_error_database_saat_simpan_tampil_di_form(dua_selesai, form_dibuat, monkeypatch):
    def terkunci(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(form_module, "batalkan_selesai", terkunci)
    form = form_dibuat(dua_selesai)
    form.daftar.setCurrentRow(0)
    form.tombol_kembalikan.click()
    assert "Gagal menyimpan ke database: database is locked" in form.error_label.text()
    assert form.daftar.currentRow() == 0  # pilihan tetap, bisa dicoba lagi
    assert form.isVisible()


def test_error_database_saat_membaca_daftar_tampil_di_form(conn, form_dibuat, monkeypatch):
    def terkunci(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(form_module, "list_done_untuk_dibatalkan", terkunci)
    form = form_dibuat(conn)
    assert "Daftar task gagal dibaca: database is locked" in form.error_label.text()
    assert not form.kosong_label.isVisible()  # gagal dibaca, bukan "tidak ada task"
    assert not form.tombol_kembalikan.isEnabled()
