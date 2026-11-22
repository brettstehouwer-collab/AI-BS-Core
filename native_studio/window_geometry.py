"""Screen-relative startup sizing, without importing Qt or application services."""
from dataclasses import dataclass


@dataclass(frozen=True)
class StartupGeometry:
    x: int
    y: int
    width: int
    height: int
    minimum_width: int
    minimum_height: int


def fit_startup_geometry(available, *, preferred=(1620, 980), minimum=(1150, 750), frame=(16, 40)):
    """Fit the complete decorated window inside an available logical-pixel rect.

    ``frame`` is total horizontal/vertical decoration, obtained by the caller
    from its window style. The normal minimum cannot exceed a small display.
    Coordinates include the available screen origin, including negative origins.
    """
    x, y, available_width, available_height = available
    if (any(type(value) is not int for value in (*available, *preferred, *minimum, *frame))
            or available_width <= 0 or available_height <= 0
            or min(*preferred, *minimum) <= 0 or min(frame) < 0):
        raise ValueError('Positive screen/window sizes and nonnegative frame dimensions required')
    usable_width = max(1, available_width - frame[0])
    usable_height = max(1, available_height - frame[1])
    width, height = min(preferred[0], usable_width), min(preferred[1], usable_height)
    return StartupGeometry(x + max(0, (available_width-width-frame[0])//2),
        y + max(0, (available_height-height-frame[1])//2), width, height,
        min(minimum[0], width), min(minimum[1], height))
