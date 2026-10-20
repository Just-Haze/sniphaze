import os

import pytest
from PIL import Image, ImageGrab

from sniphaze import winapi
from sniphaze.flow import clipboard_payload


def test_screenshots_dir_is_a_real_folder():
    assert winapi.screenshots_dir().is_dir()


def test_display_scale_is_sane():
    assert 1.0 <= winapi.cursor_display_scale() <= 4.0


@pytest.mark.skipif(not os.environ.get("SNIPHAZE_CLIPBOARD_TEST"),
                    reason="overwrites the clipboard; set SNIPHAZE_CLIPBOARD_TEST=1")
def test_clipboard_keeps_transparency():
    img = Image.new("RGBA", (40, 20), (0, 0, 0, 0))
    img.paste((255, 0, 0, 255), (10, 5, 30, 15))

    winapi.set_clipboard(clipboard_payload(img))

    back = ImageGrab.grabclipboard()  # Pillow prefers the PNG format
    assert back.size == (40, 20)
    assert back.convert("RGBA").getpixel((0, 0))[3] == 0
    assert back.convert("RGBA").getpixel((20, 10)) == (255, 0, 0, 255)
