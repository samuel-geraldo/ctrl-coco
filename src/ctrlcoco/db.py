import os
import sqlite3
from pathlib import Path


def default_db_path() -> Path:
    """Lokasi database harian: %APPDATA%\\CtrlCoco\\ctrlcoco.db (folder dibuat jika belum ada)."""
    base = os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming"
    folder = Path(base) / "CtrlCoco"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "ctrlcoco.db"


# Versi skema disimpan di PRAGMA user_version (angka milik database, bawaan 0).
# 1 = kolom tanggal dijaga CHECK (lihat CEK_TANGGAL dan CEK_WAKTU).
SCHEMA_VERSION = 1

# CHECK menolak teks tanggal yang formatnya salah, dari jalur mana pun (kode, skrip,
# atau edit manual). Dua hal penting di sini:
# - strftime() mengembalikan NULL untuk teks yang tidak bisa dibaca, dan CHECK
#   meloloskan NULL. COALESCE(..., 0) mengubah NULL itu jadi 0 (ditolak).
# - SQLite lebih longgar daripada Python: ia menerima tahun 0000 dan jam 24, padahal
#   datetime.strptime menolaknya. Dua syarat tambahan menyamakan keduanya.
CEK_TANGGAL = (
    "COALESCE(strftime('%Y-%m-%d', {kolom}) = {kolom}, 0)"
    " AND {kolom} >= '0001-01-01'"
)
CEK_WAKTU = (
    "COALESCE(strftime('%Y-%m-%d %H:%M', {kolom}) = {kolom}, 0)"
    " AND {kolom} >= '0001-01-01 00:00'"
    " AND substr({kolom}, 12, 2) < '24'"
)


def _buat_area(nama: str = "area") -> str:
    return f"""
CREATE TABLE IF NOT EXISTS {nama} (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
)"""


def _buat_task(nama: str = "task") -> str:
    return f"""
CREATE TABLE IF NOT EXISTS {nama} (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    area_id      INTEGER NOT NULL REFERENCES area(id),
    title        TEXT NOT NULL,
    deadline     TEXT CHECK (deadline IS NULL OR ({CEK_WAKTU.format(kolom="deadline")})),
    status       TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'done')),
    created_at   TEXT NOT NULL,
    completed_at TEXT
)"""


def _buat_daily_log(nama: str = "daily_log") -> str:
    return f"""
CREATE TABLE IF NOT EXISTS {nama} (
    log_date    TEXT PRIMARY KEY CHECK ({CEK_TANGGAL.format(kolom="log_date")}),
    claude_code INTEGER NOT NULL CHECK (claude_code IN (0, 1)),
    github      INTEGER NOT NULL CHECK (github IN (0, 1)),
    note        TEXT
)"""


# Tabel yang perlu dibangun ulang saat migrasi: (nama, pembuat DDL, kolom yang disalin,
# kolom yang diperiksa formatnya, kolom yang menampilkan identitas baris di pesan error).
_TABEL_MIGRASI = (
    ("task", _buat_task, "id, area_id, title, deadline, status, created_at, completed_at",
     "deadline", CEK_WAKTU, "id"),
    ("daily_log", _buat_daily_log, "log_date, claude_code, github, note",
     "log_date", CEK_TANGGAL, "log_date"),
)


def connect(path: str | os.PathLike | None = None) -> sqlite3.Connection:
    """Buka koneksi; file dibuat jika belum ada. Tanpa argumen: database di folder AppData.
    Gunakan ":memory:" untuk tes."""
    conn = sqlite3.connect(default_db_path() if path is None else path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Buat tabel jika belum ada, dan naikkan database lama ke skema terbaru.

    Aman dipanggil berulang. Database lama (user_version 0) yang sudah punya tabel
    task atau daily_log dibangun ulang dengan CHECK; jika ada baris berformat salah,
    ValueError menyebut baris itu dan database tidak diubah sama sekali.
    """
    versi = conn.execute("PRAGMA user_version").fetchone()[0]
    if versi < SCHEMA_VERSION:
        _migrasi_ke_v1(conn)
    conn.execute(_buat_area())
    conn.execute(_buat_task())
    conn.execute(_buat_daily_log())
    conn.commit()


def _migrasi_ke_v1(conn: sqlite3.Connection) -> None:
    ada = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    tabel = [t for t in _TABEL_MIGRASI if t[0] in ada]

    # 1. Periksa dulu semua baris; jika ada yang rusak, berhenti sebelum mengubah apa pun.
    rusak = []
    for nama, _, _, kolom, cek, kunci in tabel:
        syarat = cek.format(kolom=kolom)
        baris = conn.execute(
            f"SELECT {kunci}, {kolom} FROM {nama}"
            f" WHERE {kolom} IS NOT NULL AND NOT ({syarat})"
        ).fetchall()
        rusak += [f"{nama}.{kunci}={b[0]!r} {kolom}={b[1]!r}" for b in baris]
    if rusak:
        raise ValueError(
            "Database tidak bisa diperbarui; baris berikut berformat tanggal salah. "
            "Perbaiki dulu (misalnya dengan DB Browser for SQLite): " + "; ".join(rusak)
        )

    # 2. Bangun ulang tiap tabel dalam satu transaksi: salin ke tabel baru ber-CHECK,
    #    hapus yang lama, ganti namanya. Gagal di tengah = semuanya dibatalkan.
    conn.commit()
    conn.execute("BEGIN")
    try:
        for nama, buat, kolom_salin, *_ in tabel:
            conn.execute(buat(f"{nama}_baru"))
            conn.execute(f"INSERT INTO {nama}_baru ({kolom_salin}) SELECT {kolom_salin} FROM {nama}")
            conn.execute(f"DROP TABLE {nama}")
            conn.execute(f"ALTER TABLE {nama}_baru RENAME TO {nama}")
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    except BaseException:
        conn.rollback()
        raise
    conn.commit()
