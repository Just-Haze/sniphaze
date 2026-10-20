import io

from PIL import Image

from sniphaze.flow import clipboard_payload, handle_snip, wait_for_saved_file


def run(tmp_path, saved):
    copied = []
    snip = Image.new("RGB", (100, 50), (10, 10, 10))
    written = handle_snip(snip, scale=1.0, set_clipboard=copied.append, folder=tmp_path,
                          since=0, find_saved=lambda folder, since, snip: saved)
    return copied, written


def test_snip_goes_to_clipboard_with_backdrop(tmp_path):
    copied, _ = run(tmp_path, None)
    assert len(copied) == 1
    assert copied[0].size == (100 + 160, 50 + 80 + 96)


def test_saved_snip_is_replaced_and_original_kept(tmp_path):
    saved = tmp_path / "Screenshot 2026-10-20 120000.png"
    Image.new("RGB", (100, 50)).save(saved)

    _, written = run(tmp_path, saved)

    assert written == saved
    assert Image.open(saved).size == (260, 226)
    assert Image.open(tmp_path / "Originals" / saved.name).size == (100, 50)


def test_unsaved_snip_still_gets_a_file_and_original(tmp_path):
    _, written = run(tmp_path, None)

    assert Image.open(written).size == (260, 226)
    assert Image.open(tmp_path / "Originals" / written.name).size == (100, 50)


def test_clipboard_png_keeps_transparency():
    img = Image.new("RGBA", (40, 20), (0, 0, 0, 0))
    img.paste((255, 0, 0, 255), (10, 5, 30, 15))

    png = Image.open(io.BytesIO(clipboard_payload(img)["PNG"]))

    assert png.getpixel((0, 0))[3] == 0
    assert png.getpixel((20, 10)) == (255, 0, 0, 255)


def test_clipboard_bitmap_is_on_white():
    img = Image.new("RGBA", (40, 20), (0, 0, 0, 0))
    dib = clipboard_payload(img)["DIB"]
    header = int.from_bytes(dib[:4], "little")

    assert header == 40  # BITMAPINFOHEADER, as CF_DIB expects
    assert dib[header:header + 3] == bytes([255, 255, 255])


def test_finds_the_file_snipping_tool_saved_for_this_snip(tmp_path):
    snip = Image.new("RGB", (30, 20), (200, 50, 50))
    snip.convert("RGBA").save(tmp_path / "Screenshot a.png")  # Snipping Tool saves RGBA

    assert wait_for_saved_file(tmp_path, 0, snip, timeout=0.3) == tmp_path / "Screenshot a.png"


def test_never_takes_a_different_image_another_app_saved(tmp_path):
    snip = Image.new("RGB", (30, 20), (200, 50, 50))
    Image.new("RGB", (30, 20), (0, 0, 255)).save(tmp_path / "Screenshot other.png")

    assert wait_for_saved_file(tmp_path, 0, snip, timeout=0.3) is None
