import sqlite3
from datetime import datetime, timedelta

from ctrlcoco.data import TIME_FORMAT, get_daily_log, get_nearest_task

BATAS_WASPADA = timedelta(hours=24)


def get_mood(conn: sqlite3.Connection, now: datetime) -> str:
    """Kondisi Coco pada waktu `now`: "waspada", "senang", atau "tidur".

    Aturan diperiksa berurutan dan yang pertama cocok menang (docs/keputusan.md):
    1. waspada: ada task todo yang deadline-nya sudah lewat atau kurang dari 24 jam lagi.
    2. senang: log hari ini valid (claude_code = 1 dan github = 1).
    3. tidur: selain itu.
    """
    # Cukup periksa task todo dengan deadline paling awal: jika yang paling awal
    # saja masih jauh, task lain pasti lebih jauh lagi.
    task = get_nearest_task(conn)
    if task is not None:
        deadline = datetime.strptime(task["deadline"], TIME_FORMAT)
        if deadline - now < BATAS_WASPADA:
            return "waspada"

    log = get_daily_log(conn, now.date().isoformat())
    if log is not None and log["claude_code"] == 1 and log["github"] == 1:
        return "senang"

    return "tidur"
