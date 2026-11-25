"""Tes FormDasar (#57): kerangka bersama pesan error dan tombol ketiga form."""
import inspect

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout

from ctrlcoco import form_log, form_selesai, form_task
from ctrlcoco.form_dasar import ERROR_STYLE, FormDasar


@pytest.fixture
def form(app):
    f = FormDasar()
    yield f
    f.deleteLater()


def test_error_label_tersembunyi_di_awal(form):
    form.show()
    assert form.error_label.text() == ""
    assert not form.error_label.isVisible()


def test_error_label_bergaya_merah_dan_word_wrap(form):
    assert form.error_label.styleSheet() == ERROR_STYLE
    assert form.error_label.wordWrap()


def test_tampilkan_error_menampilkan_teksnya(form):
    form.show()
    form._tampilkan_error("Gagal menyimpan")
    assert form.error_label.text() == "Gagal menyimpan"
    assert form.error_label.isVisible()


def test_dihapus_saat_ditutup(form):
    assert form.testAttribute(Qt.WA_DeleteOnClose)


def test_buat_tombol_memberi_tombol_utama_dan_batal(form):
    kotak = form._buat_tombol("Simpan")
    assert form.tombol_utama.text() == "Simpan"
    assert form.tombol_batal.text() == "Batal"
    assert kotak.buttons() == [form.tombol_utama, form.tombol_batal]


def test_tombol_batal_menolak_form(form):
    # Seperti di form sungguhan: kotak tombol dimasukkan ke layout, jadi tidak dibuang Qt.
    QVBoxLayout(form).addWidget(form._buat_tombol("Simpan"))
    form.show()
    form.tombol_batal.click()
    assert form.result() == FormDasar.DialogCode.Rejected
    assert not form.isVisible()


@pytest.mark.parametrize("modul", [form_log, form_selesai])
def test_form_log_dan_selesai_tidak_mengimpor_form_task(modul):
    assert "form_task" not in inspect.getsource(modul)


def test_ketiga_form_turunan_form_dasar():
    assert issubclass(form_task.FormTambahTask, FormDasar)
    assert issubclass(form_log.FormLogHarian, FormDasar)
    assert issubclass(form_selesai.FormSelesaikanTask, FormDasar)
