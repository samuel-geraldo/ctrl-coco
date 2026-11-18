import argparse
import sqlite3
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from ctrlcoco import db
from ctrlcoco.widget import CocoWidget


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ctrlcoco")
    parser.add_argument("--db", help="path database (bawaan: folder AppData)")
    args = parser.parse_args(argv)

    # QApplication dibuat lebih dulu, karena QMessageBox di bawah membutuhkannya.
    # Jika sudah ada (misalnya saat tes), pakai yang itu: Qt hanya mengizinkan satu.
    app = QApplication.instance() or QApplication(sys.argv[:1])

    path = db.default_db_path() if args.db is None else args.db
    conn = None
    penyebab = None
    try:
        conn = db.connect(path)
        try:
            db.init_db(conn)
        except ValueError as e:  # migrasi menolak baris bertanggal rusak
            penyebab = e
    except sqlite3.Error as e:  # bukan database, rusak, atau terkunci
        penyebab = e

    if penyebab is not None:
        QMessageBox.critical(
            None,
            "CtrlCoco",
            f"Database tidak bisa dibuka.\n\nLokasi: {path}\n\nPenyebab: {penyebab}",
        )
        if conn is not None:
            conn.close()
        return 1

    widget = CocoWidget(conn)
    widget.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
