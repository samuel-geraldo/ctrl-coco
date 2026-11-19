import sqlite3
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ctrlcoco.data import complete_task, list_todo_untuk_selesai
from ctrlcoco.form_task import ERROR_STYLE

TEKS_KOSONG = "Tidak ada task yang perlu diselesaikan"


class FormSelesaikanTask(QDialog):
    """Form untuk menandai satu task 'todo' sebagai selesai."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        parent: QWidget | None = None,
        now: datetime | None = None,
    ):
        super().__init__(parent)
        self.conn = conn
        self.now = now  # None: complete_task memakai datetime.now()
        self.setWindowTitle("Selesaikan task")
        # Dihapus dari memori setelah ditutup, supaya tidak menumpuk.
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.daftar = QListWidget()
        self.kosong_label = QLabel(TEKS_KOSONG)
        self.kosong_label.hide()

        self.error_label = QLabel()
        self.error_label.setStyleSheet(ERROR_STYLE)
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        tombol = QDialogButtonBox()
        self.tombol_selesai = tombol.addButton("Tandai selesai", QDialogButtonBox.AcceptRole)
        self.tombol_batal = tombol.addButton("Batal", QDialogButtonBox.RejectRole)
        self.tombol_selesai.setEnabled(False)  # aktif setelah ada task yang dipilih
        tombol.accepted.connect(self.tandai_selesai)
        tombol.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.daftar)
        layout.addWidget(self.kosong_label)
        layout.addWidget(self.error_label)
        layout.addWidget(tombol)

        try:
            tasks = list_todo_untuk_selesai(conn)
        except sqlite3.Error as e:  # misalnya database terkunci
            self._tampilkan_error(f"Daftar task gagal dibaca: {e}")
            return

        for t in tasks:
            deadline = t["deadline"] or "tanpa deadline"
            item = QListWidgetItem(f"{t['title']} · {t['area']} · {deadline}")
            item.setData(Qt.UserRole, t["id"])  # id disimpan, tidak ditampilkan
            self.daftar.addItem(item)
        if not tasks:
            self.daftar.hide()
            self.kosong_label.show()
        self.daftar.itemSelectionChanged.connect(self._perbarui_tombol)

    def _perbarui_tombol(self) -> None:
        self.tombol_selesai.setEnabled(bool(self.daftar.selectedItems()))

    def tandai_selesai(self) -> None:
        """Tandai task yang dipilih selesai. Berhasil: form ditutup. Gagal: pesan di form."""
        dipilih = self.daftar.selectedItems()
        if not dipilih:
            return
        try:
            complete_task(self.conn, dipilih[0].data(Qt.UserRole), now=self.now)
        except ValueError as e:  # misalnya task sudah dihapus dari jalur lain
            self._tampilkan_error(str(e))
            return
        except sqlite3.Error as e:
            self._tampilkan_error(f"Gagal menyimpan ke database: {e}")
            return
        self.accept()

    def _tampilkan_error(self, pesan: str) -> None:
        self.error_label.setText(pesan)
        self.error_label.show()
