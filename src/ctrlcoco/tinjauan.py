import sqlite3
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QWidget

from ctrlcoco.analytics import RENTANG_TINJAUAN_HARI, ada_data, tinjauan_mingguan
from ctrlcoco.ringkasan import FORMAT_TANGGAL


class JendelaTinjauan(QDialog):
    """Jendela Tinjauan mingguan: angka 7 hari terakhir sampai hari ini (#80).

    Jendela hanya menampilkan. Semua angka datang dari analytics.py, dibaca sekali saat
    jendela dibuka.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        now: datetime | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Tinjauan mingguan")
        # Dihapus dari memori setelah ditutup, supaya tidak menumpuk.
        self.setAttribute(Qt.WA_DeleteOnClose)

        hasil = tinjauan_mingguan(conn, now or datetime.now())
        self.rentang_label = QLabel(
            f"{RENTANG_TINJAUAN_HARI} hari terakhir "
            f"({hasil.awal.strftime(FORMAT_TANGGAL)} - {hasil.akhir.strftime(FORMAT_TANGGAL)})"
        )

        ada = ada_data(conn)
        self.kosong_label = QLabel("Belum ada data. Catat log atau tambah task dulu.")
        self.kosong_label.setWordWrap(True)
        self.kosong_label.setVisible(not ada)

        self.selesai_label = QLabel(f"Task selesai: {hasil.task_selesai}")
        self.terlambat_label = QLabel(f"Task terlambat: {hasil.task_terlambat}")
        self.hari_valid_label = QLabel(
            f"Hari valid: {hasil.jumlah_hari_valid} dari {RENTANG_TINJAUAN_HARI}"
        )
        self.streak_label = QLabel(f"Streak saat ini: {hasil.streak} hari")

        layout = QVBoxLayout(self)
        layout.addWidget(self.rentang_label)
        layout.addWidget(self.kosong_label)
        for label in (
            self.selesai_label,
            self.terlambat_label,
            self.hari_valid_label,
            self.streak_label,
        ):
            label.setVisible(ada)  # database kosong: hanya pesannya yang tampil
            layout.addWidget(label)
