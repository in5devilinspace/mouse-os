"""Screen geometry: named regions, 3x3 grid, clamping. Pure math, no I/O."""

_EDGE_INSET = 5


class Screen:
    def __init__(self, width, height):
        if width <= 0 or height <= 0:
            raise ValueError(f"bad screen size {width}x{height}")
        self.width = width
        self.height = height

    # -- named regions ----------------------------------------------------
    def region(self, name):
        w, h, e = self.width, self.height, _EDGE_INSET
        table = {
            "center": (w // 2, h // 2),
            "top left": (e, e),
            "top right": (w - 1 - e, e),
            "bottom left": (e, h - 1 - e),
            "bottom right": (w - 1 - e, h - 1 - e),
            "top": (w // 2, e),
            "bottom": (w // 2, h - 1 - e),
            "left edge": (e, h // 2),
            "right edge": (w - 1 - e, h // 2),
        }
        if name not in table:
            raise ValueError(f"unknown region {name!r}")
        return table[name]

    def region_names(self):
        return (
            "center", "top left", "top right", "bottom left", "bottom right",
            "top", "bottom", "left edge", "right edge",
        )

    # -- 3x3 grid ----------------------------------------------------------
    def grid_cell(self, n):
        if not 1 <= n <= 9:
            raise ValueError(f"grid cell must be 1..9, got {n}")
        row, col = divmod(n - 1, 3)
        x = self.width * (2 * col + 1) // 6
        y = self.height * (2 * row + 1) // 6
        return (x, y)

    # -- helpers -----------------------------------------------------------
    def clamp(self, x, y):
        return (max(0, min(self.width - 1, int(x))),
                max(0, min(self.height - 1, int(y))))

    def percent(self, px, py):
        return self.clamp(self.width * px // 100, self.height * py // 100)

    def nearest_region(self, x, y):
        best, best_d = None, None
        for name in self.region_names():
            rx, ry = self.region(name)
            d = (rx - x) ** 2 + (ry - y) ** 2
            if best_d is None or d < best_d:
                best, best_d = name, d
        return best
