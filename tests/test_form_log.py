"""Tes form log hari ini tanpa layar: centang dan klik lewat kode."""
import sqlite3
from datetime import datetime

import pytest
import shiboken6
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from ctrlcoco import data
from ctrlcoco import form_log as form_module
from ctrlcoco.form_log import FormLogHarian

NOW = datetime(2026, 3, 10, 21, 0)
HARI_INI = "2026-03-10"


def buat_form(conn):
    f = FormLogHarian(conn, NOW)
    f.show()  # tidak menunggu; offscreen, jadi tidak ada jendela sungguhan
    return f


@pytest.fixture
def form_dibuat(app):
    """Membuat form dan menutupnya setelah tes, jika Qt belum menghapusnya."""
    dibuat = []

    def buat(conn):
        f = buat_form(conn)
        dibuat.append(f)
        return f

    yield buat
    for f in dibuat:
        if shiboken6.isValid(f):
            f.close()


def log(conn):
    baris = data.get_daily_log(conn, HARI_INI)
    return None if baris is None else (baris["claude_code"], baris["github"], baris["note"])


def test_log_belum_ada_isian_kosong(conn, form_dibuat):
    form = form_dibuat(conn)
    assert not form.claude_code_check.isChecked()
    assert not form.github_check.isChecked()
    assert form.catatan_edit.text() == ""
    assert form.claude_code_check.text() == "Claude Code"
    assert form.github_check.text() == "GitHub"
    assert form.tombol_simpan.text() == "Simpan"
    assert form.tombol_simpan.isEnabled()
    assert form.error_label.text() == ""
    assert form.testAttribute(Qt.WA_DeleteOnClose)


def test_log_sudah_ada_isian_terisi(conn, form_dibuat):
    data.set_daily_log(conn, HARI_INI, True, False, note="belajar SQL")
    data.set_daily_log(conn, "2026-03-09", False, True, note="kemarin")  # tanggal lain diabaikan
    form = form_dibuat(conn)
    assert form.claude_code_check.isChecked()
    assert not form.github_check.isChecked()
    assert form.catatan_edit.text() == "belajar SQL"


def test_centang_claude_code_lalu_simpan(conn, form_dibuat):
    form = form_dibuat(conn)
    form.claude_code_check.setChecked(True)
    form.tombol_simpan.click()
    assert log(conn) == (1, 0, None)
    assert form.result() == QDialog.Accepted
    assert not form.isVisible()


def test_tanggal_diambil_dari_now(conn, form_dibuat):
    form = form_dibuat(conn)
    form.github_check.setChecked(True)
    form.tombol_simpan.click()
    tanggal = [r["log_date"] for r in conn.execute("SELECT log_date FROM daily_log")]
    assert tanggal == [HARI_INI]


@pytest.mark.parametrize(
    "catatan_baru, hasil",
    [
        ("belajar SQL", "belajar SQL"),      # tidak diubah: catatan lama tetap
        ("  belajar SQL ", "belajar SQL"),   # hanya beda spasi: dianggap tidak diubah
        ("", ""),                            # dikosongkan: catatan dihapus
        ("   ", ""),
        ("latihan JOIN", "latihan JOIN"),    # diganti
    ],
    ids=["tidak_diubah", "beda_spasi", "dikosongkan", "hanya_spasi", "diganti"],
)
def test_catatan_lama_dipertahankan_atau_dihapus(conn, form_dibuat, catatan_baru, hasil):
    data.set_daily_log(conn, HARI_INI, True, False, note="belajar SQL")
    form = form_dibuat(conn)
    form.github_check.setChecked(True)
    form.catatan_edit.setText(catatan_baru)
    form.tombol_simpan.click()
    assert log(conn) == (1, 1, hasil)


def test_catatan_tidak_diubah_dikirim_none(conn, form_dibuat, monkeypatch):
    """Catatan yang tidak diubah dikirim sebagai None, supaya set_daily_log tidak menyentuhnya."""
    data.set_daily_log(conn, HARI_INI, True, False, note="belajar SQL")
    panggilan = []
    monkeypatch.setattr(form_module, "set_daily_log", lambda *a, **k: panggilan.append((a, k)))
    form = form_dibuat(conn)
    form.github_check.setChecked(True)
    form.tombol_simpan.click()
    assert panggilan == [((conn, HARI_INI, True, True), {"note": None})]


def test_log_baru_tanpa_catatan_tersimpan_null(conn, form_dibuat):
    form = form_dibuat(conn)
    form.claude_code_check.setChecked(True)
    form.github_check.setChecked(True)
    form.tombol_simpan.click()
    assert log(conn) == (1, 1, None)


def test_error_database_saat_simpan_tampil_di_form(conn, form_dibuat, monkeypatch):
    def simpan_terkunci(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(form_module, "set_daily_log", simpan_terkunci)
    form = form_dibuat(conn)
    form.claude_code_check.setChecked(True)
    form.catatan_edit.setText("catatan")
    form.tombol_simpan.click()

    assert "database is locked" in form.error_label.text()
    assert form.error_label.isVisible()
    assert form.isVisible()
    assert form.claude_code_check.isChecked()
    assert form.catatan_edit.text() == "catatan"
    assert log(conn) is None


def test_error_validasi_saat_simpan_tampil_di_form(conn, form_dibuat, monkeypatch):
    def simpan_ditolak(*args, **kwargs):
        raise ValueError("log_date harus berformat YYYY-MM-DD")

    monkeypatch.setattr(form_module, "set_daily_log", simpan_ditolak)
    form = form_dibuat(conn)
    form.tombol_simpan.click()
    assert "YYYY-MM-DD" in form.error_label.text()
    assert form.isVisible()


def test_error_database_saat_form_dibuat(conn, form_dibuat, monkeypatch):
    def baca_terkunci(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(form_module, "get_daily_log", baca_terkunci)
    form = form_dibuat(conn)
    assert "database is locked" in form.error_label.text()
    assert form.error_label.isVisible()
    assert not form.tombol_simpan.isEnabled()


def test_batal_tidak_mengubah_database(conn, form_dibuat):
    data.set_daily_log(conn, HARI_INI, False, False, note="lama")
    form = form_dibuat(conn)
    form.claude_code_check.setChecked(True)
    form.catatan_edit.setText("")
    form.tombol_batal.click()
    assert form.result() == QDialog.Rejected
    assert not form.isVisible()
    assert log(conn) == (0, 0, "lama")
