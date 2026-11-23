from datetime import date, timedelta

from PySide6.QtWidgets import QGridLayout, QLabel, QWidget

UKURAN_SEL_PX = 16
JARAK_SEL_PX = 3
WARNA_VALID = "#3fa34d"       # hari valid; sama dengan warna lompat Coco
WARNA_TIDAK_VALID = "#e0e0e0"  # hari dalam rentang tanpa log valid


def posisi_sel(hari: date, awal: date) -> tuple[int, int]:
    """(baris, kolom) sel `hari` di grid.

    Baris menurut hari (Senin 0 sampai Minggu 6), kolom menurut minggu.
    Kolom 0 adalah minggu (Senin sampai Minggu) yang memuat `awal`.
    """
    senin_pertama = awal - timedelta(days=awal.weekday())
    return hari.weekday(), (hari - senin_pertama).days // 7


class HeatmapKalender(QWidget):
    """Heatmap kalender: satu sel per hari dalam rentang, hari valid diberi warna.

    Hanya menggambar: daftar hari valid datang dari analytics.py. Sel sebelum `awal` dan
    sesudah `akhir` (sisa minggu pertama dan terakhir) dikosongkan, bukan digambar.
    """

    def __init__(
        self, awal: date, akhir: date, hari_valid: list[date], parent: QWidget | None = None
    ):
        super().__init__(parent)
        valid = set(hari_valid)
        self.sel: dict[date, QLabel] = {}
        self.grid = QGridLayout(self)
        self.grid.setSpacing(JARAK_SEL_PX)
        self.grid.setContentsMargins(0, 0, 0, 0)

        for i in range((akhir - awal).days + 1):
            hari = awal + timedelta(days=i)
            sel = QLabel()
            sel.setFixedSize(UKURAN_SEL_PX, UKURAN_SEL_PX)
            ditandai = hari in valid
            sel.setProperty("valid", ditandai)
            sel.setToolTip(hari.strftime("%d/%m/%Y"))
            warna = WARNA_VALID if ditandai else WARNA_TIDAK_VALID
            sel.setStyleSheet(f"background-color: {warna}; border-radius: 2px;")
            baris, kolom = posisi_sel(hari, awal)
            self.grid.addWidget(sel, baris, kolom)
            self.sel[hari] = sel
