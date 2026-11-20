"""Posisi form di samping Coco. Fungsi murni tanpa Qt.

Semua persegi berupa tuple (x, y, lebar, tinggi) dalam koordinat layar.
"""

JARAK_FORM_PX = 8  # celah antara Coco dan form

Kotak = tuple[int, int, int, int]


def posisi_form(
    coco: Kotak, form: Kotak, layar: Kotak, jarak: int = JARAK_FORM_PX
) -> tuple[int, int]:
    """Pojok kiri atas (x, y) untuk form supaya tidak menutupi Coco.

    Kanan Coco bila muat; bila tidak, kiri Coco; bila dua-duanya tidak muat, sisi yang
    ruangnya lebih besar (sama besar: kanan). Vertikal sejajar atas Coco. Hasilnya
    dijepit supaya form utuh di dalam `layar`. Dari `form` hanya lebar dan tinggi
    yang dipakai.
    """
    coco_x, coco_y, coco_lebar, _ = coco
    _, _, form_lebar, form_tinggi = form
    layar_x, layar_y, layar_lebar, layar_tinggi = layar

    x_kanan = coco_x + coco_lebar + jarak
    x_kiri = coco_x - jarak - form_lebar
    ruang_kanan = layar_x + layar_lebar - x_kanan
    ruang_kiri = coco_x - jarak - layar_x

    if form_lebar <= ruang_kanan:
        x = x_kanan
    elif form_lebar <= ruang_kiri:
        x = x_kiri
    else:
        x = x_kanan if ruang_kanan >= ruang_kiri else x_kiri

    return (
        _jepit(x, layar_x, layar_lebar, form_lebar),
        _jepit(coco_y, layar_y, layar_tinggi, form_tinggi),
    )


def _jepit(nilai: int, awal: int, panjang_layar: int, panjang_form: int) -> int:
    # Geser masuk supaya form utuh di layar. Bila form lebih besar dari layar, tepi
    # awalnya (kiri atau atas: judul dan tombol) yang diutamakan terlihat.
    return max(awal, min(nilai, awal + panjang_layar - panjang_form))
