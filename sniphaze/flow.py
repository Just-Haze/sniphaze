"""What happens to one snip: add the backdrop, put it on the clipboard, save it."""

import io
import time

from .backdrop import apply_backdrop, flatten
from .saving import fresh_snips, save_backdrop


def clipboard_payload(img):
    """Clipboard formats for the backdrop image: PNG keeps the transparency,
    the DIB (on white) is for apps that only read plain bitmaps."""
    png = io.BytesIO()
    img.save(png, "PNG", compress_level=1)  # speed over size; it's a clipboard
    bmp = io.BytesIO()
    flatten(img).save(bmp, "BMP")
    return {"PNG": png.getvalue(), "DIB": bmp.getvalue()[14:]}  # drop BITMAPFILEHEADER


def handle_snip(snip, *, scale, set_clipboard, folder, since, find_saved):
    """Backdrop the snip onto the clipboard first (that's what you paste), then
    replace the auto-saved file, keeping the original. Returns the saved path."""
    out = apply_backdrop(snip, scale=scale)
    set_clipboard(out)
    return save_backdrop(folder, find_saved(folder, since, snip), out, plain=snip)


def _same_pixels(path, snip):
    from PIL import Image

    with Image.open(path) as im:
        im.load()  # raises if Snipping Tool is still writing it
        return im.size == snip.size and im.convert("RGB").tobytes() == snip.convert("RGB").tobytes()


def wait_for_saved_file(folder, since, snip, timeout=3.0):
    """The file Snipping Tool auto-saved for this snip, if any.

    Only a file with exactly the snip's pixels counts, so a screenshot another
    app saved into the same folder meanwhile is never touched.
    """
    deadline = time.time() + timeout
    while True:
        for path in fresh_snips(folder, since):
            try:
                if _same_pixels(path, snip):
                    return path
            except OSError:
                pass  # half-written or gone; look again
        if time.time() >= deadline:
            return None
        time.sleep(0.05)


def grab_snip(attempts=20):
    from PIL import ImageGrab

    for _ in range(attempts):
        img = ImageGrab.grabclipboard()
        if img is not None and not isinstance(img, list):
            return img
        time.sleep(0.05)
    return None
