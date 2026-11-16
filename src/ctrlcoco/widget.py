import sqlite3
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QVBoxLayout, QWidget

from ctrlcoco.data import get_nearest_task
from ctrlcoco.mood import MOODS, get_mood
from ctrlcoco.sprites import SPRITE_DIR, load_frames
from ctrlcoco.streak import get_streak

ANIMATION_INTERVAL_MS = 500   # jarak antar frame animasi
REFRESH_INTERVAL_MS = 60_000  # jarak antar pembacaan ulang database

TEXT_PANEL_STYLE = (
    "QLabel { color: white; background-color: rgba(0, 0, 0, 170);"
    " border-radius: 6px; padding: 4px 8px; }"
)


class CocoWidget(QWidget):
    def __init__(self, conn: sqlite3.Connection, sprite_dir: Path = SPRITE_DIR):
        super().__init__()
        self.conn = conn
        self._drag_offset = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        # Latar jendela tembus pandang; hanya gambar Coco dan panel teks yang terlihat.
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Semua frame dimuat sekali di sini lalu disimpan (cache), supaya timer
        # animasi tidak membaca file dari disk di setiap detak.
        self._frames = {mood: load_frames(mood, sprite_dir) for mood in MOODS}
        self.mood = None
        self._frame_index = 0

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.streak_label = QLabel()
        self.task_label = QLabel()
        # Panel gelap semi-transparan di belakang teks agar terbaca di latar apa pun.
        for label in (self.streak_label, self.task_label):
            label.setStyleSheet(TEXT_PANEL_STYLE)

        layout = QVBoxLayout(self)
        layout.addWidget(self.image_label)
        layout.addWidget(self.streak_label)
        layout.addWidget(self.task_label)

        self.refresh()

        # Timer animasi: ganti ke frame berikutnya.
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.next_frame)
        self.animation_timer.start(ANIMATION_INTERVAL_MS)

        # Timer refresh: baca ulang database secara berkala.
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start(REFRESH_INTERVAL_MS)

    def refresh(self, now: datetime | None = None) -> None:
        """Baca ulang data dari database, lalu perbarui teks dan kondisi Coco."""
        now = now or datetime.now()
        self.streak_label.setText(f"Streak: {get_streak(self.conn, now.date())} hari")
        task = get_nearest_task(self.conn)
        if task is None:
            self.task_label.setText("Tidak ada task berdeadline")
        else:
            self.task_label.setText(f"{task['title']}\n{task['deadline']}")

        mood = get_mood(self.conn, now)
        if mood != self.mood:
            # Kondisi berganti: animasi kondisi baru mulai dari frame pertama.
            self.mood = mood
            self._frame_index = 0
            self._show_frame()

    def next_frame(self) -> None:
        """Maju satu frame; setelah frame terakhir kembali ke frame pertama."""
        self._frame_index = (self._frame_index + 1) % len(self._frames[self.mood])
        self._show_frame()

    def _show_frame(self) -> None:
        self.image_label.setPixmap(self._frames[self.mood][self._frame_index])

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
