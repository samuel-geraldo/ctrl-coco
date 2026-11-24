# Konfigurasi build PyInstaller: satu berkas CtrlCoco.exe (onefile), tanpa jendela konsol.
# Dijalankan dari akar repo:  pyinstaller packaging/ctrlcoco.spec --noconfirm
from pathlib import Path

RAIZ = Path(SPECPATH).parent  # SPECPATH disediakan PyInstaller: folder berkas .spec ini

a = Analysis(
    [str(RAIZ / "packaging" / "entry.py")],
    pathex=[str(RAIZ / "src")],
    # Seluruh folder assets ikut paket dan mendarat di <paket>/assets, tempat
    # ctrlcoco.aset.folder_aset() mencarinya saat berjalan sebagai .exe (#74).
    datas=[(str(RAIZ / "assets"), "assets")],
    # Modul Qt yang tidak dipakai CtrlCoco; tanpa ini ukuran .exe membengkak.
    excludes=[
        "tkinter",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuick3D",
        "PySide6.Qt3DCore",
        "PySide6.QtMultimedia",
        "PySide6.QtCharts",
    ],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="CtrlCoco",
    console=False,  # aplikasi jendela; kesalahan ditampilkan lewat QMessageBox
    upx=False,
)
