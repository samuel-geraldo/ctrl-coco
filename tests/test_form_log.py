"""Tes form log harian tanpa layar: pilih tanggal, centang, dan klik lewat kode."""
import sqlite3
from datetime import datetime

import pytest
import shiboken6
from PySide6.QtCore import QDate, Qt
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


# --- pilihan tanggal: hari ini sampai 30 hari ke belakang (#56) ---

KEMARIN = "2026-03-09"
BATAS_AWAL = "2026-02-08"  # hari ini - 30


def pilih(form, tanggal):
    form.tanggal_edit.setDate(QDate.fromString(tanggal, "yyyy-MM-dd"))


def terpilih(form):
    return form.tanggal_edit.date().toString("yyyy-MM-dd")


def isian(form):
    return (
        form.claude_code_check.isChecked(),
        form.github_check.isChecked(),
        form.catatan_edit.text(),
    )


def semua_log(conn):
    kueri = "SELECT log_date, claude_code, github, note FROM daily_log ORDER BY log_date"
    return [tuple(r) for r in conn.execute(kueri)]


def test_bawaan_tanggal_hari_ini_dengan_batas(conn, form_dibuat):
    form = form_dibuat(conn)
    assert terpilih(form) == HARI_INI
    assert form.tanggal == HARI_INI
    assert form.tanggal_edit.minimumDate().toString("yyyy-MM-dd") == BATAS_AWAL
    assert form.tanggal_edit.maximumDate().toString("yyyy-MM-dd") == HARI_INI
    assert form.tanggal_edit.displayFormat() == "dd/MM/yyyy"
    assert form.tanggal_edit.calendarPopup()


def test_tanggal_masa_depan_ditolak(conn, form_dibuat):
    form = form_dibuat(conn)
    pilih(form, "2026-03-11")
    assert terpilih(form) == HARI_INI
    assert form.tanggal == HARI_INI
    form.github_check.setChecked(True)
    form.tombol_simpan.click()
    assert [baris[0] for baris in semua_log(conn)] == [HARI_INI]


def test_tiga_puluh_hari_ke_belakang_diterima(conn, form_dibuat):
    form = form_dibuat(conn)
    pilih(form, BATAS_AWAL)
    assert terpilih(form) == BATAS_AWAL
    assert form.tanggal == BATAS_AWAL
    form.github_check.setChecked(True)
    form.tombol_simpan.click()
    assert [baris[0] for baris in semua_log(conn)] == [BATAS_AWAL]


def test_tiga_puluh_satu_hari_ke_belakang_ditolak(conn, form_dibuat):
    form = form_dibuat(conn)
    pilih(form, "2026-02-07")
    assert terpilih(form) >= BATAS_AWAL
    assert form.tanggal >= BATAS_AWAL
    form.github_check.setChecked(True)
    form.tombol_simpan.click()
    assert all(baris[0] >= BATAS_AWAL for baris in semua_log(conn))


def test_ganti_tanggal_memuat_log_tanggal_itu(conn, form_dibuat):
    data.set_daily_log(conn, HARI_INI, True, False, note="hari ini")
    data.set_daily_log(conn, KEMARIN, False, True, note="kemarin")
    form = form_dibuat(conn)
    pilih(form, KEMARIN)
    assert form.tanggal == KEMARIN
    assert isian(form) == (False, True, "kemarin")


def test_tanggal_tanpa_log_isian_kosong_lalu_kembali(conn, form_dibuat):
    data.set_daily_log(conn, HARI_INI, True, True, note="hari ini")
    form = form_dibuat(conn)
    pilih(form, KEMARIN)
    assert isian(form) == (False, False, "")
    pilih(form, HARI_INI)
    assert isian(form) == (True, True, "hari ini")


def test_perubahan_belum_disimpan_hilang_saat_ganti_tanggal(conn, form_dibuat):
    form = form_dibuat(conn)
    form.claude_code_check.setChecked(True)
    form.catatan_edit.setText("belum disimpan")
    pilih(form, KEMARIN)
    assert isian(form) == (False, False, "")
    assert semua_log(conn) == []


def test_simpan_menulis_ke_tanggal_yang_dipilih(conn, form_dibuat):
    data.set_daily_log(conn, HARI_INI, False, False, note="hari ini")
    form = form_dibuat(conn)
    pilih(form, KEMARIN)
    form.claude_code_check.setChecked(True)
    form.github_check.setChecked(True)
    form.catatan_edit.setText("menyusul")
    form.tombol_simpan.click()
    assert semua_log(conn) == [(KEMARIN, 1, 1, "menyusul"), (HARI_INI, 0, 0, "hari ini")]
    assert form.result() == QDialog.Accepted


@pytest.mark.parametrize(
    "catatan_baru, hasil",
    [("catatan lama", "catatan lama"), ("", ""), ("diganti", "diganti")],
    ids=["tidak_diubah", "dikosongkan", "diganti"],
)
def test_aturan_catatan_berlaku_untuk_tanggal_terpilih(conn, form_dibuat, catatan_baru, hasil):
    data.set_daily_log(conn, HARI_INI, False, False, note="hari ini")
    data.set_daily_log(conn, KEMARIN, True, False, note="catatan lama")
    form = form_dibuat(conn)
    pilih(form, KEMARIN)
    form.catatan_edit.setText(catatan_baru)
    form.tombol_simpan.click()
    assert semua_log(conn) == [(KEMARIN, 1, 0, hasil), (HARI_INI, 0, 0, "hari ini")]


def test_catatan_tidak_diubah_di_tanggal_lain_dikirim_none(conn, form_dibuat, monkeypatch):
    data.set_daily_log(conn, KEMARIN, True, False, note="catatan lama")
    panggilan = []
    monkeypatch.setattr(form_module, "set_daily_log", lambda *a, **k: panggilan.append((a, k)))
    form = form_dibuat(conn)
    pilih(form, KEMARIN)
    form.tombol_simpan.click()
    assert panggilan == [((conn, KEMARIN, True, False), {"note": None})]


def test_gagal_baca_saat_ganti_tanggal_lalu_pulih(conn, form_dibuat, monkeypatch):
    data.set_daily_log(conn, HARI_INI, True, True, note="hari ini")
    baca_asli = form_module.get_daily_log

    def kemarin_terkunci(koneksi, tanggal):
        if tanggal == KEMARIN:
            raise sqlite3.OperationalError("database is locked")
        return baca_asli(koneksi, tanggal)

    monkeypatch.setattr(form_module, "get_daily_log", kemarin_terkunci)
    form = form_dibuat(conn)

    pilih(form, KEMARIN)
    assert "database is locked" in form.error_label.text()
    assert KEMARIN in form.error_label.text()
    assert form.error_label.isVisible()
    assert isian(form) == (False, False, "")  # isi hari ini tidak terbawa
    assert not form.tombol_simpan.isEnabled()

    pilih(form, HARI_INI)
    assert form.tombol_simpan.isEnabled()
    assert not form.error_label.isVisible()
    assert isian(form) == (True, True, "hari ini")


def test_judul_jendela_mengikuti_tanggal(conn, form_dibuat):
    form = form_dibuat(conn)
    assert form.windowTitle() == f"Log hari ini ({HARI_INI})"
    pilih(form, KEMARIN)
    assert form.windowTitle() == f"Log tanggal ({KEMARIN})"
    pilih(form, HARI_INI)
    assert form.windowTitle() == f"Log hari ini ({HARI_INI})"
