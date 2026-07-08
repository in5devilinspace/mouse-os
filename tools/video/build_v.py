#!/usr/bin/env python3
"""Vertical 9:16 (1080x1920) cut. Center-crops the Kling shots (no re-gen),
uses the vertically-rendered shot3 + overlays, same score."""
import json
import os
import subprocess

FPS, XF, ENDCARD = 30, 0.35, 3.2
VW, VH = 1080, 1920
OV = "media/ovv"
os.makedirs("media/outv", exist_ok=True)
board = json.load(open("board.json"))
SHOTS = board["shots"]
CAPS = {1: "cap1", 2: "cap2", 4: "cap4", 5: "cap5"}


def run(a):
    subprocess.run(a, check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)


def grade_caption(n, dur):
    src = f"media/shot{n}.mp4"
    out = f"media/outv/comp{n}.mp4"
    norm = (f"scale={VW}:{VH}:force_original_aspect_ratio=increase,"
            f"crop={VW}:{VH},fps={FPS},trim=0:{dur},setpts=PTS-STARTPTS")
    grade = norm if n == 3 else (
        norm + ",eq=contrast=1.07:saturation=1.06:brightness=-0.01,vignette=PI/4.5")
    if n in CAPS:
        fg = (f"[0:v]{grade}[base];[1:v]format=rgba,"
              f"fade=in:st=0.35:d=0.5:alpha=1,fade=out:st={dur-0.6:.2f}:d=0.6:alpha=1[c];"
              f"[base][c]overlay=0:0[v]")
        run(["ffmpeg", "-y", "-i", src, "-loop", "1", "-t", str(dur), "-i",
             f"{OV}/{CAPS[n]}.png", "-filter_complex", fg, "-map", "[v]", "-an",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), "-t",
             str(dur), out])
    else:
        run(["ffmpeg", "-y", "-i", src, "-filter_complex", f"[0:v]{grade}[v]",
             "-map", "[v]", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-r", str(FPS), "-t", str(dur), out])
    return out, dur


def endcard():
    lst = "media/outv/ec.txt"
    with open(lst, "w") as fh:
        t = 0.0
        while t < ENDCARD:
            for tag in ("on", "off"):
                fh.write(f"file '{os.path.abspath(OV)}/endcard_{tag}.png'\nduration 0.5\n")
                t += 0.5
        fh.write(f"file '{os.path.abspath(OV)}/endcard_on.png'\n")
    out = "media/outv/endcard.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-vf",
         f"fps={FPS},scale={VW}:{VH},fade=in:st=0:d=0.5", "-c:v", "libx264",
         "-pix_fmt", "yuv420p", "-r", str(FPS), "-t", str(ENDCARD), out])
    return out, ENDCARD


def xchain(clips):
    inp = []
    for p, _ in clips:
        inp += ["-i", p]
    fg, prev, off = [], "0:v", 0.0
    for i in range(1, len(clips)):
        off += clips[i - 1][1] - XF
        fg.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[x{i}]")
        prev = f"x{i}"
    out = "media/outv/video.mp4"
    run(["ffmpeg", "-y", *inp, "-filter_complex", ";".join(fg), "-map",
         f"[{prev}]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), out])
    return out, sum(d for _, d in clips) - XF * (len(clips) - 1)


def score(dur):
    out = "media/outv/score.wav"
    fg = (f"sine=frequency=55:duration={dur:.2f}[a];sine=frequency=110:duration={dur:.2f}[b];"
          f"[a][b]amix=inputs=2,tremolo=f=0.25:d=0.4,lowpass=f=600,volume=0.16,"
          f"afade=in:st=0:d=1.2,afade=out:st={dur-1.5:.2f}:d=1.5[dr];"
          f"sine=frequency=880:duration=0.22,volume=0.20,afade=out:st=0.05:d=0.17,adelay=9600|9600[t1];"
          f"sine=frequency=660:duration=0.22,volume=0.16,afade=out:st=0.05:d=0.17,adelay=14200|14200[t2];"
          f"[dr][t1]amix=inputs=2:duration=first[m];[m][t2]amix=inputs=2:duration=first[out]")
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-filter_complex", fg, "-map", "[out]", "-t", str(dur), out])
    return out


clips = [grade_caption(s["n"], s["seconds"]) for s in SHOTS]
clips.append(endcard())
video, dur = xchain(clips)
aud = score(dur)
out = "media/outv/mouse-os-promo-vertical.mp4"
run(["ffmpeg", "-y", "-i", video, "-i", aud, "-map", "0:v", "-map", "1:a",
     "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
     "-movflags", "+faststart", "-shortest", out])
print(f"DONE -> {out} ({os.path.getsize(out)//1024} KB, {dur:.1f}s)")
