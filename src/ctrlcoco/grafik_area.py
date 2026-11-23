from dataclasses import dataclass

from PySide6.QtWidgets import QGridLayout, QLabel, QWidget

from ctrlcoco.analytics import RateArea

LEBAR_BATANG_PX = 200
TINGGI_BATANG_PX = 14
WARNA_BATANG = "#3fa34d"  # sama dengan heatmap dan warna lompat Coco
WARNA_KOSONG = "#9e9e9e"  # teks abu untuk area tanpa task di rentang

TEKS_KOSONG = "belum ada task"
TEKS_ON_TIME_KOSONG = "On-time rate: belum ada task selesai dengan deadline"


def _persen(rate: float) -> int:
    """Persen bulat; setengah dibulatkan ke atas (12,5 menjadi 13)."""
    return int(rate * 100 + 0.5)


def teks_rate(area: RateArea) -> str:
    """Teks di samping batang: "67% (2/3)", atau "belum ada task" bila `rate` None.

    Penyebut nol sengaja tidak ditulis "0%": 0% berarti ada task tapi belum ada yang selesai.
    """
    if area.rate is None:
        return TEKS_KOSONG
    return f"{_persen(area.rate)}% ({area.selesai}/{area.total})"


def teks_on_time(rate: float | None) -> str:
    """Teks on-time rate. `None` (tidak ada task selesai berdeadline) bukan 0%."""
    if rate is None:
        return TEKS_ON_TIME_KOSONG
    return f"On-time rate: {_persen(rate)}%"


@dataclass
class BarisArea:
    nama: QLabel
    batang: QLabel
    teks: QLabel


class GrafikCompletionRate(QWidget):
    """Grafik batang completion rate per area: satu baris per area, urutan sama dengan analitik.

    Hanya menggambar: nilainya datang dari `completion_rate_per_area` di analytics.py.
    Tiap batang membawa properti `rate` (float atau None) dan `kosong` (True bila tanpa task),
    sehingga tes membaca nilainya tanpa membandingkan piksel.
    """

    def __init__(self, rates: list[RateArea], parent: QWidget | None = None):
        super().__init__(parent)
        self.baris: list[BarisArea] = []
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)

        for i, area in enumerate(rates):
            nama = QLabel(area.nama)
            batang = QLabel()
            teks = QLabel(teks_rate(area))
            kosong = area.rate is None
            batang.setProperty("rate", area.rate)
            batang.setProperty("kosong", kosong)
            if kosong:
                batang.setFixedSize(0, TINGGI_BATANG_PX)
                batang.hide()  # tanpa batang, supaya tidak terbaca 0%
                teks.setStyleSheet(f"color: {WARNA_KOSONG};")
            else:
                batang.setFixedSize(round(area.rate * LEBAR_BATANG_PX), TINGGI_BATANG_PX)
                batang.setStyleSheet(f"background-color: {WARNA_BATANG}; border-radius: 2px;")
            grid.addWidget(nama, i, 0)
            grid.addWidget(batang, i, 1)
            grid.addWidget(teks, i, 2)
            self.baris.append(BarisArea(nama, batang, teks))
