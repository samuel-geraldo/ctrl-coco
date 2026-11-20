"""Kapan Coco merayakan. Fungsi murni tanpa Qt."""

from typing import NamedTuple

TONGGAK_STREAK = (3, 7, 14, 30)


class Perayaan(NamedTuple):
    """Jenis perayaan: "tonggak" (dengan angkanya), "log", atau "task" (dengan judulnya)."""

    jenis: str
    tonggak: int | None = None
    judul: str | None = None


def perlu_rayakan(streak_sebelum: int, streak_sesudah: int) -> int | None:
    """Tonggak streak yang BARU tercapai (sebelum < tonggak <= sesudah), atau None.

    Bila beberapa tonggak terlewati sekaligus, yang terbesar dipilih supaya Coco
    merayakan sekali saja.
    """
    tercapai = [t for t in TONGGAK_STREAK if streak_sebelum < t <= streak_sesudah]
    return max(tercapai) if tercapai else None


def jenis_perayaan_log(
    valid_sebelum: bool, valid_sesudah: bool, streak_sebelum: int, streak_sesudah: int
) -> Perayaan | None:
    """Perayaan setelah log hari ini disimpan, atau None.

    Hanya bila log BARU menjadi valid: tonggak streak bila tercapai, selain itu perayaan
    biasa. Menyimpan ulang log yang sudah valid tidak memicu apa pun.
    """
    if valid_sebelum or not valid_sesudah:
        return None
    tonggak = perlu_rayakan(streak_sebelum, streak_sesudah)
    if tonggak is not None:
        return Perayaan("tonggak", tonggak)
    return Perayaan("log")
