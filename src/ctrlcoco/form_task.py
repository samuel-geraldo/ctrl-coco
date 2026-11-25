import sqlite3
from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ctrlcoco.data import TIME_FORMAT, list_areas, simpan_task_baru
from ctrlcoco.deadline import deadline_cepat
from ctrlcoco.form_dasar import FormDasar

FORMAT_TAMPIL = "dd/MM/yyyy HH:mm"  # tampilan pemilih; yang disimpan tetap TIME_FORMAT
TEKS_TOMBOL_CEPAT = {
    "hari_ini": "Hari ini 23:59",
    "besok": "Besok 23:59",
    "minggu_depan": "Minggu depan",
}


class FormTambahTask(FormDasar):
    """Form tambah task. Tampilan saja; aturan dan penyimpanan ada di simpan_task_baru."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        parent: QWidget | None = None,
        jam: Callable[[], datetime] = datetime.now,
    ):
        super().__init__(parent)
        self.conn = conn
        # Sumber waktu untuk tombol cepat; tes menggantinya dengan jam tiruan.
        self._jam = jam
        self.setWindowTitle("Tambah task")

        # Combo yang bisa diketik: pilih area lama atau ketik nama area baru.
        self.area_combo = QComboBox()
        self.area_combo.setEditable(True)

        self.judul_edit = QLineEdit()

        # Nilai awal "Tanpa deadline": bila pengguna tidak menyentuh deadline, task tidak
        # diam-diam mendapat deadline hari ini (yang membuat Coco waspada tanpa alasan).
        self.tanpa_deadline_check = QCheckBox("Tanpa deadline")
        self.tanpa_deadline_check.setChecked(True)

        # Pemilih tanggal dan jam dengan kalender. Nonaktif selama "Tanpa deadline"
        # dicentang; isinya hari ini 23:59 sebagai titik mulai.
        self.deadline_edit = QDateTimeEdit()
        self.deadline_edit.setCalendarPopup(True)
        self.deadline_edit.setDisplayFormat(FORMAT_TAMPIL)
        self.deadline_edit.setDateTime(QDateTime(deadline_cepat("hari_ini", jam())))
        self.deadline_edit.setEnabled(False)
        self.tanpa_deadline_check.toggled.connect(
            lambda tanpa: self.deadline_edit.setEnabled(not tanpa)
        )

        baris_cepat = QHBoxLayout()
        self.tombol_cepat = {}
        for pilihan, teks in TEKS_TOMBOL_CEPAT.items():
            tombol = QPushButton(teks)
            # Bukan tombol default: Enter tetap berarti Simpan.
            tombol.setAutoDefault(False)
            tombol.clicked.connect(lambda _=False, p=pilihan: self.pilih_cepat(p))
            baris_cepat.addWidget(tombol)
            self.tombol_cepat[pilihan] = tombol

        kolom_deadline = QVBoxLayout()
        kolom_deadline.addWidget(self.tanpa_deadline_check)
        kolom_deadline.addWidget(self.deadline_edit)
        kolom_deadline.addLayout(baris_cepat)

        tombol = self._buat_tombol("Simpan")
        self.tombol_simpan = self.tombol_utama
        self.tombol_simpan.setDefault(True)  # Enter = Simpan
        tombol.accepted.connect(self.simpan)

        isian = QFormLayout()
        isian.addRow("Area", self.area_combo)
        isian.addRow("Judul", self.judul_edit)
        isian.addRow("Deadline", kolom_deadline)

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

    def pilih_cepat(self, pilihan: str) -> None:
        """Isi pemilih dari tombol cepat. Memilih tanggal berarti ingin ada deadline."""
        # Jam dibaca saat tombol diklik, bukan saat form dibuka.
        self.deadline_edit.setDateTime(QDateTime(deadline_cepat(pilihan, self._jam())))
        self.tanpa_deadline_check.setChecked(False)

    def _teks_deadline(self) -> str | None:
        """None bila tanpa deadline; selain itu teks ketat TIME_FORMAT untuk data.py."""
        if self.tanpa_deadline_check.isChecked():
            return None
        return self.deadline_edit.dateTime().toPython().strftime(TIME_FORMAT)

    def simpan(self) -> None:
        """Simpan isian. Berhasil: form ditutup (accept). Gagal: pesan tampil di form."""
        try:
            simpan_task_baru(
                self.conn,
                self.area_combo.currentText(),
                self.judul_edit.text(),
                self._teks_deadline(),
            )
        except ValueError as e:  # aturan dari data.py: nama kosong, format deadline, dll.
            self._tampilkan_error(str(e))
            return
        except sqlite3.Error as e:  # misalnya database terkunci
            self._tampilkan_error(f"Gagal menyimpan ke database: {e}")
            return
        self.accept()
