"""HotkeyListener — Win32 RegisterHotKey-based global hotkey dispatcher.

Why not a low-level keyboard hook?
----------------------------------
``WH_KEYBOARD_LL`` runs our Python callback for *every* keystroke
system-wide.  Under GIL contention (e.g. while AutoBattleService is
sending input bursts) the hook proc misses Windows' 300ms response
window, the OS silently drops further events into a queue, and the user
sees their entire keyboard "freeze".  Even when latency is fine, the
constant per-keystroke Python invocation is a real CPU/GIL tax.

``RegisterHotKey`` is the right tool for the job: Windows matches the
combo in kernel space and only sends us a ``WM_HOTKEY`` message when our
specific combo fires.  Zero per-keystroke cost, zero risk of blocking
other input.

Game foreground gating happens in our ``WM_HOTKEY`` handler: if the
foreground window doesn't match the configured game title, we silently
ignore the hotkey.  The keystroke is still consumed by Windows (the
game won't see it), but Alt+1 / Alt+2 aren't game inputs so this is
acceptable.

Combos are strings like ``"Alt+1"`` parsed by :func:`parse_combo`.
"""
from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes
from typing import Callable

from loguru import logger


# ---------------------------------------------------------------------------
# Win32 constants
# ---------------------------------------------------------------------------

_WM_QUIT = 0x0012
_WM_HOTKEY = 0x0312
_WM_USER = 0x0400

_MOD_ALT = 0x0001
_MOD_CONTROL = 0x0002
_MOD_SHIFT = 0x0004
_MOD_WIN = 0x0008
_MOD_NOREPEAT = 0x4000

_VK_SHIFT = 0x10
_VK_CONTROL = 0x11
_VK_MENU = 0x12
_VK_LWIN = 0x5B

_MODIFIER_NAMES = {
    "CTRL": _VK_CONTROL,
    "CONTROL": _VK_CONTROL,
    "ALT": _VK_MENU,
    "SHIFT": _VK_SHIFT,
    "WIN": _VK_LWIN,
}

_VK_TO_MOD = {
    _VK_CONTROL: _MOD_CONTROL,
    _VK_MENU: _MOD_ALT,
    _VK_SHIFT: _MOD_SHIFT,
    _VK_LWIN: _MOD_WIN,
}

_NAMED_KEYS = {
    "SPACE": 0x20,
    "ENTER": 0x0D,
    "RETURN": 0x0D,
    "TAB": 0x09,
    "ESC": 0x1B,
    "ESCAPE": 0x1B,
    "BACKSPACE": 0x08,
    "BACK": 0x08,
    "DELETE": 0x2E,
    "DEL": 0x2E,
    "INSERT": 0x2D,
    "HOME": 0x24,
    "END": 0x23,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
    "UP": 0x26,
    "DOWN": 0x28,
    "LEFT": 0x25,
    "RIGHT": 0x27,
}

_VK_TO_NAME = {v: k for k, v in _NAMED_KEYS.items()}


def parse_combo(combo: str) -> tuple[frozenset[int], int] | None:
    """Parse ``"Alt+1"`` → ``(frozenset({VK_MENU}), 0x31)``.

    Returns ``None`` for unparseable / empty input.
    """
    if not combo or not combo.strip():
        return None
    parts = [p.strip().upper() for p in combo.split("+") if p.strip()]
    if not parts:
        return None
    mods: set[int] = set()
    main: int | None = None
    for tok in parts:
        if tok in _MODIFIER_NAMES:
            mods.add(_MODIFIER_NAMES[tok])
            continue
        if main is not None:
            return None
        if len(tok) == 1 and "A" <= tok <= "Z":
            main = ord(tok)
        elif len(tok) == 1 and "0" <= tok <= "9":
            main = ord(tok)
        elif tok.startswith("F") and tok[1:].isdigit():
            n = int(tok[1:])
            if 1 <= n <= 24:
                main = 0x70 + (n - 1)
            else:
                return None
        elif tok in _NAMED_KEYS:
            main = _NAMED_KEYS[tok]
        else:
            return None
    if main is None:
        return None
    return frozenset(mods), main


def format_combo(mods: frozenset[int], main: int) -> str:
    order = [_VK_CONTROL, _VK_MENU, _VK_SHIFT, _VK_LWIN]
    names = {_VK_CONTROL: "Ctrl", _VK_MENU: "Alt", _VK_SHIFT: "Shift", _VK_LWIN: "Win"}
    parts = [names[v] for v in order if v in mods]
    if 0x41 <= main <= 0x5A or 0x30 <= main <= 0x39:
        parts.append(chr(main))
    elif 0x70 <= main <= 0x87:
        parts.append(f"F{main - 0x70 + 1}")
    elif main in _VK_TO_NAME:
        parts.append(_VK_TO_NAME[main].capitalize())
    else:
        parts.append(f"VK_{main:#x}")
    return "+".join(parts)


def _combo_to_winflags(mods: frozenset[int], main: int) -> tuple[int, int]:
    flags = _MOD_NOREPEAT
    for vk in mods:
        flags |= _VK_TO_MOD.get(vk, 0)
    return flags, main


class HotkeyListener:
    """Global hotkey dispatcher using Win32 RegisterHotKey."""

    _WM_APPLY = _WM_USER + 1

    def __init__(self, callback: Callable[[str], None]) -> None:
        self._callback = callback
        self._bindings: dict[str, tuple[frozenset[int], int]] = {}
        self._pending_bindings: dict[str, tuple[frozenset[int], int]] | None = None
        self._registered: dict[str, int] = {}
        self._next_id: int = 1
        self._window_title: str = ""
        self._thread: threading.Thread | None = None
        self._tid: int = 0
        self._ready = threading.Event()
        self._stop_evt = threading.Event()
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._user32.RegisterHotKey.restype = wintypes.BOOL
        self._user32.RegisterHotKey.argtypes = [
            wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT,
        ]
        self._user32.UnregisterHotKey.restype = wintypes.BOOL
        self._user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        self._user32.GetMessageW.restype = wintypes.BOOL
        self._user32.PostThreadMessageW.restype = wintypes.BOOL
        self._user32.GetForegroundWindow.restype = wintypes.HWND
        self._user32.GetWindowTextW.restype = ctypes.c_int
        self._user32.GetWindowTextLengthW.restype = ctypes.c_int
        self._kernel32.GetCurrentThreadId.restype = wintypes.DWORD

    # ------------------------------------------------------------------
    # Configuration (callable from any thread)
    # ------------------------------------------------------------------

    def update_bindings(self, raw: dict[str, str]) -> dict[str, str | None]:
        parsed: dict[str, tuple[frozenset[int], int]] = {}
        normalized: dict[str, str | None] = {}
        for action, combo in raw.items():
            p = parse_combo(combo)
            if p is None:
                normalized[action] = None
                continue
            parsed[action] = p
            normalized[action] = format_combo(*p)
        self._bindings = parsed
        self._pending_bindings = dict(parsed)
        if self._tid:
            try:
                self._user32.PostThreadMessageW(self._tid, self._WM_APPLY, 0, 0)
            except Exception:  # noqa: BLE001
                pass
        return normalized

    def set_window_title(self, title: str) -> None:
        self._window_title = title or ""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, timeout: float = 2.0) -> bool:
        if self._thread is not None:
            return self._tid != 0
        self._ready.clear()
        self._stop_evt.clear()
        self._thread = threading.Thread(
            target=self._run, name="HotkeyListener", daemon=True,
        )
        self._thread.start()
        if not self._ready.wait(timeout=timeout):
            logger.warning("HotkeyListener: thread start timed out")
            return False
        return self._tid != 0

    def stop(self) -> None:
        if self._thread is None:
            return
        self._stop_evt.set()
        if self._tid:
            try:
                self._user32.PostThreadMessageW(self._tid, _WM_QUIT, 0, 0)
            except Exception:  # noqa: BLE001
                pass
        self._thread.join(timeout=2.0)
        self._thread = None
        self._tid = 0

    # ------------------------------------------------------------------
    # Listener thread
    # ------------------------------------------------------------------

    def _foreground_is_game(self) -> bool:
        if not self._window_title:
            return False
        hwnd = self._user32.GetForegroundWindow()
        if not hwnd:
            return False
        length = self._user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return False
        buf = ctypes.create_unicode_buffer(length + 1)
        self._user32.GetWindowTextW(hwnd, buf, length + 1)
        return self._window_title in buf.value

    def _install_pending(self) -> None:
        pending = self._pending_bindings
        if pending is None:
            return
        self._pending_bindings = None
        for action, rid in list(self._registered.items()):
            try:
                self._user32.UnregisterHotKey(wintypes.HWND(0), rid)
            except Exception:  # noqa: BLE001
                pass
        self._registered.clear()
        for action, (mods, main) in pending.items():
            flags, vk = _combo_to_winflags(mods, main)
            rid = self._next_id
            self._next_id += 1
            ok = self._user32.RegisterHotKey(
                wintypes.HWND(0), rid, flags, vk,
            )
            if ok:
                self._registered[action] = rid
                logger.info(
                    "Hotkey registered: {} = {} (id={})",
                    action, format_combo(mods, main), rid,
                )
            else:
                err = ctypes.get_last_error()
                logger.warning(
                    "Hotkey register FAILED: {} = {} (err={}, may be "
                    "in use by another app)",
                    action, format_combo(mods, main), err,
                )

    def _handle_hotkey(self, rid: int) -> None:
        action = None
        for a, r in self._registered.items():
            if r == rid:
                action = a
                break
        if action is None:
            return
        if not self._foreground_is_game():
            return
        logger.info("Hotkey fired (foreground=game): {}", action)
        threading.Thread(
            target=self._dispatch, args=(action,), daemon=True,
        ).start()

    def _dispatch(self, action: str) -> None:
        try:
            self._callback(action)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Hotkey callback for {!r} failed: {}", action, exc)

    def _run(self) -> None:
        self._tid = self._kernel32.GetCurrentThreadId()
        if self._bindings and self._pending_bindings is None:
            self._pending_bindings = dict(self._bindings)
        self._install_pending()
        self._ready.set()
        msg = wintypes.MSG()
        try:
            while not self._stop_evt.is_set():
                ret = self._user32.GetMessageW(
                    ctypes.byref(msg), wintypes.HWND(0), 0, 0,
                )
                if ret == 0 or ret == -1:
                    break
                if msg.message == _WM_HOTKEY:
                    self._handle_hotkey(int(msg.wParam))
                elif msg.message == self._WM_APPLY:
                    self._install_pending()
        finally:
            for rid in list(self._registered.values()):
                try:
                    self._user32.UnregisterHotKey(wintypes.HWND(0), rid)
                except Exception:  # noqa: BLE001
                    pass
            self._registered.clear()
            logger.info("HotkeyListener: thread exited")
