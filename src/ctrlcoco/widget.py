import sqlite3
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QVBoxLayout, QWidget

from ctrlcoco.data import get_nearest_task
from ctrlcoco.streak import get_streak

COCO_IMAGE = Path(__file__).resolve().parents[2] / "assets" / "coco.png"


class CocoWidget(QWidget):
    def __init__(self, conn: sqlite3.Connection):
        super().__init__()
        self.conn = conn
        self._drag_offset = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        self.image_label = QLabel("Coco")
        self.image_label.setAlignment(Qt.AlignCenter)
        if COCO_IMAGE.exists():
            self.image_label.setPixmap(
                QPixmap(str(COCO_IMAGE)).scaledToWidth(160, Qt.FastTransformation)
            )
        self.streak_label = QLabel()
        self.task_label = QLabel()

        layout = QVBoxLayout(self)
        layout.addWidget(self.image_label)
        layout.addWidget(self.streak_label)
        layout.addWidget(self.task_label)

        self.refresh()

    def refresh(self) -> None:
        """Baca ulang data dari database dan perbarui teks."""
        self.streak_label.setText(f"Streak: {get_streak(self.conn)} hari")
        task = get_nearest_task(self.conn)
        if task is None:
            self.task_label.setText("Tidak ada task berdeadline")
        else:
            self.task_label.setText(f"{task['title']}\n{task['deadline']}")

    # --- geser jendela dengan mouse ---

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None

    # --- klik kanan: keluar ---

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("Keluar", QApplication.quit)
        menu.exec(event.globalPos())
