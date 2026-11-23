"""Metrik analitik dari database: dasar jendela Ringkasan (#42), tanpa impor Qt.

Semua fungsi menerima rentang tanggal `awal` dan `akhir` (keduanya inklusif, bertipe
`date`) dan memakai SQL berparameter (`?`): nilai masukan tidak pernah disambung ke teks SQL.
"""

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta

from ctrlcoco.streak import KONDISI_HARI_VALID


@dataclass(frozen=True)
class RateArea:
    area_id: int
    nama: str
    selesai: int
    total: int
    rate: float | None  # selesai / total; None bila total == 0


_SQL_COMPLETION_RATE = """
SELECT area.id AS area_id,
       area.name AS nama,
       COUNT(task.id) AS total,
       COALESCE(SUM(task.status = 'done'), 0) AS selesai
FROM area
LEFT JOIN task
       ON task.area_id = area.id
      AND date(task.created_at) BETWEEN ? AND ?
GROUP BY area.id
ORDER BY area.name COLLATE NOCASE
"""


def completion_rate_per_area(
    conn: sqlite3.Connection, awal: date, akhir: date
) -> list[RateArea]:
    """Completion rate tiap area: task `done` dibagi semua task di area itu.

    Task masuk rentang menurut `created_at` (tanggalnya, awal dan akhir inklusif): hanya
    kolom itu yang selalu terisi, dan penyebutnya memuat task `todo` juga.
    Semua area dikembalikan, urut nama tanpa beda huruf besar-kecil. Area tanpa task di
    rentang punya `total == 0` dan `rate is None` (bukan 0, supaya tidak terbaca "0% selesai").
    Rentang terbalik (awal > akhir) tidak cocok dengan task mana pun.
    """
    baris = conn.execute(_SQL_COMPLETION_RATE, (awal.isoformat(), akhir.isoformat()))
    return [
        RateArea(
            area_id=b["area_id"],
            nama=b["nama"],
            selesai=b["selesai"],
            total=b["total"],
            rate=b["selesai"] / b["total"] if b["total"] else None,
        )
        for b in baris
    ]


_SQL_ON_TIME = """
SELECT COUNT(*) AS total,
       COALESCE(SUM(completed_at <= deadline), 0) AS tepat_waktu
FROM task
WHERE status = 'done'
  AND deadline IS NOT NULL
  AND date(completed_at) BETWEEN ? AND ?
"""


def on_time_rate(conn: sqlite3.Connection, awal: date, akhir: date) -> float | None:
    """Bagian task selesai yang selesai tepat waktu, gabungan semua area.

    Pembilang: task `done` dengan `completed_at <= deadline` (selesai tepat pada deadline
    dihitung tepat waktu). Penyebut: task `done` yang punya deadline; task tanpa deadline
    tidak dihitung di keduanya. Kedua kolom berformat `YYYY-MM-DD HH:MM` (dijaga CHECK),
    jadi urutan teksnya sama dengan urutan waktu.

    Task masuk rentang menurut tanggal `completed_at` (awal dan akhir inklusif): hanya task
    `done` yang dihitung, dan kolom itu yang menunjukkan kapan task selesai.
    Hasil 0 sampai 1, atau `None` bila penyebutnya 0 (bukan 0, supaya "tidak ada data" tidak
    terbaca "semua terlambat").
    """
    baris = conn.execute(_SQL_ON_TIME, (awal.isoformat(), akhir.isoformat())).fetchone()
    return baris["tepat_waktu"] / baris["total"] if baris["total"] else None


# Hanya konstanta modul yang digabung ke teks SQL; nilai masukan lewat parameter "?".
_SQL_HARI_VALID = (
    "SELECT log_date FROM daily_log WHERE "
    + KONDISI_HARI_VALID
    + " AND log_date BETWEEN ? AND ? ORDER BY log_date"
)


def longest_streak(conn: sqlite3.Connection, awal: date, akhir: date) -> int:
    """Deretan hari valid berturut-turut terpanjang di dalam rentang (inklusif).

    Beda dari `get_streak`, yang hanya menghitung streak yang sedang berjalan. Definisi
    hari valid sama persis (`KONDISI_HARI_VALID` di streak.py). Hari tak tercatat atau
    tidak valid memutus deretan; deretan yang melewati batas rentang hanya dihitung bagian
    di dalamnya. Hasil 0 bila tidak ada hari valid di rentang (termasuk rentang terbalik).
    """
    baris = conn.execute(_SQL_HARI_VALID, (awal.isoformat(), akhir.isoformat()))
    terpanjang = berjalan = 0
    kemarin = None
    for b in baris:
        hari = date.fromisoformat(b["log_date"])
        berjalan = berjalan + 1 if kemarin is not None and hari - kemarin == timedelta(1) else 1
        terpanjang = max(terpanjang, berjalan)
        kemarin = hari
    return terpanjang
