r"""Isi database dengan data contoh generik (kuliah, portofolio) untuk mencoba widget.

Pakai:
    $env:PYTHONPATH = "src"
    python scripts/seed_demo.py              # menulis ke %APPDATA%\CtrlCoco\demo.db
    python -m ctrlcoco --db "$env:APPDATA\CtrlCoco\demo.db"   # lihat hasilnya

Secara bawaan skrip memakai database terpisah (demo.db), bukan database harian.
Jika --db menunjuk ke database harian, skrip meminta konfirmasi dulu.
"""
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

from ctrlcoco import data, db


def demo_db_path() -> Path:
    return db.default_db_path().with_name("demo.db")


def seed(conn, today: datetime | None = None) -> bool:
    """Isi data contoh. Mengembalikan False (tanpa menulis apa pun) jika database sudah berisi area."""
    if data.list_areas(conn):
        return False
    today = today or datetime.now()

    kuliah = data.add_area(conn, "Kuliah")
    portofolio = data.add_area(conn, "Portofolio")

    def at(days: int, hour: int) -> str:
        d = today + timedelta(days=days)
        return d.replace(hour=hour, minute=0).strftime(data.TIME_FORMAT)

    data.add_task(conn, kuliah, "Laporan praktikum basis data", at(2, 23), now=today)
    data.add_task(conn, kuliah, "Belajar untuk kuis algoritma", at(5, 8), now=today)
    data.add_task(conn, portofolio, "Tulis README proyek CtrlCoco", at(7, 20), now=today)
    data.add_task(conn, portofolio, "Rapikan halaman profil GitHub", None, now=today)

    # Streak 5 hari berturut-turut sampai hari ini; hari ke-6 bolong, hari ke-7 terisi.
    for back in range(5):
        day = (today - timedelta(days=back)).date().isoformat()
        data.set_daily_log(conn, day, True, True, "contoh")
    data.set_daily_log(conn, (today - timedelta(days=6)).date().isoformat(), True, False, "contoh")
    return True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--db", help="path database tujuan (bawaan: demo.db di folder AppData)")
    args = parser.parse_args(argv)

    target = Path(args.db) if args.db else demo_db_path()
    if target.resolve() == db.default_db_path().resolve():
        answer = input(f"{target} adalah database harian Anda. Tulis data contoh ke sana? [y/N] ")
        if answer.strip().lower() != "y":
            print("Dibatalkan.")
            return 1

    conn = db.connect(target)
    db.init_db(conn)
    if seed(conn):
        print(f"Data contoh ditulis ke {target}")
    else:
        print(f"{target} sudah berisi data; tidak ada yang diubah.")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
