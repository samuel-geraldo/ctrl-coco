import sqlite3
from datetime import datetime

DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%Y-%m-%d %H:%M"


def _now_text(now: datetime | None) -> str:
    return (now or datetime.now()).strftime(TIME_FORMAT)


def _check_format(value: str, fmt: str, nama: str, contoh: str) -> None:
    """Tolak teks tanggal yang formatnya salah atau tanggalnya tidak ada di kalender."""
    try:
        # Teks diubah jadi tanggal lalu ditulis ulang. Hasilnya harus sama persis,
        # supaya "2026-3-5" (tanpa nol di depan) ikut ditolak.
        cocok = datetime.strptime(value, fmt).strftime(fmt) == value
    except ValueError:
        cocok = False
    if not cocok:
        raise ValueError(
            f"{nama} harus berformat {contoh} dan tanggalnya harus ada di kalender: {value!r}"
        )


def _wajib_isi(teks: str | None, pesan: str) -> str:
    """Buang spasi di awal dan akhir; tolak teks yang kosong atau hanya berisi spasi.

    str.strip() membuang semua jenis spasi, termasuk tab dan baris baru. Database
    menjaga aturan yang sama untuk spasi, tab, baris baru, dan CR (lihat db.CEK_NAMA).
    """
    if teks is None or not teks.strip():
        raise ValueError(pesan)
    return teks.strip()


# --- area ---

def add_area(conn: sqlite3.Connection, name: str) -> int:
    """Tambah area; nama harus unik tanpa membedakan huruf besar-kecil.

    Spasi di awal dan akhir dibuang sebelum disimpan. Mengembalikan id area baru.
    """
    # `with conn:` menyimpan (commit) jika blok selesai, atau membatalkan (rollback)
    # jika ada error, sehingga transaksi tidak pernah dibiarkan terbuka.
    with conn:
        return _sisipkan_area(conn, name)


def _sisipkan_area(conn: sqlite3.Connection, name: str) -> int:
    """Validasi dan INSERT area TANPA commit; pemanggil yang memegang `with conn:`."""
    name = _wajib_isi(name, "Nama area wajib diisi")
    try:
        cur = conn.execute("INSERT INTO area (name) VALUES (?)", (name,))
    except sqlite3.IntegrityError as e:
        # Pesan dipilih dari penyebab sebenarnya. Penyebab yang tidak dikenal
        # diteruskan apa adanya, bukan disamarkan dengan pesan yang keliru.
        if e.sqlite_errorname == "SQLITE_CONSTRAINT_UNIQUE":
            # Kolom name ber-COLLATE NOCASE, jadi `=` di sini juga tanpa beda huruf
            # dan menemukan nama yang sudah tersimpan, misalnya "Kuliah" untuk "kuliah".
            ada = conn.execute("SELECT name FROM area WHERE name = ?", (name,)).fetchone()
            raise ValueError(f"Area sudah ada: {ada[0] if ada else name}") from None
        raise
    return cur.lastrowid


def list_areas(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT id, name FROM area ORDER BY name").fetchall()


# --- task ---

def add_task(
    conn: sqlite3.Connection,
    area_id: int,
    title: str,
    deadline: str | None = None,
    now: datetime | None = None,
) -> int:
    """Tambah task ke sebuah area. deadline opsional, format 'YYYY-MM-DD HH:MM'.

    Spasi di awal dan akhir judul dibuang sebelum disimpan.
    """
    with conn:
        return _sisipkan_task(conn, area_id, title, deadline, now)


def _sisipkan_task(
    conn: sqlite3.Connection,
    area_id: int,
    title: str,
    deadline: str | None,
    now: datetime | None,
) -> int:
    """Validasi dan INSERT task TANPA commit; pemanggil yang memegang `with conn:`."""
    title = _wajib_isi(title, "Judul task wajib diisi")
    if deadline is not None:
        _check_format(deadline, TIME_FORMAT, "deadline", "YYYY-MM-DD HH:MM")
    try:
        cur = conn.execute(
            "INSERT INTO task (area_id, title, deadline, created_at) VALUES (?, ?, ?, ?)",
            (area_id, title, deadline, _now_text(now)),
        )
    except sqlite3.IntegrityError as e:
        # Hanya pelanggaran foreign key yang berarti "area tidak ada". Penyebab lain
        # (misalnya area_id kosong) diteruskan apa adanya, bukan diberi pesan keliru.
        if e.sqlite_errorname == "SQLITE_CONSTRAINT_FOREIGNKEY":
            raise ValueError(f"Area tidak ditemukan: {area_id}") from None
        raise
    return cur.lastrowid


def simpan_task_baru(
    conn: sqlite3.Connection,
    teks_area: str,
    judul: str,
    teks_deadline: str | None,
    now: datetime | None = None,
) -> int:
    """Simpan isian form tambah task: area (lama atau baru) dan task, sekaligus.

    - teks_area yang sama dengan area lama tanpa beda huruf besar-kecil memakai area
      itu; selain itu area baru dibuat.
    - teks_deadline kosong atau hanya spasi berarti tanpa deadline (None); spasi di
      awal dan akhirnya dibuang.
    - Semua atau tidak sama sekali: jika task gagal disimpan, area baru ikut dibatalkan.

    Mengembalikan id task baru.
    """
    nama_area = _wajib_isi(teks_area, "Nama area wajib diisi")
    deadline = teks_deadline.strip() if teks_deadline is not None else ""
    # Satu `with conn:` untuk semuanya. Pembantu _sisipkan_* tidak commit sendiri,
    # jadi error di langkah mana pun membatalkan seluruh transaksi, termasuk area baru.
    with conn:
        # Kolom name ber-COLLATE NOCASE: "kuliah" menemukan "Kuliah", sama seperti UNIQUE.
        ada = conn.execute("SELECT id FROM area WHERE name = ?", (nama_area,)).fetchone()
        area_id = ada[0] if ada else _sisipkan_area(conn, nama_area)
        return _sisipkan_task(conn, area_id, judul, deadline or None, now)


def list_tasks(conn: sqlite3.Connection, status: str | None = None) -> list[sqlite3.Row]:
    """Semua task, atau hanya yang berstatus 'todo' / 'done'."""
    if status is None:
        return conn.execute("SELECT * FROM task ORDER BY id").fetchall()
    return conn.execute("SELECT * FROM task WHERE status = ? ORDER BY id", (status,)).fetchall()


def get_nearest_task(conn: sqlite3.Connection) -> sqlite3.Row | None:
    """Task 'todo' dengan deadline paling awal; None jika tidak ada."""
    return conn.execute(
        "SELECT * FROM task WHERE status = 'todo' AND deadline IS NOT NULL "
        "ORDER BY deadline LIMIT 1"
    ).fetchone()


def complete_task(conn: sqlite3.Connection, task_id: int, now: datetime | None = None) -> None:
    """Tandai task selesai dan isi completed_at. Task yang sudah done dibiarkan."""
    with conn:
        cur = conn.execute(
            "UPDATE task SET status = 'done', completed_at = ? WHERE id = ? AND status = 'todo'",
            (_now_text(now), task_id),
        )
        if cur.rowcount == 0:
            exists = conn.execute("SELECT 1 FROM task WHERE id = ?", (task_id,)).fetchone()
            if not exists:
                raise ValueError(f"Task tidak ditemukan: {task_id}")


# --- daily_log ---

def set_daily_log(
    conn: sqlite3.Connection,
    log_date: str,
    claude_code: bool,
    github: bool,
    note: str | None = None,
) -> None:
    """Catat log sebuah tanggal ('YYYY-MM-DD'); jika sudah ada, barisnya diperbarui.

    note=None membiarkan catatan lama; note="" mengosongkannya.
    """
    _check_format(log_date, DATE_FORMAT, "log_date", "YYYY-MM-DD")
    # `with conn:` seperti di fungsi tulis lain: commit jika berhasil, rollback jika gagal
    # (misalnya database dikunci proses lain), sehingga transaksi tidak tertinggal terbuka.
    with conn:
        conn.execute(
            """
            INSERT INTO daily_log (log_date, claude_code, github, note)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(log_date) DO UPDATE SET
                claude_code = excluded.claude_code,
                github = excluded.github,
                note = COALESCE(excluded.note, daily_log.note)
            """,
            (log_date, int(claude_code), int(github), note),
        )


def get_daily_log(conn: sqlite3.Connection, log_date: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM daily_log WHERE log_date = ?", (log_date,)).fetchone()
