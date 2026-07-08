#!/usr/bin/env python3
"""Vertical (1080x1920) brand overlays for the 9:16 cut."""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
AMBER = (255, 180, 84, 255)
LIGHT = (232, 236, 246, 255)
MUTE = (150, 160, 185, 255)
OUT = "media/ovv"
os.makedirs(OUT, exist_ok=True)
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def f(p, s):
    return ImageFont.truetype(p, s)


def base():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def scrim(img, top):
    grad = Image.new("L", (1, H), 0)
    for y in range(H):
        grad.putpixel((0, y), 0 if y < top else int(210 * (y - top) / (H - top)))
    grad = grad.resize((W, H))
    black = Image.new("RGBA", (W, H), (5, 8, 16, 255))
    black.putalpha(grad)
    img.alpha_composite(black)


LX = 70          # left margin
BY = H - 230     # caption baseline band

# cap1
img = base(); scrim(img, int(H * 0.66)); d = ImageDraw.Draw(img)
d.text((LX, BY), "point.", font=f(SANS_B, 76), fill=LIGHT, anchor="lm")
img.save(f"{OUT}/cap1.png")

# cap2 — command line
img = base(); scrim(img, int(H * 0.62)); d = ImageDraw.Draw(img)
d.text((LX, BY - 55), "you", font=f(MONO, 34), fill=MUTE, anchor="lm")
d.text((LX, BY + 5), '"point to', font=f(MONO_B, 58), fill=AMBER, anchor="lm")
d.text((LX, BY + 75), 'Firefox"', font=f(MONO_B, 58), fill=AMBER, anchor="lm")
w = d.textlength('Firefox"', font=f(MONO_B, 58))
d.rectangle([LX + w + 16, BY + 52, LX + w + 34, BY + 100], fill=AMBER)
img.save(f"{OUT}/cap2.png")

# cap4
img = base(); scrim(img, int(H * 0.64)); d = ImageDraw.Draw(img)
d.text((LX, BY - 30), "hands still.", font=f(SANS_B, 70), fill=LIGHT, anchor="lm")
d.text((LX, BY + 55), "the cursor isn’t.", font=f(SANS_B, 70), fill=AMBER,
       anchor="lm")
img.save(f"{OUT}/cap4.png")

# cap5
img = base(); scrim(img, int(H * 0.62)); d = ImageDraw.Draw(img)
d.text((LX, BY - 20), "Your voice", font=f(SANS_B, 68), fill=LIGHT, anchor="lm")
d.text((LX, BY + 55), "is the pointer.", font=f(SANS_B, 68), fill=LIGHT,
       anchor="lm")
d.text((LX, BY + 130), "Free · offline · open-source", font=f(MONO, 36),
       fill=MUTE, anchor="lm")
img.save(f"{OUT}/cap5.png")


# end card
def cursor(d, x, y, s, alpha=255):
    pts = [(0, 0), (0, 19), (4.4, 14.8), (7.6, 21.4), (10.6, 20),
           (7.4, 13.6), (13.4, 13)]
    d.polygon([(x + px * s, y + py * s) for px, py in pts],
              fill=(255, 180, 84, alpha))


for blink, tag in ((255, "on"), (40, "off")):
    img = Image.new("RGBA", (W, H), (10, 14, 26, 255)); d = ImageDraw.Draw(img)
    cursor(d, W // 2 - 190, 640, 2.6)
    d.text((W // 2 - 140, 664), "MOUSE OS", font=f(MONO_B, 48), fill=LIGHT,
           anchor="lm")
    d.text((W // 2, 940), "Your voice", font=f(SANS_B, 96), fill=LIGHT,
           anchor="mm")
    d.text((W // 2, 1050), "is the pointer.", font=f(SANS_B, 96), fill=LIGHT,
           anchor="mm")
    d.text((W // 2, 1200), "Free · offline · open-source.", font=f(MONO, 42),
           fill=AMBER, anchor="mm")
    d.text((W // 2, 1256), "Try Mouse OS tonight.", font=f(MONO, 42),
           fill=AMBER, anchor="mm")
    url = "github.com/in5devilinspace/mouse-os"
    d.text((W // 2, 1380), url, font=f(MONO, 34), fill=LIGHT, anchor="mm")
    uw = d.textlength(url, font=f(MONO, 34))
    d.rectangle([W // 2 + uw // 2 + 10, 1364, W // 2 + uw // 2 + 26, 1398],
                fill=(255, 180, 84, blink))
    img.save(f"{OUT}/endcard_{tag}.png")

print("vertical overlays ->", OUT)
