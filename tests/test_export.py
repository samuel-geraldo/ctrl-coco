"""Tes ekspor CSV tanpa layar: database di memori dan folder sementara (tmp_path)."""
import csv
from datetime import datetime

import pytest

from ctrlcoco import data, export

HEADER_TASK = ["area", "judul", "tenggat", "status", "dibuat", "selesai"]
HEADER_LOG = ["tanggal", "claude_code", "github", "catatan"]


def baca(path):
    """Baca CSV seperti spreadsheet: UTF-8 dengan BOM, tiap baris jadi dict."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def baca_header(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return next(csv.reader(f))


def test_ekspor_membuat_dua_file_bernama_tetap(conn, tmp_path):
    file_task, file_log = export.ekspor_csv(conn, tmp_path)
    assert file_task == tmp_path / "task.csv"
    assert file_log == tmp_path / "daily_log.csv"
    assert file_task.is_file() and file_log.is_file()


def test_header_sesuai_yang_didokumentasikan(conn, tmp_path):
    file_task, file_log = export.ekspor_csv(conn, tmp_path)
    assert baca_header(file_task) == HEADER_TASK
    assert baca_header(file_log) == HEADER_LOG


def test_database_kosong_hanya_berisi_header(conn, tmp_path):
    file_task, file_log = export.ekspor_csv(conn, tmp_path)
    assert baca(file_task) == []
    assert baca(file_log) == []


def test_file_diawali_bom_agar_excel_membacanya_sebagai_utf8(conn, tmp_path):
    file_task, file_log = export.ekspor_csv(conn, tmp_path)
    assert file_task.read_bytes().startswith(b"\xef\xbb\xbf")
    assert file_log.read_bytes().startswith(b"\xef\xbb\xbf")


def test_task_memuat_nama_area_bukan_id(conn, tmp_path):
    area_id = data.add_area(conn, "Kuliah")
    data.add_task(conn, area_id, "Laporan", "2026-03-10 23:59", now=datetime(2026, 3, 1, 8, 0))
    file_task, _ = export.ekspor_csv(conn, tmp_path)
    assert baca(file_task) == [
        {
            "area": "Kuliah",
            "judul": "Laporan",
            "tenggat": "2026-03-10 23:59",
            "status": "belum",
            "dibuat": "2026-03-01 08:00",
            "selesai": "",
        }
    ]


def test_task_selesai_ditulis_selesai_dengan_waktunya(conn, tmp_path):
    area_id = data.add_area(conn, "Kuliah")
    task_id = data.add_task(conn, area_id, "Laporan", now=datetime(2026, 3, 1, 8, 0))
    data.complete_task(conn, task_id, now=datetime(2026, 3, 2, 9, 30))
    file_task, _ = export.ekspor_csv(conn, tmp_path)
    (baris,) = baca(file_task)
    assert baris["status"] == "selesai"
    assert baris["selesai"] == "2026-03-02 09:30"


def test_nilai_kosong_menjadi_sel_kosong(conn, tmp_path):
    area_id = data.add_area(conn, "Kuliah")
    data.add_task(conn, area_id, "Tanpa tenggat")  # deadline NULL
    data.set_daily_log(conn, "2026-03-01", True, False)  # note NULL
    file_task, file_log = export.ekspor_csv(conn, tmp_path)
    assert baca(file_task)[0]["tenggat"] == ""
    assert baca(file_log)[0]["catatan"] == ""


def test_log_ditulis_ya_tidak(conn, tmp_path):
    data.set_daily_log(conn, "2026-03-01", True, False, "belajar")
    data.set_daily_log(conn, "2026-03-02", False, True)
    _, file_log = export.ekspor_csv(conn, tmp_path)
    assert baca(file_log) == [
        {"tanggal": "2026-03-01", "claude_code": "ya", "github": "tidak", "catatan": "belajar"},
        {"tanggal": "2026-03-02", "claude_code": "tidak", "github": "ya", "catatan": ""},
    ]


def test_teks_berisi_koma_kutip_dan_baris_baru_tetap_utuh(conn, tmp_path):
    judul = 'Beli "kopi", gula\nsusu'
    catatan = 'Rapat, "penting"\nlanjut besok'
    area_id = data.add_area(conn, "Rumah, dan kantor")
    data.add_task(conn, area_id, judul)
    data.set_daily_log(conn, "2026-03-01", True, True, catatan)
    file_task, file_log = export.ekspor_csv(conn, tmp_path)
    (baris_task,) = baca(file_task)
    (baris_log,) = baca(file_log)
    assert baris_task["area"] == "Rumah, dan kantor"
    assert baris_task["judul"] == judul
    assert baris_log["catatan"] == catatan


def test_huruf_non_ascii_tetap_utuh(conn, tmp_path):
    judul = "Rapat café — 会議 😀"
    area_id = data.add_area(conn, "Bahasa Inggris")
    data.add_task(conn, area_id, judul)
    data.set_daily_log(conn, "2026-03-01", True, True, "résumé")
    file_task, file_log = export.ekspor_csv(conn, tmp_path)
    assert baca(file_task)[0]["judul"] == judul
    assert baca(file_log)[0]["catatan"] == "résumé"


def test_baris_task_berurutan_menurut_id_dan_log_menurut_tanggal(conn, tmp_path):
    area_id = data.add_area(conn, "Kuliah")
    for judul in ("Pertama", "Kedua", "Ketiga"):
        data.add_task(conn, area_id, judul)
    data.set_daily_log(conn, "2026-03-03", True, True)
    data.set_daily_log(conn, "2026-03-01", True, True)
    data.set_daily_log(conn, "2026-03-02", True, True)
    file_task, file_log = export.ekspor_csv(conn, tmp_path)
    assert [b["judul"] for b in baca(file_task)] == ["Pertama", "Kedua", "Ketiga"]
    assert [b["tanggal"] for b in baca(file_log)] == ["2026-03-01", "2026-03-02", "2026-03-03"]


def test_jumlah_baris_sama_dengan_isi_tabel(conn, tmp_path):
    area_id = data.add_area(conn, "Kuliah")
    for i in range(5):
        data.add_task(conn, area_id, f"Task {i}")
    for hari in range(1, 4):
        data.set_daily_log(conn, f"2026-03-0{hari}", True, False)
    file_task, file_log = export.ekspor_csv(conn, tmp_path)
    assert len(baca(file_task)) == len(data.list_tasks(conn)) == 5
    assert len(baca(file_log)) == 3


def test_file_yang_sudah_ada_kosong_pada_folder_baru(tmp_path):
    assert export.file_yang_sudah_ada(tmp_path) == []


def test_file_yang_sudah_ada_menyebut_hanya_yang_benar_ada(tmp_path):
    (tmp_path / "task.csv").write_text("lama", encoding="utf-8")
    assert export.file_yang_sudah_ada(tmp_path) == [tmp_path / "task.csv"]
    (tmp_path / "daily_log.csv").write_text("lama", encoding="utf-8")
    assert export.file_yang_sudah_ada(tmp_path) == [
        tmp_path / "task.csv",
        tmp_path / "daily_log.csv",
    ]


def test_file_lama_ditimpa_oleh_ekspor_baru(conn, tmp_path):
    (tmp_path / "task.csv").write_text("isi lama", encoding="utf-8")
    area_id = data.add_area(conn, "Kuliah")
    data.add_task(conn, area_id, "Baru")
    file_task, _ = export.ekspor_csv(conn, tmp_path)
    assert baca(file_task)[0]["judul"] == "Baru"


def test_folder_yang_tidak_ada_melempar_oserror(conn, tmp_path):
    with pytest.raises(OSError):
        export.ekspor_csv(conn, tmp_path / "tidak_ada")
