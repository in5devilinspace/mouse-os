import pytest

from mouseos.resolve.screen import Screen


@pytest.fixture
def screen():
    return Screen(1920, 1200)


def test_grid_cells_are_cell_centers(screen):
    assert screen.grid_cell(1) == (320, 200)    # top-left cell center
    assert screen.grid_cell(5) == (960, 600)    # dead center
    assert screen.grid_cell(9) == (1600, 1000)  # bottom-right cell center


def test_grid_cell_bounds(screen):
    with pytest.raises(ValueError):
        screen.grid_cell(0)
    with pytest.raises(ValueError):
        screen.grid_cell(10)


def test_named_regions(screen):
    assert screen.region("center") == (960, 600)
    assert screen.region("top left") == (5, 5)
    assert screen.region("bottom right") == (1914, 1194)
    assert screen.region("top") == (960, 5)
    assert screen.region("left edge") == (5, 600)


def test_clamp(screen):
    assert screen.clamp(-50, 99999) == (0, 1199)
    assert screen.clamp(500, 500) == (500, 500)


def test_nearest_region_names(screen):
    assert screen.nearest_region(960, 600) == "center"
    assert screen.nearest_region(10, 8) == "top left"
    assert screen.nearest_region(1900, 1190) == "bottom right"


def test_percent(screen):
    assert screen.percent(50, 50) == (960, 600)
    assert screen.percent(0, 100) == (0, 1199)
