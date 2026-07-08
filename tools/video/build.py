#!/usr/bin/env python3
"""Composite the Mouse OS promo: grade + caption each shot, crossfade, score.

Stages (each a separate ffmpeg call for robustness):
 1. normalize+grade+caption every shot -> comp{n}.mp4 (1920x1080 @30, silent)
 2. build a 3s blinking end card -> endcard.mp4
 3. xfade-chain all clips -> video.mp4
 4. synthesize a warm drone + two soft confirmation tones -> score.wav
 5. mux -> mouse-os-promo.mp4
"""
import json
import os
import subprocess

FPS = 30
XF = 0.35            # crossfade seconds
ENDCARD = 3.2
OV = "media/ov"
os.makedirs("media/out", exist_ok=True)
board = json.load(open("board.json"))
SHOTS = board["shots"]                       # n, seconds, caption
CAPS = {1: "cap1", 2: "cap2", 4: "cap4", 5: "cap5"}   # shot3 has none


def run(args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)


def grade_caption(n, dur):
    src = f"media/shot{n}.mp4"
    out = f"media/out/comp{n}.mp4"
    norm = (f"scale=1920:1080:force_original_aspect_ratio=increase,"
            f"crop=1920:1080,fps={FPS},trim=0:{dur},setpts=PTS-STARTPTS")
    if n == 3:
        grade = norm      # locally rendered, already on-brand
    else:
        grade = (norm + ",eq=contrast=1.07:saturation=1.06:brightness=-0.01,"
                 "vignette=PI/4.5")
    if n in CAPS:
        cap = f"{OV}/{CAPS[n]}.png"
        fg = (f"[0:v]{grade}[base];"
              f"[1:v]format=rgba,fade=in:st=0.35:d=0.5:alpha=1,"
              f"fade=out:st={dur-0.6:.2f}:d=0.6:alpha=1[cap];"
              f"[base][cap]overlay=0:0[v]")
        run(["ffmpeg", "-y", "-i", src, "-loop", "1", "-t", str(dur),
             "-i", cap, "-filter_complex", fg, "-map", "[v]", "-an",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
             "-t", str(dur), out])
    else:
        run(["ffmpeg", "-y", "-i", src, "-filter_complex", f"[0:v]{grade}[v]",
             "-map", "[v]", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-r", str(FPS), "-t", str(dur), out])
    return out, dur


def endcard():
    # alternate on/off frames -> blinking caret, 3.2s
    lst = "media/out/ec_list.txt"
    with open(lst, "w") as fh:
        t = 0.0
        while t < ENDCARD:
            for tag in ("on", "off"):
                fh.write(f"file '{os.path.abspath(OV)}/endcard_{tag}.png'\n")
                fh.write("duration 0.5\n")
                t += 0.5
        fh.write(f"file '{os.path.abspath(OV)}/endcard_on.png'\n")
    out = "media/out/endcard.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
         "-vf", f"fps={FPS},scale=1920:1080,fade=in:st=0:d=0.5",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
         "-t", str(ENDCARD), out])
    return out, ENDCARD


def xchain(clips):
    # clips: list of (path, dur). Build a chained xfade filtergraph.
    inputs = []
    for p, _ in clips:
        inputs += ["-i", p]
    fg = []
    prev = "0:v"
    offset = 0.0
    for i in range(1, len(clips)):
        offset += clips[i - 1][1] - XF
        lbl = f"x{i}"
        fg.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={XF}:"
                  f"offset={offset:.3f}[{lbl}]")
        prev = lbl
    out = "media/out/video.mp4"
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fg),
         "-map", f"[{prev}]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-r", str(FPS), out])
    total = sum(d for _, d in clips) - XF * (len(clips) - 1)
    return out, total


def score(dur):
    # warm low drone (55+110Hz, tremolo, lowpass) + 2 soft confirmation tones
    out = "media/out/score.wav"
    drone = (f"sine=frequency=55:duration={dur:.2f}[a];"
             f"sine=frequency=110:duration={dur:.2f}[b];"
             f"[a][b]amix=inputs=2,tremolo=f=0.25:d=0.4,lowpass=f=600,"
             f"volume=0.16,afade=in:st=0:d=1.2,afade=out:st={dur-1.5:.2f}:d=1.5[dr];"
             # confirmation tones at ~9.6s and ~14.2s
             f"sine=frequency=880:duration=0.22,volume=0.20,"
             f"afade=out:st=0.05:d=0.17,adelay=9600|9600[t1];"
             f"sine=frequency=660:duration=0.22,volume=0.16,"
             f"afade=out:st=0.05:d=0.17,adelay=14200|14200[t2];"
             f"[dr][t1]amix=inputs=2:duration=first[m1];"
             f"[m1][t2]amix=inputs=2:duration=first[out]")
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-filter_complex", drone, "-map", "[out]", "-t", str(dur), out])
    return out


def main():
    clips = []
    for s in SHOTS:
        clips.append(grade_caption(s["n"], s["seconds"]))
        print("graded shot", s["n"])
    clips.append(endcard())
    print("endcard built")
    video, dur = xchain(clips)
    print("video chained:", dur, "s")
    aud = score(dur)
    print("score built")
    out = "media/out/mouse-os-promo.mp4"
    run(["ffmpeg", "-y", "-i", video, "-i", aud, "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a",
         "160k", "-movflags", "+faststart", "-shortest", out])
    sz = os.path.getsize(out) // 1024
    print(f"DONE -> {out} ({sz} KB, ~{dur:.1f}s)")


if __name__ == "__main__":
    main()
