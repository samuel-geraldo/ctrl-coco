"""Kalimat gelembung bicara Coco.

Fungsi murni: tanpa Qt dan tanpa datetime.now(). Waktu selalu dikirim sebagai
parameter, jadi hasilnya bisa dites tanpa jam sungguhan.
"""

import sqlite3
from datetime import date, datetime, timedelta

from ctrlcoco.data import TIME_FORMAT

PANJANG_JUDUL_MAKS = 40  # judul yang lebih panjang dipotong supaya gelembung tidak penuh


def teks_sisa_waktu(deadline: datetime, now: datetime) -> str:
    """Sisa waktu menuju deadline, mis. "45 menit lagi", "3 jam lagi", "terlambat 2 hari".

    Angka dibulatkan ke bawah. Selisih di bawah 1 menit (maju atau mundur) dianggap
    tepat di deadline, karena `now` punya detik sedangkan deadline hanya sampai menit.
    """
    selisih = deadline - now
    if abs(selisih) < timedelta(minutes=1):
        return "sekarang"
    lama = _lama(abs(selisih))
    return f"{lama} lagi" if selisih > timedelta(0) else f"terlambat {lama}"


def _lama(selisih: timedelta) -> str:
    menit = int(selisih.total_seconds() // 60)
    if menit < 60:
        return f"{menit} menit"
    jam = menit // 60
    if jam < 24:
        return f"{jam} jam"
    return f"{jam // 24} hari"


def pesan_coco(
    kondisi: str, streak: int, task: sqlite3.Row | dict | None, now: datetime
) -> str:
    """Kalimat untuk gelembung bicara sesuai kondisi Coco.

    `task` adalah task terdekat (kolom title dan deadline) atau None. Bila ada dua
    variasi kalimat, pilihannya ditentukan tanggal `now`: sama sepanjang hari,
    berganti keesokan harinya.
    """
    pilih = _indeks_variasi(now.date())
    if kondisi == "waspada":
        if task is None:
            # Hampir mustahil: task selesai dari luar di antara dua query refresh.
            return "Ada deadline yang mendekat!"
        judul = _potong_judul(task["title"])
        deadline = datetime.strptime(task["deadline"], TIME_FORMAT)
        sisa = teks_sisa_waktu(deadline, now)
        if sisa == "sekarang":
            return f'Deadline "{judul}" sekarang!'
        if deadline < now:
            return f'"{judul}" sudah {sisa}. Yuk, selesaikan!'
        return (
            f'Awas! "{judul}" deadline {sisa}.',
            f'"{judul}" deadline {sisa}. Ayo dicicil!',
        )[pilih]
    if kondisi == "senang":
        return (
            f"Log hari ini lengkap. Streak {streak} hari!",
            f"Mantap, streak {streak} hari! Sampai besok ya.",
        )[pilih]
    if kondisi == "tidur":
        if streak > 0:
            return f"Zzz... Jangan putus streak {streak} hari. Catat log hari ini yuk!"
        return "Zzz... Belum ada log hari ini. Catat yuk, mulai streak baru!"
    raise ValueError(f"Kondisi Coco tidak dikenal: {kondisi!r}")


# Kalimat saat Coco diklik, satu per kondisi.
_REAKSI = {
    "waspada": "Iya, iya! Deadline-nya tetap jalan, lho.",
    "senang": "Hehe, geli!",
    "tidur": "Hoaam... eh, aku bangun! Sudah catat log?",
}


def pesan_reaksi(kondisi: str) -> str:
    """Kalimat gelembung saat Coco diklik."""
    if kondisi not in _REAKSI:
        raise ValueError(f"Kondisi Coco tidak dikenal: {kondisi!r}")
    return _REAKSI[kondisi]


def _indeks_variasi(hari: date) -> int:
    # Nomor urut hari (toordinal) bergantian genap-ganjil: 0 hari ini, 1 besok, dst.
    return hari.toordinal() % 2


def _potong_judul(judul: str) -> str:
    if len(judul) > PANJANG_JUDUL_MAKS:
        return judul[: PANJANG_JUDUL_MAKS - 1] + "…"
    return judul
