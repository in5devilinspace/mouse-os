#!/usr/bin/env python3
"""Render brand overlays (captions + end card) as 1920x1080 RGBA PNGs.

Palette matches the landing page: navy #0A0E1A, amber #FFB454, light #E8ECF6,
DejaVu Sans (bold) for display, DejaVu Sans Mono for UI/command/CTA.
"""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
AMBER = (255, 180, 84, 255)
LIGHT = (232, 236, 246, 255)
MUTE = (138, 147, 173, 255)
OUT = "media/ov"
os.makedirs(OUT, exist_ok=True)

MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def f(path, size):
    return ImageFont.truetype(path, size)


def scrim(img, top):
    """Soft bottom gradient scrim so captions stay legible over footage."""
    grad = Image.new("L", (1, H), 0)
    for y in range(H):
        if y < top:
            grad.putpixel((0, y), 0)
        else:
            grad.putpixel((0, y), int(200 * (y - top) / (H - top)))
    grad = grad.resize((W, H))
    black = Image.new("RGBA", (W, H), (5, 8, 16, 255))
    black.putalpha(grad)
    img.alpha_composite(black)


def base():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def center_text(d, cx, y, text, font, fill, spacing=0, anchor="mm"):
    d.text((cx, y), text, font=font, fill=fill, anchor=anchor)


# -- caption 1: "point." (minimal, lower third, faint) --------------------
img = base()
scrim(img, int(H * 0.72))
d = ImageDraw.Draw(img)
d.text((160, H - 150), "point.", font=f(SANS_B, 64), fill=LIGHT, anchor="lm")
img.save(f"{OUT}/cap1.png")

# -- caption 2: the command as a mono terminal line with caret ------------
img = base()
scrim(img, int(H * 0.70))
d = ImageDraw.Draw(img)
d.text((160, H - 175), "you", font=f(MONO, 30), fill=MUTE, anchor="lm")
d.text((160, H - 130), '"point to Firefox"', font=f(MONO_B, 50), fill=AMBER,
       anchor="lm")
w = d.textlength('"point to Firefox"', font=f(MONO_B, 50))
d.rectangle([160 + w + 14, H - 152, 160 + w + 30, H - 108], fill=AMBER)
img.save(f"{OUT}/cap2.png")

# -- caption 4: "hands still. the cursor isn't." --------------------------
img = base()
scrim(img, int(H * 0.72))
d = ImageDraw.Draw(img)
d.text((160, H - 140), "hands still.", font=f(SANS_B, 60), fill=LIGHT,
       anchor="lm")
d.text((520, H - 140), " the cursor isn’t.", font=f(SANS_B, 60),
       fill=AMBER, anchor="lm")
img.save(f"{OUT}/cap4.png")

# -- caption 5 / lower third on the dawn shot -----------------------------
img = base()
scrim(img, int(H * 0.70))
d = ImageDraw.Draw(img)
d.text((160, H - 165), "Your voice is the pointer.", font=f(SANS_B, 58),
       fill=LIGHT, anchor="lm")
d.text((160, H - 108),
       "Free · offline · open-source — try Mouse OS tonight.",
       font=f(MONO, 34), fill=MUTE, anchor="lm")
img.save(f"{OUT}/cap5.png")

# -- end card: full navy, tagline, CTA, cursor ----------------------------
def cursor(d, x, y, s, alpha=255):
    pts = [(0, 0), (0, 19), (4.4, 14.8), (7.6, 21.4), (10.6, 20),
           (7.4, 13.6), (13.4, 13)]
    d.polygon([(x + px * s, y + py * s) for px, py in pts],
              fill=(255, 180, 84, alpha))

for blink, tag in ((255, "on"), (40, "off")):
    img = Image.new("RGBA", (W, H), (10, 14, 26, 255))
    d = ImageDraw.Draw(img)
    # wordmark
    cursor(d, W // 2 - 250, 300, 2.4)
    d.text((W // 2 - 205, 322), "MOUSE OS", font=f(MONO_B, 44), fill=LIGHT,
           anchor="lm")
    d.text((W // 2, H // 2 - 10), "Your voice is the pointer.",
           font=f(SANS_B, 88), fill=LIGHT, anchor="mm")
    d.text((W // 2, H // 2 + 90),
           "Free · offline · open-source. Try Mouse OS tonight.",
           font=f(MONO, 38), fill=AMBER, anchor="mm")
    # CTA line with blinking cursor caret
    url = "github.com/in5devilinspace/mouse-os"
    d.text((W // 2, H // 2 + 190), url, font=f(MONO, 40), fill=LIGHT,
           anchor="mm")
    uw = d.textlength(url, font=f(MONO, 40))
    d.rectangle([W // 2 + uw // 2 + 12, H // 2 + 172,
                 W // 2 + uw // 2 + 30, H // 2 + 208],
                fill=(255, 180, 84, blink))
    img.save(f"{OUT}/endcard_{tag}.png")

print("overlays written to", OUT)
