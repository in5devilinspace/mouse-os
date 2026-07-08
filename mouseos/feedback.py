"""Spoken + console feedback.

Sally's contract: spoken confirmations are <=2 words; the mic pauses only
while TTS actually plays and re-arms within 200 ms (SpeechSink signals a
MuteGate around the spd-say call). The feedback lexicon shares no word with
the command grammar — proven by test — so the system can never hear itself
issue a command.
"""
import shutil
import subprocess
import sys
import time

# key -> spoken utterance (<=2 words each; disjoint from grammar words)
PHRASES = {
    "ready": "ready",            # woke up
    "resting": "resting",        # went to sleep
    "done": "done",              # click executed
    "held": "held",              # button pressed and held
    "dropped": "dropped",        # button released
    "cant": "can't",             # impossible action (nothing to undo, no resolver…)
    "pardon": "pardon?",         # recognized nothing actionable
    "sure": "sure?",             # quit pending — console shows the exact phrase
    "goodbye": "goodbye",        # quitting
    "stopped": "stopped",        # stop with nothing held
    "reverted": "reverted",      # undo done
    "okay": "okay",              # never-mind / cancel acknowledged
    "opening": "opening",        # camera command launched
    "practice": "practice mode", # dummy backend active
}


class ConsoleSink:
    """Always-on audit log; the visible listening/deaf state in v1."""

    def __init__(self, quiet=False, stream=None):
        self.quiet = quiet
        self.stream = stream or sys.stdout
        self.lines = []

    def _emit(self, line):
        self.lines.append(line)
        print(line, file=self.stream, flush=True)

    def say(self, key, **kw):
        self._emit(f"mouse » {PHRASES.get(key, key)}")

    def event(self, msg):
        self._emit(f"mouse » {msg}")

    def error(self, kind, detail=""):
        self._emit(f"mouse !! {kind}: {detail}")


class SpeechSink:
    """spd-say wrapper honoring the mic-pause contract.

    mute_gate: object with .pause()/.resume() — the voice source stops
    feeding the recognizer between those calls. We resume immediately after
    the synchronous spd-say returns (well under the 200 ms budget).
    """

    def __init__(self, console=None, mute_gate=None, cmd=None):
        self.console = console or ConsoleSink()
        self.mute_gate = mute_gate
        self.cmd = cmd or ["spd-say", "-w"]
        self.available = shutil.which(self.cmd[0]) is not None

    def _speak(self, text):
        if not self.available:
            return
        if self.mute_gate is not None:
            self.mute_gate.pause()
        try:
            subprocess.run(self.cmd + [text], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            pass
        finally:
            if self.mute_gate is not None:
                self.mute_gate.resume()

    def say(self, key, **kw):
        self.console.say(key, **kw)
        self._speak(PHRASES.get(key, key))

    def event(self, msg):
        self.console.event(msg)

    def error(self, kind, detail=""):
        self.console.error(kind, detail)
        self._speak(PHRASES.get("pardon"))
