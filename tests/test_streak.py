from datetime import date

from ctrlcoco import data
from ctrlcoco.streak import get_streak

TODAY = date(2026, 3, 10)


def test_tabel_kosong(conn):
    assert get_streak(conn, today=TODAY) == 0


def test_berturut_turut_termasuk_hari_ini(conn):
    for d in ("2026-03-08", "2026-03-09", "2026-03-10"):
        data.set_daily_log(conn, d, True, True)
    assert get_streak(conn, today=TODAY) == 3


def test_ada_yang_bolong(conn):
    # 7 dan 8 valid, 9 tidak tercatat, 10 valid -> hanya hari ini yang dihitung
    for d in ("2026-03-07", "2026-03-08", "2026-03-10"):
        data.set_daily_log(conn, d, True, True)
    assert get_streak(conn, today=TODAY) == 1


def test_hari_ini_belum_diisi_mulai_dari_kemarin(conn):
    for d in ("2026-03-08", "2026-03-09"):
        data.set_daily_log(conn, d, True, True)
    assert get_streak(conn, today=TODAY) == 2


def test_hari_ini_belum_valid_mulai_dari_kemarin(conn):
    data.set_daily_log(conn, "2026-03-09", True, True)
    data.set_daily_log(conn, "2026-03-10", True, False)
    assert get_streak(conn, today=TODAY) == 1


def test_kemarin_dan_hari_ini_kosong_streak_nol(conn):
    data.set_daily_log(conn, "2026-03-07", True, True)
    assert get_streak(conn, today=TODAY) == 0


def test_hari_dengan_satu_aktivitas_tidak_valid(conn):
    data.set_daily_log(conn, "2026-03-08", True, True)
    data.set_daily_log(conn, "2026-03-09", False, True)
    data.set_daily_log(conn, "2026-03-10", True, True)
    assert get_streak(conn, today=TODAY) == 1


def test_menyeberang_batas_bulan(conn):
    for d in ("2026-02-27", "2026-02-28", "2026-03-01"):
        data.set_daily_log(conn, d, True, True)
    assert get_streak(conn, today=date(2026, 3, 1)) == 3
