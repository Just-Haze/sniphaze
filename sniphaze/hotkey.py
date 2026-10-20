"""Shortcut text like "Ctrl+Alt+S" <-> what RegisterHotKey wants."""

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN = 0x1, 0x2, 0x4, 0x8

_MODIFIERS = {"CTRL": MOD_CONTROL, "CONTROL": MOD_CONTROL, "ALT": MOD_ALT,
              "SHIFT": MOD_SHIFT, "WIN": MOD_WIN}
_NAMED_KEYS = {"PRINTSCREEN": 0x2C, "PRTSC": 0x2C, "SPACE": 0x20, "INSERT": 0x2D,
               "PAUSE": 0x13, "SCROLLLOCK": 0x91}
_NAMED_KEYS.update({f"F{n}": 0x6F + n for n in range(1, 25)})
# Keys that are fine on their own (nobody types with them).
_STANDALONE = {0x2C, 0x13, 0x91} | {0x6F + n for n in range(1, 25)}


def _key(name):
    if len(name) == 1 and name.isascii() and name.isalnum():
        return ord(name)
    if name in _NAMED_KEYS:
        return _NAMED_KEYS[name]
    raise ValueError(f"unknown key {name!r}")


def parse_hotkey(text):
    """"Ctrl+Alt+S" -> (modifiers, virtual key). Exactly one non-modifier key."""
    parts = [p.strip().upper() for p in text.split("+") if p.strip()]
    mods = 0
    keys = []
    for part in parts:
        if part in _MODIFIERS:
            mods |= _MODIFIERS[part]
        else:
            keys.append(_key(part))
    if len(keys) != 1:
        raise ValueError(f"{text!r} needs exactly one key besides Ctrl/Alt/Shift/Win")
    if not mods & (MOD_CONTROL | MOD_ALT | MOD_WIN) and keys[0] not in _STANDALONE:
        raise ValueError(f"{text!r} would take over normal typing; add Ctrl, Alt or Win")
    return mods, keys[0]


def describe(mods, vk):
    names = [n for n, m in (("Ctrl", MOD_CONTROL), ("Alt", MOD_ALT),
                            ("Shift", MOD_SHIFT), ("Win", MOD_WIN)) if mods & m]
    return "+".join(names + [_DISPLAY.get(vk, chr(vk))])


_DISPLAY = {0x2C: "PrintScreen", 0x20: "Space", 0x2D: "Insert", 0x13: "Pause",
            0x91: "ScrollLock"}
_DISPLAY.update({0x6F + n: f"F{n}" for n in range(1, 25)})
