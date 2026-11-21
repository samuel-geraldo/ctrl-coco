"""Metrik analitik dari database: dasar jendela Ringkasan (#42), tanpa impor Qt.

Semua fungsi menerima rentang tanggal `awal` dan `akhir` (keduanya inklusif, bertipe
`date`) dan memakai SQL berparameter (`?`): nilai masukan tidak pernah disambung ke teks SQL.
"""

import sqlite3
from dataclasses import dataclass
from datetime import date


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
