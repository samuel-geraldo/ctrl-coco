import re
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPixmap

SPRITE_DIR = Path(__file__).resolve().parents[2] / "assets" / "sprites"
SPRITE_WIDTH = 160

# Warna gambar sementara untuk tiap kondisi.
PLACEHOLDER_COLORS = {
    "waspada": "#e4572e",  # merah-oranye
    "senang": "#f2b134",   # kuning
    "tidur": "#6c7a99",    # biru keabu-abuan
}


def placeholder_frames(mood: str) -> list[QPixmap]:
    """Dua frame gambar sementara: lingkaran berwarna, besar lalu kecil."""
    frames = []
    for margin in (10, 22):
        pixmap = QPixmap(SPRITE_WIDTH, SPRITE_WIDTH)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(PLACEHOLDER_COLORS[mood]))
        size = SPRITE_WIDTH - 2 * margin
        painter.drawEllipse(margin, margin, size, size)
        painter.end()
        frames.append(pixmap)
    return frames


def load_frames(mood: str, sprite_dir: Path = SPRITE_DIR) -> list[QPixmap]:
    """Frame animasi sebuah kondisi dari file <kondisi>_<n>.png, urut menurut n.

    Jika tidak ada file yang bisa dimuat, yang dikembalikan gambar sementara.
    """
    pattern = re.compile(rf"{re.escape(mood)}_(\d+)\.png", re.IGNORECASE)
    numbered = []
    if sprite_dir.is_dir():
        for path in sprite_dir.iterdir():
            match = pattern.fullmatch(path.name)
            if match:
                numbered.append((int(match.group(1)), path))

    frames = []
    for _, path in sorted(numbered):
        pixmap = QPixmap(str(path))
        if not pixmap.isNull():  # file yang rusak dilewati
            frames.append(pixmap.scaledToWidth(SPRITE_WIDTH, Qt.FastTransformation))
    return frames or placeholder_frames(mood)
