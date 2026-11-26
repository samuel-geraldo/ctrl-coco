from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QWidget

ERROR_STYLE = "QLabel { color: #c62828; }"


class FormDasar(QDialog):
    """Kerangka bersama form: pesan error merah dan tombol utama + Batal.

    Isian, aksi tombol utama, dan susunan layout tetap milik tiap form.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        # Dihapus dari memori setelah ditutup, supaya membuka form berkali-kali
        # tidak meninggalkan dialog lama yang menumpuk.
        self.setAttribute(Qt.WA_DeleteOnClose)

        # Pesan error tampil di sini; form tetap terbuka dan isian tidak dihapus.
        self.error_label = QLabel()
        self.error_label.setStyleSheet(ERROR_STYLE)
        self.error_label.setWordWrap(True)
        self.error_label.hide()

    def _buat_tombol(self, teks_utama: str) -> QDialogButtonBox:
        """Buat kotak tombol berisi tombol utama dan Batal.

        Dipanggil form pada titik yang sama dengan sebelumnya (setelah isian dibuat),
        bukan di __init__, supaya urutan Tab dan fokus awal tidak berubah: Qt
        mengurutkannya menurut urutan pembuatan widget. Sinyal `accepted` disambungkan
        oleh form ke aksinya sendiri; Batal sama di semua form.
        """
        kotak = QDialogButtonBox()
        self.tombol_utama = kotak.addButton(teks_utama, QDialogButtonBox.AcceptRole)
        self.tombol_batal = kotak.addButton("Batal", QDialogButtonBox.RejectRole)
        kotak.rejected.connect(self.reject)
        return kotak

    def _tampilkan_error(self, pesan: str) -> None:
        self.error_label.setText(pesan)
        self.error_label.show()
