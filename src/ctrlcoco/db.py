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
# 2 = area.name dan task.title tidak boleh kosong (CEK_NAMA), dan area.name unik
#     tanpa membedakan huruf besar-kecil (COLLATE NOCASE).
SCHEMA_VERSION = 2

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

# trim() bawaan SQLite hanya membuang spasi biasa, sedangkan str.strip() di Python juga
# membuang tab dan baris baru. Karena itu karakter yang dibuang disebut satu per satu:
# spasi (32), tab (9), baris baru (10), dan CR (13). Spasi Unicode yang lebih jarang
# (misalnya spasi tak terputus) hanya dibuang oleh data.py.
RAPIKAN = "trim({kolom}, char(32, 9, 10, 13))"
CEK_NAMA = RAPIKAN + " <> ''"


def _buat_area(nama: str = "area") -> str:
    return f"""
CREATE TABLE IF NOT EXISTS {nama} (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK ({CEK_NAMA.format(kolom="name")})
)"""


def _buat_task(nama: str = "task") -> str:
    return f"""
CREATE TABLE IF NOT EXISTS {nama} (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    area_id      INTEGER NOT NULL REFERENCES area(id),
    title        TEXT NOT NULL CHECK ({CEK_NAMA.format(kolom="title")}),
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


# Tabel yang dibangun ulang saat migrasi, berurutan (area dulu, karena task menunjuk ke
# area): (nama, pembuat DDL, kolom tujuan, isi yang disalin). Nama area dan judul task
# disalin setelah spasi di awal dan akhirnya dibuang.
_TABEL_MIGRASI = (
    ("area", _buat_area, "id, name", "id, " + RAPIKAN.format(kolom="name")),
    ("task", _buat_task, "id, area_id, title, deadline, status, created_at, completed_at",
     "id, area_id, " + RAPIKAN.format(kolom="title")
     + ", deadline, status, created_at, completed_at"),
    ("daily_log", _buat_daily_log, "log_date, claude_code, github, note",
     "log_date, claude_code, github, note"),
)

# Kolom tanggal yang diperiksa formatnya: (tabel, kolom, aturan, kolom identitas baris).
_CEK_TANGGAL_MIGRASI = (
    ("task", "deadline", CEK_WAKTU, "id"),
    ("daily_log", "log_date", CEK_TANGGAL, "log_date"),
)

# Kolom nama yang tidak boleh kosong: (tabel, kolom).
_CEK_NAMA_MIGRASI = (
    ("area", "name"),
    ("task", "title"),
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

    Aman dipanggil berulang. Database lama (user_version 0 atau 1) dinaikkan langsung
    ke versi terbaru dalam satu langkah. Jika ada baris yang melanggar aturan baru
    (tanggal berformat salah, nama kosong, nama area kembar), ValueError menyebut
    baris-baris itu dan database tidak diubah sama sekali.
    """
    versi = conn.execute("PRAGMA user_version").fetchone()[0]
    if versi < SCHEMA_VERSION:
        _migrasi(conn)
    conn.execute(_buat_area())
    conn.execute(_buat_task())
    conn.execute(_buat_daily_log())
    conn.commit()


def _cari_pelanggaran(conn: sqlite3.Connection, ada: set[str]) -> list[str]:
    """Semua baris yang akan ditolak skema terbaru, sebagai teks untuk pesan error."""
    masalah = []
    for nama, kolom, cek, kunci in _CEK_TANGGAL_MIGRASI:
        if nama not in ada:
            continue
        baris = conn.execute(
            f"SELECT {kunci}, {kolom} FROM {nama}"
            f" WHERE {kolom} IS NOT NULL AND NOT ({cek.format(kolom=kolom)})"
        ).fetchall()
        masalah += [f"{nama}.{kunci}={b[0]!r} {kolom}={b[1]!r} (format tanggal salah)" for b in baris]

    for nama, kolom in _CEK_NAMA_MIGRASI:
        if nama not in ada:
            continue
        baris = conn.execute(
            f"SELECT id, {kolom} FROM {nama} WHERE NOT ({CEK_NAMA.format(kolom=kolom)})"
        ).fetchall()
        masalah += [f"{nama}.id={b[0]!r} {kolom}={b[1]!r} (kosong)" for b in baris]

    if "area" in ada:
        # Dibandingkan setelah spasi dibuang dan tanpa beda huruf, sama seperti skema baru.
        a, b = RAPIKAN.format(kolom="a.name"), RAPIKAN.format(kolom="b.name")
        baris = conn.execute(
            f"SELECT a.id, a.name, b.id, b.name FROM area a JOIN area b"
            f" ON {a} = {b} COLLATE NOCASE AND a.id < b.id AND {a} <> ''"
            f" ORDER BY a.id, b.id"
        ).fetchall()
        masalah += [
            f"area.id={r[0]!r} name={r[1]!r} bentrok dengan area.id={r[2]!r} name={r[3]!r}"
            for r in baris
        ]
    return masalah


def _migrasi(conn: sqlite3.Connection) -> None:
    """Naikkan database v0 atau v1 langsung ke SCHEMA_VERSION dalam satu transaksi."""
    ada = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    tabel = [t for t in _TABEL_MIGRASI if t[0] in ada]

    # 1. Periksa dulu semua baris; jika ada yang melanggar, berhenti sebelum mengubah apa pun.
    masalah = _cari_pelanggaran(conn, ada)
    if masalah:
        raise ValueError(
            "Database tidak bisa diperbarui; baris berikut melanggar aturan baru. "
            "Perbaiki dulu (misalnya dengan DB Browser for SQLite): " + "; ".join(masalah)
        )

    # 2. Bangun ulang tiap tabel dalam satu transaksi: salin ke tabel baru, hapus yang
    #    lama, ganti namanya. Gagal di tengah = semuanya dibatalkan.
    #    Kunci tamu dimatikan selama itu, karena tabel area sempat dihapus sementara task
    #    masih menunjuk ke sana. PRAGMA foreign_keys hanya berlaku di luar transaksi.
    conn.commit()
    fk_semula = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN")
        try:
            for nama, buat, kolom_tujuan, isi in tabel:
                # AUTOINCREMENT mencatat id terbesar yang pernah dipakai di sqlite_sequence.
                # Angka itu dibawa ke tabel baru, supaya id yang sudah dihapus tidak dipakai ulang.
                seq = None
                if "sqlite_sequence" in ada:
                    seq = conn.execute(
                        "SELECT seq FROM sqlite_sequence WHERE name = ?", (nama,)
                    ).fetchone()
                conn.execute(buat(f"{nama}_baru"))
                conn.execute(f"INSERT INTO {nama}_baru ({kolom_tujuan}) SELECT {isi} FROM {nama}")
                conn.execute(f"DROP TABLE {nama}")
                conn.execute(f"ALTER TABLE {nama}_baru RENAME TO {nama}")
                if seq is not None:
                    cur = conn.execute(
                        "UPDATE sqlite_sequence SET seq = max(seq, ?) WHERE name = ?",
                        (seq[0], nama),
                    )
                    if cur.rowcount == 0:  # tabel kosong: belum ada catatan untuk tabel baru
                        conn.execute(
                            "INSERT INTO sqlite_sequence (name, seq) VALUES (?, ?)", (nama, seq[0])
                        )

            # 3. Pastikan setiap task masih menunjuk ke area yang ada; jika tidak, batalkan.
            yatim = conn.execute("PRAGMA foreign_key_check").fetchall()
            if yatim:
                raise ValueError(
                    "Database tidak bisa diperbarui; baris berikut menunjuk ke baris yang tidak ada. "
                    "Perbaiki dulu (misalnya dengan DB Browser for SQLite): "
                    + "; ".join(f"{r[0]}.id={r[1]} (tidak ada di tabel {r[2]})" for r in yatim)
                )
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        except BaseException:
            conn.rollback()
            raise
        conn.commit()
    finally:
        conn.execute(f"PRAGMA foreign_keys = {fk_semula}")
