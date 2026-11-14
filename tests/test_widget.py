import os
from datetime import date, timedelta

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ctrlcoco import data
from ctrlcoco.widget import CocoWidget


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


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
