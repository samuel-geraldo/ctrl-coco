import sqlite3
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QWidget

from ctrlcoco.analytics import (
    RENTANG_MINGGU,
    ada_data,
    hari_valid,
    longest_streak,
    rentang_ringkasan,
)
from ctrlcoco.heatmap import HeatmapKalender

FORMAT_TANGGAL = "%d/%m/%Y"


class JendelaRingkasan(QDialog):
    """Jendela Ringkasan: kerangka untuk heatmap (#65) dan grafik (#66).

    Jendela hanya menampilkan. Rentang dan pemeriksaan "ada data" datang dari analytics.py.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        today: date | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Ringkasan")
        # Dihapus dari memori setelah ditutup, supaya tidak menumpuk.
        self.setAttribute(Qt.WA_DeleteOnClose)

        awal, akhir = rentang_ringkasan(today or date.today())
        self.rentang_label = QLabel(
            f"{RENTANG_MINGGU} minggu terakhir "
            f"({awal.strftime(FORMAT_TANGGAL)} - {akhir.strftime(FORMAT_TANGGAL)})"
        )

        ada = ada_data(conn)
        self.kosong_label = QLabel("Belum ada data. Catat log atau tambah task dulu.")
        self.kosong_label.setWordWrap(True)
        self.kosong_label.setVisible(not ada)

        # Heatmap hari valid (#65) dan angka streak terpanjang (#63). Keduanya disembunyikan
        # bila database kosong, supaya yang tampil hanya pesan "belum ada data".
        self.heatmap = HeatmapKalender(awal, akhir, hari_valid(conn, awal, akhir))
        self.heatmap.setVisible(ada)
        self.streak_label = QLabel(f"Streak terpanjang: {longest_streak(conn, awal, akhir)} hari")
        self.streak_label.setVisible(ada)

        layout = QVBoxLayout(self)
        layout.addWidget(self.rentang_label)
        layout.addWidget(self.kosong_label)
        layout.addWidget(self.heatmap)
        layout.addWidget(self.streak_label)
