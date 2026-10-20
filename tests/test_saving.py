import time
from datetime import datetime

from PIL import Image

from sniphaze.saving import fresh_snips, save_backdrop


def png(path, color=(0, 0, 255)):
    Image.new("RGB", (10, 10), color).save(path)
    return path


def backdrop_img():
    return Image.new("RGBA", (30, 30), (0, 0, 0, 0))


def test_replaces_saved_snip_and_keeps_original(tmp_path):
    original = png(tmp_path / "Screenshot 2026-10-20 120000.png")

    written = save_backdrop(tmp_path, original, backdrop_img())

    assert written == original
    assert Image.open(written).size == (30, 30)
    kept = tmp_path / "Originals" / "Screenshot 2026-10-20 120000.png"
    assert Image.open(kept).size == (10, 10)


def test_writes_new_file_when_snipping_tool_saved_nothing(tmp_path):
    now = datetime(2026, 10, 20, 12, 30, 5)

    written = save_backdrop(tmp_path, None, backdrop_img(), now=now)

    assert written == tmp_path / "Screenshot 2026-10-20 123005.png"
    assert written.exists()


def test_plain_snip_is_kept_when_snipping_tool_saved_nothing(tmp_path):
    now = datetime(2026, 10, 20, 12, 30, 5)
    plain = Image.new("RGB", (10, 10), (0, 0, 255))

    written = save_backdrop(tmp_path, None, backdrop_img(), plain=plain, now=now)

    kept = tmp_path / "Originals" / written.name
    assert Image.open(kept).size == (10, 10)


def test_new_file_never_overwrites_an_existing_one(tmp_path):
    now = datetime(2026, 10, 20, 12, 30, 5)
    png(tmp_path / "Screenshot 2026-10-20 123005.png")

    written = save_backdrop(tmp_path, None, backdrop_img(), now=now)

    assert written == tmp_path / "Screenshot 2026-10-20 123005 (2).png"


def test_original_with_same_name_already_kept_is_not_lost(tmp_path):
    (tmp_path / "Originals").mkdir()
    png(tmp_path / "Originals" / "a.png", (255, 0, 0))
    original = png(tmp_path / "a.png", (0, 255, 0))

    save_backdrop(tmp_path, original, backdrop_img())

    assert (tmp_path / "Originals" / "a.png").exists()
    assert (tmp_path / "Originals" / "a (2).png").exists()


def test_fresh_snips_finds_file_saved_after_start(tmp_path):
    png(tmp_path / "old.png")
    since = time.time()
    time.sleep(0.05)
    new = png(tmp_path / "new.png")

    assert fresh_snips(tmp_path, since) == [new]


def test_fresh_snips_ignores_old_files(tmp_path):
    png(tmp_path / "old.png")
    since = time.time() + 1

    assert fresh_snips(tmp_path, since) == []
