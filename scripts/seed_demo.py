r"""Isi database dengan data contoh 60 hari (area, task, log harian) untuk mencoba widget.

Pakai:
    $env:PYTHONPATH = "src"
    python scripts/seed_demo.py              # menulis ke %APPDATA%\CtrlCoco\demo.db
    python -m ctrlcoco --db "$env:APPDATA\CtrlCoco\demo.db"   # lihat hasilnya

Secara bawaan skrip memakai database terpisah (demo.db), bukan database harian.
Jika --db menunjuk ke database harian, skrip meminta konfirmasi dulu.
"""
import argparse
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

from ctrlcoco import data, db

# Data demo berupa tabel tetap. Hari ditulis relatif terhadap hari ini (-3 = tiga hari
# lalu, 5 = lima hari lagi), jadi tanggal yang sama selalu menghasilkan isi yang sama.
# Semua nama fiktif.

AREA_DEMO = ("Kuliah", "Portofolio", "Olahraga", "Bahasa Inggris")

# (area, judul, dibuat, deadline atau None, selesai atau None); waktu = (hari, "HH:MM").
# Dibuat dan selesai paling lambat kemarin, supaya tidak ada waktu di masa depan.
TASK_DEMO = (
    # Kuliah: 8 task, 6 selesai (75%); 5 tepat waktu, 1 terlambat.
    ("Kuliah", "Ringkasan bab 1 statistika", (-58, "09:00"), (-55, "23:59"), (-56, "20:00")),
    ("Kuliah", "Tugas kalkulus minggu 2", (-52, "09:00"), (-48, "23:59"), (-48, "23:59")),
    ("Kuliah", "Laporan praktikum jaringan", (-45, "09:00"), (-40, "23:59"), (-39, "08:00")),
    ("Kuliah", "Kuis basis data", (-35, "09:00"), (-30, "08:00"), (-31, "21:00")),
    ("Kuliah", "Makalah etika teknologi", (-28, "09:00"), (-21, "23:59"), (-22, "19:00")),
    ("Kuliah", "Presentasi kelompok", (-18, "09:00"), (-12, "13:00"), (-12, "09:00")),
    # Deadline hari ini 23:59: task terdekat, Coco waspada.
    ("Kuliah", "Laporan akhir praktikum", (-10, "09:00"), (0, "23:59"), None),
    ("Kuliah", "Belajar untuk ujian tengah semester", (-5, "09:00"), (5, "08:00"), None),
    # Portofolio: 6 task, 3 selesai (50%); 1 tanpa deadline, 1 tepat waktu, 1 terlambat.
    ("Portofolio", "Rapikan README proyek lama", (-50, "09:00"), None, (-44, "15:00")),
    ("Portofolio", "Tulis artikel blog pertama", (-40, "09:00"), (-33, "20:00"), (-34, "18:00")),
    ("Portofolio", "Perbarui foto profil GitHub", (-26, "09:00"), (-24, "20:00"), (-23, "11:00")),
    ("Portofolio", "Buat halaman portofolio", (-15, "09:00"), (3, "20:00"), None),
    ("Portofolio", "Rekam video demo aplikasi", (-8, "09:00"), (10, "20:00"), None),
    ("Portofolio", "Daftar ide proyek berikutnya", (-4, "09:00"), None, None),
    # Olahraga: 4 task, semua selesai (100%); 1 tanpa deadline, 3 tepat waktu.
    ("Olahraga", "Lari 5 km", (-57, "09:00"), (-54, "07:00"), (-54, "06:30")),
    ("Olahraga", "Daftar kelas renang", (-42, "09:00"), None, (-41, "16:00")),
    ("Olahraga", "Jalan pagi 7 hari", (-27, "09:00"), (-20, "08:00"), (-21, "07:30")),
    ("Olahraga", "Peregangan setelah belajar", (-13, "09:00"), (-9, "21:00"), (-10, "20:00")),
    # Bahasa Inggris: 3 task, 1 selesai (33%) dan terlambat.
    ("Bahasa Inggris", "Hafalkan 50 kosakata baru", (-36, "09:00"), (-29, "21:00"), (-27, "20:00")),
    ("Bahasa Inggris", "Latihan menulis esai pendek", (-11, "09:00"), (14, "21:00"), None),
    ("Bahasa Inggris", "Tonton film tanpa subtitle", (-6, "09:00"), None, None),
)

# Log harian untuk hari ke-59 sampai hari ini (angka = berapa hari lalu). Selain yang
# disebut di sini, setiap hari valid (Claude Code dan GitHub dicentang).
HARI_LOG = 60
LOG_BOLONG = {55, 51, 46, 30, 25, 14, 7, 0}  # tanpa baris; hari ini belum diisi
LOG_SETENGAH = {47: (True, False), 31: (False, True), 20: (False, True), 9: (True, False)}
# Hasilnya: hari ke-45 s.d. 32 valid beruntun (streak terpanjang 14), hari ke-6 s.d. 1
# valid (streak sekarang 6; mengisi log hari ini menjadikannya 7).


def demo_db_path() -> Path:
    return db.default_db_path().with_name("demo.db")


def _waktu(today: datetime, hari_jam: tuple[int, str]) -> datetime:
    hari, jam = hari_jam
    return datetime.combine(today.date() + timedelta(days=hari), time.fromisoformat(jam))


def seed(conn, today: datetime | None = None) -> bool:
    """Isi data contoh 60 hari sampai `today`.

    Mengembalikan False (tanpa menulis apa pun) jika database sudah berisi data.
    """
    # Periksa ketiga tabel: log harian bisa ada walaupun area belum pernah dibuat.
    sudah_berisi = conn.execute(
        "SELECT EXISTS (SELECT 1 FROM area)"
        " OR EXISTS (SELECT 1 FROM task)"
        " OR EXISTS (SELECT 1 FROM daily_log)"
    ).fetchone()[0]
    if sudah_berisi:
        return False
    today = today or datetime.now()

    # Semua ditulis lewat fungsi di data.py, jadi lolos validasi dan CHECK skema.
    area_id = {nama: data.add_area(conn, nama) for nama in AREA_DEMO}
    for area, judul, dibuat, deadline, selesai in TASK_DEMO:
        teks_deadline = _waktu(today, deadline).strftime(data.TIME_FORMAT) if deadline else None
        task_id = data.add_task(
            conn, area_id[area], judul, teks_deadline, now=_waktu(today, dibuat)
        )
        if selesai is not None:
            data.complete_task(conn, task_id, now=_waktu(today, selesai))

    for hari_lalu in range(HARI_LOG - 1, -1, -1):
        if hari_lalu in LOG_BOLONG:
            continue
        claude_code, github = LOG_SETENGAH.get(hari_lalu, (True, True))
        tanggal = (today.date() - timedelta(days=hari_lalu)).isoformat()
        data.set_daily_log(conn, tanggal, claude_code, github)
    return True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--db", help="path database tujuan (bawaan: demo.db di folder AppData)")
    args = parser.parse_args(argv)

    target = Path(args.db) if args.db else demo_db_path()
    if target.resolve() == db.default_db_path().resolve():
        answer = input(f"{target} adalah database harian Anda. Tulis data contoh ke sana? [y/N] ")
        if answer.strip().lower() != "y":
            print("Dibatalkan.")
            return 1

    conn = db.connect(target)
    db.init_db(conn)
    if seed(conn):
        print(f"Data contoh ditulis ke {target}")
    else:
        print(f"{target} sudah berisi data; tidak ada yang diubah.")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
