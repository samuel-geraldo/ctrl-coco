"""Deadline untuk tombol cepat di form Tambah task. Fungsi murni tanpa Qt."""

from datetime import datetime, time, timedelta

# Pilihan tombol cepat dan jarak harinya dari hari ini.
_JARAK_HARI = {"hari_ini": 0, "besok": 1, "minggu_depan": 7}
PILIHAN_CEPAT = tuple(_JARAK_HARI)

JAM_DEADLINE = time(23, 59)


def deadline_cepat(pilihan: str, now: datetime) -> datetime:
    """Deadline pukul 23:59 untuk "hari_ini", "besok", atau "minggu_depan" (7 hari).

    Hari ditambahkan ke tanggal lewat timedelta, jadi pergantian bulan, tahun, dan
    tahun kabisat ikut benar.
    """
    if pilihan not in _JARAK_HARI:
        raise ValueError(f"Pilihan deadline tidak dikenal: {pilihan!r}")
    tanggal = now.date() + timedelta(days=_JARAK_HARI[pilihan])
    return datetime.combine(tanggal, JAM_DEADLINE)
