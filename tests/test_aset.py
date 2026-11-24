"""Lokasi folder aset: mode sumber (dari kode) dan mode beku (di dalam .exe PyInstaller)."""
import sys
from pathlib import Path

import pytest
from PySide6.QtGui import QColor, QPixmap

from ctrlcoco import aset, sprites

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def mode_beku(tmp_path, monkeypatch):
    """Pura-pura berjalan sebagai .exe: PyInstaller memasang sys.frozen dan sys._MEIPASS.

    Kedua atribut tidak ada saat dijalankan dari kode, jadi raising=False; monkeypatch
    menghapusnya lagi sesudah tes.
    """
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    return tmp_path


def test_mode_sumber_menunjuk_ke_folder_assets_di_repo():
    assert aset.folder_aset() == REPO / "assets"
    assert (aset.folder_aset() / "logo.png").is_file()


def test_mode_sumber_folder_sprite_ada_di_dalam_assets():
    assert aset.folder_sprite() == REPO / "assets" / "sprites"


def test_mode_beku_menunjuk_ke_folder_paket(mode_beku):
    assert aset.folder_aset() == mode_beku / "assets"
    assert aset.folder_sprite() == mode_beku / "assets" / "sprites"


def test_lokasi_dihitung_saat_dipanggil_bukan_saat_impor(mode_beku, monkeypatch):
    # Bila lokasi dihitung sekali saat impor, mengubah mode sesudahnya tidak berpengaruh.
    assert aset.folder_aset() == mode_beku / "assets"
    monkeypatch.delattr(sys, "frozen")
    assert aset.folder_aset() == REPO / "assets"


def test_frozen_tanpa_meipass_dianggap_mode_sumber(monkeypatch):
    # Bendera frozen tanpa folder paket: jangan error, kembali ke lokasi sumber.
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    assert aset.folder_aset() == REPO / "assets"


def test_load_frames_tanpa_argumen_membaca_folder_sprite_paket(app, mode_beku):
    folder = mode_beku / "assets" / "sprites"
    folder.mkdir(parents=True)
    gambar = QPixmap(8, 8)
    gambar.fill(QColor("#123456"))
    assert gambar.save(str(folder / "senang_1.png"))

    (frame,) = sprites.load_frames("senang")

    # Gambar sementara berupa lingkaran kuning (#f2b134); warna ini hanya ada di file paket.
    assert frame.toImage().pixelColor(frame.width() // 2, frame.height() // 2) == QColor("#123456")


def test_load_frames_di_folder_paket_kosong_memakai_gambar_sementara(app, mode_beku):
    frames = sprites.load_frames("senang")
    assert len(frames) == 2  # dua frame gambar sementara
