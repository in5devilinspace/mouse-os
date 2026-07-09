#!/usr/bin/env python3
"""Narration for the Mouse OS tutorial film — synthesized with libespeak-ng
via ctypes: the very same engine the product speaks through (speech-dispatcher
-> sd_espeak-ng). Fully offline, zero installs.

Two voices, both espeak-ng:
  narrator = the cursor telling its own story (en-us+m3, calm, lower)
  product  = the exact <=2-word confirmations from mouseos/feedback.py

Outputs mono 16-bit WAVs + vo.json {id: {file, dur, cap, kind}} into $TUT_MEDIA
(default ./media) for build_tutorial.py to place on the timeline.
"""
import ctypes
import json
import os
import wave
from ctypes import CFUNCTYPE, POINTER, c_char_p, c_int, c_short, c_void_p

MEDIA = os.environ.get("TUT_MEDIA", "media")
VO = os.path.join(MEDIA, "vo")
os.makedirs(VO, exist_ok=True)

LIB = ctypes.CDLL("libespeak-ng.so.1")
AUDIO_OUTPUT_RETRIEVAL = 1
P_RATE, P_VOLUME, P_PITCH, P_RANGE, P_WORDGAP = 1, 2, 3, 4, 7

_buf = bytearray()


@CFUNCTYPE(c_int, POINTER(c_short), c_int, c_void_p)
def _collect(wav, numsamples, _events):
    if numsamples > 0 and wav:
        _buf.extend(ctypes.string_at(wav, numsamples * 2))
    return 0


SR = LIB.espeak_Initialize(AUDIO_OUTPUT_RETRIEVAL, 0, None, 0)
if SR <= 0:
    raise SystemExit("espeak-ng failed to initialize")
LIB.espeak_SetSynthCallback(_collect)
LIB.espeak_Synth.argtypes = [c_char_p, ctypes.c_size_t, ctypes.c_uint, c_int,
                             ctypes.c_uint, ctypes.c_uint,
                             ctypes.c_void_p, ctypes.c_void_p]

NARRATOR = dict(voice=b"en-us+m3", rate=152, pitch=39, rng=62, gap=1)
PRODUCT = dict(voice=b"en-us", rate=170, pitch=50, rng=48, gap=0)


def synth(text, voice, rate, pitch, rng, gap):
    _buf.clear()
    LIB.espeak_SetVoiceByName(voice)
    for param, val in ((P_RATE, rate), (P_PITCH, pitch),
                       (P_RANGE, rng), (P_WORDGAP, gap)):
        LIB.espeak_SetParameter(param, val, 0)
    data = text.encode()
    LIB.espeak_Synth(data, len(data) + 1, 0, 1, 0, 0, None, None)
    LIB.espeak_Synchronize()
    return bytes(_buf)


# (id, kind, tts text, on-screen caption) — kind n=narrator, p=product word.
# Product lines are verbatim PHRASES from mouseos/feedback.py; keep them exact.
LINES = [
    ("n01", "n", "Hi. I'm your mouse pointer. As of today, you can talk to me. "
                 "Two minutes. I'll show you everything.",
     "Hi. I'm your mouse pointer. As of today, you can talk to me."),
    ("n02", "n", "Step one. Install. Clone it, then two commands. "
                 "Straight from the read me.",
     "Step 1 — install: clone, then two commands. Straight from the README."),
    ("n03", "n", "One more line needs your password. It lets me move the real "
                 "pointer. Then log out, and back in.",
     "One line needs your password — it lets me move the real pointer."),
    ("n04", "n", "Step two. The health check. Green means go. And it tells you "
                 "how to fix anything that isn't.",
     "Step 2 — the health check. Green means go."),
    ("n05", "n", "That yellow line? Optional. The grid reaches every pixel "
                 "without it.",
     "The yellow line is optional — the grid reaches every pixel without it."),
    ("n06", "n", "Step three. Download my ears. Forty megabytes. One hundred "
                 "percent offline. Then. Run.",
     "Step 3 — download my ears (~40 MB, 100% offline). Then: run."),
    ("n07", "n", "I start asleep. Stray words never move me. Wake me. Say. "
                 "Mouse wake.",
     "I start asleep — stray words never move me. Say: “mouse wake”"),
    ("n08", "n", "Aiming is a grid. One through nine. Say. Grid five.",
     "Aiming is a grid, 1–9. Say: “grid five”"),
    ("n09", "n", "Hear the quiet? Motion is silent. I only speak when "
                 "something happens.",
     "Hear the quiet? Motion is silent — I only speak when something happens."),
    ("n09b", "n", "Fine tune me. Move up a little. Move right, a lot.",
     "Fine-tune: “move up a little” · “move right a lot”"),
    ("n10", "n", "Now act. Say. Click.", "Now act. Say: “click”"),
    ("n11", "n", "A drag is two words. Hold. Then release.",
     "A drag is two words: “hold” … “release”"),
    ("n12", "n", "And the wheel. Scroll down. A lot.",
     "The wheel: “scroll down a lot”"),
    ("n13", "n", "Three words are always hot. Stop. Freezes me.",
     "Three words are always hot. “stop” freezes me."),
    ("n14", "n", "Undo. Takes it back.", "“undo” takes it back."),
    ("n15", "n", "And never mind. Means, forget it.",
     "“never mind” means forget it."),
    ("n16", "n", "Lost? Ask. Where am I.", "Lost? Ask: “where am i”"),
    ("n16b", "n", "Names work too. With one small extension, say. Point to "
                  "firefox. And I find the window.",
     "“point to firefox” — needs the Window Calls extension (grid works without)"),
    ("n17", "n", "Done for the day? Say. Mouse quit. I always double check.",
     "Done? “mouse quit” — I always double-check."),
    ("n18", "n", "Free. Offline. Open source. Get me at github. In five devil "
                 "in space. Slash. Mouse O S. Your voice. Is the pointer.",
     "Free · offline · open source — github.com/in5devilinspace/mouse-os"),
    # product confirmations — verbatim feedback lexicon
    ("ready", "p", "ready", "ready"),
    ("done", "p", "done", "done"),
    ("held", "p", "held", "held"),
    ("dropped", "p", "dropped", "dropped"),
    ("stopped", "p", "stopped", "stopped"),
    ("reverted", "p", "reverted", "reverted"),
    ("okay", "p", "okay", "okay"),
    ("middle", "p", "middle", "middle"),
    ("sure", "p", "sure?", "sure?"),
    ("goodbye", "p", "goodbye", "goodbye"),
]

manifest = {}
total = 0.0
for lid, kind, tts, cap in LINES:
    pcm = synth(tts, **(NARRATOR if kind == "n" else PRODUCT))
    path = os.path.join(VO, f"{lid}.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm)
    dur = len(pcm) / 2 / SR
    total += dur
    manifest[lid] = {"file": path, "dur": round(dur, 3), "cap": cap,
                     "kind": kind}

with open(os.path.join(MEDIA, "vo.json"), "w") as fh:
    json.dump({"sr": SR, "lines": manifest}, fh, indent=1)
print(f"voiced {len(LINES)} lines @ {SR} Hz -> {VO}  (speech: {total:.1f}s)")
