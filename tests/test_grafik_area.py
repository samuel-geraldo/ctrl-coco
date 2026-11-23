"""Tes grafik completion rate tanpa layar: batang dibaca lewat properti, bukan piksel."""
from datetime import date, datetime
from pathlib import Path

from ctrlcoco import analytics, data
from ctrlcoco import grafik_area as grafik_module
from ctrlcoco.analytics import RateArea
from ctrlcoco.grafik_area import (
    LEBAR_BATANG_PX,
    GrafikCompletionRate,
    teks_on_time,
    teks_rate,
)

AWAL = date(2026, 3, 1)
AKHIR = date(2026, 3, 31)


def _task(conn, area_id, dibuat, selesai=False):
    t = datetime.strptime(dibuat, "%Y-%m-%d %H:%M")
    task_id = data.add_task(conn, area_id, "t", now=t)
    if selesai:
        data.complete_task(conn, task_id, now=t)


def isi_contoh(conn):
    """Kuliah 2/3, Olahraga 0/2, Portofolio tanpa task, dan satu task Kuliah di luar rentang."""
    kuliah = data.add_area(conn, "Kuliah")
    olahraga = data.add_area(conn, "Olahraga")
    data.add_area(conn, "Portofolio")
    _task(conn, kuliah, "2026-03-02 08:00", selesai=True)
    _task(conn, kuliah, "2026-03-03 08:00", selesai=True)
    _task(conn, kuliah, "2026-03-04 08:00")
    _task(conn, olahraga, "2026-03-05 08:00")
    _task(conn, olahraga, "2026-03-06 08:00")
    _task(conn, kuliah, "2025-01-01 08:00", selesai=True)  # di luar rentang


def grafik(conn):
    g = GrafikCompletionRate(analytics.completion_rate_per_area(conn, AWAL, AKHIR))
    g.show()  # offscreen, jadi tidak ada jendela sungguhan
    return g


def test_satu_baris_per_area_urut_sama_dengan_fungsi_analitik(app, conn):
    isi_contoh(conn)
    rates = analytics.completion_rate_per_area(conn, AWAL, AKHIR)
    g = grafik(conn)
    assert len(g.baris) == len(rates) == 3
    assert [b.nama.text() for b in g.baris] == ["Kuliah", "Olahraga", "Portofolio"]
    assert [b.nama.text() for b in g.baris] == [r.nama for r in rates]


def test_nilai_batang_sama_dengan_completion_rate(app, conn):
    isi_contoh(conn)
    rates = analytics.completion_rate_per_area(conn, AWAL, AKHIR)
    g = grafik(conn)
    assert [b.batang.property("rate") for b in g.baris] == [r.rate for r in rates]
    assert g.baris[0].batang.property("rate") == 2 / 3


def test_lebar_batang_sebanding_dengan_rate(app, conn):
    isi_contoh(conn)
    g = grafik(conn)
    assert g.baris[0].batang.minimumWidth() == round(2 / 3 * LEBAR_BATANG_PX)
    assert g.baris[1].batang.minimumWidth() == 0  # 0 selesai dari 2: batang kosong, bukan hilang


def test_penyebut_nol_ditandai_beda_dari_nol_persen(app, conn):
    isi_contoh(conn)
    g = grafik(conn)
    olahraga, portofolio = g.baris[1], g.baris[2]
    # 0 selesai dari 2 task: 0% sungguhan.
    assert olahraga.batang.property("kosong") is False
    assert not olahraga.batang.isHidden()
    assert olahraga.teks.text() == "0% (0/2)"
    # Tanpa task di rentang: bukan 0%, tidak ada batang.
    assert portofolio.batang.property("kosong") is True
    assert portofolio.batang.property("rate") is None
    assert portofolio.batang.isHidden()
    assert portofolio.teks.text() == "belum ada task"
    assert "0%" not in portofolio.teks.text()


def test_semua_area_penyebut_nol_tanpa_galat(app, conn):
    data.add_area(conn, "Kuliah")
    data.add_area(conn, "Olahraga")
    g = grafik(conn)
    assert len(g.baris) == 2
    assert all(b.batang.property("kosong") is True for b in g.baris)


def test_tanpa_area_tanpa_galat(app):
    g = GrafikCompletionRate([])
    g.show()
    assert g.baris == []


def test_teks_rate_membulatkan_ke_persen_bulat():
    assert teks_rate(RateArea(1, "A", 2, 3, 2 / 3)) == "67% (2/3)"
    assert teks_rate(RateArea(1, "A", 1, 3, 1 / 3)) == "33% (1/3)"
    assert teks_rate(RateArea(1, "A", 1, 8, 1 / 8)) == "13% (1/8)"  # 12,5 dibulatkan ke atas
    assert teks_rate(RateArea(1, "A", 3, 3, 1.0)) == "100% (3/3)"
    assert teks_rate(RateArea(1, "A", 0, 4, 0.0)) == "0% (0/4)"
    assert teks_rate(RateArea(1, "A", 0, 0, None)) == "belum ada task"


def test_teks_on_time():
    assert teks_on_time(0.5) == "On-time rate: 50%"
    assert teks_on_time(0.0) == "On-time rate: 0%"      # semua terlambat, bukan "tidak ada data"
    assert teks_on_time(1.0) == "On-time rate: 100%"
    assert teks_on_time(None) == "On-time rate: belum ada task selesai dengan deadline"


def test_modul_tampilan_tanpa_sql_dan_tanpa_hitungan_metrik():
    sumber = Path(grafik_module.__file__).read_text(encoding="utf-8")
    assert "execute" not in sumber and "SELECT" not in sumber
