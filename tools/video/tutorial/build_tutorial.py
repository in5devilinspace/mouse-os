#!/usr/bin/env python3
"""'Say It. It Moves.' — the Mouse OS 2-minute tutorial film, rendered
entirely locally: PIL frames -> ffmpeg. No generative video, no cloud, $0.

Truthfulness rules baked in:
 - every terminal line is real captured output (doctor, setup-uinput, REPL fmt)
 - every spoken confirmation is the verbatim feedback.py lexicon, voiced by
   libespeak-ng — the same synth the product speaks through (see narrate.py)
 - motion is silent on screen because motion IS silent in the product

Run:  TUT_MEDIA=media python3 narrate.py && python3 build_tutorial.py
"""
import json
import math
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

W, H, FPS, XF = 1920, 1080, 30, 0.35
MEDIA = os.environ.get("TUT_MEDIA", "media")
OUT = os.path.join(MEDIA, "out")
os.makedirs(OUT, exist_ok=True)
VOJ = json.load(open(os.path.join(MEDIA, "vo.json")))["lines"]

NAVY = (10, 14, 26)
AMBER = (255, 180, 84)
LIGHT = (232, 236, 246)
MUTE = (150, 160, 185)
GREEN = (129, 199, 132)
YELLOW = (233, 196, 106)
TBG = (16, 19, 28)
TBAR = (30, 34, 46)

DJ = "/usr/share/fonts/truetype/dejavu/"
F_MONO = ImageFont.truetype(DJ + "DejaVuSansMono.ttf", 28)
F_MONO_S = ImageFont.truetype(DJ + "DejaVuSansMono.ttf", 24)
F_MONO_B = ImageFont.truetype(DJ + "DejaVuSansMono-Bold.ttf", 30)
F_CHIP = ImageFont.truetype(DJ + "DejaVuSansMono-Bold.ttf", 32)
F_CAP = ImageFont.truetype(DJ + "DejaVuSans-Bold.ttf", 34)
F_CHAP = ImageFont.truetype(DJ + "DejaVuSansMono.ttf", 26)
F_BIG = ImageFont.truetype(DJ + "DejaVuSans-Bold.ttf", 88)
F_T48 = ImageFont.truetype(DJ + "DejaVuSansMono-Bold.ttf", 48)
F_NUM = ImageFont.truetype(DJ + "DejaVuSansMono-Bold.ttf", 64)


def dur(key):
    return VOJ[key]["dur"]


def ease(p):
    return 1 - (1 - min(max(p, 0.0), 1.0)) ** 3


def lerp(a, b, p):
    return a + (b - a) * p


def rr(d, box, rad, **kw):
    d.rounded_rectangle(box, radius=rad, **kw)


def _halo(R, peak):
    im = Image.new("RGBA", (R * 2, R * 2), (0, 0, 0, 0))
    px = im.load()
    for iy in range(R * 2):
        for ix in range(R * 2):
            r = math.hypot(ix - R, iy - R) / R
            if r < 1:
                px[ix, iy] = AMBER + (int(peak * (1 - r) ** 2),)
    return im


HALO = _halo(48, 95)
HALO_HELD = _halo(62, 140)


def cursor(d, x, y, s, col=AMBER, alpha=255, keyline=True):
    pts = [(0, 0), (0, 19), (4.4, 14.8), (7.6, 21.4), (10.6, 20),
           (7.4, 13.6), (13.4, 13)]
    poly = [(x + px * s, y + py * s) for px, py in pts]
    if keyline:
        d.polygon(poly, fill=col + (alpha,),
                  outline=(6, 9, 18, alpha), width=max(2, int(s)))
    else:
        d.polygon(poly, fill=col + (alpha,))


def segs_draw(d, x, y, segs, font=F_MONO):
    for text, col in segs:
        d.text((x, y), text, font=font, fill=col + (255,))
        x += d.textlength(text, font=font)
    return x


def chapter_tag(d, label, alpha=210):
    if not label:
        return
    d.ellipse([30, 66, 44, 80], fill=AMBER + (alpha,))
    d.text((58, 60), label, font=F_CHAP, fill=MUTE + (alpha,))


def caption_strip(d, text, a):
    if a <= 0:
        return
    for i in range(120):
        y = H - 120 + i
        d.line([(0, y), (W, y)], fill=(5, 8, 16, int(a * 0.82 * i / 120 * 255)))
    d.text((W / 2, H - 52), text, font=F_CAP,
           fill=LIGHT + (int(a * 255),), anchor="mm")


def chip_alpha(t, t0, hold):
    if t < t0 or t > t0 + hold + 0.25:
        return 0.0, 0
    if t < t0 + 0.18:
        p = (t - t0) / 0.18
        return p, int(14 * (1 - p))
    if t > t0 + hold:
        return 1 - (t - t0 - hold) / 0.25, 0
    return 1.0, 0


def chip_you(d, t, t0, hold, text):
    a, rise = chip_alpha(t, t0, hold)
    if a <= 0:
        return
    al = int(a * 255)
    w = d.textlength(text, font=F_CHIP) + 96
    y0 = 906 + rise
    rr(d, [64, y0, 64 + w, y0 + 62], 31, fill=(16, 22, 38, int(a * 235)),
       outline=MUTE + (al,), width=2)
    pulse = 0.5 + 0.5 * math.sin((t - t0) * 7)
    d.ellipse([88, y0 + 21, 108, y0 + 41], outline=AMBER + (al,), width=3)
    d.ellipse([94, y0 + 27, 102, y0 + 35],
              fill=AMBER + (int(al * (0.4 + 0.6 * pulse)),))
    d.text((124, y0 + 30), text, font=F_CHIP, fill=LIGHT + (al,), anchor="lm")


def chip_mouse(d, t, t0, hold, word):
    a, rise = chip_alpha(t, t0, hold)
    if a <= 0:
        return
    al = int(a * 255)
    w = d.textlength(word, font=F_CHIP) + 92
    x1 = W - 64
    y0 = 906 + rise
    rr(d, [x1 - w, y0, x1, y0 + 62], 31, fill=(26, 20, 10, int(a * 235)),
       outline=AMBER + (al,), width=2)
    cursor(d, x1 - w + 26, y0 + 16, 1.35, alpha=al)
    d.text((x1 - w + 62, y0 + 30), word, font=F_CHIP,
           fill=AMBER + (al,), anchor="lm")


def chip_info(d, t, t0, hold, text):
    a, rise = chip_alpha(t, t0, hold)
    if a <= 0:
        return
    al = int(a * 255)
    w = d.textlength(text, font=F_MONO_S) + 56
    y0 = 848 + rise
    rr(d, [(W - w) / 2, y0, (W + w) / 2, y0 + 46], 23,
       fill=(12, 16, 28, int(a * 225)), outline=MUTE + (int(al * 0.6),), width=1)
    d.text((W / 2, y0 + 23), text, font=F_MONO_S, fill=MUTE + (al,), anchor="mm")


class Scene:
    """Shared timeline: audio (t,key), captions (t,dur,text), chips, dur."""

    def __init__(self, chapter):
        self.chapter = chapter
        self.t = 0.8
        self.audio, self.caps = [], []
        self.you_chips, self.mouse_chips, self.info_chips = [], [], []

    def vo(self, key, pad=0.45, block=True):
        t0 = self.t
        self.audio.append((t0, key, 1.0))
        self.caps.append((t0, dur(key) + 0.3, VOJ[key]["cap"]))
        if block:
            self.t = t0 + dur(key) + pad
        return t0

    def reply(self, key, delay=0.3, hold=1.25):
        t0 = self.t + delay
        self.audio.append((t0, key, 0.95))
        self.mouse_chips.append((t0, hold, VOJ[key]["cap"]))
        self.t = t0 + max(dur(key), 0.5) + 0.35

    def you(self, text, lead=0.85, hold=1.7):
        self.you_chips.append((self.t, hold, text))
        self.t += lead
        return self.t

    def info(self, text, hold=2.4):
        self.info_chips.append((self.t, hold, text))

    def pause(self, s):
        self.t += s

    def finalize(self, tail=0.7):
        self.dur = math.ceil((self.t + tail) * FPS) / FPS
        self.frames = int(round(self.dur * FPS))

    def draw_common(self, d, t):
        chapter_tag(d, self.chapter)
        for t0, hold, text in self.you_chips:
            chip_you(d, t, t0, hold, text)
        for t0, hold, word in self.mouse_chips:
            chip_mouse(d, t, t0, hold, word)
        for t0, hold, text in self.info_chips:
            chip_info(d, t, t0, hold, text)
        for t0, cdur, text in self.caps:
            if t0 <= t <= t0 + cdur:
                a = min(1.0, (t - t0) / 0.25, max(0.0, (t0 + cdur - t) / 0.3))
                caption_strip(d, text, a)


# ---------------------------------------------------------------- terminal --
TW = (150, 84, 1770, 992)          # window box
TROWS_Y, TLH = 172, 38
TMAXROWS = 20


class Term(Scene):
    def __init__(self, chapter):
        super().__init__(chapter)
        self.lines = []            # ('cmd', text, t0) | ('out', segs, t0)
        self.hls = []              # (t0, t1, line_index)

    def cmd(self, text, outs, type_pre=0.3, cps=0.024):
        t0 = self.t + type_pre
        self.lines.append(("cmd", text, t0))
        te = t0 + len(text) * cps + 0.22
        ot = te + 0.16
        for segs in outs:
            self.lines.append(("out", segs, ot))
            ot += 0.10
        self.t = ot + 0.45

    def hl_last(self, n, t0, t1):
        base = len(self.lines) - n
        for i in range(n):
            self.hls.append((t0, t1, base + i))

    def draw(self, t):
        img = Image.new("RGBA", (W, H), NAVY + (255,))
        d = ImageDraw.Draw(img)
        rr(d, [TW[0] + 10, TW[1] + 14, TW[2] + 10, TW[3] + 14], 16,
           fill=(0, 0, 0, 90))
        rr(d, TW, 14, fill=TBG + (255,))
        rr(d, [TW[0], TW[1], TW[2], TW[1] + 52], 14, fill=TBAR + (255,))
        d.rectangle([TW[0], TW[1] + 30, TW[2], TW[1] + 52], fill=TBAR + (255,))
        for i, col in enumerate(((236, 106, 94), (243, 191, 79),
                                 (98, 197, 84))):
            d.ellipse([TW[0] + 24 + i * 34, TW[1] + 16, TW[0] + 44 + i * 34,
                       TW[1] + 36], fill=col + (255,))
        d.text(((TW[0] + TW[2]) / 2, TW[1] + 26),
               "indevilinspace@mouse-os: ~/mouse-os", font=F_MONO_S,
               fill=MUTE + (255,), anchor="mm")

        vis = [(i, ln) for i, ln in enumerate(self.lines) if ln[2] <= t]
        rows = vis[-TMAXROWS:]
        y = TROWS_Y
        for idx, ln in rows:
            for h0, h1, hi in self.hls:
                if hi == idx and h0 <= t <= h1:
                    a = int(70 + 50 * math.sin((t - h0) * 5))
                    rr(d, [TW[0] + 26, y - 4, TW[2] - 26, y + 30], 6,
                       fill=AMBER + (a // 3,), outline=AMBER + (a,), width=1)
            if ln[0] == "cmd":
                shown = ln[1][:max(0, int((t - ln[2]) / 0.024))]
                x = segs_draw(d, TW[0] + 40, y, [("❯ ", GREEN)], F_MONO_B)
                x = segs_draw(d, x, y, [(shown, LIGHT)])
                typing = shown != ln[1]
                if typing or (idx == len(self.lines) - 1
                              and int(t * 2) % 2 == 0):
                    d.rectangle([x + 4, y + 2, x + 18, y + 30],
                                fill=AMBER + (230,))
            else:
                segs_draw(d, TW[0] + 40, y, ln[1])
            y += TLH
        self.draw_common(d, t)
        return img


# ----------------------------------------------------------------- desktop --
FFW = (1020, 128, 1832, 934)       # firefox window
FLW = (104, 208, 736, 786)         # files window


class Desk(Scene):
    def __init__(self, chapter, pos0, scroll0=0.0, awake=True):
        super().__init__(chapter)
        self.pos = pos0
        self.segs, self.blooms, self.rings = [], [], []
        self.holds, self.scrolls = [], []
        self.grid_ev = []
        self.scroll0, self.awake0 = scroll0, awake
        self.wake_t = None
        self.fade_t = None
        self.point_hl = []

    def glide(self, p, gdur):
        self.segs.append((self.t, self.t + gdur, self.pos, p))
        self.pos = p
        self.t += gdur

    def grid(self, cell, target):
        self.grid_ev.append((self.t, 1.6, cell))
        self.t += 0.35
        self.glide(target, 0.6)
        self.t += 0.35

    def click(self):
        self.blooms.append(self.t)
        self.t += 0.25

    def hold_span(self, from_t):
        self.holds.append([from_t, None])

    def release(self):
        self.holds[-1][1] = self.t

    def scroll(self, dy, sdur=0.85):
        s0 = self.scroll0 + sum(s[3] - s[2] for s in self.scrolls)
        self.scrolls.append((self.t, self.t + sdur, s0, s0 + dy))
        self.t += sdur

    def wake(self):
        self.wake_t = self.t
        self.rings.append(self.t)
        self.t += 0.5

    def stop_flash(self):
        self.rings.append(self.t)
        self.t += 0.3

    def fade_out(self):
        self.fade_t = self.t
        self.t += 1.1

    def highlight_window(self):
        self.point_hl.append((self.t, 1.4))

    # -- drawing --
    def cur_pos(self, t):
        x, y = self.pos0_frozen
        for t0, t1, p0, p1 in self.segs:
            if t >= t1:
                x, y = p1
            elif t >= t0:
                p = ease((t - t0) / (t1 - t0))
                x, y = lerp(p0[0], p1[0], p), lerp(p0[1], p1[1], p)
        return x, y

    def cur_scroll(self, t):
        s = self.scroll0
        for t0, t1, s0, s1 in self.scrolls:
            if t >= t1:
                s = s1
            elif t >= t0:
                s = lerp(s0, s1, ease((t - t0) / (t1 - t0)))
        return s

    def finalize(self, tail=0.7):
        super().finalize(tail)
        self.pos0_frozen = self.segs[0][2] if self.segs else self.pos

    def draw(self, t):
        img = Image.new("RGBA", (W, H), NAVY + (255,))
        d = ImageDraw.Draw(img)
        for gx in range(0, W, 120):                     # faint dot field
            for gy in range(60, H, 120):
                d.point((gx, gy), fill=(60, 70, 100, 255))
        # top bar
        d.rectangle([0, 0, W, 40], fill=(5, 7, 13, 255))
        d.text((28, 20), "Activities", font=F_MONO_S, fill=MUTE + (255,),
               anchor="lm")
        d.text((W / 2, 20), "Jul 8  20:32", font=F_MONO_S, fill=LIGHT + (255,),
               anchor="mm")
        for i in range(3):
            d.ellipse([W - 118 + i * 34, 14, W - 106 + i * 34, 26],
                      fill=MUTE + (255,))
        scroll = self.cur_scroll(t)
        self._window_files(d)
        self._window_ff(d, t, scroll)
        # grid overlay
        for t0, gdur, cell in self.grid_ev:
            if t0 - 0.2 <= t <= t0 + gdur:
                a = min(1.0, (t - t0 + 0.2) / 0.3,
                        max(0.0, (t0 + gdur - t) / 0.4))
                al = int(150 * a)
                for i in (1, 2):
                    d.line([(W * i / 3, 40), (W * i / 3, H)],
                           fill=AMBER + (al,), width=2)
                    d.line([(0, 40 + (H - 40) * i / 3),
                            (W, 40 + (H - 40) * i / 3)],
                           fill=AMBER + (al,), width=2)
                for n in range(9):
                    cx = W * (n % 3 * 2 + 1) / 6
                    cy = 40 + (H - 40) * (n // 3 * 2 + 1) / 6
                    col = AMBER if n + 1 == cell else MUTE
                    d.text((cx, cy), str(n + 1), font=F_NUM,
                           fill=col + (int(al * 1.5) if n + 1 == cell
                                       else al,), anchor="mm")
        # cursor + effects
        x, y = self.cur_pos(t)
        awake = self.awake0 or (self.wake_t is not None and t >= self.wake_t)
        held = any(h0 <= t <= (h1 or self.dur) for h0, h1 in self.holds)
        for rt in self.rings:
            if rt <= t <= rt + 0.7:
                p = ease((t - rt) / 0.7)
                rad = lerp(10, 120, p)
                d.ellipse([x - rad, y - rad, x + rad, y + rad],
                          outline=AMBER + (int(210 * (1 - p)),), width=3)
        for bt in self.blooms:
            if bt <= t <= bt + 0.5:
                p = ease((t - bt) / 0.5)
                rad = lerp(6, 70, p)
                d.ellipse([x - rad, y - rad, x + rad, y + rad],
                          outline=AMBER + (int(230 * (1 - p)),), width=4)
        fade = 1.0
        if self.fade_t is not None and t >= self.fade_t:
            fade = max(0.25, 1 - (t - self.fade_t) / 1.0)
        k = (1.0 if awake else 0.0) * fade
        if k > 0.02:
            halo = HALO_HELD if held else HALO
            if k < 0.98:
                halo = halo.copy()
                halo.putalpha(halo.getchannel("A").point(
                    lambda v: int(v * k)))
            img.alpha_composite(halo, (int(x + 14 - halo.width / 2),
                                       int(y + 24 - halo.height / 2)))
        if held:
            rr(d, [x + 18, y + 34, x + 158, y + 124], 10,
               fill=(33, 42, 66, 245), outline=AMBER + (255,), width=3)
            d.text((x + 88, y + 79), "tile", font=F_MONO_S,
                   fill=LIGHT + (255,), anchor="mm")
        cursor(d, x, y, 2.2, alpha=int((255 if awake else 150) * fade))
        self.draw_common(d, t)
        return img

    def _window_files(self, d):
        x0, y0, x1, y1 = FLW
        rr(d, [x0 + 8, y0 + 12, x1 + 8, y1 + 12], 14, fill=(0, 0, 0, 80))
        rr(d, [x0, y0, x1, y1], 12, fill=(21, 26, 40, 255))
        rr(d, [x0, y0, x1, y0 + 46], 12, fill=(30, 36, 54, 255))
        d.rectangle([x0, y0 + 24, x1, y0 + 46], fill=(30, 36, 54, 255))
        d.text(((x0 + x1) / 2, y0 + 23), "Files", font=F_MONO_S,
               fill=MUTE + (255,), anchor="mm")
        d.rectangle([x0, y0 + 46, x0 + 150, y1], fill=(17, 21, 34, 255))
        for i in range(6):
            fx = x0 + 190 + (i % 3) * 150
            fy = y0 + 90 + (i // 3) * 150
            rr(d, [fx, fy, fx + 104, fy + 84], 10, fill=(38, 47, 72, 255))
            rr(d, [fx, fy, fx + 44, fy + 16], 6, fill=(48, 59, 88, 255))

    def _window_ff(self, d, t, scroll):
        x0, y0, x1, y1 = FFW
        rr(d, [x0 + 8, y0 + 12, x1 + 8, y1 + 12], 14, fill=(0, 0, 0, 90))
        rr(d, [x0, y0, x1, y1], 12, fill=(19, 23, 37, 255))
        rr(d, [x0, y0, x1, y0 + 46], 12, fill=(30, 36, 54, 255))
        d.rectangle([x0, y0 + 24, x1, y0 + 46], fill=(30, 36, 54, 255))
        d.text(((x0 + x1) / 2, y0 + 23), "Mouse OS — Firefox", font=F_MONO_S,
               fill=MUTE + (255,), anchor="mm")
        cy0, cy1 = y0 + 46, y1 - 8
        ty = y0 + 96 - scroll
        if cy0 < ty - 24 and ty + 24 < cy1:
            cursor(d, x0 + 56, ty - 20, 1.9)
            d.text((x0 + 110, ty), "MOUSE OS", font=F_T48,
                   fill=LIGHT + (255,), anchor="lm")
        widths = [0.86, 0.72, 0.80, 0.55, 0.78, 0.66, 0.84, 0.60, 0.74, 0.52,
                  0.81, 0.69, 0.77, 0.58]
        by = y0 + 170 - scroll
        for i, wfrac in enumerate(widths):
            b0, b1 = by + i * 52, by + i * 52 + 22
            b0c, b1c = max(b0, cy0 + 6), min(b1, cy1)
            if b1c > b0c:
                col = AMBER if i == 4 else (52, 62, 92)
                al = 120 if i == 4 else 255
                rr(d, [x0 + 56, b0c, x0 + 56 + (x1 - x0 - 130) * wfrac, b1c],
                   8, fill=(col + (al,)) if i == 4 else col + (255,))
        for ht0, hdur in self.point_hl:
            if ht0 - 0.1 <= t <= ht0 + hdur:
                a = min(1.0, (t - ht0 + 0.1) / 0.2,
                        max(0.0, (ht0 + hdur - t) / 0.4))
                rr(d, [x0 - 5, y0 - 5, x1 + 5, y1 + 5], 15,
                   outline=AMBER + (int(220 * a),), width=4)


# ----------------------------------------------------------------- endcard --
class EndCard(Scene):
    def draw(self, t):
        img = Image.new("RGBA", (W, H), NAVY + (255,))
        d = ImageDraw.Draw(img)
        a = int(255 * min(1.0, t / 0.5))
        cursor(d, W / 2 - 210, 300, 3.0, alpha=a)
        d.text((W / 2 - 150, 330), "MOUSE OS", font=F_T48, fill=LIGHT + (a,),
               anchor="lm")
        d.text((W / 2, 520), "Your voice is the pointer.", font=F_BIG,
               fill=LIGHT + (a,), anchor="mm")
        d.text((W / 2, 640), "say it. it moves.", font=F_CHIP,
               fill=AMBER + (a,), anchor="mm")
        url = "github.com/in5devilinspace/mouse-os"
        d.text((W / 2, 760), url, font=F_MONO_B, fill=LIGHT + (a,),
               anchor="mm")
        uw = d.textlength(url, font=F_MONO_B)
        if int(t * 2) % 2 == 0:
            d.rectangle([W / 2 + uw / 2 + 12, 744, W / 2 + uw / 2 + 28, 778],
                        fill=AMBER + (a,))
        d.text((W / 2, 850), "free · offline · open source", font=F_MONO_S,
               fill=MUTE + (a,), anchor="mm")
        self.draw_common(d, t)
        return img


# ------------------------------------------------------------------ script --
def build_scenes():
    scenes = []

    s0 = Desk(None, (430, 840), awake=False)          # cold open
    s0.pause(0.2)
    s0.vo("n01", block=False)
    s0.pause(1.2)
    s0.glide((620, 700), 1.6)
    s0.pause(dur("n01") - 2.8 + 0.6)
    s0.finalize(0.5)
    scenes.append(s0)

    s1 = Term("01 · install")                          # install
    s1.vo("n02", block=False)
    s1.pause(1.0)
    s1.cmd("git clone https://github.com/in5devilinspace/mouse-os && cd mouse-os",
           [[("Cloning into 'mouse-os'…  done.", MUTE)]])
    s1.cmd("uv venv .venv",
           [[("Creating virtual environment at: .venv", MUTE)]])
    s1.cmd("VIRTUAL_ENV=$PWD/.venv uv pip install -e '.[voice]'",
           [[("Installed 14 packages in 1.2s", MUTE)]])
    s1.pause(0.3)
    s1.vo("n03", block=False)
    s1.pause(1.3)
    s1.cmd("sudo bash scripts/setup-uinput.sh",
           [[("[sudo] password for indevilinspace:", MUTE)],
            [("→ loading the uinput kernel module (now and at every boot)",
              LIGHT)],
            [("→ udev rule: /dev/uinput owned by group 'input', mode 0660",
              LIGHT)],
            [("→ adding indevilinspace to the 'input' group", LIGHT)],
            [("Done. Log out and back in, then verify with: ", GREEN),
             ("mouseos doctor", LIGHT)]])
    s1.pause(0.9)
    s1.finalize()
    scenes.append(s1)

    s2 = Term("02 · health check")                     # doctor (real output)
    s2.vo("n04", block=False)
    s2.pause(1.2)
    s2.cmd("mouseos doctor",
           [[("================================================================",
              (60, 70, 100))],
            [("[  OK  ] ", GREEN), ("uinput         ", LIGHT),
             ("virtual input devices allowed", MUTE)],
            [("[  OK  ] ", GREEN), ("spd-say        ", LIGHT),
             ("spoken feedback available", MUTE)],
            [("[  OK  ] ", GREEN), ("microphone     ", LIGHT),
             ("capture via pw-record", MUTE)],
            [("[  OK  ] ", GREEN), ("vosk           ", LIGHT),
             ("model at ~/.cache/mouseos/vosk-model-small-en-us-0.15", MUTE)],
            [("[  OK  ] ", GREEN), ("screen         ", LIGHT),
             ("3440x1440 (Mutter D-Bus)", MUTE)],
            [("[ FIX  ] ", YELLOW), ("windows        ", LIGHT),
             ("GNOME 'Window Calls' extension not detected", MUTE)],
            [("         fix → grid one..nine reaches every pixel meanwhile",
              YELLOW)]])
    s2.pause(0.2)
    t0 = s2.vo("n05", block=False)
    s2.hl_last(2, t0, t0 + dur("n05") + 0.4)
    s2.pause(dur("n05") + 0.7)
    s2.finalize()
    scenes.append(s2)

    s3 = Term("03 · run")                              # model + run
    s3.vo("n06", block=False)
    s3.pause(1.4)
    s3.cmd("mouseos setup-model",
           [[("downloading https://alphacephei.com/vosk/models/"
              "vosk-model-small-en-us-0.15.zip (~40 MB)…", MUTE)],
            [("done: ~/.cache/mouseos/vosk-model-small-en-us-0.15", MUTE)]])
    s3.cmd("mouseos run --input voice",
           [[("mouse » ", AMBER), ("pointer backend: uinput_abs", LIGHT)],
            [("mouse » ", AMBER),
             ("listening (say 'mouse wake' to begin,", LIGHT)],
            [("        ", AMBER),
             (" 'mouse quit' then 'confirm quit' to exit)", LIGHT)]])
    s3.pause(1.0)
    s3.finalize()
    scenes.append(s3)

    s4 = Desk("04 · wake", (620, 700), awake=False)    # wake
    s4.vo("n07")
    s4.you("mouse wake")
    s4.wake()
    s4.reply("ready")
    s4.pause(0.4)
    s4.finalize()
    scenes.append(s4)

    s5 = Desk("05 · aim", (620, 700))                  # grid + nudge + name
    s5.vo("n08")
    s5.you("grid five")
    s5.grid(5, (960, 540))
    s5.vo("n09", pad=0.3)
    s5.vo("n09b", block=False)
    s5.pause(1.1)
    s5.you("move up a little", hold=1.4)
    s5.glide((960, 515), 0.35)
    s5.pause(0.5)
    s5.you("move right a lot", hold=1.4)
    s5.glide((1260, 515), 0.55)
    s5.pause(0.4)
    s5.vo("n16b", block=False)
    s5.pause(2.2)
    s5.you("point to firefox", hold=1.6)
    s5.glide((1426, 152), 0.6)
    s5.highlight_window()
    s5.pause(max(0.0, dur("n16b") - 2.2 - 0.85 - 0.6) + 0.7)
    s5.finalize()
    scenes.append(s5)

    s6 = Desk("06 · act", (1426, 152))                 # click/drag/scroll
    s6.glide((1260, 515), 0.5)
    s6.vo("n10", pad=0.2)
    s6.you("click")
    s6.click()
    s6.reply("done")
    s6.vo("n11", pad=0.2)
    hold_at = s6.you("hold")
    s6.hold_span(hold_at)
    s6.reply("held", delay=0.2)
    s6.glide((1420, 660), 0.9)
    s6.pause(0.2)
    s6.you("release", hold=1.4)
    s6.release()
    s6.reply("dropped", delay=0.2)
    s6.vo("n12", block=False)
    s6.pause(1.4)
    s6.you("scroll down a lot", hold=1.5)
    s6.scroll(300)
    s6.pause(0.6)
    s6.finalize()
    scenes.append(s6)

    s7 = Desk("07 · safety words", (1420, 660), scroll0=300)
    s7.vo("n13", block=False)
    s7.pause(1.6)
    s7.you("stop", hold=1.3)
    s7.stop_flash()
    s7.reply("stopped", delay=0.2)
    s7.vo("n14", pad=0.25)
    s7.you("undo", hold=1.3)
    s7.glide((1260, 515), 0.6)
    s7.reply("reverted", delay=0.1)
    s7.vo("n15", pad=0.25)
    s7.you("never mind", hold=1.3)
    s7.reply("okay", delay=0.25)
    s7.vo("n16", pad=0.2)
    s7.you("where am i", hold=1.5)
    s7.info("at (1260, 515) — near center", hold=2.6)
    s7.reply("middle", delay=0.3)
    s7.pause(0.4)
    s7.finalize()
    scenes.append(s7)

    s8 = Desk("08 · quit", (1260, 515), scroll0=300)   # two-step quit
    s8.vo("n17", pad=0.3)
    s8.you("mouse quit", hold=1.5)
    s8.reply("sure", delay=0.3)
    s8.info('say "confirm quit" within 10 seconds', hold=2.6)
    s8.pause(0.7)
    s8.you("confirm quit", hold=1.5)
    s8.reply("goodbye", delay=0.3)
    s8.fade_out()
    s8.finalize()
    scenes.append(s8)

    s9 = EndCard(None)                                 # end card
    s9.pause(0.2)
    s9.vo("n18", pad=0.9)
    s9.finalize(0.9)
    scenes.append(s9)
    return scenes


# ------------------------------------------------------------------ render --
def run(a):
    subprocess.run(a, check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)


def render_scene(i, sc):
    path = f"{OUT}/scene{i}.mp4"
    p = subprocess.Popen(
        ["ffmpeg", "-y", "-f", "image2pipe", "-vcodec", "png", "-r", str(FPS),
         "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
         "-pix_fmt", "yuv420p", "-r", str(FPS), path],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)
    for f in range(sc.frames):
        sc.draw(f / FPS).convert("RGB").save(p.stdin, "PNG")
    p.stdin.close()
    p.wait()
    return path


def main():
    scenes = build_scenes()
    starts, acc = [], 0.0
    for i, sc in enumerate(scenes):
        starts.append(acc)
        acc += sc.dur - XF
    total = acc + XF
    print("plan:")
    for i, sc in enumerate(scenes):
        print(f"  scene{i}  start {starts[i]:6.2f}s  dur {sc.dur:5.2f}s  "
              f"{sc.chapter or '—'}")
    print(f"  total ≈ {total:.1f}s")

    clips = []
    for i, sc in enumerate(scenes):
        clips.append((render_scene(i, sc), sc.dur))
        print(f"rendered scene{i}")

    inp, fg, prev, off = [], [], "0:v", 0.0
    for pth, _ in clips:
        inp += ["-i", pth]
    for i in range(1, len(clips)):
        off += clips[i - 1][1] - XF
        fg.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={XF}:"
                  f"offset={off:.3f}[x{i}]")
        prev = f"x{i}"
    video = f"{OUT}/video.mp4"
    run(["ffmpeg", "-y", *inp, "-filter_complex", ";".join(fg), "-map",
         f"[{prev}]", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
         "-pix_fmt", "yuv420p", "-r", str(FPS), video])
    print("video chained")

    drone = f"{OUT}/drone.wav"
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
         "-filter_complex",
         f"sine=frequency=55:duration={total:.2f}[a];"
         f"sine=frequency=110:duration={total:.2f}[b];"
         f"[a][b]amix=inputs=2,tremolo=f=0.25:d=0.4,lowpass=f=600,"
         f"volume=0.11,afade=in:st=0:d=1.2,"
         f"afade=out:st={total-1.6:.2f}:d=1.6[out]",
         "-map", "[out]", "-t", f"{total:.2f}", drone])

    audio_ev, caps_ev = [], []
    for i, sc in enumerate(scenes):
        for t0, key, gain in sc.audio:
            audio_ev.append((starts[i] + t0, VOJ[key]["file"], gain))
        for t0, cdur, text in sc.caps:
            caps_ev.append((starts[i] + t0, cdur, text))
    audio_ev.sort()
    caps_ev.sort()

    inputs = ["-i", video, "-i", drone]
    graph, mix = [], "[1:a]aresample=48000,volume=1.0[a0];"
    labels = ["[a0]"]
    for k, (gt, wav, gain) in enumerate(audio_ev):
        inputs += ["-i", wav]
        ms = int(gt * 1000)
        graph.append(f"[{k + 2}:a]aresample=48000,adelay={ms}|{ms},"
                     f"volume={gain}[a{k + 1}]")
        labels.append(f"[a{k + 1}]")
    graph.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:"
                 f"duration=first,alimiter=limit=0.95[mix]")
    final = f"{OUT}/mouse-os-tutorial.mp4"
    run(["ffmpeg", "-y", *inputs, "-filter_complex", mix + ";".join(graph),
         "-map", "0:v", "-map", "[mix]", "-c:v", "copy", "-c:a", "aac",
         "-b:a", "160k", "-ac", "2", "-movflags", "+faststart",
         "-shortest", final])

    def ts(sec, sep=","):
        h, rem = divmod(sec, 3600)
        m, s = divmod(rem, 60)
        return f"{int(h):02}:{int(m):02}:{int(s):02}{sep}{int(sec % 1 * 1000):03}"

    with open(f"{OUT}/mouse-os-tutorial.srt", "w") as srt, \
            open(f"{OUT}/mouse-os-tutorial.vtt", "w") as vtt:
        vtt.write("WEBVTT\n\n")
        for n, (t0, cdur, text) in enumerate(caps_ev, 1):
            srt.write(f"{n}\n{ts(t0)} --> {ts(t0 + cdur)}\n{text}\n\n")
            vtt.write(f"{ts(t0, '.')} --> {ts(t0 + cdur, '.')}\n{text}\n\n")

    wake_i = next(i for i, sc in enumerate(scenes) if sc.chapter
                  and sc.chapter.startswith("04"))
    poster_t = starts[wake_i] + scenes[wake_i].mouse_chips[0][0] + 0.3
    run(["ffmpeg", "-y", "-ss", f"{poster_t:.2f}", "-i", final, "-frames:v",
         "1", "-q:v", "3", f"{OUT}/mouse-os-tutorial-poster.jpg"])
    sz = os.path.getsize(final) // 1024
    print(f"DONE -> {final} ({sz} KB, ~{total:.1f}s), poster @ {poster_t:.1f}s")


if __name__ == "__main__":
    main()
