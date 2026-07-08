"""Text REPL input source — works with no microphone, no model, no display."""
import sys


class ReplSource:
    repl = True

    def __init__(self, stream=None, echo=True, prompt="you » "):
        self.stream = stream if stream is not None else sys.stdin
        self.echo = echo
        self.prompt = prompt

    def __iter__(self):
        while True:
            if self.echo and self.stream is sys.stdin:
                print(self.prompt, end="", flush=True)
            line = self.stream.readline()
            if not line:                      # EOF
                return
            utterance = " ".join(line.lower().split())
            if not utterance:
                continue
            yield utterance
