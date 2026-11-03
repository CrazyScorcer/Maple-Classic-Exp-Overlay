"""Linux: MapleStory runs through Wine, Proton or Lutris, so its window is found with Xlib (X11)
by its title or window class, and positions are in pixels: the units mss screenshots and
tkinter use too. A Wayland session keeps the screen out of X11's reach, so a picture of the
whole screen can't be taken there: the game is read from its own window's pixels instead (see
window_capture), which also means a window on top of the game does no harm."""
import ctypes
import ctypes.util
import fcntl
import os
import platform
import select
import subprocess
import tempfile
import threading
import tkinter as tk
from collections import namedtuple
from pathlib import Path
from tkinter import messagebox

import numpy as np

from capture import WindowCapture

from .base import Hotkeys, Platform, parse_hotkey

# --------------------------------------------------------------------------- Xlib
#
# X11 is spoken to directly with ctypes (as mss does): nothing to install, and nothing to load on
# a system without X11 at all. Each thread gets its own connection, so the reading thread, the
# overlay's windows and the hotkeys thread never share one.

_x11 = None
try:
    _x11 = ctypes.CDLL(ctypes.util.find_library("X11") or "libX11.so.6")
except OSError:
    pass                                    # (no X11: no windows to find, no screen to read)
else:
    # The reading thread, the hotkeys thread and the overlay's own windows each use Xlib with their
    # own connection: this is what lets them do it at the same time.
    _x11.XInitThreads()

_fontconfig = None                          # (only needed to give Tk the overlay's own typeface)
try:
    _fontconfig = ctypes.CDLL(ctypes.util.find_library("fontconfig") or "libfontconfig.so.1")
except OSError:
    pass

_vp, _XID, _Atom = ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong

_IS_VIEWABLE = 2                            # MapState of a window that is on screen
_ZPIXMAP, _ALL_PLANES = 2, 0xFFFFFFFF       # (XGetImage's format and plane mask)
_PROPERTY_REPLACE, _CARDINAL = 0, 6         # PropModeReplace, XA_CARDINAL
_LOCK_MASK, _SHIFT_MASK, _CONTROL_MASK, _MOD1_MASK, _MOD2_MASK = 0x2, 0x1, 0x4, 0x8, 0x10
_ANY_MODIFIER = 1 << 15                     # (XUngrabKey: every combination this program grabbed)
_STRUCTURE_NOTIFY, _STRUCTURE_REDIRECT = 1 << 19, 1 << 20
_KEY_PRESS, _CLIENT_MESSAGE = 2, 33
_BAD_ACCESS = 10
_ASYNC = 1                                  # GrabModeAsync: a grabbed key still reaches this program's queue

# The overlay's modifier bits (base.HOTKEY_MODS) as X11's: MOD_SHIFT, MOD_CONTROL, MOD_ALT.
_MODIFIERS = {0x4: _SHIFT_MASK, 0x2: _CONTROL_MASK, 0x1: _MOD1_MASK}


class _XWindowAttributes(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int), ("width", ctypes.c_int), ("height", ctypes.c_int),
                ("border_width", ctypes.c_int), ("depth", ctypes.c_int), ("visual", _vp), ("window_root", _XID),
                ("class_", ctypes.c_int), ("bit_gravity", ctypes.c_int), ("win_gravity", ctypes.c_int),
                ("backing_store", ctypes.c_int), ("backing_planes", ctypes.c_ulong),
                ("backing_pixel", ctypes.c_ulong), ("save_under", ctypes.c_int), ("colormap", _XID),
                ("map_installed", ctypes.c_int), ("map_state", ctypes.c_int),
                ("all_event_masks", ctypes.c_long), ("your_event_mask", ctypes.c_long),
                ("do_not_propagate_mask", ctypes.c_long), ("override_redirect", ctypes.c_int), ("screen", _vp)]


class _XImage(ctypes.Structure):
    # (only what a picture is read with: the fields past blue_mask are never looked at)
    _fields_ = [("width", ctypes.c_int), ("height", ctypes.c_int), ("xoffset", ctypes.c_int),
                ("format", ctypes.c_int), ("data", ctypes.POINTER(ctypes.c_char)),
                ("byte_order", ctypes.c_int), ("bitmap_unit", ctypes.c_int), ("bitmap_bit_order", ctypes.c_int),
                ("bitmap_pad", ctypes.c_int), ("depth", ctypes.c_int), ("bytes_per_line", ctypes.c_int),
                ("bits_per_pixel", ctypes.c_int), ("red_mask", ctypes.c_ulong),
                ("green_mask", ctypes.c_ulong), ("blue_mask", ctypes.c_ulong)]


class _XKeyEvent(ctypes.Structure):
    _fields_ = [("type", ctypes.c_int), ("serial", ctypes.c_ulong), ("send_event", ctypes.c_int),
                ("display", _vp), ("window", _XID), ("root", _XID), ("subwindow", _XID),
                ("time", ctypes.c_ulong), ("x", ctypes.c_int), ("y", ctypes.c_int),
                ("x_root", ctypes.c_int), ("y_root", ctypes.c_int), ("state", ctypes.c_uint),
                ("keycode", ctypes.c_uint), ("same_screen", ctypes.c_int)]


class _XClientMessageData(ctypes.Union):
    _fields_ = [("b", ctypes.c_char * 20), ("s", ctypes.c_short * 10), ("l", ctypes.c_long * 5)]


class _XClientMessageEvent(ctypes.Structure):
    _fields_ = [("type", ctypes.c_int), ("serial", ctypes.c_ulong), ("send_event", ctypes.c_int),
                ("display", _vp), ("window", _XID), ("message_type", _Atom), ("format", ctypes.c_int),
                ("data", _XClientMessageData)]


class _XEvent(ctypes.Union):
    _fields_ = [("type", ctypes.c_int), ("xkey", _XKeyEvent), ("xclient", _XClientMessageEvent),
                ("pad", ctypes.c_long * 24)]


class _XErrorEvent(ctypes.Structure):
    _fields_ = [("type", ctypes.c_int), ("display", _vp), ("resourceid", _XID), ("serial", ctypes.c_ulong),
                ("error_code", ctypes.c_ubyte), ("request_code", ctypes.c_ubyte),
                ("minor_code", ctypes.c_ubyte)]


_ErrorHandler = ctypes.CFUNCTYPE(ctypes.c_int, _vp, ctypes.POINTER(_XErrorEvent))

_grabbing = None                            # (the hotkey being grabbed right now: see _on_error)
_grab_failed = set()


def _on_error(_dpy, event):
    """X errors are ordinary here: a window that just closed, a key another program already uses.
    They must never end the overlay, and a key that can't be grabbed is worth saying in Settings."""
    if _grabbing and event and event.contents.error_code == _BAD_ACCESS:
        _grab_failed.add(_grabbing)
    return 0


_ERROR_HANDLER = _ErrorHandler(_on_error)   # (kept: Xlib keeps the pointer, not a reference)


def _api(fn, restype, *argtypes):
    fn.restype, fn.argtypes = restype, list(argtypes)
    return fn


if _x11 is not None:
    _XOpenDisplay = _api(_x11.XOpenDisplay, _vp, ctypes.c_char_p)
    _XDefaultRootWindow = _api(_x11.XDefaultRootWindow, _XID, _vp)
    _XInternAtom = _api(_x11.XInternAtom, _Atom, _vp, ctypes.c_char_p, ctypes.c_int)
    _XGetWindowProperty = _api(_x11.XGetWindowProperty, ctypes.c_int, _vp, _XID, _Atom, ctypes.c_long,
                               ctypes.c_long, ctypes.c_int, _Atom, ctypes.POINTER(_Atom),
                               ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_ulong),
                               ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)))
    _XFree = _api(_x11.XFree, ctypes.c_int, _vp)
    _XQueryTree = _api(_x11.XQueryTree, ctypes.c_int, _vp, _XID, ctypes.POINTER(_XID), ctypes.POINTER(_XID),
                       ctypes.POINTER(ctypes.POINTER(_XID)), ctypes.POINTER(ctypes.c_uint))
    _XGetWindowAttributes = _api(_x11.XGetWindowAttributes, ctypes.c_int, _vp, _XID,
                                 ctypes.POINTER(_XWindowAttributes))
    _XTranslateCoordinates = _api(_x11.XTranslateCoordinates, ctypes.c_int, _vp, _XID, _XID, ctypes.c_int,
                                  ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
                                  ctypes.POINTER(_XID))
    _XGetImage = _api(_x11.XGetImage, _vp, _vp, _XID, ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint,
                      ctypes.c_ulong, ctypes.c_int)
    _XDestroyImage = _api(_x11.XDestroyImage, ctypes.c_int, _vp)
    _XGetSelectionOwner = _api(_x11.XGetSelectionOwner, _XID, _vp, _Atom)
    _XKeysymToKeycode = _api(_x11.XKeysymToKeycode, ctypes.c_ubyte, _vp, ctypes.c_ulong)
    _XGrabKey = _api(_x11.XGrabKey, ctypes.c_int, _vp, ctypes.c_int, ctypes.c_uint, _XID, ctypes.c_int,
                     ctypes.c_int, ctypes.c_int)
    _XUngrabKey = _api(_x11.XUngrabKey, ctypes.c_int, _vp, ctypes.c_int, ctypes.c_uint, _XID)
    _XSync = _api(_x11.XSync, ctypes.c_int, _vp, ctypes.c_int)
    _XPending = _api(_x11.XPending, ctypes.c_int, _vp)
    _XNextEvent = _api(_x11.XNextEvent, ctypes.c_int, _vp, ctypes.POINTER(_XEvent))
    _XConnectionNumber = _api(_x11.XConnectionNumber, ctypes.c_int, _vp)
    _XGetInputFocus = _api(_x11.XGetInputFocus, ctypes.c_int, _vp, ctypes.POINTER(_XID),
                           ctypes.POINTER(ctypes.c_int))
    _XChangeProperty = _api(_x11.XChangeProperty, ctypes.c_int, _vp, _XID, _Atom, _Atom, ctypes.c_int,
                            ctypes.c_int, ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int)
    _XSendEvent = _api(_x11.XSendEvent, ctypes.c_int, _vp, _XID, ctypes.c_int, ctypes.c_long,
                       ctypes.POINTER(_XEvent))
    _XMapRaised = _api(_x11.XMapRaised, ctypes.c_int, _vp, _XID)
    _XFlush = _api(_x11.XFlush, ctypes.c_int, _vp)
    _XSetErrorHandler = _api(_x11.XSetErrorHandler, _vp, _ErrorHandler)
    _XSetErrorHandler(_ERROR_HANDLER)

if _fontconfig is not None:
    _FcConfigGetCurrent = _api(_fontconfig.FcConfigGetCurrent, _vp)
    _FcConfigAppFontAddDir = _api(_fontconfig.FcConfigAppFontAddDir, ctypes.c_int, _vp, ctypes.c_char_p)

_conn = threading.local()                   # (this thread's connection: Xlib isn't shared between threads)


def _display():
    """This thread's X connection, or None when there is no X server (or no X11 at all)."""
    if _x11 is None:
        return None
    if not getattr(_conn, "tried", False):
        _conn.tried, _conn.dpy = True, _XOpenDisplay(None)
    return _conn.dpy or None


_atoms = {}                                 # (atoms are the server's, so they're shared by every connection)


def _atom(dpy, name):
    atom = _atoms.get(name)
    if atom is None:
        atom = _atoms[name] = _XInternAtom(dpy, name.encode(), False)
    return atom


def _property(dpy, win, name):
    """A window property as (format, bytes), or None. Format 32 values come back as C longs."""
    actual, fmt = _Atom(), ctypes.c_int()
    count, after = ctypes.c_ulong(), ctypes.c_ulong()
    data = ctypes.POINTER(ctypes.c_ubyte)()
    status = _XGetWindowProperty(dpy, win, _atom(dpy, name), 0, 1 << 18, False, 0, ctypes.byref(actual),
                                 ctypes.byref(fmt), ctypes.byref(count), ctypes.byref(after),
                                 ctypes.byref(data))
    if status != 0 or not data:
        return None
    try:
        if fmt.value == 32:                 # (Xlib hands each 32-bit item back as a long)
            return 32, ctypes.string_at(data, count.value * ctypes.sizeof(ctypes.c_long))
        return fmt.value, ctypes.string_at(data, count.value * (fmt.value // 8))
    finally:
        _XFree(data)


def _cardinals(dpy, win, name):
    """The numbers of a 32-bit window property (e.g. _NET_WM_STATE's atoms), or []."""
    got = _property(dpy, win, name)
    if not got or got[0] != 32:
        return []
    raw, wide = got[1], ctypes.sizeof(ctypes.c_long)
    return [int.from_bytes(raw[i:i + 4], "little") for i in range(0, len(raw) - wide + 1, wide)]


def _text(dpy, win, *names):
    """A window property as text (from the first of the names it has), or ''."""
    for name in names:
        got = _property(dpy, win, name)
        if got and got[1]:
            return got[1].decode("utf-8", "replace").rstrip("\x00")
    return ""


def _wm_class(dpy, win):
    """A window's class (the second of WM_CLASS's two names: e.g. 'maplestory.exe')."""
    got = _property(dpy, win, "WM_CLASS")
    if not got or not got[1]:
        return ""
    parts = got[1].decode("utf-8", "replace").split("\x00")
    return next((p for p in reversed(parts) if p), "")


_programs = {}                              # (pid -> its program's name, for the windows on screen)


def _program(pid):
    """The name a program runs under (Wine and Proton name theirs after the game: 'MapleStory.exe')."""
    if pid not in _programs:
        if len(_programs) > 512:            # (a long-running overlay: windows come and go)
            _programs.clear()
        try:
            # This is the name the window manager shows, which for a Wine program is its .exe
            _programs[pid] = Path(f"/proc/{pid}/comm").read_text(encoding="utf-8", errors="replace").strip()
        except OSError:                     # (a program that has just ended, or another user's)
            _programs[pid] = ""
    return _programs[pid]


LinuxWindow = namedtuple("LinuxWindow", "xid pid cls title program rect minimized")


def _children(dpy, win):
    """The windows directly inside one (the window manager's top-level ones for the root window)."""
    root, parent = _XID(), _XID()
    kids, count = ctypes.POINTER(_XID)(), ctypes.c_uint()
    if not _XQueryTree(dpy, win, ctypes.byref(root), ctypes.byref(parent), ctypes.byref(kids),
                       ctypes.byref(count)):
        return []
    try:
        return [kids[i] for i in range(count.value)]
    finally:
        if kids:
            _XFree(kids)


def _window(dpy, win):
    """What the overlay needs to know about one X window, or None if X doesn't know it any more."""
    attrs = _XWindowAttributes()
    if not _XGetWindowAttributes(dpy, win, ctypes.byref(attrs)):
        return None
    rect, x, y, child = None, ctypes.c_int(), ctypes.c_int(), _XID()
    if attrs.map_state == _IS_VIEWABLE and attrs.width >= 100 and attrs.height >= 100 and _XTranslateCoordinates(
            dpy, win, _XDefaultRootWindow(dpy), 0, 0, ctypes.byref(x), ctypes.byref(y), ctypes.byref(child)):
        rect = (x.value, y.value, attrs.width, attrs.height)
    states = _cardinals(dpy, win, "_NET_WM_STATE")
    minimized = attrs.map_state != _IS_VIEWABLE or _atom(dpy, "_NET_WM_STATE_HIDDEN") in states
    pid = (_cardinals(dpy, win, "_NET_WM_PID") or [0])[0]
    return LinuxWindow(win, pid, _wm_class(dpy, win), _text(dpy, win, "_NET_WM_NAME", "WM_NAME"),
                       _program(pid) if pid else "", rect, minimized)


def window_list():
    """LinuxWindows, front to back (only the windows that say what they are: the window manager's
    own windows and menus have no class or title). Empty when there is no X server."""
    dpy = _display()
    if not dpy:
        return []
    found = []
    for win in _children(dpy, _XDefaultRootWindow(dpy)):
        w = _window(dpy, win)
        if w is not None and (w.cls or w.title):
            found.append(w)
    found.reverse()                         # (X lists windows bottom to top)
    return found


def is_game(w, own_pid):
    """Could this window be MapleStory's? (Wine, Proton and Lutris name the program with .exe, which
    is what tells the game apart from a browser or a shop page showing "MapleStory".)"""
    if not w.rect or w.minimized or not w.pid or w.pid == own_pid:
        return False
    named = "maplestory" in w.cls.lower() or "maplestory" in w.title.lower().replace(" ", "")
    program = w.program.lower()
    return named and (program.endswith(".exe") or program.startswith("wine"))


def window_image(xid, x, y, width, height):
    """A window's own pixels (its picture, whatever is on top of it): bgr (h, w, 3), or None."""
    dpy = _display()
    if not dpy or width < 1 or height < 1:
        return None
    image = _XGetImage(dpy, xid, x, y, width, height, _ALL_PLANES, _ZPIXMAP)
    if not image:
        return None
    try:
        picture = ctypes.cast(image, ctypes.POINTER(_XImage)).contents
        if picture.bits_per_pixel != 32 or picture.byte_order != 0:    # (a 24 or 32-bit little-endian screen)
            return None
        raw = ctypes.string_at(picture.data, picture.bytes_per_line * picture.height)
        height_, width_, line = picture.height, picture.width, picture.bytes_per_line
    finally:
        _XDestroyImage(image)
    rows = np.frombuffer(raw, np.uint8).reshape(height_, line)[:, :width_ * 4]
    return np.ascontiguousarray(rows.reshape(height_, width_, 4)[:, :, :3])


class _GameWindow:
    """The game's window for capture.WindowCapture: where it is on screen, and its own pixels."""

    def __init__(self, platform):
        self.platform, self.xid = platform, None

    def rect(self):
        if not (self.xid and self.platform.window_exists(self.xid)):
            self.xid = self.platform.find_game_window()     # (the game was closed, or started again)
        return self.platform.client_rect(self.xid) if self.xid else None

    def grab(self, x, y, width, height):
        return window_image(self.xid, x, y, width, height) if self.xid else None


# --------------------------------------------------------------------------- hotkeys
#
# A hotkey is kept as (modifiers, key) in Windows' codes (see base.parse_hotkey). X11's keysyms
# for 0-9 and A-Z are those same numbers, and F1-F12 are XK_F1 (0xFFBE) onwards.

_VK_KEYSYMS = {**{chr(c): c for c in range(0x30, 0x3A)},                    # '0'..'9'
               **{key: c for c in range(0x41, 0x5B) for key in (chr(c), chr(c).lower())},   # 'a' and 'A'
               **{f"F{i}": 0x6F + i for i in range(1, 13)}}                  # 'F1'..'F12'


def keysym_to_vk(name):
    """The overlay's key code for a Tk keysym name ('a', '1', 'F12'), or None for any other key."""
    return _VK_KEYSYMS.get(name)


def _keysym(vk):
    if 0x70 <= vk <= 0x7B:                  # (F1-F12)
        return 0xFFBE + vk - 0x70
    return vk if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A else None


def _keycode(dpy, vk):
    """The keyboard's own number for a key (0 if this keyboard hasn't got it)."""
    sym = _keysym(vk)
    return _XKeysymToKeycode(dpy, sym) if sym and dpy else 0


def _x_mods(mods):
    """The overlay's modifier bits (base.HOTKEY_MODS) as X11's."""
    return sum(mask for bit, mask in _MODIFIERS.items() if mods & bit)


def _parent(dpy, win):
    root, parent = _XID(), _XID()
    kids, count = ctypes.POINTER(_XID)(), ctypes.c_uint()
    if not _XQueryTree(dpy, win, ctypes.byref(root), ctypes.byref(parent), ctypes.byref(kids),
                       ctypes.byref(count)):
        return 0
    if kids:
        _XFree(kids)
    return parent.value


def _toplevel(dpy, win):
    """The window itself, walking out of a widget or a window frame to what the window manager manages."""
    root = _XDefaultRootWindow(dpy)
    for _ in range(8):                      # (a window manager adds a frame or two at most)
        parent = _parent(dpy, win)
        if not parent or parent == root:
            return win
        win = parent
    return win


def _active_window(dpy):
    """The window in front: the one the window manager names, else whatever has the keyboard."""
    active = _cardinals(dpy, _XDefaultRootWindow(dpy), "_NET_ACTIVE_WINDOW")
    if active and active[0]:
        return active[0]
    focus, revert = _XID(), ctypes.c_int()
    _XGetInputFocus(dpy, ctypes.byref(focus), ctypes.byref(revert))
    return _toplevel(dpy, focus.value) if focus.value > 1 else 0    # (0 None, 1 PointerRoot)


def _pid_of(dpy, win):
    """The program a window says it belongs to (0 if it doesn't say)."""
    pid = _cardinals(dpy, win, "_NET_WM_PID")
    if not pid or not pid[0]:
        top = _toplevel(dpy, win)           # (some window managers name the frame, which has no pid)
        pid = _cardinals(dpy, top, "_NET_WM_PID") if top and top != win else []
    return pid[0] if pid else 0


class LinuxHotkeys(Hotkeys):
    """X11 hotkeys, as Discord and OBS use, on their own thread: they work while you play even
    though they never touch the game. They're grabbed only while MapleStory or the overlay is the
    window in front, so other programs can still use those keys (e.g. to type "!")."""

    def __init__(self, on_press):
        super().__init__(on_press)
        self._wanted, self._paused, self._changed = {}, False, True
        self._lock = threading.Lock()
        threading.Thread(target=self._run, daemon=True).start()

    def set(self, keys, on=True):
        with self._lock:
            self._wanted = {a: parse_hotkey(k) for a, k in keys.items() if on and parse_hotkey(k)}
            self._changed = True

    def pause(self, paused):
        with self._lock:
            self._paused, self._changed = paused, True

    def in_front(self):
        """Is MapleStory or the overlay the window in front?"""
        dpy = _display()
        win = _active_window(dpy) if dpy else 0
        if not win:
            return False
        if _pid_of(dpy, win) == os.getpid():            # one of the overlay's own windows
            return True
        window = _window(dpy, win)
        return bool(window) and is_game(window, os.getpid())

    def _run(self):
        global _grabbing
        dpy = _display()
        if not dpy:                             # (no X server: nothing to grab)
            return
        fd, root = _XConnectionNumber(dpy), _XDefaultRootWindow(dpy)
        event, active, was_on = _XEvent(), {}, None     # active: (keycode, state) -> action
        while True:
            select.select([fd], [], [], 0.25)   # (which is also how often what's in front is checked)
            while _XPending(dpy):
                _XNextEvent(dpy, ctypes.byref(event))
                if event.type == _KEY_PRESS:    # (a key that was grabbed: CapsLock and NumLock don't matter)
                    action = active.get((event.xkey.keycode, event.xkey.state & ~(_LOCK_MASK | _MOD2_MASK)))
                    if action:
                        self.on_press(action)
            try:
                on = self.in_front()
            except Exception:
                on = False
            with self._lock:
                changed, wanted, paused, self._changed = self._changed, dict(self._wanted), self._paused, False
            on = on and not paused
            if not changed and on == was_on:
                continue
            _XUngrabKey(dpy, 0, _ANY_MODIFIER, root)        # (every key this program had grabbed)
            active, was_on = {}, on
            if on:
                for action, (mods, vk) in wanted.items():
                    keycode, state = _keycode(dpy, vk), _x_mods(mods)
                    if not keycode:
                        self.problems[action] = "not a key on this keyboard"
                        continue
                    _grabbing = action
                    try:
                        # With CapsLock and NumLock on, the same key arrives with other modifiers.
                        for extra in (0, _LOCK_MASK, _MOD2_MASK, _LOCK_MASK | _MOD2_MASK):
                            _XGrabKey(dpy, keycode, state | extra, root, False, _ASYNC, _ASYNC)
                        _XSync(dpy, False)      # (so a key another program already uses is known now)
                    finally:
                        _grabbing = None
                    if action in _grab_failed:
                        _grab_failed.discard(action)
                        self.problems[action] = "used by another program"
                    else:
                        self.problems.pop(action, None)
                        active[(keycode, state)] = action
            _XFlush(dpy)


# --------------------------------------------------------------------------- the platform

def _activate(dpy, xid):
    """Brings a window to the front (the window manager's way, and raised, for one that ignores that)."""
    message = _XEvent()
    message.xclient.type = _CLIENT_MESSAGE
    message.xclient.window = xid
    message.xclient.message_type = _atom(dpy, "_NET_ACTIVE_WINDOW")
    message.xclient.format = 32
    message.xclient.data.l[0] = 2               # (from a program, not a click)
    message.xclient.data.l[1] = 0               # (CurrentTime)
    _XSendEvent(dpy, _XDefaultRootWindow(dpy), False, _STRUCTURE_REDIRECT | _STRUCTURE_NOTIFY,
                ctypes.byref(message))
    _XMapRaised(dpy, xid)
    _XFlush(dpy)


def _wayland():
    """Is this a Wayland session? (Its compositor keeps the screen out of X11's reach, though a
    window's own pixels can still be read: see window_capture.)"""
    return (os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
            or bool(os.environ.get("WAYLAND_DISPLAY")))


_xft_dpi = []                                   # (read once: X11 has one scale for all its screens)

# The overlay's Windows fonts -> Linux's own, for when the bundled Manrope can't be given to Tk
# (see register_fonts). DejaVu comes with every desktop.
_FONTS = {"Segoe UI": ("DejaVu Sans", None), "Segoe UI Semibold": ("DejaVu Sans", "bold"),
          "Consolas": ("DejaVu Sans Mono", None)}


def _screen_dpi(dpy):
    """The Xft.dpi the X11 session was started with (what Tk sizes everything for), or None."""
    if not _xft_dpi:
        dpi = None
        for line in _text(dpy, _XDefaultRootWindow(dpy), "RESOURCE_MANAGER").splitlines():
            key, _, value = line.partition(":")
            if key.strip() == "Xft.dpi":
                try:
                    dpi = int(float(value.strip()))
                except ValueError:
                    dpi = None
        _xft_dpi.append(dpi)
    return _xft_dpi[0]


class LinuxPlatform(Platform):
    name = "Linux"

    def __init__(self):
        self._marked = set()                    # (our windows that were told which program they belong to)
        self._lock = None

    def version(self):
        try:
            release = platform.freedesktop_os_release()
            name = release.get("PRETTY_NAME") or release.get("NAME") or "Linux"
        except OSError:
            name = "Linux"
        session = "Wayland" if _wayland() else "X11" if os.environ.get("DISPLAY") else "no display"
        return f"{name} (Linux {platform.release()}, {session})"

    def data_root(self):
        return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")

    def tesseract_candidates(self, home_dir, app_dir):
        # Only full paths from PATH: a program called tesseract in the folder the overlay was started
        # from must never be run (as on Windows).
        on_path = [Path(d) / "tesseract" for d in os.environ.get("PATH", "").split(os.pathsep)
                   if d.strip() and os.path.isabs(d.strip())]
        return [home_dir / "tesseract" / "tesseract",           # comes with the download
                app_dir / "tesseract" / "tesseract",
                Path("/usr/bin/tesseract"), Path("/usr/local/bin/tesseract"), Path("/snap/bin/tesseract"),
                *on_path]

    def tessdata_candidates(self, exe):
        # Where each distribution keeps eng.traineddata (Arch and Fedora, then Debian and Ubuntu),
        # and the overlay's own layout, which is <folder>/tesseract/tessdata.
        return [*([Path(os.environ["TESSDATA_PREFIX"])] if os.environ.get("TESSDATA_PREFIX") else []),
                exe.parent / "tessdata",
                exe.parent.parent / "share" / "tessdata",       # /usr/local/bin -> /usr/local/share
                Path("/usr/share/tessdata"),
                Path("/usr/share/tesseract-ocr/5/tessdata"),
                Path("/usr/share/tesseract-ocr/4.00/tessdata"),
                Path("/usr/share/tesseract-ocr/tessdata"),
                Path("/usr/local/share/tessdata")]

    def tessdata_arg(self, exe, folder):
        return str(folder)                       # (paths are UTF-8 here: no short-name trouble as on Windows)

    def claim_single_instance(self, key, title, old_titles=()):
        self._lock = open(Path(tempfile.gettempdir()) / f"MapleEXP-{key}.lock", "w")   # (unlocked at exit)
        try:
            fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            dpy = _display()
            found = [w for w in window_list() if w.title.startswith((title, *old_titles))]
            if dpy and found:
                _activate(dpy, found[0].xid)     # the copy that's already running, in front
            else:
                self._say_running(title)
            return False

    @staticmethod
    def _say_running(title):
        """Says that the overlay is already running (with a small message of its own: no tray needed)."""
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo(title, f"{title} is already running.", parent=root)
            root.destroy()
        except Exception:                        # (no window system to say it in)
            print(f"{title} is already running.")

    def find_game_window(self):
        found = [(w.rect[2] * w.rect[3], w.xid) for w in window_list() if is_game(w, os.getpid())]
        return max(found)[1] if found else None

    def window_exists(self, xid):
        dpy = _display()
        attrs = _XWindowAttributes()
        return bool(dpy) and bool(_XGetWindowAttributes(dpy, xid, ctypes.byref(attrs)))

    def client_rect(self, xid):
        # The game area itself (what Wine draws in), moving with the window, like Windows' client area.
        dpy = _display()
        attrs = _XWindowAttributes()
        if not dpy or not _XGetWindowAttributes(dpy, xid, ctypes.byref(attrs)):
            return None
        if attrs.map_state != _IS_VIEWABLE or attrs.width < 100 or attrs.height < 100:
            return None
        x, y, child = ctypes.c_int(), ctypes.c_int(), _XID()
        if not _XTranslateCoordinates(dpy, xid, _XDefaultRootWindow(dpy), 0, 0, ctypes.byref(x),
                                      ctypes.byref(y), ctypes.byref(child)):
            return None
        return x.value, y.value, attrs.width, attrs.height

    def own_window_rect(self, root):
        # The window the window manager put around ours (or ours itself, where it reparents nothing),
        # frame included: a little more than drawn is what this is for (this window's picture is
        # never read as the game's).
        dpy = _display()
        if not dpy:
            return None
        try:
            xid = int(root.tk.call("wm", "frame", root._w), 0)
        except Exception:                        # (not on screen yet, or something other than a Toplevel)
            return None
        if not xid:
            return None
        self._mark_own(dpy, xid)
        attrs = _XWindowAttributes()
        if not _XGetWindowAttributes(dpy, xid, ctypes.byref(attrs)) or not attrs.width or not attrs.height:
            return None
        x, y, child = ctypes.c_int(), ctypes.c_int(), _XID()
        if not _XTranslateCoordinates(dpy, xid, _XDefaultRootWindow(dpy), 0, 0, ctypes.byref(x),
                                      ctypes.byref(y), ctypes.byref(child)):
            return None
        return x.value, y.value, attrs.width, attrs.height

    def _mark_own(self, dpy, xid):
        """Says which program one of the overlay's windows belongs to (Tk doesn't set _NET_WM_PID), so
        the hotkeys can tell that the overlay itself is the window in front, not some other program."""
        if not xid or not dpy or xid in self._marked:
            return
        self._marked.add(xid)
        pid = ctypes.c_long(os.getpid())         # (a 32-bit property is handed to Xlib as longs)
        _XChangeProperty(dpy, xid, _atom(dpy, "_NET_WM_PID"), _CARDINAL, 32, _PROPERTY_REPLACE,
                         ctypes.cast(ctypes.byref(pid), ctypes.POINTER(ctypes.c_ubyte)), 1)

    def style_window(self, root, background, text):
        # X11 title bars belong to the window manager, and Tk asks for none of its own: nothing to
        # colour here. The window is marked instead, so the hotkeys know it is the overlay's.
        try:
            self._mark_own(_display(), int(root.tk.call("wm", "frame", root._w), 0))
        except Exception:
            pass

    def screen_dpi(self, x, y):
        dpy = _display()
        return _screen_dpi(dpy) if dpy else None

    def create_hotkeys(self, on_press):
        return LinuxHotkeys(on_press)

    def window_capture(self):
        # A compositing desktop keeps each window's own picture, so what is on top of the game isn't in
        # it; without one there's only what shows through, which the reader must treat as a copy of the
        # screen (a window of this app on top of the EXP bar would be in the picture).
        return WindowCapture(_GameWindow(self), sees_through=self.composited())

    def composited(self):
        """Is a compositing manager running? (Then a window's picture is its own, not the screen's.)"""
        dpy = _display()
        return bool(dpy) and bool(_XGetSelectionOwner(dpy, _atom(dpy, "_NET_WM_CM_S0")))

    def screen_capture_note(self):
        if _wayland():
            return ("A Wayland session doesn't let the overlay take a picture of the whole screen: "
                    "click Follow game, or log in with X11 (Xorg).")
        return None

    def open_folder(self, path):
        subprocess.Popen(["xdg-open", str(path)])

    def show_file(self, path):
        # FileManager1 shows the folder with the file selected (as /select, and -R do on the other
        # OSes); where there is no such service, the folder itself is opened.
        uri = Path(path).resolve().as_uri()
        for cmd in (["dbus-send", "--session", "--type=method_call", "--dest=org.freedesktop.FileManager1",
                     "--print-reply", "/org/freedesktop/FileManager1",
                     "org.freedesktop.FileManager1.ShowItems", f"array:string:{uri}", "string:"],
                    ["gdbus", "call", "--session", "--dest", "org.freedesktop.FileManager1", "--object-path",
                     "/org/freedesktop/FileManager1", "--method", "org.freedesktop.FileManager1.ShowItems",
                     f"[{uri}]", ""]):
            try:
                if subprocess.run(cmd, capture_output=True, timeout=5).returncode == 0:
                    return
            except Exception:
                continue
        subprocess.Popen(["xdg-open", str(Path(path).parent)])

    def register_fonts(self, paths):
        # Fontconfig can take a folder of font files for this program only (FcConfigAppFontAddDir):
        # nothing is installed, and Tk can use the overlay's own typeface by name, as it does on the
        # other OSes (which matters: the same font is what decides whether a caption fits its box).
        try:
            config = _FcConfigGetCurrent()
            folders = {Path(font).resolve().parent for font in paths}     # (a folder of fonts, scanned once)
            return bool(config) and all(_FcConfigAppFontAddDir(config, str(folder).encode()) for folder in folders)
        except Exception:
            return False

    def font(self, family, weight):
        linux_family, linux_weight = _FONTS.get(family, (family, None))
        return linux_family, linux_weight or weight

    def hotkey_event(self, event):
        # Tk on X11 gives the X keycode and X11's own modifier bits, so the keys are named from what
        # was pressed (a keysym) rather than from a number Windows and X11 would each read differently.
        return (bool(event.state & _CONTROL_MASK), bool(event.state & _MOD1_MASK),
                bool(event.state & _SHIFT_MASK), keysym_to_vk(event.keysym) or 0)
