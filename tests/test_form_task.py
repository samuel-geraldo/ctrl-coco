"""Tes form tambah task tanpa layar: field diisi dan tombol diklik lewat kode."""
import sqlite3
from datetime import datetime

import pytest
import shiboken6
from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import QDialog

from ctrlcoco import data
from ctrlcoco import form_task as form_module
from ctrlcoco.form_task import FormTambahTask

NOW = datetime(2026, 3, 10, 9, 30)


class JamTiruan:
    """Pengganti datetime.now: mengembalikan waktu yang bisa diatur tes."""

    def __init__(self, waktu):
        self.waktu = waktu

    def __call__(self):
        return self.waktu


@pytest.fixture
def jam():
    return JamTiruan(NOW)


@pytest.fixture
def form(app, conn, jam):
    data.add_area(conn, "Kuliah")
    data.add_area(conn, "Magang")
    f = FormTambahTask(conn, jam=jam)
    f.show()  # tidak menunggu; offscreen, jadi tidak ada jendela sungguhan
    yield f
    if shiboken6.isValid(f):  # WA_DeleteOnClose: bisa sudah dihapus Qt
        f.close()


def isi(form, area, judul, deadline=None):
    """deadline None = centang "Tanpa deadline"; teks "YYYY-MM-DD HH:MM" = pilih tanggal."""
    form.area_combo.setEditText(area)
    form.judul_edit.setText(judul)
    if deadline is None:
        form.tanpa_deadline_check.setChecked(True)
    else:
        form.tanpa_deadline_check.setChecked(False)
        form.deadline_edit.setDateTime(QDateTime(datetime.strptime(deadline, "%Y-%m-%d %H:%M")))


def nilai_pemilih(form):
    return form.deadline_edit.dateTime().toPython()


def isi_database(conn):
    areas = [a["name"] for a in data.list_areas(conn)]
    tasks = [(t["area_id"], t["title"], t["deadline"]) for t in data.list_tasks(conn)]
    return areas, tasks


def test_form_berisi_area_lama_dan_tombol(form):
    combo = form.area_combo
    assert combo.isEditable()
    assert [combo.itemText(i) for i in range(combo.count())] == ["Kuliah", "Magang"]
    assert form.tombol_simpan.text() == "Simpan"
    assert form.tombol_batal.text() == "Batal"
    assert form.error_label.text() == ""
    assert form.testAttribute(Qt.WA_DeleteOnClose)


# --- pemilih deadline ---

def test_nilai_awal_tanpa_deadline(form):
    # Paling aman: form tidak diam-diam menyimpan tanggal hari ini.
    assert form.tanpa_deadline_check.text() == "Tanpa deadline"
    assert form.tanpa_deadline_check.isChecked()
    assert not form.deadline_edit.isEnabled()


def test_pemilih_berkalender_dan_berisi_hari_ini_23_59(form):
    assert form.deadline_edit.calendarPopup()
    assert form.deadline_edit.displayFormat() == "dd/MM/yyyy HH:mm"
    assert nilai_pemilih(form) == datetime(2026, 3, 10, 23, 59)


def test_hapus_centang_mengaktifkan_pemilih_dan_centang_lagi_menonaktifkan(form):
    form.tanpa_deadline_check.setChecked(False)
    assert form.deadline_edit.isEnabled()
    form.tanpa_deadline_check.setChecked(True)
    assert not form.deadline_edit.isEnabled()


@pytest.mark.parametrize(
    "pilihan, teks, harapan",
    [
        ("hari_ini", "Hari ini 23:59", datetime(2026, 3, 10, 23, 59)),
        ("besok", "Besok 23:59", datetime(2026, 3, 11, 23, 59)),
        ("minggu_depan", "Minggu depan", datetime(2026, 3, 17, 23, 59)),
    ],
)
def test_tombol_cepat_mengisi_pemilih_dan_menghapus_centang(form, pilihan, teks, harapan):
    tombol = form.tombol_cepat[pilihan]
    assert tombol.text() == teks
    tombol.click()
    assert nilai_pemilih(form) == harapan
    assert not form.tanpa_deadline_check.isChecked()
    assert form.deadline_edit.isEnabled()


def test_tombol_cepat_memakai_jam_saat_diklik(form, jam):
    # Form dibuka 10 Maret, tombol diklik setelah lewat tengah malam (31 Des -> 1 Jan).
    jam.waktu = datetime(2026, 12, 31, 23, 58)
    form.tombol_cepat["besok"].click()
    assert nilai_pemilih(form) == datetime(2027, 1, 1, 23, 59)


# --- simpan ---

def test_simpan_task_valid_menutup_form(form, conn):
    isi(form, "Kuliah", "Laporan", "2026-03-12 23:59")
    form.tombol_simpan.click()
    assert isi_database(conn)[1] == [(1, "Laporan", "2026-03-12 23:59")]
    assert form.result() == QDialog.Accepted
    assert not form.isVisible()


def test_tombol_cepat_tersimpan_dengan_time_format(form, conn):
    isi(form, "Kuliah", "Laporan")
    form.tombol_cepat["besok"].click()
    form.tombol_simpan.click()
    assert data.list_tasks(conn)[0]["deadline"] == "2026-03-11 23:59"


def test_simpan_tanpa_deadline_tersimpan_null(form, conn):
    isi(form, "Kuliah", "Laporan", None)
    form.tombol_simpan.click()
    assert data.list_tasks(conn)[0]["deadline"] is None


def test_centang_lagi_setelah_memilih_tanggal_tersimpan_null(form, conn):
    isi(form, "Kuliah", "Laporan")
    form.tombol_cepat["besok"].click()
    form.tanpa_deadline_check.setChecked(True)
    form.tombol_simpan.click()
    assert data.list_tasks(conn)[0]["deadline"] is None


def test_form_mengirim_teks_ketat_ke_simpan_task_baru(form, monkeypatch):
    dikirim = []

    def simpan_tiruan(conn, area, judul, deadline):
        dikirim.append(deadline)

    monkeypatch.setattr(form_module, "simpan_task_baru", simpan_tiruan)
    isi(form, "Kuliah", "Laporan", "2026-03-12 07:05")
    form.tombol_simpan.click()
    isi(form, "Kuliah", "Laporan", None)
    form.tombol_simpan.click()
    assert dikirim == ["2026-03-12 07:05", None]


def test_simpan_area_beda_huruf_tidak_membuat_area_baru(form, conn):
    isi(form, "kuliah", "Laporan")
    form.tombol_simpan.click()
    assert isi_database(conn) == (["Kuliah", "Magang"], [(1, "Laporan", None)])


def test_simpan_area_baru(form, conn):
    isi(form, "Organisasi", "Rapat")
    form.tombol_simpan.click()
    areas, tasks = isi_database(conn)
    assert areas == ["Kuliah", "Magang", "Organisasi"]
    assert tasks == [(3, "Rapat", None)]


@pytest.mark.parametrize(
    "area, judul, pesan",
    [
        ("Kuliah", "   ", "Judul task wajib diisi"),
        ("", "Rapat", "Nama area wajib diisi"),
    ],
    ids=["judul_kosong", "area_kosong"],
)
def test_error_validasi_tampil_di_form_dan_form_tetap_terbuka(form, conn, area, judul, pesan):
    sebelum = isi_database(conn)
    isi(form, area, judul, "2026-03-12 23:59")
    form.tombol_simpan.click()

    assert pesan in form.error_label.text()
    assert form.error_label.isVisible()
    assert form.isVisible()
    # Isian tidak hilang, supaya bisa langsung diperbaiki.
    assert (form.area_combo.currentText(), form.judul_edit.text()) == (area, judul)
    assert not form.tanpa_deadline_check.isChecked()
    assert nilai_pemilih(form) == datetime(2026, 3, 12, 23, 59)
    assert isi_database(conn) == sebelum


def test_error_database_tampil_di_form(form, conn, monkeypatch):
    def simpan_terkunci(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(form_module, "simpan_task_baru", simpan_terkunci)
    isi(form, "Kuliah", "Laporan")
    form.tombol_simpan.click()

    assert "database is locked" in form.error_label.text()
    assert form.isVisible()
    assert data.list_tasks(conn) == []


def test_perbaiki_lalu_simpan_lagi_berhasil(form, conn):
    isi(form, "Kuliah", "   ", "2026-03-12 23:59")
    form.tombol_simpan.click()
    assert form.isVisible()

    form.judul_edit.setText("Laporan")
    form.tombol_simpan.click()
    assert not form.isVisible()
    assert isi_database(conn)[1] == [(1, "Laporan", "2026-03-12 23:59")]


def test_batal_tidak_mengubah_database(form, conn):
    sebelum = isi_database(conn)
    isi(form, "Organisasi", "Rapat")
    form.tombol_batal.click()
    assert form.result() == QDialog.Rejected
    assert not form.isVisible()
    assert isi_database(conn) == sebelum


def test_error_database_saat_form_dibuat(app, conn, monkeypatch):
    """Celah dari #37: list_areas gagal saat form dibuat; form tetap terbuka dengan pesan."""
    def baca_terkunci(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(form_module, "list_areas", baca_terkunci)
    f = FormTambahTask(conn, jam=JamTiruan(NOW))
    f.show()
    try:
        assert "database is locked" in f.error_label.text()
        assert f.error_label.isVisible()
        assert not f.tombol_simpan.isEnabled()
    finally:
        f.close()
