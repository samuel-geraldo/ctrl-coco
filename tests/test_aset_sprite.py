"""Penjaga aset sprite di assets/sprites/ (aturan di docs/sprite.md).

Selama folder sprite belum ada, tes untuk folder sungguhan lulus tanpa memeriksa apa
pun; tes ini mulai bekerja saat sprite ditambahkan (#71-#73).
"""
import re

import pytest
from ctrlcoco.aset import folder_sprite
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage

UKURAN_SPRITE = 64
KONDISI_SPRITE = ("senang", "waspada", "tidur", "lompat")
POLA_PNG = re.compile(rf"({'|'.join(KONDISI_SPRITE)})_([1-9][0-9]*)\.png")
POLA_PISKEL = re.compile(rf"({'|'.join(KONDISI_SPRITE)})\.piskel")


def masalah_aset(folder):
    """Daftar pelanggaran aturan sprite di `folder`; kosong berarti semua sesuai."""
    if not folder.is_dir():
        return []
    masalah = []
    nomor = {}
    for path in sorted(folder.iterdir()):
        if POLA_PISKEL.fullmatch(path.name):
            continue
        cocok = POLA_PNG.fullmatch(path.name)
        if not cocok:
            masalah.append(f"{path.name}: nama tidak sesuai pola <kondisi>_<n>.png")
            continue
        nomor.setdefault(cocok.group(1), []).append(int(cocok.group(2)))
        gambar = QImage(str(path))
        if gambar.isNull():
            masalah.append(f"{path.name}: bukan gambar PNG yang bisa dibaca")
            continue
        if (gambar.width(), gambar.height()) != (UKURAN_SPRITE, UKURAN_SPRITE):
            masalah.append(f"{path.name}: ukuran {gambar.width()}x{gambar.height()}, harus 64x64")
        if not gambar.hasAlphaChannel() or gambar.pixelColor(0, 0).alpha() != 0:
            masalah.append(f"{path.name}: latar tidak transparan")
    for kondisi, daftar in nomor.items():
        if sorted(daftar) != list(range(1, len(daftar) + 1)):
            masalah.append(f"{kondisi}: nomor frame harus berurutan mulai 1, ada {sorted(daftar)}")
    return masalah


def simpan_png(path, ukuran=UKURAN_SPRITE, latar=Qt.transparent):
    gambar = QImage(ukuran, ukuran, QImage.Format_ARGB32)
    gambar.fill(latar)
    gambar.setPixelColor(ukuran // 2, ukuran // 2, QColor("#d1923a"))  # sedikit isi
    assert gambar.save(str(path))


# --- folder sprite sungguhan ---

def test_aset_sprite_di_repo_sesuai_aturan(app):
    assert masalah_aset(folder_sprite()) == []


# --- pemeriksa itu sendiri, dengan folder sementara ---

def test_folder_yang_belum_ada_tidak_bermasalah(tmp_path):
    assert masalah_aset(tmp_path / "tidak_ada") == []


def test_sprite_yang_benar_lolos(app, tmp_path):
    for nama in ["senang_1.png", "senang_2.png", "lompat_1.png", "lompat_2.png", "lompat_3.png"]:
        simpan_png(tmp_path / nama)
    (tmp_path / "senang.piskel").write_text("{}", encoding="utf-8")
    assert masalah_aset(tmp_path) == []


@pytest.mark.parametrize(
    "nama",
    ["Senang_1.png", "senang_0.png", "senang_01.png", "senang.png", "marah_1.png", "catatan.txt"],
)
def test_nama_salah_ditandai(app, tmp_path, nama):
    # Nama diperiksa sebelum isinya, jadi isi berkas tidak penting di sini.
    (tmp_path / nama).write_bytes(b"x")
    assert masalah_aset(tmp_path) == [f"{nama}: nama tidak sesuai pola <kondisi>_<n>.png"]


def test_ukuran_selain_64_ditandai(app, tmp_path):
    simpan_png(tmp_path / "senang_1.png", ukuran=32)
    assert masalah_aset(tmp_path) == ["senang_1.png: ukuran 32x32, harus 64x64"]


def test_latar_tidak_transparan_ditandai(app, tmp_path):
    simpan_png(tmp_path / "senang_1.png", latar=QColor("white"))
    assert masalah_aset(tmp_path) == ["senang_1.png: latar tidak transparan"]


def test_nomor_frame_meloncat_ditandai(app, tmp_path):
    simpan_png(tmp_path / "tidur_1.png")
    simpan_png(tmp_path / "tidur_3.png")
    assert masalah_aset(tmp_path) == ["tidur: nomor frame harus berurutan mulai 1, ada [1, 3]"]


def test_berkas_rusak_ditandai(app, tmp_path):
    (tmp_path / "senang_1.png").write_bytes(b"bukan gambar")
    assert masalah_aset(tmp_path) == ["senang_1.png: bukan gambar PNG yang bisa dibaca"]
