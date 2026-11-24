"""Ekspor task dan daily_log ke CSV (UTF-8 dengan BOM) agar bisa dibuka di Excel."""
import csv
import sqlite3
from pathlib import Path

NAMA_FILE_TASK = "task.csv"
NAMA_FILE_LOG = "daily_log.csv"

HEADER_TASK = ["area", "judul", "tenggat", "status", "dibuat", "selesai"]
HEADER_LOG = ["tanggal", "claude_code", "github", "catatan"]

_STATUS = {"todo": "belum", "done": "selesai"}


def _teks(nilai):
    """NULL di database menjadi sel kosong."""
    return "" if nilai is None else nilai


def _ya_tidak(nilai):
    return "ya" if nilai else "tidak"


def _tulis(path: Path, header, baris):
    # utf-8-sig menulis BOM; newline="" wajib untuk modul csv.
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        penulis = csv.writer(f)
        penulis.writerow(header)
        penulis.writerows(baris)


def file_yang_sudah_ada(folder: Path) -> list[Path]:
    """File ekspor di folder yang akan tertimpa, urut task lalu daily_log."""
    kandidat = [Path(folder) / NAMA_FILE_TASK, Path(folder) / NAMA_FILE_LOG]
    return [p for p in kandidat if p.exists()]


def ekspor_csv(conn: sqlite3.Connection, folder: Path) -> tuple[Path, Path]:
    """Tulis task.csv dan daily_log.csv ke folder; file lama ditimpa.

    Melempar OSError bila folder tidak bisa ditulis.
    """
    folder = Path(folder)
    file_task = folder / NAMA_FILE_TASK
    file_log = folder / NAMA_FILE_LOG

    baris_task = conn.execute(
        "SELECT area.name, task.title, task.deadline, task.status,"
        " task.created_at, task.completed_at"
        " FROM task JOIN area ON area.id = task.area_id ORDER BY task.id"
    ).fetchall()
    baris_log = conn.execute(
        "SELECT log_date, claude_code, github, note FROM daily_log ORDER BY log_date"
    ).fetchall()

    _tulis(
        file_task,
        HEADER_TASK,
        [
            [
                r[0],
                r[1],
                _teks(r[2]),
                _STATUS.get(r[3], r[3]),
                _teks(r[4]),
                _teks(r[5]),
            ]
            for r in baris_task
        ],
    )
    _tulis(
        file_log,
        HEADER_LOG,
        [[r[0], _ya_tidak(r[1]), _ya_tidak(r[2]), _teks(r[3])] for r in baris_log],
    )
    return file_task, file_log
