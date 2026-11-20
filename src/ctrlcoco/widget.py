import sqlite3
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QVBoxLayout, QWidget

from ctrlcoco.data import get_nearest_task
from ctrlcoco.form_log import FormLogHarian
from ctrlcoco.form_selesai import FormSelesaikanTask
from ctrlcoco.form_task import FormTambahTask
from ctrlcoco.mood import MOODS, get_mood
from ctrlcoco.pesan import pesan_coco
from ctrlcoco.sprites import SPRITE_DIR, load_frames
from ctrlcoco.streak import get_streak

ANIMATION_INTERVAL_MS = 500   # jarak antar frame animasi
REFRESH_INTERVAL_MS = 60_000  # jarak antar pembacaan ulang database
LEBAR_GELEMBUNG = 200         # lebar maksimum gelembung; kalimat lebih panjang turun baris

BUBBLE_STYLE = (
    "QLabel { color: white; background-color: rgba(0, 0, 0, 170);"
    " border-radius: 10px; padding: 6px 10px; }"
)


class CocoWidget(QWidget):
    def __init__(self, conn: sqlite3.Connection, sprite_dir: Path = SPRITE_DIR):
        super().__init__()
        self.conn = conn
        self._drag_offset = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        # Latar jendela tembus pandang; hanya gambar Coco dan gelembung yang terlihat.
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Semua frame dimuat sekali di sini lalu disimpan (cache), supaya timer
        # animasi tidak membaca file dari disk di setiap detak.
        self._frames = {mood: load_frames(mood, sprite_dir) for mood in MOODS}
        self.mood = None
        self._frame_index = 0

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)

        # Gelembung bicara di atas Coco. Panel gelap semi-transparan agar terbaca di
        # latar apa pun.
        self.bubble_label = QLabel()
        self.bubble_label.setStyleSheet(BUBBLE_STYLE)
        # Teks biasa, bukan HTML: judul task berisi "<b>" tampil apa adanya.
        self.bubble_label.setTextFormat(Qt.TextFormat.PlainText)
        # Word wrap butuh batas lebar; tanpa itu label melebar mengikuti teks.
        self.bubble_label.setWordWrap(True)
        self.bubble_label.setMaximumWidth(LEBAR_GELEMBUNG)

        layout = QVBoxLayout(self)
        layout.addWidget(self.bubble_label, alignment=Qt.AlignHCenter)
        layout.addWidget(self.image_label)

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
        """Baca ulang data dari database, lalu perbarui gelembung dan kondisi Coco."""
        now = now or datetime.now()
        # Baca semua data dulu, baru ubah tampilan: jika satu query gagal, gelembung
        # tidak sempat berisi campuran data baru dan lama.
        try:
            streak = get_streak(self.conn, now.date())
            task = get_nearest_task(self.conn)
            mood = get_mood(self.conn, now)
        except sqlite3.Error:
            # Misalnya database terkunci. Kalimat lama tidak ditampilkan seolah masih
            # benar. Timer refresh tetap berjalan, jadi detak berikutnya mencoba lagi.
            self.bubble_label.setText("Data gagal dimuat")
            if self.mood is not None:
                return  # Coco tetap di kondisi terakhir
            mood = "tidur"  # refresh pertama gagal: next_frame tetap butuh kondisi
        else:
            self.bubble_label.setText(pesan_coco(mood, streak, task, now))

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

    # --- klik kanan: log hari ini, tambah task, selesaikan task, keluar ---

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("Log hari ini…", self.buka_form_log)
        menu.addAction("Tambah task…", self.buka_form_tambah_task)
        menu.addAction("Selesaikan task…", self.buka_form_selesai)
        menu.addSeparator()
        menu.addAction("Keluar", QApplication.quit)
        menu.exec(event.globalPos())

    def buka_form_log(self) -> FormLogHarian:
        return self._buka_form(FormLogHarian(self.conn, datetime.now(), self))

    def buka_form_tambah_task(self) -> FormTambahTask:
        return self._buka_form(FormTambahTask(self.conn, self))

    def buka_form_selesai(self) -> FormSelesaikanTask:
        return self._buka_form(FormSelesaikanTask(self.conn, self))

    def _buka_form(self, form):
        # Widget menjadi parent form, supaya form muncul di atas Coco yang always on top.
        # Setelah tersimpan, baca ulang database tanpa menunggu timer refresh.
        form.accepted.connect(self.refresh)
        # open(), bukan exec(): form modal (Coco tidak bisa diklik selama form terbuka),
        # tapi kode tidak berhenti menunggu dan tidak ada event loop bersarang.
        form.open()
        return form
