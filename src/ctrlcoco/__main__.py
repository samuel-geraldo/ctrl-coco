import argparse
import sys

from PySide6.QtWidgets import QApplication

from ctrlcoco import db
from ctrlcoco.widget import CocoWidget


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ctrlcoco")
    parser.add_argument("--db", help="path database (bawaan: folder AppData)")
    args = parser.parse_args(argv)

    conn = db.connect(args.db)
    db.init_db(conn)
    app = QApplication(sys.argv[:1])
    widget = CocoWidget(conn)
    widget.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
