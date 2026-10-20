from sniphaze.capture import guard_clipboard, open_overlay, wait_for_snip


class Timeline:
    """Fake clock: the overlay is open between `opens` and `closes`; the
    clipboard changes at each time in `changes` (with that owner)."""

    def __init__(self, opens=0.3, closes=None, changes=()):
        self.t = 0.0
        self.opens, self.closes, self.changes = opens, closes, list(changes)

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += s

    def overlay_open(self):
        return self.t >= self.opens and (self.closes is None or self.t < self.closes)

    def sequence(self):
        return 100 + sum(1 for at, _ in self.changes if self.t >= at)

    def owner_exe(self):
        done = [owner for at, owner in self.changes if self.t >= at]
        return done[-1] if done else None


def wait(tl, **kw):
    return wait_for_snip(tl.sequence(), sequence=tl.sequence, overlay_open=tl.overlay_open,
                         owner_exe=tl.owner_exe, now=tl.now, sleep=tl.sleep, **kw)


def test_snip_from_snipping_tool_is_picked_up():
    tl = Timeline(closes=4.0, changes=[(4.0, "SnippingTool.exe")])
    assert wait(tl) == "snip"


def test_clipboard_change_from_another_app_is_ignored():
    tl = Timeline(closes=6.0, changes=[(2.0, "chrome.exe"), (6.0, "SnippingTool.exe")])
    assert wait(tl) == "snip"
    assert tl.t >= 6.0


def test_escape_closes_overlay_without_a_snip():
    tl = Timeline(closes=3.0)
    assert wait(tl) == "cancelled"


def test_snip_landing_just_after_overlay_closes_still_counts():
    tl = Timeline(closes=3.0, changes=[(3.4, "SnippingTool.exe")])
    assert wait(tl) == "snip"


def test_gives_up_if_overlay_never_opens():
    tl = Timeline(opens=999)
    assert wait(tl, appear_timeout=10) == "no-overlay"
    assert tl.t < 11


def test_gives_up_eventually_if_overlay_stays_open():
    tl = Timeline()
    assert wait(tl, total_timeout=60) == "timeout"


def test_waits_for_snipping_tools_second_clipboard_write():
    # Win+Shift+S snips land on the clipboard twice, ~130ms apart. Writing the
    # backdrop between the two would get it overwritten.
    tl = Timeline(closes=4.0, changes=[(4.0, "SnippingTool.exe"), (4.13, "SnippingTool.exe")])
    assert wait(tl, settle=0.2) == "snip"
    assert tl.t >= 4.33


def test_single_clipboard_write_settles_quickly():
    tl = Timeline(closes=4.0, changes=[(4.0, "SnippingTool.exe")])
    assert wait(tl, settle=0.2) == "snip"
    assert tl.t < 4.3


class Launch:
    def __init__(self, keys_work):
        self.t, self.keys_work, self.calls = 0.0, keys_work, []

    def press_keys(self):
        self.calls.append("keys")
        self.opened_at = self.t + 0.25 if self.keys_work else None

    def open_link(self):
        self.calls.append("link")
        self.opened_at = self.t + 1.0

    def overlay_open(self):
        return self.opened_at is not None and self.t >= self.opened_at

    def sleep(self, s):
        self.t += s


def launch(fake):
    return open_overlay(press_keys=fake.press_keys, open_link=fake.open_link,
                        overlay_open=fake.overlay_open, now=lambda: fake.t, sleep=fake.sleep)


def test_overlay_opens_with_the_snip_keys():
    fake = Launch(keys_work=True)
    assert launch(fake) is True
    assert fake.calls == ["keys"]
    assert fake.t < 0.5


def test_falls_back_to_the_link_when_keys_do_nothing():
    fake = Launch(keys_work=False)
    assert launch(fake) is True
    assert fake.calls == ["keys", "link"]


def test_ownerless_clipboard_writes_are_not_snips():
    # Clipboard managers (and SnipHaze itself) write with no owner window.
    tl = Timeline(closes=5.0, changes=[(2.0, None), (5.0, "SnippingTool.exe")])
    assert wait(tl) == "snip"
    assert tl.t >= 5.0


def test_older_snipping_tool_host_counts_too():
    tl = Timeline(closes=4.0, changes=[(4.0, "ScreenClippingHost.exe")])
    assert wait(tl) == "snip"


def guard(tl, rewrites):
    def rewrite():
        rewrites.append(tl.t)
        return tl.sequence()
    return guard_clipboard(tl.sequence(), sequence=tl.sequence, owner_exe=tl.owner_exe,
                           rewrite=rewrite, now=tl.now, sleep=tl.sleep, watch=0.6)


def test_late_snipping_tool_write_gets_the_backdrop_again():
    tl = Timeline(changes=[(0.25, "SnippingTool.exe")])
    rewrites = []
    guard(tl, rewrites)
    assert len(rewrites) == 1 and rewrites[0] >= 0.25


def test_quiet_clipboard_is_left_alone():
    tl = Timeline()
    rewrites = []
    guard(tl, rewrites)
    assert rewrites == []


def test_user_copying_something_else_is_left_alone():
    tl = Timeline(changes=[(0.2, "chrome.exe"), (0.3, "SnippingTool.exe")])
    rewrites = []
    guard(tl, rewrites)
    assert rewrites == []
