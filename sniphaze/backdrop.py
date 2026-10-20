"""Shadow Backdrop: the macOS-screenshot look from opensnap.

Transparent canvas, 80px padding (96 below so the shadow isn't clipped),
12px rounded corners, shadow rgba(0,0,0,.45) blur 60 offset y 30, 1px hairline.
Every measurement is at 1x and multiplied by `scale` (2 on a 200% display).
"""

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

PAD = 80
PAD_BOTTOM = 96
RADIUS = 12
SHADOW_ALPHA = 0.45
SHADOW_BLUR = 60  # canvas shadowBlur; Gaussian sigma is half of it
SHADOW_OFFSET_Y = 30
HAIRLINE = 1
HAIRLINE_LIGHT = (255, 255, 255, 255)  # opensnap default
HAIRLINE_DARK = (255, 255, 255, round(0.12 * 255))  # macOS window edge on dark art

_SUPERSAMPLE = 4


def _rounded_mask(size, radius):
    """Anti-aliased rounded-rectangle mask; only the corners are supersampled."""
    w, h = size
    mask = Image.new("L", size, 255)
    r = max(0, min(radius, w // 2, h // 2))
    if r == 0:
        return mask
    big = r * _SUPERSAMPLE
    corner = Image.new("L", (big, big), 0)
    ImageDraw.Draw(corner).pieslice((0, 0, 2 * big - 1, 2 * big - 1), 180, 270, fill=255)
    corner = corner.resize((r, r), Image.LANCZOS)
    mask.paste(corner, (0, 0))
    mask.paste(corner.transpose(Image.FLIP_LEFT_RIGHT), (w - r, 0))
    mask.paste(corner.transpose(Image.FLIP_TOP_BOTTOM), (0, h - r))
    mask.paste(corner.transpose(Image.ROTATE_180), (w - r, h - r))
    return mask


def _is_dark(img):
    small = img.convert("L").resize((64, 64))
    return ImageStat.Stat(small).mean[0] < 128


def apply_backdrop(img, scale=1.0):
    """Return the snip floating on a transparent RGBA canvas with a soft shadow."""
    def px(v):
        return max(1, round(v * scale))

    pad, pad_bottom, radius = px(PAD), px(PAD_BOTTOM), px(RADIUS)
    hairline, offset_y = px(HAIRLINE), px(SHADOW_OFFSET_Y)
    sigma = SHADOW_BLUR / 2 * scale

    snip = img.convert("RGBA")
    w, h = snip.size
    size = (w + 2 * pad, h + pad + pad_bottom)
    shape = _rounded_mask((w, h), radius)

    # Shadow: the card's shape, pushed down, blurred, 45% black.
    shadow_alpha = Image.new("L", size, 0)
    shadow_alpha.paste(shape.point(lambda v: round(v * SHADOW_ALPHA)), (pad, pad + offset_y))
    shadow_alpha = shadow_alpha.filter(ImageFilter.GaussianBlur(sigma))
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.putalpha(shadow_alpha)

    # Hairline: a ring just outside the card's edge.
    outer = Image.new("L", size, 0)
    outer.paste(_rounded_mask((w + 2 * hairline, h + 2 * hairline), radius + hairline),
                (pad - hairline, pad - hairline))
    inner = Image.new("L", size, 0)
    inner.paste(shape, (pad, pad))
    ring = ImageChops.subtract(outer, inner)
    color = HAIRLINE_DARK if _is_dark(snip) else HAIRLINE_LIGHT
    edge = Image.new("RGBA", size, color[:3] + (0,))
    edge.putalpha(ring.point(lambda v: round(v * color[3] / 255)))
    out.alpha_composite(edge)

    # The snip itself, clipped to the rounded shape.
    card = snip.copy()
    card.putalpha(ImageChops.multiply(snip.getchannel("A"), shape))
    out.alpha_composite(card, (pad, pad))
    return out


def flatten(img, background=(255, 255, 255)):
    """Backdrop on a solid colour, for apps that can't paste transparency."""
    base = Image.new("RGBA", img.size, background + (255,))
    base.alpha_composite(img)
    return base.convert("RGB")
