"""Metrik analitik dari database: dasar jendela Ringkasan (#42), tanpa impor Qt.

Semua fungsi menerima rentang tanggal `awal` dan `akhir` (keduanya inklusif, bertipe
`date`) dan memakai SQL berparameter (`?`): nilai masukan tidak pernah disambung ke teks SQL.
"""

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from statistics import median

from ctrlcoco.data import TIME_FORMAT
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
       COALESCE(SUM(tepat_waktu), 0) AS tepat_waktu
FROM v_task_selesai
WHERE deadline IS NOT NULL
  AND date(selesai) BETWEEN ? AND ?
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


@dataclass(frozen=True)
class MedianArea:
    area_id: int
    nama: str
    jam: float | None  # median jam dari dibuat sampai selesai; None bila belum ada


_SQL_WAKTU_SELESAI = """
SELECT area.id AS area_id,
       area.name AS nama,
       v.dibuat AS dibuat,
       v.selesai AS selesai
FROM area
LEFT JOIN v_task_selesai AS v
       ON v.area_id = area.id
      AND date(v.selesai) BETWEEN ? AND ?
ORDER BY area.name COLLATE NOCASE
"""


def _selisih_jam(dibuat: str, selesai: str) -> float:
    selisih = datetime.strptime(selesai, TIME_FORMAT) - datetime.strptime(dibuat, TIME_FORMAT)
    return selisih.total_seconds() / 3600


def median_penyelesaian_per_area(
    conn: sqlite3.Connection, awal: date, akhir: date
) -> list[MedianArea]:
    """Median waktu dari dibuat sampai selesai tiap area, dalam jam.

    Hanya task `done`. Task masuk rentang menurut tanggal `completed_at` (awal dan akhir
    inklusif), sama dengan `on_time_rate`. Median dihitung di Python karena SQLite tidak
    punya fungsinya; untuk jumlah genap, rata-rata dua nilai tengah.
    Semua area dikembalikan, urut nama tanpa beda huruf besar-kecil; area tanpa task
    selesai di rentang punya `jam is None`.
    """
    area: dict[int, tuple[str, list[float]]] = {}
    for b in conn.execute(_SQL_WAKTU_SELESAI, (awal.isoformat(), akhir.isoformat())):
        _, durasi = area.setdefault(b["area_id"], (b["nama"], []))
        if b["selesai"] is not None:  # NULL: baris LEFT JOIN untuk area tanpa task selesai
            durasi.append(_selisih_jam(b["dibuat"], b["selesai"]))
    return [
        MedianArea(area_id, nama, median(durasi) if durasi else None)
        for area_id, (nama, durasi) in area.items()
    ]


@dataclass(frozen=True)
class ProduktivitasHari:
    nama: str  # "Senin" sampai "Minggu"
    task_selesai: int
    hari_valid: int  # banyaknya tanggal valid yang jatuh pada hari itu


NAMA_HARI = ("Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu")

_SQL_SELESAI_PER_HARI = """
SELECT CAST(strftime('%w', selesai) AS INTEGER) AS w, COUNT(*) AS jumlah
FROM v_task_selesai
WHERE date(selesai) BETWEEN ? AND ?
GROUP BY w
"""


def produktivitas_per_hari(
    conn: sqlite3.Connection, awal: date, akhir: date
) -> list[ProduktivitasHari]:
    """Task selesai dan hari valid untuk tiap hari Senin sampai Minggu.

    Task dihitung menurut tanggal `completed_at`; hari valid memakai `hari_valid`.
    Rentang inklusif. Selalu 7 baris berurutan Senin sampai Minggu, termasuk yang 0.
    """
    selesai = [0] * 7
    for b in conn.execute(_SQL_SELESAI_PER_HARI, (awal.isoformat(), akhir.isoformat())):
        # "%w" SQLite: 0 = Minggu. Digeser supaya 0 = Senin, sama dengan date.weekday().
        selesai[(b["w"] + 6) % 7] = b["jumlah"]
    valid = [0] * 7
    for tanggal in hari_valid(conn, awal, akhir):
        valid[tanggal.weekday()] += 1
    return [ProduktivitasHari(*baris) for baris in zip(NAMA_HARI, selesai, valid, strict=True)]


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


# Rentang tetap jendela Ringkasan (#64): 12 minggu terakhir, berakhir hari ini.
RENTANG_MINGGU = 12


def rentang_ringkasan(today: date) -> tuple[date, date]:
    """Rentang jendela Ringkasan: `RENTANG_MINGGU` minggu (84 hari) berakhir di `today`.

    Awal dan akhir sama-sama dihitung (inklusif), seperti parameter fungsi analitik lain.
    `today` dikirim dari luar, tidak diambil di sini, supaya bisa dites dengan tanggal tetap.
    """
    return today - timedelta(days=RENTANG_MINGGU * 7 - 1), today


_SQL_ADA_DATA = "SELECT EXISTS (SELECT 1 FROM task) OR EXISTS (SELECT 1 FROM daily_log)"


def ada_data(conn: sqlite3.Connection) -> bool:
    """Apakah database punya data untuk diringkas: minimal satu task atau satu log.

    Seluruh database, bukan hanya rentang Ringkasan. Area tanpa task belum dihitung data.
    Log apa pun dihitung, termasuk yang bukan hari valid. Kolom tanggal tidak diperiksa,
    jadi task tanpa deadline atau tanpa `completed_at` tetap terhitung.
    """
    return bool(conn.execute(_SQL_ADA_DATA).fetchone()[0])


def hari_valid(conn: sqlite3.Connection, awal: date, akhir: date) -> list[date]:
    """Hari valid di dalam rentang (inklusif), urut dari yang paling awal.

    Dasar heatmap kalender (#65). Definisi hari valid sama persis dengan `longest_streak`
    (`KONDISI_HARI_VALID` di streak.py, lewat kueri yang sama). Rentang terbalik atau
    tanpa hari valid menghasilkan daftar kosong.
    """
    baris = conn.execute(_SQL_HARI_VALID, (awal.isoformat(), akhir.isoformat()))
    return [date.fromisoformat(b["log_date"]) for b in baris]
