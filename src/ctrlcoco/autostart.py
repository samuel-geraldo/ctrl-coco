"""Jalan otomatis saat Windows menyala: satu entri di kunci Run milik pengguna.

Logika di sini tanpa Qt. Registri dibaca dan ditulis lewat `RegistriRun`, dan semua
fungsi menerima objek pengganti (`registri`), jadi tes tidak menyentuh registri sungguhan.
"""
import sys
import winreg

NAMA_ENTRI = "CtrlCoco"
# Kunci Run milik pengguna (HKCU): tidak butuh hak administrator, dan Windows menjalankan
# isinya setiap kali pengguna itu login.
KUNCI_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"


def perintah_jalan() -> str | None:
    """Perintah yang ditulis ke entri: path .exe dalam kutip, atau None bila dari sumber.

    Dalam kutip karena path bisa berspasi (misalnya di Program Files). Dari sumber
    (`python -m ctrlcoco`) tidak ada .exe yang bisa ditunjuk, jadi None.
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return None


def tersedia() -> bool:
    """Opsi hanya bisa dinyalakan dari .exe."""
    return perintah_jalan() is not None


class RegistriRun:
    """Satu nilai teks di bawah kunci Run milik pengguna."""

    def baca(self, nama: str) -> str | None:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KUNCI_RUN, 0, winreg.KEY_READ) as kunci:
                nilai, _jenis = winreg.QueryValueEx(kunci, nama)
        except FileNotFoundError:  # kunci atau nilainya belum ada
            return None
        return nilai if isinstance(nilai, str) else None

    def tulis(self, nama: str, nilai: str) -> None:
        # CreateKeyEx: membuat kunci bila belum ada, lalu membukanya untuk ditulis.
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, KUNCI_RUN, 0, winreg.KEY_SET_VALUE
        ) as kunci:
            winreg.SetValueEx(kunci, nama, 0, winreg.REG_SZ, nilai)

    def hapus(self, nama: str) -> None:
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, KUNCI_RUN, 0, winreg.KEY_SET_VALUE
            ) as kunci:
                winreg.DeleteValue(kunci, nama)
        except FileNotFoundError:  # sudah tidak ada: hasil yang diinginkan tercapai
            pass


def aktif(registri=None) -> bool:
    """Apakah entri ada dan menunjuk ke .exe yang sedang berjalan.

    Entri ke path lain (.exe dipindah) dianggap mati: yang dicentang di menu adalah
    "CtrlCoco ini akan terbuka saat login", dan entri lama tidak membuka yang ini.
    Dari sumber selalu False.
    """
    perintah = perintah_jalan()
    if perintah is None:
        return False
    registri = registri or RegistriRun()
    tersimpan = registri.baca(NAMA_ENTRI)
    # Windows tidak membedakan huruf besar dan kecil pada path.
    return tersimpan is not None and tersimpan.casefold() == perintah.casefold()


def nyalakan(registri=None) -> None:
    perintah = perintah_jalan()
    if perintah is None:
        raise RuntimeError("Jalan otomatis hanya tersedia dari CtrlCoco.exe.")
    (registri or RegistriRun()).tulis(NAMA_ENTRI, perintah)


def matikan(registri=None) -> None:
    """Hapus entri. Tetap boleh dari sumber, supaya entri sisa dari .exe bisa dibersihkan."""
    (registri or RegistriRun()).hapus(NAMA_ENTRI)
