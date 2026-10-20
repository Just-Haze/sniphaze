"""SnipHaze: Snipping Tool snips with a macOS-style shadow backdrop.

    pythonw SnipHaze.pyw                     listen for Ctrl+Alt+S (starts with Windows)
    pythonw SnipHaze.pyw --hotkey CTRL+ALT+G listen for another shortcut
    pythonw SnipHaze.pyw --once              take one snip now and exit
    pythonw SnipHaze.pyw --quit              stop the running listener
    python  SnipHaze.pyw --check --hotkey X  check a shortcut is usable
"""

import argparse
import logging
import os
import time
from pathlib import Path

from . import capture, winapi
from .hotkey import describe, parse_hotkey

APP_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SnipHaze"
LOG = APP_DIR / "sniphaze.log"
LOG_LIMIT = 512 * 1024


def _start_log():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if LOG.exists() and LOG.stat().st_size > LOG_LIMIT:
            LOG.replace(LOG.with_suffix(".old.log"))
    except OSError:
        pass  # another SnipHaze has it open; rotate next time
    logging.basicConfig(filename=LOG, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")


def _set_clipboard(img):
    """Put the backdrop on the clipboard and keep it there if Snipping Tool
    writes the plain snip again a moment later."""
    from . import flow

    payload = flow.clipboard_payload(img)

    def write():
        winapi.set_clipboard(payload)
        return winapi.clipboard_sequence()

    capture.guard_clipboard(write(), sequence=winapi.clipboard_sequence,
                            owner_exe=winapi.clipboard_owner_exe, rewrite=write,
                            now=time.monotonic, sleep=time.sleep)


def snip():
    """One snip: open the overlay, wait for the snip, add the backdrop."""
    started = time.time()
    baseline = winapi.clipboard_sequence()
    opened = capture.open_overlay(press_keys=winapi.press_snip_keys,
                                  open_link=winapi.open_snip_link,
                                  overlay_open=winapi.overlay_open,
                                  now=time.monotonic, sleep=time.sleep)
    opened_in = time.time() - started
    from . import flow  # Pillow loads while the user drags (only slow the first time)

    if not opened:
        logging.warning("Snipping Tool's overlay didn't open")
        return
    result = capture.wait_for_snip(
        baseline, sequence=winapi.clipboard_sequence, overlay_open=winapi.overlay_open,
        owner_exe=winapi.clipboard_owner_exe, now=time.monotonic, sleep=time.sleep)
    if result != "snip":
        logging.info("no snip (%s); last clipboard owner: %s", result, winapi.clipboard_owner_exe())
        return
    snipped = time.time()
    img = flow.grab_snip()
    if img is None:
        logging.warning("clipboard changed but held no image")
        return
    scale = winapi.cursor_display_scale()
    saved = flow.handle_snip(img, scale=scale, set_clipboard=_set_clipboard,
                             folder=winapi.screenshots_dir(), since=started,
                             find_saved=flow.wait_for_saved_file)
    logging.info("snip %sx%s @%.2gx: overlay in %.2fs, saved %.2fs after snip -> %s",
                 *img.size, scale, opened_in, time.time() - snipped, saved)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="SnipHaze", description=__doc__.splitlines()[0])
    parser.add_argument("--hotkey", default="CTRL+ALT+S")
    parser.add_argument("--once", action="store_true", help="take one snip now and exit")
    parser.add_argument("--quit", action="store_true", help="stop the running listener")
    parser.add_argument("--check", action="store_true", help="only check that --hotkey is usable")
    args = parser.parse_args(argv)

    if args.check:
        try:
            print(describe(*parse_hotkey(args.hotkey)))
        except ValueError as e:
            print(e)
            raise SystemExit(1)
        return

    from . import listener

    if args.quit:
        listener.stop_running()
        return
    winapi.make_dpi_aware()
    _start_log()
    if args.once:
        try:
            snip()
        except Exception:
            logging.exception("snip failed")
        return

    try:
        mods, vk = parse_hotkey(args.hotkey)
    except ValueError as e:
        listener.warn(f"Can't use the shortcut {args.hotkey!r}: {e}")
        return
    lock = winapi.single_instance("Local\\SnipHaze.listener")
    if lock is None:
        return  # already listening
    try:
        logging.info("listening for %s", describe(mods, vk))
        listener.Listener(mods, vk, on_hotkey=snip).run()
    except listener.HotkeyTaken:
        logging.error("%s is already used by another app", describe(mods, vk))
        listener.warn(f"{describe(mods, vk)} is already used by another app.\n\n"
                      "Pick another shortcut:  .\\install.ps1 -Hotkey CTRL+ALT+G")


if __name__ == "__main__":
    main()
