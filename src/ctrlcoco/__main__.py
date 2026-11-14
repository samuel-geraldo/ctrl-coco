import sys

from PySide6.QtWidgets import QApplication

from ctrlcoco import db
from ctrlcoco.widget import CocoWidget


def main() -> int:
    conn = db.connect()
    db.init_db(conn)
    app = QApplication(sys.argv)
    widget = CocoWidget(conn)
    widget.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
