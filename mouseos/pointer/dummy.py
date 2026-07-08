"""Recording backend: tests and honest pre-setup 'practice mode'."""


class DummyPointer:
    name = "dummy"

    def __init__(self, echo=False):
        self.ops = []
        self.echo = echo

    def _op(self, *op):
        self.ops.append(op)
        if self.echo:
            print(f"[DUMMY] {' '.join(str(p) for p in op)}", flush=True)

    def move_to(self, x, y):
        self._op("move_to", x, y)

    def move_rel(self, dx, dy):
        self._op("move_rel", dx, dy)

    def click(self, button="left", double=False):
        self._op("click", button, double)

    def press(self, button="left"):
        self._op("press", button)

    def release(self, button="left"):
        self._op("release", button)

    def scroll(self, amount):
        self._op("scroll", amount)
