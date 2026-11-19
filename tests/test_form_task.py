"""Tes form tambah task tanpa layar: field diisi dan tombol diklik lewat kode."""
import sqlite3

import pytest
import shiboken6
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from ctrlcoco import data
from ctrlcoco import form_task as form_module
from ctrlcoco.form_task import FormTambahTask


@pytest.fixture
def form(app, conn):
    data.add_area(conn, "Kuliah")
    data.add_area(conn, "Magang")
    f = FormTambahTask(conn)
    f.show()  # tidak menunggu; offscreen, jadi tidak ada jendela sungguhan
    yield f
    if shiboken6.isValid(f):  # WA_DeleteOnClose: bisa sudah dihapus Qt
        f.close()


def isi(form, area, judul, deadline):
    form.area_combo.setEditText(area)
    form.judul_edit.setText(judul)
    form.deadline_edit.setText(deadline)


def isi_database(conn):
    areas = [a["name"] for a in data.list_areas(conn)]
    tasks = [(t["area_id"], t["title"], t["deadline"]) for t in data.list_tasks(conn)]
    return areas, tasks


def test_form_berisi_area_lama_dan_placeholder_deadline(form):
    combo = form.area_combo
    assert combo.isEditable()
    assert [combo.itemText(i) for i in range(combo.count())] == ["Kuliah", "Magang"]
    assert form.deadline_edit.placeholderText() == "YYYY-MM-DD HH:MM"
    assert form.tombol_simpan.text() == "Simpan"
    assert form.tombol_batal.text() == "Batal"
    assert form.error_label.text() == ""
    assert form.testAttribute(Qt.WA_DeleteOnClose)


def test_simpan_task_valid_menutup_form(form, conn):
    isi(form, "Kuliah", "Laporan", "2026-03-12 23:59")
    form.tombol_simpan.click()
    assert isi_database(conn)[1] == [(1, "Laporan", "2026-03-12 23:59")]
    assert form.result() == QDialog.Accepted
    assert not form.isVisible()


def test_simpan_deadline_kosong_tersimpan_null(form, conn):
    isi(form, "Kuliah", "Laporan", "   ")
    form.tombol_simpan.click()
    assert data.list_tasks(conn)[0]["deadline"] is None


def test_simpan_area_beda_huruf_tidak_membuat_area_baru(form, conn):
    isi(form, "kuliah", "Laporan", "")
    form.tombol_simpan.click()
    assert isi_database(conn) == (["Kuliah", "Magang"], [(1, "Laporan", None)])


def test_simpan_area_baru(form, conn):
    isi(form, "Organisasi", "Rapat", "")
    form.tombol_simpan.click()
    areas, tasks = isi_database(conn)
    assert areas == ["Kuliah", "Magang", "Organisasi"]
    assert tasks == [(3, "Rapat", None)]


@pytest.mark.parametrize(
    "area, judul, deadline, pesan",
    [
        ("Organisasi", "Rapat", "2026-3-12 9:00", "YYYY-MM-DD HH:MM"),
        ("Kuliah", "   ", "", "Judul task wajib diisi"),
        ("", "Rapat", "", "Nama area wajib diisi"),
    ],
    ids=["deadline_salah", "judul_kosong", "area_kosong"],
)
def test_error_validasi_tampil_di_form_dan_form_tetap_terbuka(form, conn, area, judul, deadline, pesan):
    sebelum = isi_database(conn)
    isi(form, area, judul, deadline)
    form.tombol_simpan.click()

    assert pesan in form.error_label.text()
    assert form.error_label.isVisible()
    assert form.isVisible()
    # Isian tidak hilang, supaya bisa langsung diperbaiki.
    assert (form.area_combo.currentText(), form.judul_edit.text(), form.deadline_edit.text()) == (
        area, judul, deadline,
    )
    assert isi_database(conn) == sebelum


def test_error_database_tampil_di_form(form, conn, monkeypatch):
    def simpan_terkunci(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(form_module, "simpan_task_baru", simpan_terkunci)
    isi(form, "Kuliah", "Laporan", "")
    form.tombol_simpan.click()

    assert "database is locked" in form.error_label.text()
    assert form.isVisible()
    assert data.list_tasks(conn) == []


def test_perbaiki_lalu_simpan_lagi_berhasil(form, conn):
    isi(form, "Kuliah", "Laporan", "besok")
    form.tombol_simpan.click()
    assert form.isVisible()

    form.deadline_edit.setText("2026-03-12 23:59")
    form.tombol_simpan.click()
    assert not form.isVisible()
    assert len(data.list_tasks(conn)) == 1


def test_batal_tidak_mengubah_database(form, conn):
    sebelum = isi_database(conn)
    isi(form, "Organisasi", "Rapat", "")
    form.tombol_batal.click()
    assert form.result() == QDialog.Rejected
    assert not form.isVisible()
    assert isi_database(conn) == sebelum


def test_error_database_saat_form_dibuat(app, conn, monkeypatch):
    """Celah dari #37: list_areas gagal saat form dibuat; form tetap terbuka dengan pesan."""
    def baca_terkunci(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(form_module, "list_areas", baca_terkunci)
    f = FormTambahTask(conn)
    f.show()
    try:
        assert "database is locked" in f.error_label.text()
        assert f.error_label.isVisible()
        assert not f.tombol_simpan.isEnabled()
    finally:
        f.close()
