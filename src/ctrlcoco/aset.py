"""Lokasi folder aset (sprite, logo): satu sumber untuk mode sumber dan mode .exe."""
import sys
from pathlib import Path


def folder_aset() -> Path:
    """Folder `assets`: di dalam paket bila berjalan sebagai .exe, di repo bila dari kode.

    PyInstaller menandai program yang dibekukan dengan `sys.frozen` dan menaruh isi paket
    di folder sementara `sys._MEIPASS`. Dihitung setiap dipanggil, bukan saat impor.
    """
    paket = getattr(sys, "_MEIPASS", None)
    if getattr(sys, "frozen", False) and paket:
        return Path(paket) / "assets"
    return Path(__file__).resolve().parents[2] / "assets"


def folder_sprite() -> Path:
    return folder_aset() / "sprites"
