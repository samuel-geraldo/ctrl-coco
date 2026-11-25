r"""Buat gambar README (PNG) tanpa membuka widget sungguhan.

Pakai (dari akar repo):
    $env:PYTHONPATH = "src"
    python scripts/seed_demo.py              # sekali saja, mengisi demo.db
    python scripts/tangkapan_layar.py        # menulis PNG ke docs/gambar/

Yang dihasilkan:
    widget_senang.png, widget_waspada.png, widget_tidur.png   Coco di tiga kondisi
    ringkasan.png                                             jendela Ringkasan

Tiap kondisi Coco dirender dari database sementara kecil dengan waktu tetap, jadi
kondisinya ditentukan get_mood yang sungguhan, bukan diatur langsung. Jendela Ringkasan
dirender dari demo.db. Database harian tidak pernah dibaca: path itu ditolak.
"""
import argparse
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Qt menggambar di memori saja, tanpa jendela di layar. Harus diatur sebelum Qt dimuat.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from ctrlcoco import data, db  # noqa: E402
from ctrlcoco.mood import MOODS, get_mood  # noqa: E402
from ctrlcoco.ringkasan import JendelaRingkasan  # noqa: E402
from ctrlcoco.widget import CocoWidget  # noqa: E402

# Waktu tetap untuk ketiga kondisi, supaya gambar yang sama bisa dibuat ulang kapan saja.
WAKTU_TETAP = datetime(2026, 11, 14, 9, 0)
FOLDER_GAMBAR = Path(__file__).resolve().parents[1] / "docs" / "gambar"


def demo_db_path() -> Path:
    return db.default_db_path().with_name("demo.db")


def buat_db_kondisi(kondisi: str, now: datetime = WAKTU_TETAP):
    """Database di memori yang membuat get_mood(conn, now) mengembalikan `kondisi`."""
    conn = db.connect(":memory:")
    db.init_db(conn)
    if kondisi == "waspada":
        # Deadline 2 jam lagi: kurang dari 24 jam.
        area_id = data.add_area(conn, "Kuliah")
        deadline = (now + timedelta(hours=2)).strftime(data.TIME_FORMAT)
        data.add_task(conn, area_id, "Laporan praktikum", deadline, now=now)
    elif kondisi == "senang":
        # Log hari ini dengan kedua kotak dicentang, tanpa deadline dekat.
        data.set_daily_log(conn, now.date().isoformat(), True, True)
    elif kondisi != "tidur":
        # "tidur": tanpa log hari ini dan tanpa deadline dekat, jadi database dibiarkan kosong.
        conn.close()
        raise ValueError(f"Kondisi tidak dikenal: {kondisi}")
    return conn


def simpan(widget, tujuan: Path) -> None:
    # grab() menggambar widget ke gambar di memori; latar tembus pandang tetap tembus pandang.
    if not widget.grab().save(str(tujuan)):
        raise OSError(f"Gagal menulis {tujuan}")


def render_widget(kondisi: str, folder: Path, now: datetime = WAKTU_TETAP) -> Path:
    conn = buat_db_kondisi(kondisi, now)
    try:
        # Pastikan get_mood benar-benar menghasilkan kondisi yang dimaksud.
        hasil = get_mood(conn, now)
        if hasil != kondisi:
            raise RuntimeError(f"get_mood mengembalikan {hasil!r}, bukan {kondisi!r}")
        widget = CocoWidget(conn)
        widget.refresh(now)
        widget.adjustSize()
        tujuan = folder / f"widget_{kondisi}.png"
        simpan(widget, tujuan)
        widget.deleteLater()
    finally:
        conn.close()
    return tujuan


def render_ringkasan(db_path: Path, folder: Path, today: date) -> Path:
    conn = db.connect(db_path)
    try:
        jendela = JendelaRingkasan(conn, today=today)
        jendela.adjustSize()
        tujuan = folder / "ringkasan.png"
        simpan(jendela, tujuan)
        jendela.deleteLater()
    finally:
        conn.close()
    return tujuan


def render_semua(db_path: Path, folder: Path, today: date) -> list[Path]:
    # QApplication dibuat lebih dulu; bila sudah ada (misalnya saat tes), pakai yang itu.
    app = QApplication.instance() or QApplication(sys.argv[:1])
    folder.mkdir(parents=True, exist_ok=True)
    hasil = [render_widget(kondisi, folder) for kondisi in MOODS]
    hasil.append(render_ringkasan(db_path, folder, today))
    app.processEvents()
    return hasil


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--db", help="path demo.db (bawaan: demo.db di folder AppData)")
    parser.add_argument("--out", help="folder tujuan PNG (bawaan: docs/gambar)")
    args = parser.parse_args(argv)

    sumber = Path(args.db) if args.db else demo_db_path()
    # Ditolak sebelum database dibuka sama sekali.
    if sumber.resolve() == db.default_db_path().resolve():
        print(f"{sumber} adalah database harian Anda. Pakai demo.db (python scripts/seed_demo.py).")
        return 1
    if not sumber.is_file():
        # connect() akan membuat berkas kosong bila path belum ada, jadi diperiksa dulu.
        print(f"{sumber} tidak ada. Jalankan python scripts/seed_demo.py dulu.")
        return 1

    folder = Path(args.out) if args.out else FOLDER_GAMBAR
    for berkas in render_semua(sumber, folder, date.today()):
        print(f"Ditulis: {berkas}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
