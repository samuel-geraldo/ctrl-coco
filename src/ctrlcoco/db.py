import sqlite3

DEFAULT_DB_PATH = "ctrlcoco.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS area (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS task (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    area_id      INTEGER NOT NULL REFERENCES area(id),
    title        TEXT NOT NULL,
    deadline     TEXT,
    status       TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'done')),
    created_at   TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS daily_log (
    log_date    TEXT PRIMARY KEY,
    claude_code INTEGER NOT NULL CHECK (claude_code IN (0, 1)),
    github      INTEGER NOT NULL CHECK (github IN (0, 1)),
    note        TEXT
);
"""


def connect(path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Buka koneksi; file dibuat jika belum ada. Gunakan ":memory:" untuk tes."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Buat tabel jika belum ada (aman dipanggil berulang)."""
    conn.executescript(SCHEMA)
    conn.commit()
