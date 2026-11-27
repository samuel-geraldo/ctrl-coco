import sqlite3
from datetime import datetime

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from ctrlcoco.data import DATE_FORMAT, get_daily_log, set_daily_log
from ctrlcoco.form_dasar import FormDasar

# Hari yang terlewat boleh diisi sampai sejauh ini ke belakang (hari ini - 30 masih boleh).
MAKS_HARI_MUNDUR = 30


class FormLogHarian(FormDasar):
    """Form log harian: pilih tanggal, centang Claude Code dan GitHub, catatan opsional."""

    def __init__(self, conn: sqlite3.Connection, now: datetime, parent: QWidget | None = None):
        super().__init__(parent)
        self.conn = conn
        # Hari ini diambil saat form dibuka, dari parameter (bukan datetime.now() di sini),
        # supaya bisa dites dengan tanggal tetap.
        self._hari_ini = QDate(now.year, now.month, now.day)

        self.tanggal_edit = QDateEdit()
        self.tanggal_edit.setCalendarPopup(True)
        self.tanggal_edit.setDisplayFormat("dd/MM/yyyy")
        # Rentang membuat Qt menolak tanggal masa depan dan yang terlalu lama.
        self.tanggal_edit.setDateRange(
            self._hari_ini.addDays(-MAKS_HARI_MUNDUR), self._hari_ini
        )
        self.tanggal_edit.setDate(self._hari_ini)
        self.claude_code_check = QCheckBox("Claude Code")
        self.github_check = QCheckBox("GitHub")
        self.catatan_edit = QLineEdit()
        self.catatan_edit.setPlaceholderText("opsional")

        tombol = self._buat_tombol("Simpan")
        self.tombol_simpan = self.tombol_utama
        self.tombol_simpan.setDefault(True)
        tombol.accepted.connect(self.simpan)

        isian = QFormLayout()
        isian.addRow("Tanggal", self.tanggal_edit)
        isian.addRow(self.claude_code_check)
        isian.addRow(self.github_check)
        isian.addRow("Catatan", self.catatan_edit)

        layout = QVBoxLayout(self)
        layout.addLayout(isian)
        layout.addWidget(self.error_label)
        layout.addWidget(tombol)

        self.tanggal_edit.dateChanged.connect(self._muat_log)
        self._muat_log(self._hari_ini)

    def _muat_log(self, tanggal: QDate) -> None:
        """Ganti isian dengan log `tanggal`. Perubahan yang belum disimpan dibuang."""
        self.tanggal = tanggal.toPython().strftime(DATE_FORMAT)
        judul = "Log hari ini" if tanggal == self._hari_ini else "Log tanggal"
        self.setWindowTitle(f"{judul} ({self.tanggal})")

        # Dikosongkan lebih dulu, supaya isi tanggal sebelumnya tidak terbawa bila
        # tanggal ini belum punya log atau gagal dibaca.
        self.claude_code_check.setChecked(False)
        self.github_check.setChecked(False)
        self.catatan_edit.clear()
        # Catatan saat dimuat. Saat Simpan, catatan yang sama dikirim sebagai
        # note=None (catatan lama tidak disentuh), bukan ditulis ulang.
        self._catatan_awal = ""
        self.error_label.clear()
        self.error_label.hide()

        try:
            log = get_daily_log(self.conn, self.tanggal)
        except sqlite3.Error as e:  # misalnya database terkunci
            self._tampilkan_error(f"Log {self.tanggal} gagal dibaca: {e}")
            self.tombol_simpan.setEnabled(False)
            return
        self.tombol_simpan.setEnabled(True)
        if log is not None:
            self.claude_code_check.setChecked(bool(log["claude_code"]))
            self.github_check.setChecked(bool(log["github"]))
            self._catatan_awal = (log["note"] or "").strip()
            self.catatan_edit.setText(log["note"] or "")

    def simpan(self) -> None:
        """Simpan log tanggal terpilih. Berhasil: form ditutup. Gagal: pesan tampil di form."""
        catatan = self.catatan_edit.text().strip()
        # set_daily_log: note=None membiarkan catatan lama, note="" mengosongkannya.
        note = None if catatan == self._catatan_awal else catatan
        try:
            set_daily_log(
                self.conn,
                self.tanggal,
                self.claude_code_check.isChecked(),
                self.github_check.isChecked(),
                note=note,
            )
        except ValueError as e:
            self._tampilkan_error(str(e))
            return
        except sqlite3.Error as e:
            self._tampilkan_error(f"Gagal menyimpan ke database: {e}")
            return
        self.accept()
