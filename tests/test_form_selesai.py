"""Tes form Selesaikan task tanpa layar: pilih dan klik lewat kode."""
import sqlite3
from datetime import datetime

import pytest
import shiboken6
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from ctrlcoco import data
from ctrlcoco import form_selesai as form_module
from ctrlcoco.form_selesai import FormSelesaikanTask

NOW = datetime(2026, 3, 10, 9, 30)


@pytest.fixture
def form_dibuat(app):
    """Membuat form dan menutupnya setelah tes, jika Qt belum menghapusnya."""
    dibuat = []

    def buat(conn):
        f = FormSelesaikanTask(conn, now=NOW)
        f.show()  # tidak menunggu; offscreen, jadi tidak ada jendela sungguhan
        dibuat.append(f)
        return f

    yield buat
    for f in dibuat:
        if shiboken6.isValid(f):
            f.close()


@pytest.fixture
def tiga_task(conn):
    kuliah = data.add_area(conn, "Kuliah")
    magang = data.add_area(conn, "Magang")
    data.add_task(conn, magang, "Rapat", now=NOW)                          # id 1, tanpa deadline
    data.add_task(conn, kuliah, "Laporan", "2026-03-12 23:59", now=NOW)    # id 2
    data.add_task(conn, kuliah, "Kuis", "2026-03-11 08:00", now=NOW)       # id 3
    return conn


def teks_daftar(form):
    return [form.daftar.item(i).text() for i in range(form.daftar.count())]


def pilih(form, baris):
    form.daftar.setCurrentRow(baris)


def status(conn, task_id):
    t = conn.execute("SELECT status, completed_at FROM task WHERE id = ?", (task_id,)).fetchone()
    return tuple(t)


def test_daftar_berisi_judul_area_deadline_dengan_urutan_benar(tiga_task, form_dibuat):
    form = form_dibuat(tiga_task)
    assert teks_daftar(form) == [
        "Kuis · Kuliah · 2026-03-11 08:00",
        "Laporan · Kuliah · 2026-03-12 23:59",
        "Rapat · Magang · tanpa deadline",
    ]
    assert [form.daftar.item(i).data(Qt.UserRole) for i in range(3)] == [3, 2, 1]
    assert not form.kosong_label.isVisible()
    assert form.tombol_selesai.text() == "Tandai selesai"
    assert form.testAttribute(Qt.WA_DeleteOnClose)


def test_tanpa_task_todo_tampil_teks_kosong(conn, form_dibuat):
    data.add_area(conn, "Kuliah")
    form = form_dibuat(conn)
    assert form.kosong_label.text() == "Tidak ada task yang perlu diselesaikan"
    assert form.kosong_label.isVisible()
    assert form.daftar.count() == 0
    assert not form.tombol_selesai.isEnabled()


def test_tombol_aktif_hanya_jika_ada_task_dipilih(tiga_task, form_dibuat):
    form = form_dibuat(tiga_task)
    assert not form.tombol_selesai.isEnabled()
    pilih(form, 1)
    assert form.tombol_selesai.isEnabled()
    form.daftar.clearSelection()
    assert not form.tombol_selesai.isEnabled()


def test_tandai_selesai_mengubah_status_dan_menutup_form(tiga_task, form_dibuat):
    form = form_dibuat(tiga_task)
    pilih(form, 1)  # Laporan, id 2
    form.tombol_selesai.click()
    assert status(tiga_task, 2) == ("done", "2026-03-10 09:30")
    assert status(tiga_task, 3) == ("todo", None)
    assert status(tiga_task, 1) == ("todo", None)
    assert form.result() == QDialog.Accepted
    assert not form.isVisible()


def test_task_sudah_dihapus_pesan_tampil_di_form(tiga_task, form_dibuat):
    form = form_dibuat(tiga_task)
    pilih(form, 0)  # Kuis, id 3
    with tiga_task:
        tiga_task.execute("DELETE FROM task WHERE id = 3")  # dihapus dari jalur lain
    form.tombol_selesai.click()
    assert "Task tidak ditemukan: 3" in form.error_label.text()
    assert form.error_label.isVisible()
    assert form.isVisible()


def test_error_database_saat_tandai_selesai_tampil_di_form(tiga_task, form_dibuat, monkeypatch):
    def selesai_terkunci(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(form_module, "complete_task", selesai_terkunci)
    form = form_dibuat(tiga_task)
    pilih(form, 0)
    form.tombol_selesai.click()
    assert "database is locked" in form.error_label.text()
    assert form.isVisible()
    assert form.daftar.currentRow() == 0  # pilihan tidak hilang
    assert status(tiga_task, 3) == ("todo", None)


def test_error_database_saat_form_dibuat(tiga_task, form_dibuat, monkeypatch):
    def baca_terkunci(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(form_module, "list_todo_untuk_selesai", baca_terkunci)
    form = form_dibuat(tiga_task)
    assert "database is locked" in form.error_label.text()
    assert form.error_label.isVisible()
    assert not form.kosong_label.isVisible()  # bukan "tidak ada task", tapi gagal dibaca
    assert not form.tombol_selesai.isEnabled()


def test_batal_tidak_mengubah_database(tiga_task, form_dibuat):
    form = form_dibuat(tiga_task)
    pilih(form, 0)
    form.tombol_batal.click()
    assert form.result() == QDialog.Rejected
    assert not form.isVisible()
    assert [r["status"] for r in data.list_tasks(tiga_task)] == ["todo", "todo", "todo"]
