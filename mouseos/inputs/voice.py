"""Vosk grammar-constrained voice source, fed by a pw-record/arecord subprocess.

No PortAudio needed: raw 16 kHz mono s16 PCM is piped from PipeWire/ALSA CLI
tools. The recognizer is rebuilt with the tight asleep grammar when the engine
sleeps (wake/quit only) — recognition is constrained twice over.

MuteGate implements Sally's contract: SpeechSink pauses the gate only while
TTS actually plays; audio read while muted is discarded so the system cannot
hear itself; the gate re-arms immediately on resume (well under 200 ms).
"""
import json
import shutil
import subprocess
import threading

SAMPLE_RATE = 16000
_CHUNK_BYTES = 4000

CAPTURE_CMDS = (
    ["pw-record", "--format", "s16", "--rate", str(SAMPLE_RATE),
     "--channels", "1", "-"],
    ["arecord", "-q", "-f", "S16_LE", "-r", str(SAMPLE_RATE),
     "-c", "1", "-t", "raw", "-"],
)


def build_grammar_json(phrase_list):
    """Vosk grammar: the closed vocabulary plus [unk] to absorb everything else."""
    return json.dumps(list(phrase_list) + ["[unk]"])


def pick_capture_cmd():
    for cmd in CAPTURE_CMDS:
        if shutil.which(cmd[0]):
            return cmd
    return None


class MuteGate:
    """Nested pause counter; muted while any pause is outstanding."""

    def __init__(self):
        self._lock = threading.Lock()
        self._pauses = 0

    def pause(self):
        with self._lock:
            self._pauses += 1

    def resume(self):
        with self._lock:
            if self._pauses > 0:
                self._pauses -= 1

    @property
    def muted(self):
        with self._lock:
            return self._pauses > 0


class VoskSource:
    """Iterates final recognized utterances. repl=False: voice grammar only."""

    repl = False

    def __init__(self, model_dir, phrases, mute_gate=None, capture_cmd=None,
                 recognizer=None, chunks=None, on_state=None):
        self.model_dir = str(model_dir)
        self.phrases = list(phrases)
        self.gate = mute_gate or MuteGate()
        self.capture_cmd = capture_cmd
        self._recognizer = recognizer      # injectable for tests
        self._chunks = chunks              # injectable for tests
        self.on_state = on_state or (lambda s: None)
        self._proc = None

    # -- wiring ----------------------------------------------------------------
    def _make_recognizer(self):
        if self._recognizer is not None:
            return self._recognizer
        from vosk import KaldiRecognizer, Model, SetLogLevel
        SetLogLevel(-1)
        model = Model(self.model_dir)
        return KaldiRecognizer(model, SAMPLE_RATE,
                               build_grammar_json(self.phrases))

    def _audio_chunks(self):
        if self._chunks is not None:
            yield from self._chunks
            return
        cmd = self.capture_cmd or pick_capture_cmd()
        if cmd is None:
            raise RuntimeError("no capture tool found (need pw-record or arecord)")
        self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                      stderr=subprocess.DEVNULL)
        try:
            while True:
                data = self._proc.stdout.read(_CHUNK_BYTES)
                if not data:
                    return
                yield data
        finally:
            self._proc.terminate()

    # -- the loop -----------------------------------------------------------------
    def __iter__(self):
        rec = self._make_recognizer()
        self.on_state("listening")
        for chunk in self._audio_chunks():
            if self.gate.muted:
                self.on_state("deaf")
                continue                    # discard: never hear ourselves
            self.on_state("listening")
            if rec.AcceptWaveform(chunk):
                result = json.loads(rec.Result())
                text = " ".join(result.get("text", "").split())
                if text and text != "[unk]":
                    yield text.replace("[unk]", "").strip()
