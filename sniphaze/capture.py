"""Opening Snipping Tool's overlay and waiting for the snip.

Pure timing logic (no Windows or Pillow imports) so it starts fast and tests
run against a fake clock.
"""

# Processes that put snips on the clipboard (ScreenClippingHost on older Windows 11).
SNIP_OWNERS = {"SnippingTool.exe", "ScreenClippingHost.exe"}


def open_overlay(*, press_keys, open_link, overlay_open, now, sleep,
                 keys_timeout=1.5, link_timeout=8.0, poll=0.01):
    """Open the overlay the fast way (Win+Shift+S), falling back to the
    ms-screenclip: link if the keys did nothing. Returns True once it's open."""
    for launch, timeout in ((press_keys, keys_timeout), (open_link, link_timeout)):
        launch()
        deadline = now() + timeout
        while now() < deadline:
            if overlay_open():
                return True
            sleep(poll)
    return False


def wait_for_snip(start_seq, *, sequence, overlay_open, owner_exe, now, sleep,
                  appear_timeout=10.0, total_timeout=180.0, grace=1.5,
                  settle=0.2, max_settle=1.0, poll=0.02):
    """Watch the clipboard and the overlay until the user snips or gives up.

    Snipping Tool writes a snip to the clipboard more than once, so after its
    first write we wait until the clipboard has been quiet for `settle`
    seconds. Returns "snip", "cancelled" (overlay closed with no snip),
    "no-overlay" or "timeout".
    """
    start = now()
    baseline = start_seq
    seen_overlay = False
    closed_at = None
    first_write = last_write = None
    while True:
        t = now()
        seq = sequence()
        if seq != baseline:
            baseline = seq
            if owner_exe() in SNIP_OWNERS:
                first_write = first_write if first_write is not None else t
                last_write = t
            # else: another app (or a clipboard manager) copied; keep waiting
        if first_write is not None:
            if t - last_write >= settle or t - first_write >= max_settle:
                return "snip"
        elif overlay_open():
            seen_overlay, closed_at = True, None
        elif seen_overlay:
            closed_at = closed_at if closed_at is not None else t
            if t - closed_at >= grace:
                return "cancelled"
        elif t - start >= appear_timeout:
            return "no-overlay"
        if t - start >= total_timeout:
            return "timeout"
        sleep(poll)


def guard_clipboard(our_seq, *, sequence, owner_exe, rewrite, now, sleep, watch=0.6, poll=0.02):
    """For a moment after we write the backdrop, put it back if Snipping Tool
    writes the plain snip again late. Anyone else copying ends the watch.
    `rewrite` writes the backdrop again and returns the new sequence number."""
    deadline = now() + watch
    while now() < deadline:
        seq = sequence()
        if seq != our_seq:
            if owner_exe() not in SNIP_OWNERS:
                return
            our_seq = rewrite()
        sleep(poll)
