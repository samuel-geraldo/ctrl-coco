from datetime import datetime

import pytest

from ctrlcoco import data
from ctrlcoco.mood import get_mood

NOW = datetime(2026, 3, 10, 9, 30)
HARI_INI = "2026-03-10"


@pytest.fixture
def area_id(conn):
    return data.add_area(conn, "Kuliah")


# --- tidur ---

def test_tidak_ada_data_tidur(conn):
    assert get_mood(conn, NOW) == "tidur"


@pytest.mark.parametrize("claude_code, github", [(True, False), (False, True), (False, False)])
def test_log_belum_lengkap_tidur(conn, claude_code, github):
    data.set_daily_log(conn, HARI_INI, claude_code, github)
    assert get_mood(conn, NOW) == "tidur"


def test_log_valid_kemarin_saja_tidur(conn):
    data.set_daily_log(conn, "2026-03-09", True, True)
    assert get_mood(conn, NOW) == "tidur"


# --- senang ---

def test_hari_ini_valid_senang(conn):
    data.set_daily_log(conn, HARI_INI, True, True)
    assert get_mood(conn, NOW) == "senang"


# --- waspada ---

def test_deadline_kurang_dari_24_jam_waspada(conn, area_id):
    data.add_task(conn, area_id, "Laporan", deadline="2026-03-11 09:29", now=NOW)
    assert get_mood(conn, NOW) == "waspada"


def test_deadline_sudah_lewat_waspada(conn, area_id):
    data.add_task(conn, area_id, "Terlambat", deadline="2026-03-08 12:00", now=NOW)
    assert get_mood(conn, NOW) == "waspada"


def test_deadline_tepat_24_jam_belum_waspada(conn, area_id):
    data.add_task(conn, area_id, "Besok", deadline="2026-03-11 09:30", now=NOW)
    assert get_mood(conn, NOW) == "tidur"


def test_deadline_masih_jauh_tidak_waspada(conn, area_id):
    data.add_task(conn, area_id, "Minggu depan", deadline="2026-03-17 09:30", now=NOW)
    assert get_mood(conn, NOW) == "tidur"


def test_task_tanpa_deadline_tidak_waspada(conn, area_id):
    data.add_task(conn, area_id, "Kapan-kapan", now=NOW)
    assert get_mood(conn, NOW) == "tidur"


def test_task_done_tidak_waspada(conn, area_id):
    task_id = data.add_task(conn, area_id, "Selesai", deadline="2026-03-10 12:00", now=NOW)
    data.complete_task(conn, task_id, now=NOW)
    assert get_mood(conn, NOW) == "tidur"


def test_satu_task_dekat_di_antara_task_jauh_waspada(conn, area_id):
    data.add_task(conn, area_id, "Jauh", deadline="2026-03-20 10:00", now=NOW)
    data.add_task(conn, area_id, "Dekat", deadline="2026-03-10 18:00", now=NOW)
    data.add_task(conn, area_id, "Tanpa deadline", now=NOW)
    assert get_mood(conn, NOW) == "waspada"


# --- benturan antar aturan ---

def test_waspada_menang_atas_senang(conn, area_id):
    data.set_daily_log(conn, HARI_INI, True, True)
    data.add_task(conn, area_id, "Laporan", deadline="2026-03-10 18:00", now=NOW)
    assert get_mood(conn, NOW) == "waspada"


def test_waspada_menang_atas_tidur(conn, area_id):
    data.set_daily_log(conn, HARI_INI, True, False)
    data.add_task(conn, area_id, "Laporan", deadline="2026-03-10 18:00", now=NOW)
    assert get_mood(conn, NOW) == "waspada"


def test_hari_valid_dan_deadline_tepat_24_jam_senang(conn, area_id):
    data.set_daily_log(conn, HARI_INI, True, True)
    data.add_task(conn, area_id, "Besok", deadline="2026-03-11 09:30", now=NOW)
    assert get_mood(conn, NOW) == "senang"


def test_hari_valid_dan_task_dekat_sudah_done_senang(conn, area_id):
    data.set_daily_log(conn, HARI_INI, True, True)
    task_id = data.add_task(conn, area_id, "Selesai", deadline="2026-03-10 12:00", now=NOW)
    data.complete_task(conn, task_id, now=NOW)
    assert get_mood(conn, NOW) == "senang"


def test_hari_valid_dan_task_tanpa_deadline_senang(conn, area_id):
    data.set_daily_log(conn, HARI_INI, True, True)
    data.add_task(conn, area_id, "Kapan-kapan", now=NOW)
    assert get_mood(conn, NOW) == "senang"
