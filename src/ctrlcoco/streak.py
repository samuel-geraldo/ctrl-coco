import sqlite3
from datetime import date, timedelta


def get_streak(conn: sqlite3.Connection, today: date | None = None) -> int:
    """Jumlah hari valid berturut-turut (aturan di docs/erd.md).

    Hari valid = claude_code = 1 DAN github = 1. Dihitung mundur dari hari ini,
    atau dari kemarin jika hari ini belum valid.
    """
    today = today or date.today()
    rows = conn.execute(
        "SELECT log_date FROM daily_log WHERE claude_code = 1 AND github = 1"
    ).fetchall()
    valid_days = {date.fromisoformat(r["log_date"]) for r in rows}

    day = today if today in valid_days else today - timedelta(days=1)
    streak = 0
    while day in valid_days:
        streak += 1
        day -= timedelta(days=1)
    return streak
