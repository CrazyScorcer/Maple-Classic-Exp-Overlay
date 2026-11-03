"""Where the reader's pictures of the screen come from.

The reader asks a Capture for a rectangle in SCREEN coordinates and gets it back as (bgr, left, top), or
None when it is off the monitors. A copy of the screen (ScreenCapture) shows whatever window is on top,
this app's included. A window's own picture (WindowCapture, where the OS can give it: see
Platform.window_capture) doesn't, which it says with `sees_through_windows`, so the reader doesn't skip
areas this app covers."""

import numpy as np


def grab(sct, left, top, width, height):
    """Screenshot of a screen rectangle, clipped to the monitors: (bgr, left, top) or None."""
    v = sct.monitors[0]
    x0, y0 = max(left, v["left"]), max(top, v["top"])
    x1 = min(left + width, v["left"] + v["width"])
    y1 = min(top + height, v["top"] + v["height"])
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None
    shot = np.array(sct.grab({"left": x0, "top": y0, "width": x1 - x0, "height": y1 - y0}))
    return np.ascontiguousarray(shot[:, :, :3]), x0, y0


class Capture:
    """The interface. Subclasses fill in grab() and, if they see through windows, the flag."""
    name = "screen"                     # for bug reports and health reports
    sees_through_windows = False        # True: a window on top of the game isn't in the picture

    def grab(self, left, top, width, height):
        raise NotImplementedError

    def begin_look(self):
        """Called before the reader's look at the screen (a source that fetches one frame per look does it here)."""

    def end_look(self):
        """Called after the look, whatever happened."""


class ScreenCapture(Capture):
    """A copy of the screen (mss): shows whatever is on top, so this app's own window is in the way."""
    name = "screen"

    def __init__(self, sct):
        self.sct = sct

    def grab(self, left, top, width, height):
        return grab(self.sct, left, top, width, height)


class WindowCapture(Capture):
    """The game's own window's pixels, not the screen's, so a window on top of it (this app's own
    included) isn't in the picture. `window` is the OS's way of reading it: window.rect() gives
    (left, top, width, height) on screen or None, and window.grab(x, y, width, height) its bgr pixels
    in the window's own coordinates, or None."""

    name = "window"

    def __init__(self, window, sees_through=True):
        self.window = window
        # True: nothing on top of the game is in the picture (a compositing desktop). False: what shows
        # through is, so the reader must still keep this app's own window off the game's areas.
        self.sees_through_windows = sees_through

    def grab(self, left, top, width, height):
        rect = self.window.rect()
        if not rect:
            return None
        wx, wy, ww, wh = rect
        x0, y0 = max(left, wx), max(top, wy)
        x1, y1 = min(left + width, wx + ww), min(top + height, wy + wh)
        if x1 - x0 < 8 or y1 - y0 < 8:                  # (as for a rectangle off the monitors, above)
            return None
        pixels = self.window.grab(x0 - wx, y0 - wy, x1 - x0, y1 - y0)
        return (pixels, x0, y0) if pixels is not None else None


def as_capture(source):
    """A Capture from either a Capture or a bare mss-like object (the tests pass a fake screen)."""
    return source if isinstance(source, Capture) else ScreenCapture(source)
