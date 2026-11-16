import pytest
from PySide6.QtGui import QColor, QPixmap

from ctrlcoco.mood import MOODS
from ctrlcoco.sprites import PLACEHOLDER_COLORS, SPRITE_WIDTH, load_frames, placeholder_frames


def buat_sprite(folder, nama, warna):
    """Simpan gambar kecil satu warna sebagai file sprite."""
    pixmap = QPixmap(8, 8)
    pixmap.fill(QColor(warna))
    assert pixmap.save(str(folder / nama))


def warna_tengah(pixmap):
    image = pixmap.toImage()
    return image.pixelColor(image.width() // 2, image.height() // 2).name()


# --- memuat dari file ---

def test_load_frames_urut_menurut_nomor(app, tmp_path):
    buat_sprite(tmp_path, "senang_2.png", "#00ff00")
    buat_sprite(tmp_path, "senang_10.png", "#0000ff")
    buat_sprite(tmp_path, "senang_1.png", "#ff0000")
    frames = load_frames("senang", tmp_path)
    assert [warna_tengah(f) for f in frames] == ["#ff0000", "#00ff00", "#0000ff"]


def test_load_frames_hanya_kondisi_yang_diminta(app, tmp_path):
    buat_sprite(tmp_path, "senang_1.png", "#ff0000")
    buat_sprite(tmp_path, "tidur_1.png", "#0000ff")
    frames = load_frames("tidur", tmp_path)
    assert [warna_tengah(f) for f in frames] == ["#0000ff"]


def test_load_frames_diskalakan_ke_lebar_widget(app, tmp_path):
    buat_sprite(tmp_path, "senang_1.png", "#ff0000")
    assert load_frames("senang", tmp_path)[0].width() == SPRITE_WIDTH


# --- fallback ke gambar sementara ---

def test_setiap_kondisi_punya_warna_sementara_yang_berbeda():
    assert set(PLACEHOLDER_COLORS) == set(MOODS)
    assert len(set(PLACEHOLDER_COLORS.values())) == len(MOODS)


@pytest.mark.parametrize("mood", MOODS)
def test_placeholder_dua_frame_berwarna_kondisi(app, mood):
    frames = placeholder_frames(mood)
    assert len(frames) == 2
    assert all(not f.isNull() for f in frames)
    assert all(warna_tengah(f) == PLACEHOLDER_COLORS[mood] for f in frames)
    # Dua frame harus berbeda supaya animasinya terlihat.
    assert frames[0].toImage() != frames[1].toImage()


@pytest.mark.parametrize("mood", MOODS)
def test_fallback_jika_folder_tidak_ada(app, tmp_path, mood):
    frames = load_frames(mood, tmp_path / "tidak_ada")
    assert [warna_tengah(f) for f in frames] == [PLACEHOLDER_COLORS[mood]] * 2


@pytest.mark.parametrize("mood", MOODS)
def test_fallback_jika_folder_kosong(app, tmp_path, mood):
    frames = load_frames(mood, tmp_path)
    assert [warna_tengah(f) for f in frames] == [PLACEHOLDER_COLORS[mood]] * 2


def test_fallback_hanya_untuk_kondisi_tanpa_file(app, tmp_path):
    buat_sprite(tmp_path, "senang_1.png", "#ff0000")
    assert [warna_tengah(f) for f in load_frames("senang", tmp_path)] == ["#ff0000"]
    assert warna_tengah(load_frames("waspada", tmp_path)[0]) == PLACEHOLDER_COLORS["waspada"]


@pytest.mark.parametrize("nama", ["senang.png", "senang_a.png", "senang_1.txt", "xsenang_1.png"])
def test_nama_file_yang_tidak_cocok_diabaikan(app, tmp_path, nama):
    buat_sprite(tmp_path, "contoh.png", "#ff0000")
    (tmp_path / "contoh.png").rename(tmp_path / nama)
    assert warna_tengah(load_frames("senang", tmp_path)[0]) == PLACEHOLDER_COLORS["senang"]


def test_file_rusak_dilewati(app, tmp_path):
    (tmp_path / "senang_1.png").write_bytes(b"bukan gambar")
    assert warna_tengah(load_frames("senang", tmp_path)[0]) == PLACEHOLDER_COLORS["senang"]

    buat_sprite(tmp_path, "senang_2.png", "#00ff00")
    assert [warna_tengah(f) for f in load_frames("senang", tmp_path)] == ["#00ff00"]
