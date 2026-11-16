from datetime import date, datetime, timedelta

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap

from ctrlcoco import data
from ctrlcoco.mood import MOODS
from ctrlcoco.sprites import PLACEHOLDER_COLORS
from ctrlcoco.widget import ANIMATION_INTERVAL_MS, REFRESH_INTERVAL_MS, CocoWidget

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
    assert w.streak_label.text() == "Streak: 0 hari"
    assert w.task_label.text() == "Tidak ada task berdeadline"


def test_widget_menampilkan_streak_dan_task_terdekat(app, conn):
    today = date.today()
    data.set_daily_log(conn, today.isoformat(), True, True)
    data.set_daily_log(conn, (today - timedelta(days=1)).isoformat(), True, True)
    area_id = data.add_area(conn, "Kuliah")
    data.add_task(conn, area_id, "Laporan", deadline="2099-01-01 10:00")
    w = CocoWidget(conn)
    assert w.streak_label.text() == "Streak: 2 hari"
    assert "Laporan" in w.task_label.text()
    assert "2099-01-01 10:00" in w.task_label.text()


def test_widget_tanpa_bingkai_dan_selalu_di_atas(app, conn):
    w = CocoWidget(conn)
    assert w.windowFlags() & Qt.FramelessWindowHint
    assert w.windowFlags() & Qt.WindowStaysOnTopHint


def test_widget_latar_transparan_dan_teks_berpanel(app, conn):
    w = CocoWidget(conn)
    assert w.testAttribute(Qt.WA_TranslucentBackground)
    for label in (w.streak_label, w.task_label):
        assert "color: white" in label.styleSheet()
        assert "rgba(0, 0, 0" in label.styleSheet()


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
    assert w.streak_label.text() == "Streak: 1 hari"


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
    assert w.streak_label.text() == "Streak: 0 hari"

    data.set_daily_log(conn, date.today().isoformat(), True, True)
    w.refresh_timer.timeout.emit()  # satu detak timer, tanpa menunggu
    assert w.streak_label.text() == "Streak: 1 hari"
    assert w.mood == "senang"
