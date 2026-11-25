import sqlite3
from datetime import datetime

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from ctrlcoco.data import DATE_FORMAT, get_daily_log, set_daily_log
from ctrlcoco.form_dasar import FormDasar


class FormLogHarian(FormDasar):
    """Form log hari ini: centang Claude Code dan GitHub, plus catatan opsional."""

    def __init__(self, conn: sqlite3.Connection, now: datetime, parent: QWidget | None = None):
        super().__init__(parent)
        self.conn = conn
        # Tanggal diambil saat form dibuka, dari parameter (bukan datetime.now() di sini),
        # supaya bisa dites dengan tanggal tetap.
        self.tanggal = now.strftime(DATE_FORMAT)
        self.setWindowTitle(f"Log hari ini ({self.tanggal})")

        self.claude_code_check = QCheckBox("Claude Code")
        self.github_check = QCheckBox("GitHub")
        self.catatan_edit = QLineEdit()
        self.catatan_edit.setPlaceholderText("opsional")

        tombol = self._buat_tombol("Simpan")
        self.tombol_simpan = self.tombol_utama
        self.tombol_simpan.setDefault(True)
        tombol.accepted.connect(self.simpan)

        isian = QFormLayout()
        isian.addRow(self.claude_code_check)
        isian.addRow(self.github_check)
        isian.addRow("Catatan", self.catatan_edit)

        layout = QVBoxLayout(self)
        layout.addLayout(isian)
        layout.addWidget(self.error_label)
        layout.addWidget(tombol)

        # Catatan saat form dibuka. Saat Simpan, catatan yang sama dikirim sebagai
        # note=None (catatan lama tidak disentuh), bukan ditulis ulang.
        self._catatan_awal = ""
        try:
            log = get_daily_log(conn, self.tanggal)
        except sqlite3.Error as e:  # misalnya database terkunci
            self._tampilkan_error(f"Log hari ini gagal dibaca: {e}")
            self.tombol_simpan.setEnabled(False)
            return
        if log is not None:
            self.claude_code_check.setChecked(bool(log["claude_code"]))
            self.github_check.setChecked(bool(log["github"]))
            self._catatan_awal = (log["note"] or "").strip()
            self.catatan_edit.setText(log["note"] or "")

    def simpan(self) -> None:
        """Simpan log hari ini. Berhasil: form ditutup (accept). Gagal: pesan tampil di form."""
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
