import sqlite3
from datetime import date, datetime, timedelta

import pytest
from PySide6.QtCore import QDateTime, QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QContextMenuEvent, QMouseEvent, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QMenu, QMessageBox

from ctrlcoco import data, db
from ctrlcoco import widget as widget_module
from ctrlcoco.form_log import FormLogHarian
from ctrlcoco.form_selesai import FormSelesaikanTask
from ctrlcoco.form_task import FormTambahTask
from ctrlcoco.mood import MOODS
from ctrlcoco.pesan import (
    pesan_coco,
    pesan_perayaan,
    pesan_perayaan_log,
    pesan_perayaan_task,
    pesan_reaksi,
)
from ctrlcoco.ringkasan import JendelaRingkasan
from ctrlcoco.sprites import PLACEHOLDER_COLORS
from ctrlcoco.streak import get_streak
from ctrlcoco.widget import (
    ANIMATION_INTERVAL_MS,
    DURASI_PERAYAAN_MS,
    DURASI_REAKSI_MS,
    INTERVAL_LOMPAT_MS,
    INTERVAL_REAKSI_MS,
    REFRESH_INTERVAL_MS,
    CocoWidget,
)

NOW = datetime(2026, 3, 10, 9, 30)

# Warna dua frame sprite tiruan untuk tiap kondisi.
WARNA_SPRITE = {
    "waspada": ["#ff0000", "#800000"],
    "senang": ["#00ff00", "#008000"],
    "tidur": ["#0000ff", "#000080"],
}


@pytest.fixture
def sprite_dir(tmp_path):
    """Folder sprite tiruan: dua frame satu warna untuk tiap kondisi."""
    for mood, colors in WARNA_SPRITE.items():
        for n, color in enumerate(colors, start=1):
            pixmap = QPixmap(8, 8)
            pixmap.fill(QColor(color))
            assert pixmap.save(str(tmp_path / f"{mood}_{n}.png"))
    return tmp_path


def siapkan_kondisi(conn, mood):
    """Isi database supaya get_mood(conn, NOW) menghasilkan `mood`."""
    if mood == "waspada":
        area_id = data.add_area(conn, "Kuliah")
        data.add_task(conn, area_id, "Laporan", deadline="2026-03-10 18:00", now=NOW)
    elif mood == "senang":
        data.set_daily_log(conn, "2026-03-10", True, True)


def warna_gambar(widget):
    """Warna di tengah gambar yang sedang ditampilkan widget."""
    image = widget.image_label.pixmap().toImage()
    return image.pixelColor(image.width() // 2, image.height() // 2).name()


def test_widget_kosong(app, conn):
    w = CocoWidget(conn)
    w.refresh(NOW)
    assert w.bubble_label.text() == pesan_coco("tidur", 0, None, NOW)


@pytest.mark.parametrize("mood", MOODS)
def test_gelembung_berisi_pesan_coco(app, conn, mood):
    siapkan_kondisi(conn, mood)
    data.set_daily_log(conn, "2026-03-09", True, True)  # streak kemarin
    w = CocoWidget(conn)
    w.refresh(NOW)
    harapan = pesan_coco(mood, get_streak(conn, NOW.date()), data.get_nearest_task(conn), NOW)
    assert w.mood == mood
    assert w.bubble_label.text() == harapan


def test_gelembung_waspada_menyebut_judul_dan_sisa_waktu(app, conn):
    siapkan_kondisi(conn, "waspada")  # Laporan, deadline 18:00; NOW 09:30
    w = CocoWidget(conn)
    w.refresh(NOW)
    assert '"Laporan" deadline 8 jam lagi' in w.bubble_label.text()


def test_gelembung_senang_menyebut_streak(app, conn):
    data.set_daily_log(conn, "2026-03-09", True, True)
    data.set_daily_log(conn, "2026-03-10", True, True)
    w = CocoWidget(conn)
    w.refresh(NOW)
    assert "streak 2 hari" in w.bubble_label.text().lower()


def test_judul_berisi_tag_html_tampil_apa_adanya(app, conn):
    area_id = data.add_area(conn, "Kuliah")
    data.add_task(conn, area_id, "<b>tebal</b>", deadline="2026-03-10 18:00", now=NOW)
    w = CocoWidget(conn)
    w.refresh(NOW)
    # Teks biasa, bukan HTML: tag tidak membuat huruf tebal, tetapi tampil sebagai teks.
    assert w.bubble_label.textFormat() == Qt.TextFormat.PlainText
    assert "<b>tebal</b>" in w.bubble_label.text()


def test_gelembung_membungkus_kalimat_panjang(app, conn):
    w = CocoWidget(conn)
    assert w.bubble_label.wordWrap()
    # Tanpa batas lebar, word wrap tidak berguna: label akan melebar mengikuti teks.
    assert w.bubble_label.maximumWidth() == widget_module.LEBAR_GELEMBUNG


def test_gelembung_di_atas_coco(app, conn):
    w = CocoWidget(conn)
    layout = w.layout()
    assert layout.indexOf(w.bubble_label) < layout.indexOf(w.image_label)


def test_widget_tanpa_bingkai_dan_selalu_di_atas(app, conn):
    w = CocoWidget(conn)
    assert w.windowFlags() & Qt.FramelessWindowHint
    assert w.windowFlags() & Qt.WindowStaysOnTopHint


def test_widget_latar_transparan_dan_teks_berpanel(app, conn):
    w = CocoWidget(conn)
    assert w.testAttribute(Qt.WA_TranslucentBackground)
    assert "color: white" in w.bubble_label.styleSheet()
    assert "rgba(0, 0, 0" in w.bubble_label.styleSheet()


# --- gambar sesuai kondisi ---

@pytest.mark.parametrize("mood", MOODS)
def test_sprite_dipilih_sesuai_kondisi(app, conn, sprite_dir, mood):
    siapkan_kondisi(conn, mood)
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    w.refresh(NOW)
    assert w.mood == mood
    assert warna_gambar(w) == WARNA_SPRITE[mood][0]


@pytest.mark.parametrize("mood", MOODS)
def test_gambar_sementara_jika_sprite_tidak_ada(app, conn, tmp_path, mood):
    siapkan_kondisi(conn, mood)
    w = CocoWidget(conn, sprite_dir=tmp_path / "tidak_ada")
    w.refresh(NOW)
    assert w.mood == mood
    assert warna_gambar(w) == PLACEHOLDER_COLORS[mood]


def test_widget_bawaan_selalu_punya_gambar(app, conn):
    w = CocoWidget(conn)
    assert not w.image_label.pixmap().isNull()


# --- animasi ---

def test_next_frame_bergantian_lalu_kembali_ke_awal(app, conn, sprite_dir):
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    w.refresh(NOW)
    assert warna_gambar(w) == WARNA_SPRITE["tidur"][0]
    w.next_frame()
    assert warna_gambar(w) == WARNA_SPRITE["tidur"][1]
    w.next_frame()
    assert warna_gambar(w) == WARNA_SPRITE["tidur"][0]


def test_timer_animasi_berjalan_dan_memajukan_frame(app, conn, sprite_dir):
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    w.refresh(NOW)
    assert w.animation_timer.isActive()
    assert w.animation_timer.interval() == ANIMATION_INTERVAL_MS
    w.animation_timer.timeout.emit()  # satu detak timer, tanpa menunggu
    assert warna_gambar(w) == WARNA_SPRITE["tidur"][1]


# --- refresh berkala ---

def test_refresh_mengganti_ekspresi_dan_mulai_dari_frame_pertama(app, conn, sprite_dir):
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    w.refresh(NOW)
    w.next_frame()
    assert warna_gambar(w) == WARNA_SPRITE["tidur"][1]

    data.set_daily_log(conn, "2026-03-10", True, True)
    w.refresh(NOW)
    assert w.mood == "senang"
    assert warna_gambar(w) == WARNA_SPRITE["senang"][0]
    assert w.bubble_label.text() == pesan_coco("senang", 1, None, NOW)


def test_refresh_dengan_kondisi_sama_tidak_mengulang_animasi(app, conn, sprite_dir):
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    w.refresh(NOW)
    w.next_frame()
    w.refresh(NOW)
    assert warna_gambar(w) == WARNA_SPRITE["tidur"][1]


def test_refresh_mengikuti_waktu(app, conn, sprite_dir):
    area_id = data.add_area(conn, "Kuliah")
    data.add_task(conn, area_id, "Laporan", deadline="2026-03-12 09:00", now=NOW)
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    w.refresh(NOW)
    assert w.mood == "tidur"
    w.refresh(datetime(2026, 3, 11, 9, 30))  # deadline tinggal 23,5 jam
    assert w.mood == "waspada"


def test_timer_refresh_berjalan_dan_membaca_ulang_data(app, conn, sprite_dir):
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    assert w.refresh_timer.isActive()
    assert w.refresh_timer.interval() == REFRESH_INTERVAL_MS
    assert "Belum ada log hari ini" in w.bubble_label.text()

    data.set_daily_log(conn, date.today().isoformat(), True, True)
    w.refresh_timer.timeout.emit()  # satu detak timer, tanpa menunggu
    assert "streak 1 hari" in w.bubble_label.text().lower()
    assert w.mood == "senang"


# --- error database saat refresh ---

class KoneksiBisaGagal:
    """Pembungkus koneksi: selama `error` terisi, setiap query melempar error itu."""

    def __init__(self, conn):
        self._conn = conn
        self.error = None

    def execute(self, *args, **kwargs):
        if self.error is not None:
            raise self.error
        return self._conn.execute(*args, **kwargs)


def test_refresh_gagal_menampilkan_tanda_lalu_pulih(app, conn, sprite_dir):
    data.set_daily_log(conn, date.today().isoformat(), True, True)
    area_id = data.add_area(conn, "Kuliah")
    data.add_task(conn, area_id, "Laporan", deadline="2099-01-01 10:00")
    koneksi = KoneksiBisaGagal(conn)
    w = CocoWidget(koneksi, sprite_dir=sprite_dir)
    assert "streak 1 hari" in w.bubble_label.text().lower()

    koneksi.error = sqlite3.OperationalError("database is locked")
    w.refresh_timer.timeout.emit()
    # Kalimat lama tidak boleh tetap tampil seolah masih benar.
    assert w.bubble_label.text() == "Data gagal dimuat"
    assert w.refresh_timer.isActive()

    koneksi.error = None
    w.refresh_timer.timeout.emit()
    assert "streak 1 hari" in w.bubble_label.text().lower()


def test_refresh_saat_database_terkunci_sungguhan_lalu_pulih(app, tmp_path, sprite_dir):
    # Kunci sungguhan dari koneksi lain, bukan error tiruan. timeout kecil supaya tes
    # cepat: yang diuji di sini perilaku pulih, bukan lamanya menunggu.
    path = tmp_path / "kunci.db"
    c = db.connect(path, timeout=0.05)
    db.init_db(c)
    data.set_daily_log(c, date.today().isoformat(), True, True)
    area_id = data.add_area(c, "Kuliah")
    data.add_task(c, area_id, "Laporan", deadline="2099-01-01 10:00")
    w = CocoWidget(c, sprite_dir=sprite_dir)
    try:
        assert "streak 1 hari" in w.bubble_label.text().lower()

        lain = sqlite3.connect(path, isolation_level=None)
        lain.execute("BEGIN EXCLUSIVE")
        try:
            w.refresh_timer.timeout.emit()
            assert w.bubble_label.text() == "Data gagal dimuat"
        finally:
            lain.rollback()
            lain.close()

        w.refresh_timer.timeout.emit()
        assert "streak 1 hari" in w.bubble_label.text().lower()
    finally:
        w.close()
        c.close()


def test_refresh_pertama_gagal_coco_tidur(app, conn, sprite_dir):
    koneksi = KoneksiBisaGagal(conn)
    koneksi.error = sqlite3.OperationalError("database is locked")
    w = CocoWidget(koneksi, sprite_dir=sprite_dir)
    assert w.bubble_label.text() == "Data gagal dimuat"
    assert w.mood == "tidur"
    assert warna_gambar(w) == WARNA_SPRITE["tidur"][0]
    w.next_frame()  # timer animasi tidak boleh crash
    assert warna_gambar(w) == WARNA_SPRITE["tidur"][1]


def test_error_selain_sqlite_tetap_naik(app, conn):
    koneksi = KoneksiBisaGagal(conn)
    w = CocoWidget(koneksi)
    koneksi.error = RuntimeError("bug di kode, bukan masalah database")
    with pytest.raises(RuntimeError):
        w.refresh()


# --- interaksi mouse ---

def test_seret_memindahkan_jendela(app, conn):
    w = CocoWidget(conn)
    w.move(100, 100)
    w.show()
    QTest.mousePress(w, Qt.LeftButton, pos=QPoint(10, 10))
    QTest.mouseMove(w, QPoint(60, 40))  # 50 ke kanan, 30 ke bawah
    QTest.mouseRelease(w, Qt.LeftButton, pos=QPoint(60, 40))
    assert w.pos() == QPoint(150, 130)
    # Seret bukan klik: Coco tidak bereaksi.
    assert not w.bereaksi
    assert not w.reaksi_timer.isActive()


# --- klik: reaksi dan log cepat ---

def coco_siap_diklik(conn, sprite_dir):
    """Widget yang sudah tampil, dengan isi gelembung yang diketahui (refresh di NOW)."""
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    w.move(100, 100)
    w.show()
    w.refresh(NOW)
    return w


def test_klik_tanpa_gerak_memicu_reaksi(app, conn, sprite_dir):
    w = coco_siap_diklik(conn, sprite_dir)
    QTest.mouseClick(w, Qt.LeftButton, pos=QPoint(10, 10))

    assert w.bereaksi
    assert w.reaksi_timer.isActive()
    assert w.reaksi_timer.isSingleShot()
    assert w.reaksi_timer.interval() == DURASI_REAKSI_MS
    # Coco bergoyang: animasi kondisinya diputar lebih cepat.
    assert w.animation_timer.interval() == INTERVAL_REAKSI_MS
    assert w.bubble_label.text() == pesan_reaksi("tidur")


def test_klik_dengan_gerak_di_bawah_ambang_tetap_reaksi(app, conn, sprite_dir):
    w = coco_siap_diklik(conn, sprite_dir)
    QTest.mousePress(w, Qt.LeftButton, pos=QPoint(10, 10))
    QTest.mouseMove(w, QPoint(13, 14))  # 3 ke kanan, 4 ke bawah: jarak 7 < 10
    # Jendela ikut bergeser, jadi kursor tetap di titik yang sama pada widget.
    QTest.mouseRelease(w, Qt.LeftButton, pos=QPoint(10, 10))
    assert w.pos() == QPoint(103, 104)
    assert w.bereaksi


def test_setelah_reaksi_kembali_ke_animasi_kondisi(app, conn, sprite_dir):
    w = coco_siap_diklik(conn, sprite_dir)
    QTest.mouseClick(w, Qt.LeftButton, pos=QPoint(10, 10))
    w.next_frame()
    assert warna_gambar(w) == WARNA_SPRITE["tidur"][1]

    w.reaksi_timer.timeout.emit()  # reaksi selesai, tanpa menunggu 1 detik

    assert not w.bereaksi
    assert w.animation_timer.interval() == ANIMATION_INTERVAL_MS
    assert warna_gambar(w) == WARNA_SPRITE["tidur"][0]  # mulai dari frame pertama
    assert w.bubble_label.text() == pesan_coco("tidur", 0, None, NOW)


def test_klik_saat_reaksi_memulai_ulang_reaksi(app, conn, sprite_dir):
    w = coco_siap_diklik(conn, sprite_dir)
    QTest.mouseClick(w, Qt.LeftButton, pos=QPoint(10, 10))
    w.reaksi_timer.stop()  # anggap hitungan hampir habis
    QTest.mouseClick(w, Qt.LeftButton, pos=QPoint(10, 10))
    assert w.reaksi_timer.isActive()
    assert w.bereaksi


def test_refresh_saat_reaksi_tidak_memotong_reaksi(app, conn, sprite_dir):
    w = coco_siap_diklik(conn, sprite_dir)
    QTest.mouseClick(w, Qt.LeftButton, pos=QPoint(10, 10))

    data.set_daily_log(conn, "2026-03-10", True, True)
    w.refresh(NOW)
    assert w.bereaksi
    assert w.bubble_label.text() == pesan_reaksi("tidur")

    w.reaksi_timer.timeout.emit()
    # Setelah reaksi selesai, yang tampil kondisi dan kalimat terbaru.
    assert w.mood == "senang"
    assert warna_gambar(w) == WARNA_SPRITE["senang"][0]
    assert w.bubble_label.text() == pesan_coco("senang", 1, None, NOW)


def test_setelah_reaksi_data_gagal_dimuat_tetap_tampil(app, conn, sprite_dir):
    koneksi = KoneksiBisaGagal(conn)
    w = CocoWidget(koneksi, sprite_dir=sprite_dir)
    w.show()
    koneksi.error = sqlite3.OperationalError("database is locked")
    w.refresh(NOW)
    QTest.mouseClick(w, Qt.LeftButton, pos=QPoint(10, 10))
    assert w.bubble_label.text() == pesan_reaksi("tidur")
    w.reaksi_timer.timeout.emit()
    assert w.bubble_label.text() == "Data gagal dimuat"


def test_klik_tidak_mengubah_database(app, conn, sprite_dir):
    w = coco_siap_diklik(conn, sprite_dir)
    sebelum = conn.total_changes
    QTest.mouseClick(w, Qt.LeftButton, pos=QPoint(10, 10))
    w.reaksi_timer.timeout.emit()
    assert conn.total_changes == sebelum


def test_klik_dua_kali_membuka_form_log(app, conn, sprite_dir):
    w = coco_siap_diklik(conn, sprite_dir)
    QTest.mouseDClick(w, Qt.LeftButton, pos=QPoint(10, 10))
    form = satu_form(w, FormLogHarian)
    assert form.tanggal == date.today().isoformat()
    form.close()


def test_klik_kanan_tidak_memicu_reaksi(app, conn, sprite_dir):
    w = coco_siap_diklik(conn, sprite_dir)
    # Event dikirim langsung ke handler: QTest.mouseClick kanan bisa membuka menu
    # sungguhan yang menunggu klik.
    for jenis in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
        posisi = QPointF(10, 10)
        event = QMouseEvent(
            jenis, posisi, w.mapToGlobal(posisi), Qt.RightButton, Qt.RightButton, Qt.NoModifier
        )
        if jenis == QEvent.MouseButtonPress:
            w.mousePressEvent(event)
        else:
            w.mouseReleaseEvent(event)
    assert not w.bereaksi


def test_menu_klik_kanan_punya_keluar(app, conn, monkeypatch):
    # Menu sungguhan menunggu klik. Widget diberi QMenu tiruan yang exec-nya hanya
    # mencatat menu yang akan dibuka. (Mengganti QMenu.exec langsung di kelas Qt
    # tidak berpengaruh: menu sungguhan tetap terbuka.)
    menu_dibuka = []

    class MenuTiruan(QMenu):
        def exec(self, *args):
            menu_dibuka.append(self)

    monkeypatch.setattr(widget_module, "QMenu", MenuTiruan)
    # quit sungguhan akan menghentikan aplikasi; gantinya hanya mencatat panggilan.
    keluar = []
    monkeypatch.setattr(QApplication, "quit", staticmethod(lambda: keluar.append(True)))

    w = CocoWidget(conn)
    w.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Mouse, QPoint(5, 5), QPoint(5, 5)))
    assert len(menu_dibuka) == 1
    aksi_keluar = [a for a in menu_dibuka[0].actions() if a.text() == "Keluar"]
    assert len(aksi_keluar) == 1

    aksi_keluar[0].trigger()
    assert keluar == [True]


def buka_menu(w, monkeypatch):
    """Buka menu klik kanan dengan QMenu tiruan, kembalikan daftar aksinya."""
    menu_dibuka = []

    class MenuTiruan(QMenu):
        def exec(self, *args):
            menu_dibuka.append(self)

    monkeypatch.setattr(widget_module, "QMenu", MenuTiruan)
    w.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Mouse, QPoint(5, 5), QPoint(5, 5)))
    assert len(menu_dibuka) == 1
    return menu_dibuka[0].actions()


def picu_aksi(w, monkeypatch, teks):
    aksi = [a for a in buka_menu(w, monkeypatch) if a.text() == teks]
    assert len(aksi) == 1
    aksi[0].trigger()


def satu_form(w, kelas):
    forms = w.findChildren(kelas)
    assert len(forms) == 1
    form = forms[0]
    assert form.parent() is w           # muncul di atas Coco
    assert form.isVisible() and form.isModal()
    return form


def form_sudah_dihapus(w, kelas):
    # WA_DeleteOnClose: setelah Qt memproses penghapusan, form tidak tertinggal di memori.
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    return w.findChildren(kelas) == []


def test_menu_klik_kanan_berurutan(app, conn, monkeypatch):
    w = CocoWidget(conn)
    aksi = buka_menu(w, monkeypatch)
    assert [("---" if a.isSeparator() else a.text()) for a in aksi] == [
        "Log hari ini…", "Tambah task…", "Selesaikan task…", "Ringkasan…", "Ekspor CSV…",
        "---", "Keluar",
    ]


def jendela_ringkasan_terbuka(w):
    return [j for j in w.findChildren(JendelaRingkasan) if j.isVisible()]


def test_ringkasan_membuka_jendela_dan_menutupnya_tidak_menutup_widget(app, conn, monkeypatch):
    w = CocoWidget(conn)
    w.show()
    picu_aksi(w, monkeypatch, "Ringkasan…")
    terbuka = jendela_ringkasan_terbuka(w)
    assert len(terbuka) == 1
    assert terbuka[0].parent() is w          # muncul di atas Coco
    assert not terbuka[0].isModal()          # Coco tetap bisa diklik

    terbuka[0].close()
    assert form_sudah_dihapus(w, JendelaRingkasan)
    assert w.isVisible()
    w.close()


def test_ringkasan_dipilih_dua_kali_tidak_menggandakan_jendela(app, conn, monkeypatch):
    w = CocoWidget(conn)
    w.show()
    picu_aksi(w, monkeypatch, "Ringkasan…")
    pertama = jendela_ringkasan_terbuka(w)[0]
    picu_aksi(w, monkeypatch, "Ringkasan…")
    assert jendela_ringkasan_terbuka(w) == [pertama]
    pertama.close()
    w.close()


def test_buka_tutup_ringkasan_berkali_kali_tidak_meninggalkan_jendela_lama(app, conn, monkeypatch):
    w = CocoWidget(conn)
    w.show()
    for _ in range(5):
        picu_aksi(w, monkeypatch, "Ringkasan…")
        terbuka = jendela_ringkasan_terbuka(w)
        assert len(terbuka) == 1
        terbuka[0].close()
        assert form_sudah_dihapus(w, JendelaRingkasan)
    w.close()


def test_log_hari_ini_membuka_form_dan_coco_langsung_senang(app, conn, monkeypatch):
    w = CocoWidget(conn)
    assert "Belum ada log hari ini" in w.bubble_label.text()
    assert w.mood == "tidur"

    picu_aksi(w, monkeypatch, "Log hari ini…")
    form = satu_form(w, FormLogHarian)
    assert form.tanggal == date.today().isoformat()
    form.claude_code_check.setChecked(True)
    form.github_check.setChecked(True)
    form.tombol_simpan.click()

    # Tanpa menunggu timer refresh: kondisi Coco langsung berubah. Log baru lengkap
    # memicu perayaan (#93); setelah perayaan selesai, gelembung menyebut streak.
    assert w.mood == "senang"
    w.perayaan_timer.timeout.emit()
    assert "streak 1 hari" in w.bubble_label.text().lower()
    assert form_sudah_dihapus(w, FormLogHarian)


def test_selesaikan_task_membuka_form_dan_widget_langsung_refresh(app, conn, monkeypatch):
    area_id = data.add_area(conn, "Kuliah")
    mepet = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
    data.add_task(conn, area_id, "Kuis", deadline=mepet)
    data.add_task(conn, area_id, "Laporan", deadline="2099-01-01 10:00")
    w = CocoWidget(conn)
    assert '"Kuis"' in w.bubble_label.text()
    assert w.mood == "waspada"

    picu_aksi(w, monkeypatch, "Selesaikan task…")
    form = satu_form(w, FormSelesaikanTask)
    form.daftar.setCurrentRow(0)  # Kuis, deadline paling awal
    form.tombol_selesai.click()

    # Coco tidak waspada lagi. Task selesai memicu perayaan (#93); setelah perayaan
    # selesai, task yang sudah selesai hilang dari gelembung.
    assert w.mood == "tidur"
    w.perayaan_timer.timeout.emit()
    assert "Kuis" not in w.bubble_label.text()
    assert form_sudah_dihapus(w, FormSelesaikanTask)


def test_tambah_task_membuka_form_dan_widget_langsung_refresh(app, conn, monkeypatch):
    menu_dibuka = []

    class MenuTiruan(QMenu):
        def exec(self, *args):
            menu_dibuka.append(self)

    monkeypatch.setattr(widget_module, "QMenu", MenuTiruan)
    w = CocoWidget(conn)
    assert w.mood == "tidur"

    w.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Mouse, QPoint(5, 5), QPoint(5, 5)))
    aksi = [a for a in menu_dibuka[0].actions() if a.text() == "Tambah task…"]
    aksi[0].trigger()

    forms = w.findChildren(FormTambahTask)
    assert len(forms) == 1
    form = forms[0]
    assert form.parent() is w           # muncul di atas Coco
    assert form.isVisible() and form.isModal()

    form.area_combo.setEditText("Kuliah")
    form.judul_edit.setText("Laporan praktikum")
    form.tanpa_deadline_check.setChecked(False)
    form.deadline_edit.setDateTime(QDateTime(datetime(2026, 3, 12, 23, 59)))
    form.tombol_simpan.click()

    # Tanpa menunggu timer refresh: task baru langsung terlihat (deadline sudah lewat).
    assert '"Laporan praktikum" sudah terlambat' in w.bubble_label.text()
    assert w.mood == "waspada"
    # WA_DeleteOnClose: setelah Qt memproses penghapusan, form tidak tertinggal di memori.
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    assert w.findChildren(FormTambahTask) == []


# --- posisi form: di samping Coco, tidak menutupinya ---

def kotak(rect):
    return (rect.x(), rect.y(), rect.width(), rect.height())


@pytest.mark.parametrize(
    "buka, kelas",
    [
        ("buka_form_log", FormLogHarian),
        ("buka_form_tambah_task", FormTambahTask),
        ("buka_form_selesai", FormSelesaikanTask),
    ],
)
def test_ketiga_form_memakai_posisi_form(app, conn, monkeypatch, buka, kelas):
    panggilan = []

    def posisi_tiruan(coco, form, layar):
        panggilan.append((coco, form, layar))
        return (123, 45)

    monkeypatch.setattr(widget_module, "posisi_form", posisi_tiruan)
    w = CocoWidget(conn)
    w.move(300, 200)
    w.show()
    form = getattr(w, buka)()

    assert isinstance(form, kelas)
    assert len(panggilan) == 1
    coco, ukuran_form, layar = panggilan[0]
    assert coco == kotak(w.frameGeometry())
    assert layar == kotak(w.screen().availableGeometry())
    assert ukuran_form[2:] == kotak(form.frameGeometry())[2:]
    assert form.pos() == QPoint(123, 45)
    form.close()


def test_form_dibuka_utuh_di_dalam_layar(app, conn):
    w = CocoWidget(conn)
    layar = w.screen().availableGeometry()
    w.move(layar.right() - w.width(), layar.bottom() - w.height())  # pojok kanan bawah
    w.show()
    form = w.buka_form_log()
    assert layar.contains(form.frameGeometry())
    form.close()


# --- perayaan: tonggak streak, log baru lengkap, task selesai (#93) ---

def siapkan_streak_kemarin(conn, hari):
    """Log valid untuk `hari` hari terakhir sebelum hari ini (hari ini belum diisi)."""
    for n in range(1, hari + 1):
        data.set_daily_log(conn, (date.today() - timedelta(days=n)).isoformat(), True, True)


def simpan_log(w, claude_code=True, github=True):
    form = w.buka_form_log()
    form.claude_code_check.setChecked(claude_code)
    form.github_check.setChecked(github)
    form.tombol_simpan.click()


def variasi(fungsi, *args):
    """Kedua variasi kalimat (hari ini dan besok) dari fungsi pesan berbasis tanggal."""
    sekarang = datetime.now()
    return {fungsi(*args, sekarang), fungsi(*args, sekarang + timedelta(days=1))}


def test_konstanta_perayaan():
    assert DURASI_PERAYAAN_MS == {"tonggak": 3000, "log": 1500, "task": 1500}
    assert INTERVAL_LOMPAT_MS == 200


def test_log_mencapai_tonggak_3_memicu_perayaan_tonggak(app, conn, sprite_dir):
    siapkan_streak_kemarin(conn, 2)
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    simpan_log(w)  # streak 2 -> 3

    assert w.merayakan
    assert w.perayaan_timer.isActive()
    assert w.perayaan_timer.isSingleShot()
    assert w.perayaan_timer.interval() == DURASI_PERAYAAN_MS["tonggak"]
    assert w.animation_timer.interval() == INTERVAL_LOMPAT_MS
    # Belum ada lompat_<n>.png: gambar sementara lompat dipakai tanpa error.
    assert warna_gambar(w) == PLACEHOLDER_COLORS["lompat"]
    assert w.bubble_label.text() == pesan_perayaan(3)


def test_setelah_perayaan_kembali_ke_kondisi(app, conn, sprite_dir):
    siapkan_streak_kemarin(conn, 2)
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    simpan_log(w)
    w.next_frame()

    w.perayaan_timer.timeout.emit()  # perayaan selesai, tanpa menunggu

    assert not w.merayakan
    assert w.animation_timer.interval() == ANIMATION_INTERVAL_MS
    assert warna_gambar(w) == WARNA_SPRITE["senang"][0]
    assert "streak 3 hari" in w.bubble_label.text().lower()


def test_log_baru_valid_tanpa_tonggak_memicu_perayaan_biasa(app, conn, sprite_dir):
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    simpan_log(w)  # streak 0 -> 1
    assert w.merayakan
    assert w.perayaan_timer.interval() == DURASI_PERAYAAN_MS["log"]
    assert w.bubble_label.text() in variasi(pesan_perayaan_log)


def test_simpan_ulang_log_yang_sudah_valid_tidak_merayakan(app, conn, sprite_dir):
    siapkan_streak_kemarin(conn, 2)
    data.set_daily_log(conn, date.today().isoformat(), True, True)
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    simpan_log(w)  # streak tetap 3
    assert not w.merayakan
    assert not w.perayaan_timer.isActive()


def test_log_belum_lengkap_tidak_merayakan(app, conn, sprite_dir):
    siapkan_streak_kemarin(conn, 2)
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    simpan_log(w, claude_code=True, github=False)
    assert not w.merayakan


def test_form_log_dibatalkan_tidak_merayakan(app, conn, sprite_dir):
    siapkan_streak_kemarin(conn, 2)
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    form = w.buka_form_log()
    form.claude_code_check.setChecked(True)
    form.github_check.setChecked(True)
    form.tombol_batal.click()
    assert not w.merayakan


def test_refresh_timer_tidak_memicu_perayaan(app, conn, sprite_dir):
    siapkan_streak_kemarin(conn, 2)
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    data.set_daily_log(conn, date.today().isoformat(), True, True)  # bukan lewat form
    w.refresh_timer.timeout.emit()
    assert w.mood == "senang"
    assert not w.merayakan


def test_widget_baru_dibuka_tidak_merayakan(app, conn, sprite_dir):
    siapkan_streak_kemarin(conn, 2)
    data.set_daily_log(conn, date.today().isoformat(), True, True)
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    assert not w.merayakan


def test_selesaikan_task_memicu_perayaan_task(app, conn, sprite_dir):
    area_id = data.add_area(conn, "Kuliah")
    data.add_task(conn, area_id, "Laporan", deadline="2099-01-01 10:00")
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    form = w.buka_form_selesai()
    form.daftar.setCurrentRow(0)
    form.tombol_selesai.click()

    assert w.merayakan
    assert w.perayaan_timer.interval() == DURASI_PERAYAAN_MS["task"]
    assert warna_gambar(w) == PLACEHOLDER_COLORS["lompat"]
    assert w.bubble_label.text() in variasi(pesan_perayaan_task, "Laporan")


def test_form_selesai_dibatalkan_tidak_merayakan(app, conn, sprite_dir):
    area_id = data.add_area(conn, "Kuliah")
    data.add_task(conn, area_id, "Laporan", deadline="2099-01-01 10:00")
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    form = w.buka_form_selesai()
    form.daftar.setCurrentRow(0)
    form.tombol_batal.click()
    assert not w.merayakan


def test_tambah_task_tidak_merayakan(app, conn, sprite_dir):
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    form = w.buka_form_tambah_task()
    form.area_combo.setEditText("Kuliah")
    form.judul_edit.setText("Laporan")
    form.tombol_simpan.click()
    assert len(data.list_tasks(conn)) == 1
    assert not w.merayakan


def test_refresh_saat_perayaan_tidak_memotong(app, conn, sprite_dir):
    siapkan_streak_kemarin(conn, 2)
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    simpan_log(w)
    area_id = data.add_area(conn, "Kuliah")
    data.add_task(conn, area_id, "Kuis", deadline="2000-01-01 10:00")  # Coco jadi waspada

    w.refresh()
    assert w.merayakan
    assert w.bubble_label.text() == pesan_perayaan(3)
    assert warna_gambar(w) == PLACEHOLDER_COLORS["lompat"]

    w.perayaan_timer.timeout.emit()
    assert w.mood == "waspada"
    assert warna_gambar(w) == WARNA_SPRITE["waspada"][0]
    assert '"Kuis"' in w.bubble_label.text()


def test_klik_saat_merayakan_diabaikan(app, conn, sprite_dir):
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    w.show()
    w.mulai_perayaan("Hore!", DURASI_PERAYAAN_MS["log"])
    QTest.mouseClick(w, Qt.LeftButton, pos=QPoint(10, 10))
    assert not w.bereaksi
    assert w.bubble_label.text() == "Hore!"
    assert w.animation_timer.interval() == INTERVAL_LOMPAT_MS


def test_perayaan_menghentikan_reaksi_klik(app, conn, sprite_dir):
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    w.refresh(NOW)
    w.mulai_reaksi()
    w.mulai_perayaan("Hore!", DURASI_PERAYAAN_MS["log"])
    assert not w.bereaksi
    assert not w.reaksi_timer.isActive()
    assert w.merayakan
    assert w.bubble_label.text() == "Hore!"

    w.perayaan_timer.timeout.emit()
    assert w.bubble_label.text() == pesan_coco("tidur", 0, None, NOW)


def test_perayaan_memakai_frame_lompat_dari_berkas(app, conn, sprite_dir):
    warna_lompat = ["#112233", "#445566", "#778899"]
    for n, warna in enumerate(warna_lompat, start=1):
        pixmap = QPixmap(8, 8)
        pixmap.fill(QColor(warna))
        assert pixmap.save(str(sprite_dir / f"lompat_{n}.png"))
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    w.mulai_perayaan("Hore!", DURASI_PERAYAAN_MS["log"])

    terlihat = [warna_gambar(w)]
    for _ in range(3):
        w.next_frame()
        terlihat.append(warna_gambar(w))
    assert terlihat == [*warna_lompat, warna_lompat[0]]


def test_perayaan_tidak_mengubah_database(app, conn, sprite_dir):
    siapkan_streak_kemarin(conn, 2)
    w = CocoWidget(conn, sprite_dir=sprite_dir)
    simpan_log(w)
    sebelum = conn.total_changes
    w.next_frame()
    w.perayaan_timer.timeout.emit()
    assert conn.total_changes == sebelum


# --- Ekspor CSV (#43): pilih folder, tanya dulu bila file ada, lapor hasil atau error ---


@pytest.fixture
def dialog(monkeypatch):
    """Ganti dialog Qt: tidak menunggu klik, hanya mencatat panggilan dan memberi jawaban."""

    class Dialog:
        folder = ""  # jawaban dialog pilih folder; "" berarti dibatalkan
        timpa = QMessageBox.Yes  # jawaban pertanyaan "timpa file lama?"

        def __init__(self):
            self.folder_diminta = []
            self.pertanyaan = []
            self.info = []
            self.error = []

    d = Dialog()

    def pilih_folder(*args, **kwargs):
        d.folder_diminta.append(args)
        return d.folder

    def tanya(*args, **kwargs):
        d.pertanyaan.append(args)
        return d.timpa

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(pilih_folder))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(tanya))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a: d.info.append(a)))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a: d.error.append(a)))
    return d


def test_menu_ekspor_csv_membuka_dialog_pilih_folder_di_atas_coco(app, conn, monkeypatch, dialog):
    w = CocoWidget(conn)
    picu_aksi(w, monkeypatch, "Ekspor CSV…")
    assert len(dialog.folder_diminta) == 1
    assert dialog.folder_diminta[0][0] is w  # parent Coco: dialog tampil di depan


def test_ekspor_csv_menulis_dua_file_dan_melaporkan_folder(app, conn, tmp_path, dialog):
    area_id = data.add_area(conn, "Kuliah")
    data.add_task(conn, area_id, "Laporan")
    dialog.folder = str(tmp_path)
    w = CocoWidget(conn)
    w.buka_ekspor()
    assert (tmp_path / "task.csv").is_file()
    assert (tmp_path / "daily_log.csv").is_file()
    assert len(dialog.info) == 1
    teks = dialog.info[0][2]  # QMessageBox.information(parent, judul, teks)
    assert str(tmp_path) in teks
    assert dialog.pertanyaan == [] and dialog.error == []


def test_ekspor_csv_dibatalkan_tidak_menulis_apa_pun(app, conn, tmp_path, dialog):
    dialog.folder = ""  # pengguna menutup dialog pilih folder
    w = CocoWidget(conn)
    w.buka_ekspor()
    assert list(tmp_path.iterdir()) == []
    assert dialog.pertanyaan == [] and dialog.info == [] and dialog.error == []


def test_ekspor_csv_file_ada_ditanya_dulu_dan_ditimpa_bila_ya(app, conn, tmp_path, dialog):
    (tmp_path / "task.csv").write_text("isi lama", encoding="utf-8")
    dialog.folder = str(tmp_path)
    dialog.timpa = QMessageBox.Yes
    w = CocoWidget(conn)
    w.buka_ekspor()
    assert len(dialog.pertanyaan) == 1
    assert "task.csv" in dialog.pertanyaan[0][2]  # pertanyaan menyebut file yang tertimpa
    assert (tmp_path / "task.csv").read_text(encoding="utf-8-sig").startswith("area,")
    assert len(dialog.info) == 1


def test_ekspor_csv_file_ada_dan_jawaban_tidak_membiarkan_file_lama(app, conn, tmp_path, dialog):
    (tmp_path / "task.csv").write_text("isi lama", encoding="utf-8")
    dialog.folder = str(tmp_path)
    dialog.timpa = QMessageBox.No
    w = CocoWidget(conn)
    w.buka_ekspor()
    assert (tmp_path / "task.csv").read_text(encoding="utf-8") == "isi lama"
    assert not (tmp_path / "daily_log.csv").exists()
    assert dialog.info == [] and dialog.error == []


def test_ekspor_csv_folder_baru_tidak_bertanya(app, conn, tmp_path, dialog):
    dialog.folder = str(tmp_path)
    w = CocoWidget(conn)
    w.buka_ekspor()
    assert dialog.pertanyaan == []


def test_ekspor_csv_gagal_menulis_menampilkan_pesan_error_tanpa_crash(app, conn, tmp_path, dialog):
    dialog.folder = str(tmp_path / "tidak_ada")  # OSError saat membuka file
    w = CocoWidget(conn)
    w.buka_ekspor()  # tidak boleh melempar
    assert dialog.info == []
    assert len(dialog.error) == 1
    teks = dialog.error[0][2]  # QMessageBox.critical(parent, judul, teks)
    assert "tidak_ada" in teks  # lokasi
    assert "Penyebab" in teks
