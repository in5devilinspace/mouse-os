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
    """Nested pause counter; muted while any pause is outstanding.

    `dirty` records that a full mute cycle just ended: audio captured during
    the mute (the machine's own TTS, buffered in the capture pipe) is stale
    and must be discarded before the recognizer sees it. The source consumes
    the flag exactly once via consume_dirty().
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._pauses = 0
        self._dirty = False

    def pause(self):
        with self._lock:
            self._pauses += 1

    def resume(self):
        with self._lock:
            if self._pauses > 0:
                self._pauses -= 1
                if self._pauses == 0:
                    self._dirty = True

    def consume_dirty(self):
        with self._lock:
            was, self._dirty = self._dirty, False
            return was

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

    def _drain(self):
        """Empty any audio the OS buffered in the capture pipe during a mute."""
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        try:
            fd = proc.stdout.fileno()
            os.set_blocking(fd, False)
            try:
                while os.read(fd, _CHUNK_BYTES):
                    pass
            except (BlockingIOError, OSError):
                pass
            finally:
                os.set_blocking(fd, True)
        except (OSError, ValueError):
            pass

    @staticmethod
    def _clean_final(text):
        """A final is usable only if it is entirely in-vocabulary.

        Any [unk] token means the audio didn't cleanly match the grammar —
        reject the whole utterance rather than risk fusing non-adjacent words
        ('mouse [unk] wake' must NOT wake the machine) or emitting noise.
        """
        tokens = text.split()
        if not tokens or any(t == "[unk]" for t in tokens):
            return None
        return " ".join(tokens)

    # -- the loop -----------------------------------------------------------------
    def __iter__(self):
        rec = self._make_recognizer()
        self.on_state("listening")
        for chunk in self._audio_chunks():
            if self.gate.consume_dirty():
                # TTS just played; this chunk and whatever is buffered behind
                # it are the machine hearing itself. Drop them and reset.
                rec.Reset()
                self._drain()
                self.on_state("listening")
                continue
            if self.gate.muted:
                self.on_state("deaf")
                continue                    # discard: never hear ourselves
            self.on_state("listening")
            if rec.AcceptWaveform(chunk):
                result = json.loads(rec.Result())
                text = self._clean_final(" ".join(result.get("text", "").split()))
                if text:
                    yield text
