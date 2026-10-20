"""The resident part: a hidden window that owns the hotkey.

It blocks in GetMessage (no CPU, no polling) until Windows delivers WM_HOTKEY.
Windows hands the hotkey straight to us, so unlike a shortcut-file hotkey it
isn't slowed down by other apps that have stopped responding.
"""

import ctypes
import ctypes.wintypes as w
import logging
import threading
import time

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32")

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, w.HWND, w.UINT, w.WPARAM, w.LPARAM)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", w.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", w.HINSTANCE), ("hIcon", w.HICON),
                ("hCursor", w.HANDLE), ("hbrBackground", w.HBRUSH),
                ("lpszMenuName", w.LPCWSTR), ("lpszClassName", w.LPCWSTR)]


user32.DefWindowProcW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_ssize_t
user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.CreateWindowExW.argtypes = [w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, w.HWND, w.HMENU,
                                   w.HINSTANCE, w.LPVOID]
user32.CreateWindowExW.restype = w.HWND
user32.RegisterHotKey.argtypes = [w.HWND, ctypes.c_int, w.UINT, w.UINT]
user32.UnregisterHotKey.argtypes = [w.HWND, ctypes.c_int]
user32.GetMessageW.argtypes = [ctypes.POINTER(w.MSG), w.HWND, w.UINT, w.UINT]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(w.MSG)]
user32.FindWindowExW.argtypes = [w.HWND, w.HWND, w.LPCWSTR, w.LPCWSTR]
user32.FindWindowExW.restype = w.HWND
user32.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
user32.DestroyWindow.argtypes = [w.HWND]
user32.MessageBoxW.argtypes = [w.HWND, w.LPCWSTR, w.LPCWSTR, w.UINT]
kernel32.GetModuleHandleW.restype = w.HMODULE

CLASS_NAME = "SnipHazeListener"
HWND_MESSAGE = w.HWND(-3)
WM_DESTROY, WM_CLOSE, WM_HOTKEY = 0x0002, 0x0010, 0x0312
MOD_NOREPEAT = 0x4000
HOTKEY_ID = 1
MB_ICONWARNING = 0x30


class HotkeyTaken(OSError):
    """Another app already owns this shortcut."""


class Listener:
    def __init__(self, mods, vk, on_hotkey):
        self.mods, self.vk, self.on_hotkey = mods, vk, on_hotkey
        self._busy = threading.Lock()
        self._proc = WNDPROC(self._wndproc)  # keep a reference: Windows calls it
        self.hwnd = None

    def _wndproc(self, hwnd, msg, wparam, lparam):
        if msg == WM_HOTKEY and wparam == HOTKEY_ID:
            # One snip at a time; a second press while snipping does nothing.
            if self._busy.acquire(blocking=False):
                threading.Thread(target=self._snip, daemon=True).start()
            return 0
        if msg == WM_CLOSE:
            user32.DestroyWindow(hwnd)
            return 0
        if msg == WM_DESTROY:
            user32.UnregisterHotKey(hwnd, HOTKEY_ID)
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _snip(self):
        try:
            self.on_hotkey()
        except Exception:
            logging.exception("snip failed")
        finally:
            self._busy.release()

    def run(self):
        """Own the hotkey and wait for it until stop() is called from anywhere."""
        hinst = kernel32.GetModuleHandleW(None)
        wc = WNDCLASSW(lpfnWndProc=self._proc, hInstance=hinst, lpszClassName=CLASS_NAME)
        user32.RegisterClassW(ctypes.byref(wc))
        self.hwnd = user32.CreateWindowExW(0, CLASS_NAME, "SnipHaze", 0, 0, 0, 0, 0,
                                           HWND_MESSAGE, None, hinst, None)
        if not self.hwnd:
            raise ctypes.WinError(ctypes.get_last_error())
        if not user32.RegisterHotKey(self.hwnd, HOTKEY_ID, self.mods | MOD_NOREPEAT, self.vk):
            user32.DestroyWindow(self.hwnd)
            raise HotkeyTaken(ctypes.get_last_error(), "hotkey already registered")
        msg = w.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))


def _find():
    return user32.FindWindowExW(HWND_MESSAGE, None, CLASS_NAME, None)


def stop_running(wait=3.0):
    """Ask a running SnipHaze listener to quit and wait until it has.
    Returns True if one was running."""
    hwnd = _find()
    if not hwnd:
        return False
    user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
    deadline = time.monotonic() + wait
    while _find() and time.monotonic() < deadline:
        time.sleep(0.05)
    time.sleep(0.2)  # let the process exit and drop its single-instance lock
    return True


def warn(text):
    user32.MessageBoxW(None, text, "SnipHaze", MB_ICONWARNING)
