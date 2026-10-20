from PIL import Image

from sniphaze.backdrop import apply_backdrop, flatten

W, H = 400, 300
PAD, PAD_BOTTOM = 80, 96


def snip(color=(220, 40, 40)):
    return Image.new("RGB", (W, H), color)


def test_adds_padding_around_the_snip():
    out = apply_backdrop(snip())
    assert out.size == (W + 2 * PAD, H + PAD + PAD_BOTTOM)


def test_canvas_is_transparent():
    out = apply_backdrop(snip())
    assert out.mode == "RGBA"
    assert out.getpixel((0, 0))[3] == 0


def test_snip_pixels_are_kept_untouched():
    out = apply_backdrop(snip())
    assert out.getpixel((PAD + W // 2, PAD + H // 2)) == (220, 40, 40, 255)


def test_corners_are_rounded():
    out = apply_backdrop(snip())
    r, g, b, a = out.getpixel((PAD, PAD))  # the snip's own top-left pixel
    assert a < 128


def test_shadow_falls_below_the_snip():
    out = apply_backdrop(snip())
    cx = PAD + W // 2
    below = out.getpixel((cx, PAD + H + 20))
    above = out.getpixel((cx, PAD - 40))
    assert below[3] > 40 and below[:3] == (0, 0, 0)
    assert below[3] > above[3]


def test_scale_two_doubles_every_measurement():
    out = apply_backdrop(snip(), scale=2)
    assert out.size == (W + 4 * PAD, H + 2 * PAD + 2 * PAD_BOTTOM)


def test_light_snip_gets_a_white_hairline():
    out = apply_backdrop(snip((245, 245, 245)))
    r, g, b, a = out.getpixel((PAD - 1, PAD + H // 2))
    assert (r, g, b) == (255, 255, 255) and a > 200


def test_dark_snip_gets_a_faint_hairline():
    out = apply_backdrop(snip((10, 10, 12)))
    r, g, b, a = out.getpixel((PAD - 1, PAD + H // 2))
    assert r > 0 and a < 200  # translucent white over the shadow, not pure shadow


def test_flatten_puts_backdrop_on_white():
    flat = flatten(apply_backdrop(snip()))
    assert flat.mode == "RGB"
    assert flat.getpixel((0, 0)) == (255, 255, 255)
