"""Penjaga README (#77): susunan bagian, kalimat Privasi, peta jalan, dan gambar yang ada."""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
README = (REPO / "README.md").read_text(encoding="utf-8")
# Isi blok kode dibuang: baris "## ..." di dalamnya (komentar skrip) bukan judul.
TANPA_KODE = re.sub(r"```.*?```", "", README, flags=re.DOTALL)


def judul_bagian():
    """Judul tingkat dua (`## ...`) menurut urutan muncul."""
    return re.findall(r"^## (.+)$", TANPA_KODE, flags=re.MULTILINE)


def isi_bagian(judul):
    pola = rf"^## {re.escape(judul)}$(.*?)(?=^## |\Z)"
    cocok = re.search(pola, TANPA_KODE, re.MULTILINE | re.DOTALL)
    assert cocok, f"bagian {judul!r} tidak ada"
    return cocok.group(1)


def test_susunan_bagian_mengikuti_issue_77():
    urutan = ["Fitur", "Privasi", "Cara instal", "FAQ", "Cara build dan tes", "Lisensi"]
    judul = judul_bagian()
    posisi = [judul.index(j) for j in urutan]
    assert posisi == sorted(posisi)


def test_peta_jalan_ada_sebelum_lisensi():
    judul = judul_bagian()
    assert judul.index("Peta jalan") < judul.index("Lisensi")


def test_privasi_memuat_kalimat_wajib():
    assert "semua data lokal, tanpa akun dan jaringan" in isi_bagian("Privasi").lower()


def peta_per_versi():
    """Butir peta jalan tiap versi sebagai daftar (tanda centang, teks)."""
    v010, v020 = isi_bagian("Peta jalan").split("**v0.2.0**", 1)
    return [re.findall(r"^- \[([ x])\] (.+)$", t, re.MULTILINE) for t in (v010, v020)]


def test_peta_jalan_memuat_tenggat_tiap_versi():
    peta = isi_bagian("Peta jalan")
    assert "**v0.1.0** (tenggat 9 Desember 2026)" in peta
    assert "**v0.2.0** (tenggat 19 Desember 2026)" in peta
    assert "(opsional)" not in peta  # penanda lama sebelum milestone ada


@pytest.mark.parametrize(
    "fitur",
    [
        "Tahap 6: jendela Tinjauan mingguan",
        "waktu penyelesaian",
        "SQL view",
        "Batalkan status selesai dan isi log",
        "Kelas dasar form",
        "cakupan tes",
    ],
)
def test_v010_memuat_fitur_yang_sudah_ada_di_main_dan_tercentang(fitur):
    v010, _ = peta_per_versi()
    assert [centang for centang, teks in v010 if fitur in teks] == ["x"]


def test_v010_menyisakan_empat_butir_yang_belum_selesai():
    v010, _ = peta_per_versi()
    belum = [teks for centang, teks in v010 if centang == " "]
    assert len(belum) == 4
    for teks, kata in zip(belum, ("Sprite", "tangkapan layar", "CHANGELOG", "Release v0.1.0"),
                          strict=True):
        assert kata in teks


def test_v020_hanya_berisi_yang_belum_dikerjakan():
    _, v020 = peta_per_versi()
    assert v020 == [
        (" ", "Opsi jalan otomatis saat Windows menyala"),
        (" ", "Studi kasus portofolio"),
    ]


def test_peta_jalan_hanya_berisi_kotak_centang():
    peta = isi_bagian("Peta jalan")
    butir = [b for b in peta.splitlines() if b.startswith("- ")]
    assert butir
    assert all(re.match(r"- \[[ x]\] ", b) for b in butir)


def test_semua_gambar_relatif_ada_filenya():
    # Gambar rusak tampil sebagai ikon patah di halaman repo; tautan ke berkas yang
    # belum ada dicegah di sini.
    markdown = re.findall(r"!\[[^\]]*\]\(([^)\s]+)", README)
    html = re.findall(r'<img[^>]*src="([^"]+)"', README)
    relatif = [s for s in markdown + html if not s.startswith(("http://", "https://"))]
    assert relatif
    for s in relatif:
        assert (REPO / s).is_file(), s


def test_tautan_anchor_internal_menunjuk_ke_judul_yang_ada():
    def slug(judul):
        return re.sub(r"[^\w\- ]", "", judul.lower()).strip().replace(" ", "-")

    judul = {slug(j) for j in re.findall(r"^#{2,3} (.+)$", TANPA_KODE, flags=re.MULTILINE)}
    for anchor in re.findall(r"\]\(#([^)]+)\)", README):
        assert anchor in judul, anchor
