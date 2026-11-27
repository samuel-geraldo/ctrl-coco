import sqlite3
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from ctrlcoco import autostart, export
from ctrlcoco.data import DATE_FORMAT, get_daily_log, get_nearest_task
from ctrlcoco.form_batalkan import FormBatalkanSelesai
from ctrlcoco.form_log import FormLogHarian
from ctrlcoco.form_selesai import FormSelesaikanTask
from ctrlcoco.form_task import FormTambahTask
from ctrlcoco.klik import adalah_klik
from ctrlcoco.mood import MOODS, get_mood
from ctrlcoco.perayaan import Perayaan, jenis_perayaan_log
from ctrlcoco.pesan import (
    pesan_coco,
    pesan_perayaan,
    pesan_perayaan_log,
    pesan_perayaan_task,
    pesan_reaksi,
)
from ctrlcoco.posisi import posisi_form
from ctrlcoco.ringkasan import JendelaRingkasan
from ctrlcoco.sprites import load_frames
from ctrlcoco.streak import get_streak
from ctrlcoco.tinjauan import JendelaTinjauan

ANIMATION_INTERVAL_MS = 500   # jarak antar frame animasi
INTERVAL_REAKSI_MS = 120      # jarak antar frame saat bereaksi (Coco bergoyang cepat)
DURASI_REAKSI_MS = 1000       # lama reaksi setelah Coco diklik
INTERVAL_LOMPAT_MS = 200      # jarak antar frame lompat saat merayakan
# Lama perayaan per jenis: tonggak streak lebih panjang daripada perayaan biasa.
DURASI_PERAYAAN_MS = {"tonggak": 3000, "log": 1500, "task": 1500}
REFRESH_INTERVAL_MS = 60_000  # jarak antar pembacaan ulang database
LEBAR_GELEMBUNG = 200         # lebar maksimum gelembung; kalimat lebih panjang turun baris

BUBBLE_STYLE = (
    "QLabel { color: white; background-color: rgba(0, 0, 0, 170);"
    " border-radius: 10px; padding: 6px 10px; }"
)


class CocoWidget(QWidget):
    def __init__(self, conn: sqlite3.Connection, sprite_dir: Path | None = None):
        super().__init__()
        self.conn = conn
        self._drag_offset = None
        self._posisi_tekan = None  # posisi layar saat tombol kiri ditekan (klik vs seret)
        self.bereaksi = False
        self.merayakan = False
        # Kalimat terakhir dari refresh, tampil lagi setelah reaksi atau perayaan selesai.
        self._teks_gelembung = ""

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        # Latar jendela tembus pandang; hanya gambar Coco dan gelembung yang terlihat.
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Semua frame dimuat sekali di sini lalu disimpan (cache), supaya timer
        # animasi tidak membaca file dari disk di setiap detak.
        self._frames = {mood: load_frames(mood, sprite_dir) for mood in MOODS}
        self._frames_lompat = load_frames("lompat", sprite_dir)  # untuk perayaan
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

        # Timer reaksi: sekali jalan, mengakhiri reaksi klik.
        self.reaksi_timer = QTimer(self)
        self.reaksi_timer.setSingleShot(True)
        self.reaksi_timer.setInterval(DURASI_REAKSI_MS)
        self.reaksi_timer.timeout.connect(self.selesai_reaksi)

        # Timer perayaan: sekali jalan, lamanya diatur saat perayaan dimulai.
        self.perayaan_timer = QTimer(self)
        self.perayaan_timer.setSingleShot(True)
        self.perayaan_timer.timeout.connect(self.selesai_perayaan)

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
            self._atur_gelembung("Data gagal dimuat")
            if self.mood is not None:
                return  # Coco tetap di kondisi terakhir
            mood = "tidur"  # refresh pertama gagal: next_frame tetap butuh kondisi
        else:
            self._atur_gelembung(pesan_coco(mood, streak, task, now))

        if mood != self.mood:
            self.mood = mood
            # Kondisi berganti: animasi kondisi baru mulai dari frame pertama. Selama
            # merayakan, frame lompat tidak dipotong; kondisi baru tampil sesudahnya.
            if not self.merayakan:
                self._frame_index = 0
                self._show_frame()

    def next_frame(self) -> None:
        """Maju satu frame; setelah frame terakhir kembali ke frame pertama."""
        self._frame_index = (self._frame_index + 1) % len(self._frames_aktif())
        self._show_frame()

    def _frames_aktif(self):
        return self._frames_lompat if self.merayakan else self._frames[self.mood]

    def _show_frame(self) -> None:
        self.image_label.setPixmap(self._frames_aktif()[self._frame_index])

    def _atur_gelembung(self, teks: str) -> None:
        # Selama bereaksi atau merayakan, kalimat baru disimpan saja; tampil sesudahnya.
        self._teks_gelembung = teks
        if not (self.bereaksi or self.merayakan):
            self.bubble_label.setText(teks)

    # --- reaksi klik: Coco bergoyang cepat dan berkata sesuatu ---

    def mulai_reaksi(self) -> None:
        """Mulai (atau ulangi) reaksi klik. Tidak menyentuh database."""
        if self.merayakan:
            return  # klik tidak memotong perayaan
        self.bereaksi = True
        self.bubble_label.setText(pesan_reaksi(self.mood))
        self.animation_timer.setInterval(INTERVAL_REAKSI_MS)
        self.reaksi_timer.start()  # bila sudah berjalan, hitungan mulai lagi dari awal

    def selesai_reaksi(self) -> None:
        """Kembali ke animasi kondisi dan kalimat terakhir dari refresh."""
        self.bereaksi = False
        self.animation_timer.setInterval(ANIMATION_INTERVAL_MS)
        self._frame_index = 0
        self._show_frame()
        self.bubble_label.setText(self._teks_gelembung)

    # --- perayaan: Coco melompat dan berkata sesuatu (tonggak streak, log, task) ---

    def mulai_perayaan(self, teks: str, durasi_ms: int) -> None:
        """Mainkan frame lompat dan tampilkan `teks` selama `durasi_ms`.

        Satu mesin untuk ketiga jenis perayaan. Reaksi klik yang sedang berjalan
        dihentikan. Tidak menyentuh database.
        """
        self.reaksi_timer.stop()
        self.bereaksi = False
        self.merayakan = True
        self._frame_index = 0
        self.animation_timer.setInterval(INTERVAL_LOMPAT_MS)
        self._show_frame()
        self.bubble_label.setText(teks)
        self.perayaan_timer.start(durasi_ms)

    def selesai_perayaan(self) -> None:
        """Kembali ke animasi kondisi dan kalimat terakhir dari refresh."""
        self.merayakan = False
        self.animation_timer.setInterval(ANIMATION_INTERVAL_MS)
        self._frame_index = 0
        self._show_frame()
        self.bubble_label.setText(self._teks_gelembung)

    def _rayakan(self, perayaan: Perayaan, now: datetime) -> None:
        if perayaan.jenis == "tonggak":
            teks = pesan_perayaan(perayaan.tonggak)
        elif perayaan.jenis == "log":
            teks = pesan_perayaan_log(now)
        else:
            teks = pesan_perayaan_task(perayaan.judul, now)
        self.mulai_perayaan(teks, DURASI_PERAYAAN_MS[perayaan.jenis])

    def _status_log(self, now: datetime) -> tuple[bool, int] | None:
        """(log hari ini valid?, streak) pada tanggal `now`; None bila gagal dibaca."""
        try:
            log = get_daily_log(self.conn, now.strftime(DATE_FORMAT))
            streak = get_streak(self.conn, now.date())
        except sqlite3.Error:
            return None  # tanpa perayaan; pesan error sudah ditangani refresh
        valid = log is not None and log["claude_code"] == 1 and log["github"] == 1
        return valid, streak

    def _rayakan_log(self) -> None:
        """Setelah form log tersimpan: bandingkan status log sebelum dan sesudahnya."""
        now, sebelum = self._log_sebelum
        sesudah = self._status_log(now)
        if sebelum is None or sesudah is None:
            return
        perayaan = jenis_perayaan_log(sebelum[0], sesudah[0], sebelum[1], sesudah[1])
        if perayaan is not None:
            self._rayakan(perayaan, now)

    def _rayakan_task(self) -> None:
        """Setelah form Selesaikan task tersimpan: rayakan task yang diselesaikan."""
        form = self.sender()  # form yang memancarkan sinyal accepted
        if form.judul_selesai is not None:
            self._rayakan(Perayaan("task", judul=form.judul_selesai), datetime.now())

    # --- mouse: seret untuk menggeser, klik untuk reaksi, klik dua kali untuk log ---

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            posisi = event.globalPosition().toPoint()
            self._drag_offset = posisi - self.frameGeometry().topLeft()
            self._posisi_tekan = posisi

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._posisi_tekan is not None:
            tekan, lepas = self._posisi_tekan, event.globalPosition().toPoint()
            if adalah_klik((tekan.x(), tekan.y()), (lepas.x(), lepas.y())):
                self.mulai_reaksi()
        self._drag_offset = None
        self._posisi_tekan = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Pelepasan tombol sesudah klik dua kali bukan klik baru.
            self._posisi_tekan = None
            self.buka_form_log()

    # --- menu klik kanan ---

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("Log hari ini…", self.buka_form_log)
        menu.addAction("Tambah task…", self.buka_form_tambah_task)
        menu.addAction("Selesaikan task…", self.buka_form_selesai)
        menu.addAction("Batalkan selesai…", self.buka_form_batalkan)
        menu.addAction("Ringkasan…", self.buka_ringkasan)
        menu.addAction("Tinjauan mingguan…", self.buka_tinjauan)
        menu.addAction("Ekspor CSV…", self.buka_ekspor)
        # Bercentang sesuai keadaan registri saat menu dibuka. Dari sumber (bukan .exe)
        # tidak ada .exe yang bisa ditunjuk, jadi nonaktif.
        jalan = menu.addAction("Jalan otomatis saat Windows menyala")
        jalan.setCheckable(True)
        jalan.setEnabled(autostart.tersedia())
        jalan.setChecked(self._jalan_otomatis_aktif())
        jalan.triggered.connect(self.ubah_jalan_otomatis)
        menu.addSeparator()
        menu.addAction("Keluar", QApplication.quit)
        menu.exec(event.globalPos())

    def buka_form_log(self) -> FormLogHarian:
        now = datetime.now()
        # Status log dan streak dicatat sebelum form diisi, lalu dibandingkan dengan
        # sesudah disimpan untuk menentukan perayaan. Tanggal sama dengan tanggal form.
        # Form modal, jadi hanya ada satu form log yang terbuka pada satu waktu.
        self._log_sebelum = (now, self._status_log(now))
        form = self._buka_form(FormLogHarian(self.conn, now, self))
        # Dihubungkan setelah refresh (di _buka_form), jadi refresh jalan lebih dulu.
        # Method terikat, bukan lambda: lambda yang memegang self membuat widget ikut
        # terhapus saat form (anaknya) dihapus, lalu program crash.
        form.accepted.connect(self._rayakan_log)
        return form

    def buka_form_tambah_task(self) -> FormTambahTask:
        return self._buka_form(FormTambahTask(self.conn, self))

    def buka_form_selesai(self) -> FormSelesaikanTask:
        form = self._buka_form(FormSelesaikanTask(self.conn, self))
        form.accepted.connect(self._rayakan_task)  # method terikat, lihat buka_form_log
        return form

    def buka_form_batalkan(self) -> FormBatalkanSelesai:
        return self._buka_form(FormBatalkanSelesai(self.conn, self))

    def buka_ringkasan(self) -> JendelaRingkasan:
        return self._buka_jendela_tunggal(JendelaRingkasan)

    def buka_tinjauan(self) -> JendelaTinjauan:
        return self._buka_jendela_tunggal(JendelaTinjauan)

    def _buka_jendela_tunggal(self, kelas):
        # Satu jendela per jenis: bila sudah terbuka, dibawa ke depan, tidak dibuat ganda.
        # Yang sudah ditutup tapi belum dihapus Qt (hapus tertunda) tidak dihitung.
        for jendela in self.findChildren(kelas):
            if jendela.isVisible():
                jendela.raise_()
                jendela.activateWindow()
                return jendela
        # Parent widget, supaya jendela tampil di depan Coco yang always on top. Tidak
        # modal: Coco tetap bisa diklik. show(), bukan open().
        jendela = kelas(self.conn, parent=self)
        jendela.show()
        return jendela

    def buka_ekspor(self) -> tuple[Path, Path] | None:
        """Pilih folder, tanya dulu bila file lama akan tertimpa, lalu tulis dua CSV.

        Mengembalikan kedua path bila berhasil, None bila dibatalkan atau gagal.
        """
        # Dialog bawaan Qt dengan Coco sebagai parent, supaya tampil di depan Coco yang
        # always on top. Berhenti di sini sampai ditutup (dialog sesaat, bukan form).
        pilihan = QFileDialog.getExistingDirectory(self, "Pilih folder ekspor CSV")
        if not pilihan:  # dialog ditutup tanpa memilih
            return None
        folder = Path(pilihan)

        ada = export.file_yang_sudah_ada(folder)
        if ada:
            daftar = "\n".join(f"• {p.name}" for p in ada)
            jawab = QMessageBox.question(
                self,
                "CtrlCoco",
                f"File ini sudah ada di folder itu dan akan ditimpa:\n\n{daftar}\n\nTimpa?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,  # jawaban bawaan: aman, tidak menimpa
            )
            if jawab != QMessageBox.Yes:
                return None

        # Hanya OSError (izin ditolak, disk penuh, folder hilang) yang ditangkap: error
        # lain adalah bug dan harus tetap terlihat.
        try:
            hasil = export.ekspor_csv(self.conn, folder)
        except OSError as e:
            QMessageBox.critical(
                self,
                "CtrlCoco",
                f"Ekspor gagal.\n\nLokasi: {folder}\n\nPenyebab: {e.strerror or e}",
            )
            return None
        QMessageBox.information(self, "CtrlCoco", f"Selesai. Dua file ditulis ke:\n{folder}")
        return hasil

    def _jalan_otomatis_aktif(self) -> bool:
        # Registri yang tidak terbaca tidak boleh menggagalkan menu: anggap mati.
        try:
            return autostart.aktif()
        except OSError:
            return False

    def ubah_jalan_otomatis(self, nyala: bool) -> None:
        """Nyalakan atau matikan jalan otomatis; error registri ditampilkan, bukan dilempar."""
        # Hanya OSError (izin ditolak, kebijakan komputer) yang ditangkap: error lain
        # adalah bug dan harus tetap terlihat.
        try:
            if nyala:
                autostart.nyalakan()
            else:
                autostart.matikan()
        except OSError as e:
            QMessageBox.critical(
                self,
                "CtrlCoco",
                f"Pengaturan jalan otomatis gagal.\n\nPenyebab: {e.strerror or e}",
            )

    def _buka_form(self, form):
        # Widget menjadi parent form, supaya form tampil di depan Coco yang always on top.
        # Setelah tersimpan, baca ulang database tanpa menunggu timer refresh.
        form.accepted.connect(self.refresh)
        # open(), bukan exec(): form modal (Coco tidak bisa diklik selama form terbuka),
        # tapi kode tidak berhenti menunggu dan tidak ada event loop bersarang.
        form.open()
        # Pindahkan ke samping Coco supaya Coco tetap terlihat. Diukur setelah open():
        # ukuran bingkai jendela (baris judul) baru diketahui setelah jendela dibuat.
        x, y = posisi_form(
            _kotak(self.frameGeometry()),
            _kotak(form.frameGeometry()),
            _kotak(self.screen().availableGeometry()),  # layar tempat Coco, tanpa taskbar
        )
        form.move(x, y)
        return form


def _kotak(rect) -> tuple[int, int, int, int]:
    """QRect menjadi tuple (x, y, lebar, tinggi) untuk posisi_form."""
    return (rect.x(), rect.y(), rect.width(), rect.height())
