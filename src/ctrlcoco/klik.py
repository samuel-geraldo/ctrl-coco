"""Membedakan klik dari seret. Fungsi murni tanpa Qt."""

# Jarak minimum (piksel) supaya gerakan mouse dianggap seret; sama dengan bawaan Qt
# (QApplication.startDragDistance).
AMBANG_SERET_PX = 10


def adalah_klik(
    posisi_tekan: tuple[int, int],
    posisi_lepas: tuple[int, int],
    ambang: int = AMBANG_SERET_PX,
) -> bool:
    """True bila tombol dilepas cukup dekat dari tempat ditekan (klik, bukan seret).

    Jarak dihitung |dx| + |dy| (manhattan length), sama seperti Qt. Jarak di bawah
    ambang berarti klik; tepat di ambang atau lebih berarti seret.
    """
    dx = posisi_lepas[0] - posisi_tekan[0]
    dy = posisi_lepas[1] - posisi_tekan[1]
    return abs(dx) + abs(dy) < ambang
