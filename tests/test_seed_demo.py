import importlib.util
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from ctrlcoco import data, db
from ctrlcoco.mood import get_mood
from ctrlcoco.streak import get_streak

_spec = importlib.util.spec_from_file_location(
    "seed_demo", Path(__file__).resolve().parents[1] / "scripts" / "seed_demo.py"
)
seed_demo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed_demo)

TODAY = datetime(2026, 11, 14, 9, 0)
AREA_DEMO = ["Bahasa Inggris", "Kuliah", "Olahraga", "Portofolio"]


@pytest.fixture
def demo(conn):
    """Database di memori yang sudah diisi data demo untuk TODAY."""
    assert seed_demo.seed(conn, today=TODAY) is True
    return conn


def isi_semua(conn):
    """Isi ketiga tabel, untuk membandingkan dua database."""
    return [
        [tuple(r) for r in conn.execute(f"SELECT * FROM {tabel} ORDER BY 1").fetchall()]
        for tabel in ("area", "task", "daily_log")
    ]


def waktu(teks):
    return datetime.strptime(teks, data.TIME_FORMAT)


def hari_valid(conn):
    rows = conn.execute(
        "SELECT log_date FROM daily_log WHERE claude_code = 1 AND github = 1"
    ).fetchall()
    return {date.fromisoformat(r["log_date"]) for r in rows}


def streak_terpanjang(hari):
    terpanjang = sekarang = 0
    for h in sorted(hari):
        sekarang = sekarang + 1 if h - timedelta(days=1) in hari else 1
        terpanjang = max(terpanjang, sekarang)
    return terpanjang


# --- determinisme ---

def test_dua_kali_seed_dengan_today_sama_hasilnya_identik(demo):
    lain = db.connect(":memory:")
    db.init_db(lain)
    seed_demo.seed(lain, today=TODAY)
    assert isi_semua(lain) == isi_semua(demo)
    lain.close()


def test_jam_berbeda_di_tanggal_sama_hasilnya_identik(demo):
    lain = db.connect(":memory:")
    db.init_db(lain)
    seed_demo.seed(lain, today=TODAY.replace(hour=0, minute=1))
    assert isi_semua(lain) == isi_semua(demo)
    lain.close()


# --- area dan task ---

def test_empat_area_dengan_completion_rate_berbeda(demo):
    rows = demo.execute(
        "SELECT area.name, SUM(task.status = 'done'), COUNT(*)"
        " FROM task JOIN area ON area.id = task.area_id GROUP BY area.name ORDER BY area.name"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        ("Bahasa Inggris", 1, 3),
        ("Kuliah", 6, 8),
        ("Olahraga", 4, 4),
        ("Portofolio", 3, 6),
    ]


def test_task_ada_di_setiap_kategori(demo):
    tasks = data.list_tasks(demo)
    done = [t for t in tasks if t["status"] == "done"]
    todo = [t for t in tasks if t["status"] == "todo"]
    tepat_waktu = [t for t in done if t["deadline"] and t["completed_at"] <= t["deadline"]]
    terlambat = [t for t in done if t["deadline"] and t["completed_at"] > t["deadline"]]
    assert len(tasks) == 21
    assert len(tepat_waktu) == 9
    assert len(terlambat) == 3
    assert sum(1 for t in tepat_waktu if t["completed_at"] == t["deadline"]) == 1
    assert sum(1 for t in done if t["deadline"] is None) == 2
    assert sum(1 for t in todo if t["deadline"] is not None) == 5
    assert sum(1 for t in todo if t["deadline"] is None) == 2


def test_task_terdekat_deadline_hari_ini_dan_coco_waspada(demo):
    terdekat = data.get_nearest_task(demo)
    assert terdekat["title"] == "Laporan akhir praktikum"
    assert terdekat["deadline"] == "2026-11-14 23:59"
    # Deadline 23:59 hari ini selalu kurang dari 24 jam dari jam berapa pun di hari itu.
    for jam in (0, 9, 23):
        assert get_mood(demo, TODAY.replace(hour=jam)) == "waspada"


def test_tidak_ada_todo_yang_sudah_terlambat(demo):
    awal_hari_ini = TODAY.replace(hour=0, minute=0)
    for t in data.list_tasks(demo, status="todo"):
        assert t["deadline"] is None or waktu(t["deadline"]) >= awal_hari_ini


# --- waktu ---

def test_tidak_ada_waktu_di_masa_depan_dan_semua_dalam_60_hari(demo):
    awal_hari_ini = TODAY.replace(hour=0, minute=0)
    batas_awal = awal_hari_ini - timedelta(days=59)
    for t in data.list_tasks(demo):
        # Paling lambat kemarin: tetap aman walau seed dijalankan pukul 00:01.
        assert batas_awal <= waktu(t["created_at"]) < awal_hari_ini
        if t["completed_at"] is not None:
            assert waktu(t["completed_at"]) < awal_hari_ini


def test_completed_at_tidak_lebih_awal_dari_created_at(demo):
    for t in data.list_tasks(demo, status="done"):
        assert t["completed_at"] >= t["created_at"]


# --- log harian dan streak ---

def test_log_harian_dalam_60_hari_sampai_today(demo):
    tanggal = [date.fromisoformat(r[0]) for r in demo.execute("SELECT log_date FROM daily_log")]
    assert len(tanggal) == 52
    assert all(TODAY.date() - timedelta(days=59) <= t <= TODAY.date() for t in tanggal)
    assert data.get_daily_log(demo, "2026-11-14") is None  # hari ini belum diisi


def test_streak_sekarang_6_dan_terpanjang_14(demo):
    valid = hari_valid(demo)
    assert len(valid) == 48
    assert get_streak(demo, today=TODAY.date()) == 6
    assert streak_terpanjang(valid) == 14


# --- lolos aturan database ---

def test_semua_data_lolos_aturan_database(demo):
    assert demo.execute("PRAGMA foreign_key_check").fetchall() == []
    for t in data.list_tasks(demo):
        assert t["title"].strip() == t["title"] and t["title"]
        for kolom in ("deadline", "created_at", "completed_at"):
            if t[kolom] is not None:
                assert waktu(t[kolom]).strftime(data.TIME_FORMAT) == t[kolom]
    for r in demo.execute("SELECT log_date FROM daily_log"):
        assert date.fromisoformat(r[0]).isoformat() == r[0]
    judul = [t["title"] for t in data.list_tasks(demo)]
    assert len(set(judul)) == len(judul)
    assert [a["name"] for a in data.list_areas(demo)] == AREA_DEMO


# --- penjaga: database yang sudah berisi tidak ditimpa ---

def test_seed_tidak_menimpa_database_berisi(conn):
    data.add_area(conn, "Milik saya")
    assert seed_demo.seed(conn) is False
    assert [a["name"] for a in data.list_areas(conn)] == ["Milik saya"]


def test_seed_tidak_menimpa_database_yang_hanya_berisi_log(conn):
    # Streak bisa dicatat tanpa pernah membuat area; log seperti ini tidak boleh tertimpa.
    data.set_daily_log(conn, "2026-11-14", True, True, note="catatan asli")
    assert seed_demo.seed(conn, today=TODAY) is False
    assert data.get_daily_log(conn, "2026-11-14")["note"] == "catatan asli"
    assert data.list_areas(conn) == []


# --- konfirmasi sebelum menulis ke database harian ---

@pytest.fixture
def folder_appdata(tmp_path, monkeypatch):
    """APPDATA dan folder kerja dialihkan ke tmp_path, supaya database harian asli
    tidak tersentuh dan tidak ada demo.db yang tercipta di folder repo."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    return tmp_path / "CtrlCoco"


def ganti_input(monkeypatch, jawaban):
    """Ganti input(): langsung menjawab `jawaban` dan mencatat setiap pertanyaan."""
    ditanya = []

    def input_tiruan(prompt=""):
        ditanya.append(prompt)
        return jawaban

    monkeypatch.setattr("builtins.input", input_tiruan)
    return ditanya


def nama_area_di(path):
    c = db.connect(path)
    nama = [a["name"] for a in data.list_areas(c)]
    c.close()
    return nama


def test_seed_demo_jawab_n_tidak_menulis_apa_pun(folder_appdata, monkeypatch):
    harian = folder_appdata / "ctrlcoco.db"
    ditanya = ganti_input(monkeypatch, "n")
    assert seed_demo.main(["--db", str(harian)]) == 1
    assert len(ditanya) == 1
    assert not harian.exists()


def test_seed_demo_jawab_y_menulis_data(folder_appdata, monkeypatch):
    harian = folder_appdata / "ctrlcoco.db"
    ditanya = ganti_input(monkeypatch, "y")
    assert seed_demo.main(["--db", str(harian)]) == 0
    assert len(ditanya) == 1
    assert nama_area_di(harian) == AREA_DEMO


def test_seed_demo_tanpa_db_tidak_bertanya(folder_appdata, monkeypatch):
    ditanya = ganti_input(monkeypatch, "y")
    assert seed_demo.main([]) == 0
    assert ditanya == []
    assert nama_area_di(folder_appdata / "demo.db") == AREA_DEMO
    assert not (folder_appdata / "ctrlcoco.db").exists()
