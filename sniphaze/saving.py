"""Where the backdrop version of a snip lands on disk."""

import shutil
from datetime import datetime
from pathlib import Path

ORIGINALS = "Originals"


def _free_name(path):
    """`path`, or `name (2).png`, `name (3).png`... whichever doesn't exist yet."""
    path = Path(path)
    n = 2
    candidate = path
    while candidate.exists():
        candidate = path.with_name(f"{path.stem} ({n}){path.suffix}")
        n += 1
    return candidate


def fresh_snips(folder, since):
    """PNGs saved directly in `folder` at or after `since` (epoch seconds), newest first."""
    fresh = []
    for p in Path(folder).glob("*.png"):
        try:
            mtime = p.stat().st_mtime
        except OSError:  # deleted or renamed while we looked
            continue
        if mtime >= since:
            fresh.append((mtime, p))
    return [p for _, p in sorted(fresh, reverse=True)]


def save_backdrop(folder, original, img, plain=None, now=None):
    """Write `img` as the saved snip.

    If Snipping Tool saved the snip (`original`), that file becomes the backdrop
    version and the untouched original is copied to `folder/Originals` first
    (so an interrupted save never loses it). Otherwise a
    new `Screenshot YYYY-MM-DD HHMMSS.png` is written next to the others, with
    the `plain` snip (if given) kept under the same name in `folder/Originals`.
    """
    folder = Path(folder)
    if original is not None:
        original = Path(original)
        keep = _free_name(folder / ORIGINALS / original.name)
        keep.parent.mkdir(exist_ok=True)
        shutil.copy2(original, keep)
        target = original
    else:
        stamp = (now or datetime.now()).strftime("%Y-%m-%d %H%M%S")
        target = _free_name(folder / f"Screenshot {stamp}.png")
        if plain is not None:
            keep = _free_name(folder / ORIGINALS / target.name)
            keep.parent.mkdir(exist_ok=True)
            plain.save(keep, "PNG")
    img.save(target, "PNG")
    return target
