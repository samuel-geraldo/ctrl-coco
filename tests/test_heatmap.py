"""Tes heatmap kalender tanpa layar: sel dibaca lewat properti, bukan piksel."""
from datetime import date
from pathlib import Path

from ctrlcoco import heatmap as heatmap_module
from ctrlcoco.heatmap import HeatmapKalender, posisi_sel

AWAL = date(2025, 12, 17)   # Rabu
AKHIR = date(2026, 3, 10)   # Selasa; rentang 84 hari, seperti jendela Ringkasan


def buat(hari_valid):
    h = HeatmapKalender(AWAL, AKHIR, hari_valid)
    h.show()  # offscreen, jadi tidak ada jendela sungguhan
    return h


def ditandai(h):
    return {hari for hari, sel in h.sel.items() if sel.property("valid")}


def test_satu_sel_per_hari_dalam_rentang(app):
    h = buat([])
    assert len(h.sel) == 84
    assert min(h.sel) == AWAL and max(h.sel) == AKHIR


def test_sel_ditandai_sama_dengan_hari_valid(app):
    valid = [date(2026, 1, 5), date(2026, 1, 6), date(2026, 3, 10)]
    h = buat(valid)
    assert ditandai(h) == set(valid)


def test_hari_valid_di_luar_rentang_tidak_ditandai_dan_tidak_punya_sel(app):
    h = buat([date(2025, 12, 16), date(2026, 3, 11), date(2026, 1, 5)])
    assert date(2025, 12, 16) not in h.sel and date(2026, 3, 11) not in h.sel
    assert ditandai(h) == {date(2026, 1, 5)}


def test_sel_valid_tampil_berbeda_dari_sel_tidak_valid(app):
    h = buat([date(2026, 1, 5)])
    assert h.sel[date(2026, 1, 5)].styleSheet() != h.sel[date(2026, 1, 6)].styleSheet()


def test_kolom_dimulai_hari_senin_dan_baris_menurut_hari(app):
    h = buat([])
    assert h.grid.columnCount() == 13
    for hari, sel in h.sel.items():
        baris, kolom, _, _ = h.grid.getItemPosition(h.grid.indexOf(sel))
        assert (baris, kolom) == posisi_sel(hari, AWAL)
        assert baris == hari.weekday()  # Senin di baris 0, Minggu di baris 6


def test_posisi_sel_awal_dan_hari_ini():
    assert posisi_sel(AWAL, AWAL) == (2, 0)     # Rabu di kolom pertama
    assert posisi_sel(AKHIR, AWAL) == (1, 12)   # Selasa di kolom terakhir


def test_sel_sebelum_awal_dan_sesudah_akhir_dikosongkan(app):
    h = buat([])
    assert h.grid.itemAtPosition(0, 0) is None    # Senin 15 Des, sebelum rentang
    assert h.grid.itemAtPosition(1, 0) is None    # Selasa 16 Des
    assert h.grid.itemAtPosition(2, 0) is not None  # Rabu 17 Des, awal rentang
    assert h.grid.itemAtPosition(1, 12) is not None  # Selasa 10 Mar, hari ini
    assert h.grid.itemAtPosition(2, 12) is None   # Rabu 11 Mar, sesudah rentang


def test_modul_tampilan_tanpa_sql_dan_tanpa_hitungan_metrik():
    sumber = Path(heatmap_module.__file__).read_text(encoding="utf-8")
    assert "execute" not in sumber and "SELECT" not in sumber
