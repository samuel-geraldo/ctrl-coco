"""Buat badge cakupan tes (SVG) dari angka TOTAL laporan coverage (#126).

Dipakai job `badge` di .github/workflows/tests.yml:

    python scripts/badge_cakupan.py 99 cakupan.svg
"""
import argparse
import sys
from pathlib import Path

LEBAR_LABEL = 62
LEBAR_ANGKA = 44
TINGGI = 20


def buat_svg(persen: int) -> str:
    """Isi berkas SVG: kotak "cakupan" di kiri dan angka persen di kanan."""
    if not 0 <= persen <= 100:
        raise ValueError(f"Cakupan harus 0 sampai 100, bukan {persen}")
    lebar = LEBAR_LABEL + LEBAR_ANGKA
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{lebar}" height="{TINGGI}"'
        f' role="img" aria-label="cakupan {persen}%">\n'
        f'  <rect width="{LEBAR_LABEL}" height="{TINGGI}" fill="#555"/>\n'
        f'  <rect x="{LEBAR_LABEL}" width="{LEBAR_ANGKA}" height="{TINGGI}" fill="#007ec6"/>\n'
        '  <g fill="#fff" text-anchor="middle"'
        ' font-family="Verdana,DejaVu Sans,sans-serif" font-size="11">\n'
        f'    <text x="{LEBAR_LABEL // 2}" y="14">cakupan</text>\n'
        f'    <text x="{LEBAR_LABEL + LEBAR_ANGKA // 2}" y="14">{persen}%</text>\n'
        "  </g>\n"
        "</svg>\n"
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("persen", type=int, help="angka TOTAL, misalnya 99")
    parser.add_argument("tujuan", type=Path, help="berkas SVG yang ditulis")
    args = parser.parse_args(argv)
    args.tujuan.write_text(buat_svg(args.persen), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
