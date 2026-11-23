import sqlite3
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QWidget

from ctrlcoco.analytics import RENTANG_MINGGU, ada_data, rentang_ringkasan

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

        self.kosong_label = QLabel("Belum ada data. Catat log atau tambah task dulu.")
        self.kosong_label.setWordWrap(True)
        self.kosong_label.setVisible(not ada_data(conn))

        layout = QVBoxLayout(self)
        layout.addWidget(self.rentang_label)
        layout.addWidget(self.kosong_label)
