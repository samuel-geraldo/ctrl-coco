"""Jalan otomatis (#76): entri di kunci Run milik pengguna, tanpa menyentuh registri sungguhan."""
import sys

import pytest

from ctrlcoco import autostart

EXE = r"C:\Apps\CtrlCoco\CtrlCoco.exe"
PERINTAH = f'"{EXE}"'


class RegistriPalsu:
    """Pengganti RegistriRun: kamus di memori."""

    def __init__(self, isi=None):
        self.isi = dict(isi or {})

    def baca(self, nama):
        return self.isi.get(nama)

    def tulis(self, nama, nilai):
        self.isi[nama] = nilai

    def hapus(self, nama):
        self.isi.pop(nama, None)


@pytest.fixture
def sebagai_exe(monkeypatch):
    """Tiru program yang dibekukan PyInstaller."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", EXE)


@pytest.fixture
def dari_sumber(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)


# --- perintah dan ketersediaan ---


def test_perintah_dari_exe_adalah_path_exe_dalam_kutip(sebagai_exe):
    assert autostart.perintah_jalan() == PERINTAH
    assert autostart.tersedia() is True


def test_perintah_dari_sumber_tidak_ada(dari_sumber):
    assert autostart.perintah_jalan() is None
    assert autostart.tersedia() is False


def test_path_dengan_spasi_tetap_satu_perintah(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Program Files\Coco App\CtrlCoco.exe")
    assert autostart.perintah_jalan() == r'"C:\Program Files\Coco App\CtrlCoco.exe"'


# --- nyalakan, matikan, status ---


def test_awalnya_mati(sebagai_exe):
    assert autostart.aktif(RegistriPalsu()) is False


def test_nyalakan_menulis_entri_yang_menunjuk_ke_exe(sebagai_exe):
    reg = RegistriPalsu()
    autostart.nyalakan(reg)
    assert reg.isi == {autostart.NAMA_ENTRI: PERINTAH}
    assert autostart.aktif(reg) is True


def test_matikan_menghapus_entri(sebagai_exe):
    reg = RegistriPalsu({autostart.NAMA_ENTRI: PERINTAH})
    autostart.matikan(reg)
    assert reg.isi == {}
    assert autostart.aktif(reg) is False


def test_matikan_saat_sudah_mati_tidak_error(sebagai_exe):
    reg = RegistriPalsu()
    autostart.matikan(reg)
    assert reg.isi == {}


def test_nyalakan_dua_kali_tetap_satu_entri(sebagai_exe):
    reg = RegistriPalsu()
    autostart.nyalakan(reg)
    autostart.nyalakan(reg)
    assert reg.isi == {autostart.NAMA_ENTRI: PERINTAH}


def test_entri_lain_di_kunci_run_tidak_tersentuh(sebagai_exe):
    reg = RegistriPalsu({"Spotify": "spotify.exe"})
    autostart.nyalakan(reg)
    autostart.matikan(reg)
    assert reg.isi == {"Spotify": "spotify.exe"}


def test_entri_ke_path_lama_dianggap_mati_dan_nyalakan_memperbaruinya(sebagai_exe):
    reg = RegistriPalsu({autostart.NAMA_ENTRI: r'"D:\Lama\CtrlCoco.exe"'})
    assert autostart.aktif(reg) is False
    autostart.nyalakan(reg)
    assert reg.isi[autostart.NAMA_ENTRI] == PERINTAH
    assert autostart.aktif(reg) is True


def test_perbandingan_path_tidak_peka_huruf_besar_kecil(sebagai_exe):
    reg = RegistriPalsu({autostart.NAMA_ENTRI: PERINTAH.upper()})
    assert autostart.aktif(reg) is True


def test_dari_sumber_selalu_mati_dan_nyalakan_ditolak(dari_sumber):
    reg = RegistriPalsu({autostart.NAMA_ENTRI: PERINTAH})
    assert autostart.aktif(reg) is False
    with pytest.raises(RuntimeError):
        autostart.nyalakan(reg)
    assert reg.isi == {autostart.NAMA_ENTRI: PERINTAH}  # tidak berubah


def test_matikan_dari_sumber_tetap_boleh(dari_sumber):
    # Entri yang dibuat dari .exe bisa dibersihkan walau sedang menjalankan versi sumber.
    reg = RegistriPalsu({autostart.NAMA_ENTRI: PERINTAH})
    autostart.matikan(reg)
    assert reg.isi == {}


def test_tanpa_argumen_memakai_registri_run_sungguhan_kelas(sebagai_exe, monkeypatch):
    dipakai = RegistriPalsu()
    monkeypatch.setattr(autostart, "RegistriRun", lambda: dipakai)
    autostart.nyalakan()
    assert autostart.aktif() is True
    autostart.matikan()
    assert dipakai.isi == {}


# --- RegistriRun terhadap winreg palsu ---


class KunciPalsu:
    def __init__(self, nilai):
        self.nilai = nilai

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class WinregPalsu:
    """Modul winreg tiruan: satu kunci Run di memori, mencatat izin yang diminta."""

    HKEY_CURRENT_USER = "HKCU"
    KEY_READ = 1
    KEY_SET_VALUE = 2
    REG_SZ = 1

    def __init__(self, kunci_ada=True):
        self.nilai = {}
        self.kunci_ada = kunci_ada
        self.dibuka = []

    def OpenKey(self, akar, sub, reserved, akses):
        if not self.kunci_ada:
            raise FileNotFoundError
        self.dibuka.append((akar, sub, akses))
        return KunciPalsu(self.nilai)

    def CreateKeyEx(self, akar, sub, reserved, akses):
        self.kunci_ada = True
        self.dibuka.append((akar, sub, akses))
        return KunciPalsu(self.nilai)

    def QueryValueEx(self, kunci, nama):
        if nama not in kunci.nilai:
            raise FileNotFoundError
        return kunci.nilai[nama], self.REG_SZ

    def SetValueEx(self, kunci, nama, reserved, jenis, nilai):
        assert jenis == self.REG_SZ
        kunci.nilai[nama] = nilai

    def DeleteValue(self, kunci, nama):
        if nama not in kunci.nilai:
            raise FileNotFoundError
        del kunci.nilai[nama]


@pytest.fixture
def winreg_palsu(monkeypatch):
    palsu = WinregPalsu()
    monkeypatch.setattr(autostart, "winreg", palsu)
    return palsu


def test_registri_tulis_lalu_baca_dan_hapus(winreg_palsu):
    reg = autostart.RegistriRun()
    assert reg.baca("CtrlCoco") is None
    reg.tulis("CtrlCoco", PERINTAH)
    assert reg.baca("CtrlCoco") == PERINTAH
    reg.hapus("CtrlCoco")
    assert reg.baca("CtrlCoco") is None


def test_registri_hapus_nilai_yang_tidak_ada_tidak_error(winreg_palsu):
    autostart.RegistriRun().hapus("CtrlCoco")


def test_registri_hanya_menyentuh_kunci_run_milik_pengguna(winreg_palsu):
    reg = autostart.RegistriRun()
    reg.tulis("CtrlCoco", PERINTAH)
    reg.baca("CtrlCoco")
    reg.hapus("CtrlCoco")
    assert {(akar, sub) for akar, sub, _ in winreg_palsu.dibuka} == {
        ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Run")
    }


def test_registri_baca_hanya_meminta_izin_baca_dan_tulis_izin_tulis(winreg_palsu):
    reg = autostart.RegistriRun()
    reg.tulis("CtrlCoco", PERINTAH)
    reg.baca("CtrlCoco")
    reg.hapus("CtrlCoco")
    assert [akses for _, _, akses in winreg_palsu.dibuka] == [
        winreg_palsu.KEY_SET_VALUE, winreg_palsu.KEY_READ, winreg_palsu.KEY_SET_VALUE,
    ]


def test_registri_tanpa_kunci_run_dianggap_kosong(monkeypatch):
    monkeypatch.setattr(autostart, "winreg", WinregPalsu(kunci_ada=False))
    reg = autostart.RegistriRun()
    assert reg.baca("CtrlCoco") is None
    reg.hapus("CtrlCoco")  # tidak error


def test_registri_nilai_bukan_teks_dibaca_sebagai_kosong(winreg_palsu):
    winreg_palsu.nilai["CtrlCoco"] = 123
    assert autostart.RegistriRun().baca("CtrlCoco") is None
