#!/usr/bin/env python3
"""Shot 3 — the abstract 'voice becomes light becomes the pointer' hero beat.

Fully rendered locally (Canvas-style via PIL) so it matches the brand palette
exactly: an amber point of light streaks across a deep-navy void, decelerates
with weight, and resolves into the crisp arrow cursor with a click-ring bloom.
Outputs a 5s 1920x1080 30fps mp4 via ffmpeg image2pipe.
"""
import math
import subprocess
import sys

import os as _os
W = int(_os.environ.get("VW", "1920"))
H = int(_os.environ.get("VH", "1080"))
FPS, DUR = 30, 5
N = FPS * DUR
NAVY = (10, 14, 26)
AMBER = (255, 180, 84)

from PIL import Image, ImageDraw

OUT = sys.argv[1] if len(sys.argv) > 1 else "media/shot3.mp4"


def ease_out(t):
    return 1 - (1 - t) ** 3


def lerp(a, b, t):
    return a + (b - a) * t


def add_glow(draw, x, y, r, col, a):
    for i in range(6, 0, -1):
        rr = r * i / 2
        alpha = int(a * (0.10 if i > 2 else 0.28))
        draw.ellipse([x - rr, y - rr, x + rr, y + rr],
                     fill=col + (alpha,))


def cursor(draw, x, y, s, col, alpha=255):
    pts = [(0, 0), (0, 19), (4.4, 14.8), (7.6, 21.4), (10.6, 20),
           (7.4, 13.6), (13.4, 13)]
    poly = [(x + px * s, y + py * s) for px, py in pts]
    draw.polygon(poly, fill=col + (alpha,))


def frame(i):
    t = i / (N - 1)
    img = Image.new("RGB", (W, H), NAVY)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    # faint navy vignette gradient (subtle)
    # travel path: from left low to a landing point right-of-center
    x0, y0 = W * 0.12, H * 0.62
    x1, y1 = W * 0.68, H * 0.42
    travel = ease_out(min(1.0, t / 0.72))
    cx = lerp(x0, x1, travel)
    cy = lerp(y0, y1, travel)

    # comet trail (fading samples behind current pos)
    for k in range(1, 26):
        tt = travel - k * 0.012
        if tt < 0:
            break
        tx = lerp(x0, x1, tt)
        ty = lerp(y0, y1, tt)
        a = int(120 * (1 - k / 26) ** 2)
        rr = lerp(2, 9, 1 - k / 26)
        d.ellipse([tx - rr, ty - rr, tx + rr, ty + rr], fill=AMBER + (a,))

    landed = t > 0.72
    if not landed:
        add_glow(d, cx, cy, 34, AMBER, 200)
        d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=AMBER + (255,))
    else:
        # click ring bloom + resolve into the arrow cursor
        p = (t - 0.72) / 0.28
        ring = ease_out(p)
        rr = lerp(6, 120, ring)
        a = int(200 * (1 - ring))
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  outline=AMBER + (a,), width=3)
        add_glow(d, cx, cy, lerp(34, 10, ring), AMBER, int(200 * (1 - ring)))
        cursor(d, cx - 2, cy - 2, lerp(1.4, 2.6, ring), AMBER,
               alpha=int(lerp(180, 255, ring)))

    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    return img


def main():
    p = subprocess.Popen([
        "ffmpeg", "-y", "-f", "image2pipe", "-vcodec", "png", "-r", str(FPS),
        "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
        OUT], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)
    for i in range(N):
        frame(i).save(p.stdin, "PNG")
    p.stdin.close()
    p.wait()
    print("wrote", OUT)


if __name__ == "__main__":
    main()
