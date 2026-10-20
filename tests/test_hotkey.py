import pytest

from sniphaze.hotkey import MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, parse_hotkey


def test_default_shortcut():
    assert parse_hotkey("CTRL+ALT+S") == (MOD_CONTROL | MOD_ALT, ord("S"))


def test_case_and_spaces_dont_matter():
    assert parse_hotkey(" ctrl + shift + g ") == (MOD_CONTROL | MOD_SHIFT, ord("G"))


def test_digits_and_win_key():
    assert parse_hotkey("WIN+ALT+1") == (MOD_WIN | MOD_ALT, ord("1"))


def test_function_keys():
    assert parse_hotkey("CTRL+F9") == (MOD_CONTROL, 0x78)


def test_print_screen_alone():
    assert parse_hotkey("PRINTSCREEN") == (0, 0x2C)


@pytest.mark.parametrize("bad", ["", "CTRL+ALT", "CTRL+FOO", "CTRL+S+D", "F25", "S", "SHIFT+S", "5"])
def test_rejects_shortcuts_windows_cant_register(bad):
    with pytest.raises(ValueError):
        parse_hotkey(bad)


def test_describe_round_trips():
    from sniphaze.hotkey import describe
    assert describe(*parse_hotkey("alt+ctrl+s")) == "Ctrl+Alt+S"


def test_function_key_alone_is_fine():
    assert parse_hotkey("F9") == (0, 0x78)
