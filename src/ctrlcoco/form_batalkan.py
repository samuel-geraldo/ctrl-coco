import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ctrlcoco.data import batalkan_selesai, list_done_untuk_dibatalkan
from ctrlcoco.form_dasar import FormDasar

TEKS_KOSONG = "Tidak ada task yang sudah selesai"


class FormBatalkanSelesai(FormDasar):
    """Form untuk mengembalikan satu task 'done' ke 'todo'."""

    def __init__(self, conn: sqlite3.Connection, parent: QWidget | None = None):
        super().__init__(parent)
        self.conn = conn
        self.setWindowTitle("Batalkan selesai")

        self.daftar = QListWidget()
        self.kosong_label = QLabel(TEKS_KOSONG)
        self.kosong_label.hide()

        # "Kembalikan", bukan "Batalkan": di sebelahnya sudah ada tombol "Batal".
        tombol = self._buat_tombol("Kembalikan")
        self.tombol_kembalikan = self.tombol_utama
        self.tombol_kembalikan.setEnabled(False)  # aktif setelah ada task yang dipilih
        tombol.accepted.connect(self.kembalikan)

        layout = QVBoxLayout(self)
        layout.addWidget(self.daftar)
        layout.addWidget(self.kosong_label)
        layout.addWidget(self.error_label)
        layout.addWidget(tombol)

        self.daftar.itemSelectionChanged.connect(self._perbarui_tombol)
        gagal = self._isi_daftar()
        if gagal:
            self._tampilkan_error(gagal)

    def _isi_daftar(self) -> str | None:
        """Baca task 'done' dan isi daftar dari awal. Mengembalikan pesan error atau None."""
        self.daftar.clear()
        self.tombol_kembalikan.setEnabled(False)
        try:
            tasks = list_done_untuk_dibatalkan(self.conn)
        except sqlite3.Error as e:  # misalnya database terkunci
            self.daftar.show()
            self.kosong_label.hide()
            return f"Daftar task gagal dibaca: {e}"

        for t in tasks:
            item = QListWidgetItem(f"{t['title']} · {t['area']} · selesai {t['completed_at']}")
            item.setData(Qt.UserRole, t["id"])  # id disimpan, tidak ditampilkan
            self.daftar.addItem(item)
        self.daftar.setVisible(bool(tasks))
        self.kosong_label.setVisible(not tasks)
        return None

    def _perbarui_tombol(self) -> None:
        self.tombol_kembalikan.setEnabled(bool(self.daftar.selectedItems()))

    def kembalikan(self) -> None:
        """Kembalikan task yang dipilih. Berhasil: form ditutup. Gagal: pesan di form."""
        dipilih = self.daftar.selectedItems()
        if not dipilih:
            return
        try:
            batalkan_selesai(self.conn, dipilih[0].data(Qt.UserRole))
        except ValueError as e:  # task sudah dihapus dari jalur lain
            pesan = str(e)
            gagal = self._isi_daftar()
            if gagal:
                pesan = f"{pesan}\n{gagal}"
            self._tampilkan_error(pesan)
            return
        except sqlite3.Error as e:
            self._tampilkan_error(f"Gagal menyimpan ke database: {e}")
            return
        self.accept()
