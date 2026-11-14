import sqlite3
from datetime import datetime

DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%Y-%m-%d %H:%M"


def _now_text(now: datetime | None) -> str:
    return (now or datetime.now()).strftime(TIME_FORMAT)


def _check_format(value: str, fmt: str, nama: str, contoh: str) -> None:
    """Tolak teks tanggal yang formatnya salah atau tanggalnya tidak ada di kalender."""
    try:
        # Teks diubah jadi tanggal lalu ditulis ulang. Hasilnya harus sama persis,
        # supaya "2026-3-5" (tanpa nol di depan) ikut ditolak.
        cocok = datetime.strptime(value, fmt).strftime(fmt) == value
    except ValueError:
        cocok = False
    if not cocok:
        raise ValueError(
            f"{nama} harus berformat {contoh} dan tanggalnya harus ada di kalender: {value!r}"
        )


# --- area ---

def add_area(conn: sqlite3.Connection, name: str) -> int:
    """Tambah area; nama harus unik. Mengembalikan id area baru."""
    try:
        cur = conn.execute("INSERT INTO area (name) VALUES (?)", (name,))
    except sqlite3.IntegrityError:
        raise ValueError(f"Area sudah ada: {name}") from None
    conn.commit()
    return cur.lastrowid


def list_areas(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT id, name FROM area ORDER BY name").fetchall()


# --- task ---

def add_task(
    conn: sqlite3.Connection,
    area_id: int,
    title: str,
    deadline: str | None = None,
    now: datetime | None = None,
) -> int:
    """Tambah task ke sebuah area. deadline opsional, format 'YYYY-MM-DD HH:MM'."""
    if deadline is not None:
        _check_format(deadline, TIME_FORMAT, "deadline", "YYYY-MM-DD HH:MM")
    try:
        cur = conn.execute(
            "INSERT INTO task (area_id, title, deadline, created_at) VALUES (?, ?, ?, ?)",
            (area_id, title, deadline, _now_text(now)),
        )
    except sqlite3.IntegrityError:
        raise ValueError(f"Area tidak ditemukan: {area_id}") from None
    conn.commit()
    return cur.lastrowid


def list_tasks(conn: sqlite3.Connection, status: str | None = None) -> list[sqlite3.Row]:
    """Semua task, atau hanya yang berstatus 'todo' / 'done'."""
    if status is None:
        return conn.execute("SELECT * FROM task ORDER BY id").fetchall()
    return conn.execute("SELECT * FROM task WHERE status = ? ORDER BY id", (status,)).fetchall()


def get_nearest_task(conn: sqlite3.Connection) -> sqlite3.Row | None:
    """Task 'todo' dengan deadline paling awal; None jika tidak ada."""
    return conn.execute(
        "SELECT * FROM task WHERE status = 'todo' AND deadline IS NOT NULL "
        "ORDER BY deadline LIMIT 1"
    ).fetchone()


def complete_task(conn: sqlite3.Connection, task_id: int, now: datetime | None = None) -> None:
    """Tandai task selesai dan isi completed_at. Task yang sudah done dibiarkan."""
    cur = conn.execute(
        "UPDATE task SET status = 'done', completed_at = ? WHERE id = ? AND status = 'todo'",
        (_now_text(now), task_id),
    )
    if cur.rowcount == 0:
        exists = conn.execute("SELECT 1 FROM task WHERE id = ?", (task_id,)).fetchone()
        if not exists:
            raise ValueError(f"Task tidak ditemukan: {task_id}")
    conn.commit()


# --- daily_log ---

def set_daily_log(
    conn: sqlite3.Connection,
    log_date: str,
    claude_code: bool,
    github: bool,
    note: str | None = None,
) -> None:
    """Catat log sebuah tanggal ('YYYY-MM-DD'); jika sudah ada, barisnya diperbarui."""
    _check_format(log_date, DATE_FORMAT, "log_date", "YYYY-MM-DD")
    conn.execute(
        """
        INSERT INTO daily_log (log_date, claude_code, github, note)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(log_date) DO UPDATE SET
            claude_code = excluded.claude_code,
            github = excluded.github,
            note = excluded.note
        """,
        (log_date, int(claude_code), int(github), note),
    )
    conn.commit()


def get_daily_log(conn: sqlite3.Connection, log_date: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM daily_log WHERE log_date = ?", (log_date,)).fetchone()
