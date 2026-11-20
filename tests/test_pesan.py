import ast
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from ctrlcoco import pesan
from ctrlcoco.pesan import pesan_coco, teks_sisa_waktu

NOW = datetime(2026, 3, 10, 9, 30)


def task(judul="Laporan", deadline=NOW + timedelta(hours=3)):
    """Task tiruan dengan kolom yang dipakai pesan_coco (seperti sqlite3.Row)."""
    return {"title": judul, "deadline": deadline.strftime("%Y-%m-%d %H:%M")}


# --- teks sisa waktu ---

@pytest.mark.parametrize(
    "selisih, teks",
    [
        (timedelta(minutes=30), "30 menit lagi"),
        (timedelta(minutes=1), "1 menit lagi"),
        (timedelta(minutes=59), "59 menit lagi"),
        (timedelta(minutes=60), "1 jam lagi"),
        (timedelta(hours=3, minutes=59), "3 jam lagi"),
        (timedelta(hours=23, minutes=59), "23 jam lagi"),
        (timedelta(hours=24), "1 hari lagi"),
        (timedelta(days=2, hours=5), "2 hari lagi"),
    ],
)
def test_sisa_waktu_sebelum_deadline(selisih, teks):
    assert teks_sisa_waktu(NOW + selisih, NOW) == teks


@pytest.mark.parametrize(
    "selisih",
    [timedelta(0), timedelta(seconds=30), timedelta(seconds=-30)],
    ids=["tepat", "30_detik_sebelum", "30_detik_sesudah"],
)
def test_sisa_waktu_tepat_di_deadline(selisih):
    # now punya detik, deadline hanya sampai menit: selisih di bawah 1 menit dianggap tepat.
    assert teks_sisa_waktu(NOW + selisih, NOW) == "sekarang"


@pytest.mark.parametrize(
    "terlambat, teks",
    [
        (timedelta(minutes=1), "terlambat 1 menit"),
        (timedelta(minutes=45), "terlambat 45 menit"),
        (timedelta(hours=2, minutes=30), "terlambat 2 jam"),
        (timedelta(days=3, hours=1), "terlambat 3 hari"),
    ],
)
def test_sisa_waktu_sudah_lewat(terlambat, teks):
    assert teks_sisa_waktu(NOW - terlambat, NOW) == teks


# --- pesan_coco: waspada ---

@pytest.mark.parametrize("hari_ke", [0, 1], ids=["hari_ini", "besok"])
def test_waspada_menyebut_judul_dan_sisa_waktu(hari_ke):
    now = NOW + timedelta(days=hari_ke)
    kalimat = pesan_coco("waspada", 0, task("Laporan", now + timedelta(hours=3)), now)
    assert '"Laporan"' in kalimat
    assert "3 jam lagi" in kalimat


def test_waspada_tepat_di_deadline():
    kalimat = pesan_coco("waspada", 0, task("Laporan", NOW), NOW)
    assert kalimat == 'Deadline "Laporan" sekarang!'


def test_waspada_sudah_lewat_menyebut_terlambat():
    kalimat = pesan_coco("waspada", 0, task("Laporan", NOW - timedelta(hours=2)), NOW)
    assert kalimat == '"Laporan" sudah terlambat 2 jam. Yuk, selesaikan!'


def test_waspada_tanpa_task_tidak_gagal():
    # Hampir mustahil: task selesai dari luar di antara dua query refresh.
    assert pesan_coco("waspada", 0, None, NOW) == "Ada deadline yang mendekat!"


def test_judul_40_karakter_utuh():
    judul = "a" * 40
    kalimat = pesan_coco("waspada", 0, task(judul, NOW - timedelta(hours=2)), NOW)
    assert f'"{judul}"' in kalimat


def test_judul_41_karakter_dipotong():
    judul = "a" * 40 + "b"
    kalimat = pesan_coco("waspada", 0, task(judul, NOW - timedelta(hours=2)), NOW)
    assert f'"{"a" * 39}…"' in kalimat
    assert "b" not in kalimat.split('"')[1]


# --- pesan_coco: senang dan tidur ---

@pytest.mark.parametrize("hari_ke", [0, 1], ids=["hari_ini", "besok"])
def test_senang_menyebut_streak(hari_ke):
    # Dua hari berturut-turut: kedua variasi kalimat sama-sama menyebut streak.
    kalimat = pesan_coco("senang", 5, None, NOW + timedelta(days=hari_ke))
    assert "streak 5 hari" in kalimat.lower()


def test_tidur_streak_0_mengajak_mencatat_log():
    kalimat = pesan_coco("tidur", 0, None, NOW)
    assert kalimat == "Zzz... Belum ada log hari ini. Catat yuk, mulai streak baru!"


def test_tidur_dengan_streak_menyebut_streak_dan_mengajak_mencatat_log():
    kalimat = pesan_coco("tidur", 5, None, NOW)
    assert "streak 5 hari" in kalimat
    assert "Catat log hari ini" in kalimat


def test_kondisi_tidak_dikenal_ditolak():
    with pytest.raises(ValueError):
        pesan_coco("marah", 0, None, NOW)


# --- variasi kalimat deterministik ---

@pytest.mark.parametrize("kondisi", ["waspada", "senang"])
def test_variasi_sama_untuk_input_sama(kondisi):
    t = task("Laporan", NOW + timedelta(hours=3))
    assert pesan_coco(kondisi, 5, t, NOW) == pesan_coco(kondisi, 5, t, NOW)


@pytest.mark.parametrize("kondisi", ["waspada", "senang"])
def test_variasi_tetap_sepanjang_hari(kondisi):
    # Pagi dan sore di hari yang sama, sisa waktunya sama-sama 3 jam lagi:
    # kalimatnya harus sama, supaya gelembung tidak berganti-ganti tiap refresh.
    pagi = NOW.replace(hour=8, minute=0)
    sore = NOW.replace(hour=17, minute=0)
    assert pesan_coco(kondisi, 5, task("Laporan", pagi + timedelta(hours=3)), pagi) == (
        pesan_coco(kondisi, 5, task("Laporan", sore + timedelta(hours=3)), sore)
    )


@pytest.mark.parametrize("kondisi", ["waspada", "senang"])
def test_variasi_berganti_di_hari_berikutnya(kondisi):
    besok = NOW + timedelta(days=1)
    hari_ini = pesan_coco(kondisi, 5, task("Laporan", NOW + timedelta(hours=3)), NOW)
    esok = pesan_coco(kondisi, 5, task("Laporan", besok + timedelta(hours=3)), besok)
    assert hari_ini != esok


# --- modul murni ---

def test_modul_pesan_tidak_mengimpor_pyside6():
    pohon = ast.parse(Path(pesan.__file__).read_text(encoding="utf-8"))
    modul = set()
    for node in ast.walk(pohon):
        if isinstance(node, ast.Import):
            modul.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modul.add(node.module.split(".")[0])
    assert "PySide6" not in modul
