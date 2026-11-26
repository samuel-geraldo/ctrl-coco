import sqlite3
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QWidget

from ctrlcoco.analytics import (
    RENTANG_MINGGU,
    ada_data,
    completion_rate_per_area,
    hari_valid,
    longest_streak,
    median_penyelesaian_per_area,
    on_time_rate,
    produktivitas_per_hari,
    rentang_ringkasan,
)
from ctrlcoco.grafik_area import (
    GrafikCompletionRate,
    teks_median,
    teks_on_time,
    teks_per_hari,
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

        # Grafik completion rate per area (#61) dan on-time rate (#62), juga disembunyikan
        # bila database kosong.
        self.grafik = GrafikCompletionRate(completion_rate_per_area(conn, awal, akhir))
        self.grafik.setVisible(ada)
        self.on_time_label = QLabel(teks_on_time(on_time_rate(conn, awal, akhir)))
        self.on_time_label.setVisible(ada)

        # Median waktu penyelesaian per area (#81). Teks polos: nama area diketik pengguna.
        self.median_label = QLabel()
        self.median_label.setTextFormat(Qt.PlainText)
        self.median_label.setText(teks_median(median_penyelesaian_per_area(conn, awal, akhir)))
        self.median_label.setVisible(ada)

        # Task selesai dan hari valid per hari dalam seminggu (#82).
        self.per_hari_label = QLabel(teks_per_hari(produktivitas_per_hari(conn, awal, akhir)))
        self.per_hari_label.setVisible(ada)

        layout = QVBoxLayout(self)
        layout.addWidget(self.rentang_label)
        layout.addWidget(self.kosong_label)
        layout.addWidget(self.heatmap)
        layout.addWidget(self.streak_label)
        layout.addWidget(self.grafik)
        layout.addWidget(self.on_time_label)
        layout.addWidget(self.median_label)
        layout.addWidget(self.per_hari_label)
