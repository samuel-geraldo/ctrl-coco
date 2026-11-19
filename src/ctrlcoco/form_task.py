import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from ctrlcoco.data import list_areas, simpan_task_baru

ERROR_STYLE = "QLabel { color: #c62828; }"


class FormTambahTask(QDialog):
    """Form tambah task. Tampilan saja; aturan dan penyimpanan ada di simpan_task_baru."""

    def __init__(self, conn: sqlite3.Connection, parent: QWidget | None = None):
        super().__init__(parent)
        self.conn = conn
        self.setWindowTitle("Tambah task")
        # Dihapus dari memori setelah ditutup, supaya membuka form berkali-kali
        # tidak meninggalkan dialog lama yang menumpuk.
        self.setAttribute(Qt.WA_DeleteOnClose)

        # Combo yang bisa diketik: pilih area lama atau ketik nama area baru.
        self.area_combo = QComboBox()
        self.area_combo.setEditable(True)

        self.judul_edit = QLineEdit()
        self.deadline_edit = QLineEdit()
        self.deadline_edit.setPlaceholderText("YYYY-MM-DD HH:MM")

        # Pesan error tampil di sini; form tetap terbuka dan isian tidak dihapus.
        self.error_label = QLabel()
        self.error_label.setStyleSheet(ERROR_STYLE)
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        tombol = QDialogButtonBox()
        self.tombol_simpan = tombol.addButton("Simpan", QDialogButtonBox.AcceptRole)
        self.tombol_batal = tombol.addButton("Batal", QDialogButtonBox.RejectRole)
        self.tombol_simpan.setDefault(True)  # Enter = Simpan
        tombol.accepted.connect(self.simpan)
        tombol.rejected.connect(self.reject)

        isian = QFormLayout()
        isian.addRow("Area", self.area_combo)
        isian.addRow("Judul", self.judul_edit)
        isian.addRow("Deadline", self.deadline_edit)

        layout = QVBoxLayout(self)
        layout.addLayout(isian)
        layout.addWidget(self.error_label)
        layout.addWidget(tombol)

        try:
            areas = list_areas(conn)
        except sqlite3.Error as e:  # misalnya database terkunci
            self._tampilkan_error(f"Daftar area gagal dibaca: {e}")
            self.tombol_simpan.setEnabled(False)
            return
        self.area_combo.addItems([a["name"] for a in areas])

    def simpan(self) -> None:
        """Simpan isian. Berhasil: form ditutup (accept). Gagal: pesan tampil di form."""
        try:
            simpan_task_baru(
                self.conn,
                self.area_combo.currentText(),
                self.judul_edit.text(),
                self.deadline_edit.text(),
            )
        except ValueError as e:  # aturan dari data.py: nama kosong, format deadline, dll.
            self._tampilkan_error(str(e))
            return
        except sqlite3.Error as e:  # misalnya database terkunci
            self._tampilkan_error(f"Gagal menyimpan ke database: {e}")
            return
        self.accept()

    def _tampilkan_error(self, pesan: str) -> None:
        self.error_label.setText(pesan)
        self.error_label.show()
