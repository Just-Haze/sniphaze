"""The few Windows calls SnipHaze needs, through ctypes only (no pywin32, no
Pillow) so the overlay opens before anything heavy is imported."""

import ctypes
import ctypes.wintypes as w
import os
import time
import uuid
from pathlib import Path

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32")
shcore = ctypes.WinDLL("shcore")
ole32 = ctypes.WinDLL("ole32")

user32.OpenClipboard.argtypes = [w.HWND]
user32.SetClipboardData.argtypes = [w.UINT, w.HANDLE]
user32.SetClipboardData.restype = w.HANDLE
user32.RegisterClipboardFormatW.argtypes = [w.LPCWSTR]
user32.RegisterClipboardFormatW.restype = w.UINT
user32.GetClipboardOwner.restype = w.HWND
user32.GetClipboardSequenceNumber.restype = w.DWORD
user32.FindWindowW.argtypes = [w.LPCWSTR, w.LPCWSTR]
user32.FindWindowW.restype = w.HWND
user32.MonitorFromPoint.argtypes = [w.POINT, w.DWORD]
user32.MonitorFromPoint.restype = w.HMONITOR
user32.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
user32.SetProcessDpiAwarenessContext.argtypes = [w.HANDLE]
kernel32.GlobalAlloc.argtypes = [w.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = w.HGLOBAL
kernel32.GlobalLock.argtypes = [w.HGLOBAL]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [w.HGLOBAL]
kernel32.GlobalFree.argtypes = [w.HGLOBAL]
kernel32.OpenProcess.restype = w.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD)]
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, w.BOOL, w.LPCWSTR]
kernel32.CreateMutexW.restype = w.HANDLE
user32.keybd_event.argtypes = [w.BYTE, w.BYTE, w.DWORD, ctypes.c_size_t]
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
shcore.GetDpiForMonitor.argtypes = [w.HMONITOR, ctypes.c_int, ctypes.POINTER(w.UINT), ctypes.POINTER(w.UINT)]

CF_DIB = 8
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
VK_SHIFT, VK_LWIN, VK_S = 0x10, 0x5B, 0x53
VK_UNASSIGNED = 0xE8  # tapped so a released Alt/Win doesn't open a menu
# (vk, extended) for modifiers the Ctrl+Alt+S shortcut may still be holding down
HELD_MODIFIERS = [(0xA2, False), (0xA3, True), (0xA4, False), (0xA5, True),
                  (0xA0, False), (0xA1, False), (0x5B, True), (0x5C, True)]
MENU_KEYS = (0xA4, 0xA5, 0x5B, 0x5C)  # Alt and Win: releasing them alone opens a menu
GMEM_MOVEABLE = 0x0002
ERROR_ALREADY_EXISTS = 183
MONITOR_DEFAULTTONEAREST = 2
MDT_EFFECTIVE_DPI = 0
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = w.HANDLE(-4)
OVERLAY_CLASS = "SnipOverlayRootWindow"  # Snipping Tool's capture overlay
FOLDERID_SCREENSHOTS = uuid.UUID("b7bede81-df94-4682-a7d8-57a52620b86f")


class GUID(ctypes.Structure):
    _fields_ = [("data", ctypes.c_byte * 16)]


def make_dpi_aware():
    user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)


def single_instance(name="Local\\SnipHaze"):
    """Hold a named mutex; returns None if another SnipHaze is already running."""
    handle = kernel32.CreateMutexW(None, False, name)
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        return None
    return handle


def screenshots_dir():
    """The Screenshots known folder (where Snipping Tool auto-saves)."""
    guid = GUID()
    ctypes.memmove(guid.data, FOLDERID_SCREENSHOTS.bytes_le, 16)
    out = ctypes.c_wchar_p()
    if shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(out)) == 0:
        path = Path(out.value)
        ole32.CoTaskMemFree(out)
        return path
    return Path(os.path.expanduser("~")) / "Pictures" / "Screenshots"


def cursor_display_scale():
    """Scale factor (1.0 = 100%) of the display under the mouse."""
    pt = w.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    monitor = user32.MonitorFromPoint(pt, MONITOR_DEFAULTTONEAREST)
    dx, dy = w.UINT(), w.UINT()
    if shcore.GetDpiForMonitor(monitor, MDT_EFFECTIVE_DPI, ctypes.byref(dx), ctypes.byref(dy)) != 0:
        return 1.0
    return dx.value / 96


def clipboard_sequence():
    return user32.GetClipboardSequenceNumber()


def clipboard_owner_exe():
    """File name of the process that last set the clipboard, or None if unknown."""
    hwnd = user32.GetClipboardOwner()
    if not hwnd:
        return None
    pid = w.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    proc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not proc:
        return None
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = w.DWORD(len(buf))
        if not kernel32.QueryFullProcessImageNameW(proc, 0, buf, ctypes.byref(size)):
            return None
        return os.path.basename(buf.value)
    finally:
        kernel32.CloseHandle(proc)


def overlay_open():
    return bool(user32.FindWindowW(OVERLAY_CLASS, None))


def _key(vk, up=False, extended=False):
    flags = (KEYEVENTF_KEYUP if up else 0) | (KEYEVENTF_EXTENDEDKEY if extended else 0)
    user32.keybd_event(vk, 0, flags, 0)


def press_snip_keys():
    """Press Win+Shift+S: the fastest way to open Snipping Tool's overlay.

    The shortcut that started us may still be held (Ctrl+Alt), and Windows
    would read Ctrl+Alt+Win+Shift+S as something else, so let go of those first.
    """
    held = [(vk, ext) for vk, ext in HELD_MODIFIERS if user32.GetAsyncKeyState(vk) & 0x8000]
    if any(vk in MENU_KEYS for vk, _ in held):
        _key(VK_UNASSIGNED)
        _key(VK_UNASSIGNED, up=True)
    for vk, ext in held:
        _key(vk, up=True, extended=ext)
    _key(VK_LWIN, extended=True)
    _key(VK_SHIFT)
    _key(VK_S)
    _key(VK_S, up=True)
    _key(VK_SHIFT, up=True)
    _key(VK_LWIN, up=True, extended=True)


def open_snip_link():
    """The slower fallback: Snipping Tool's ms-screenclip: link."""
    try:
        os.startfile("ms-screenclip:")
    except OSError:
        pass


def _open_clipboard(attempts=40):
    # Snipping Tool may still hold the clipboard for a moment right after a snip.
    for _ in range(attempts):
        if user32.OpenClipboard(None):
            return
        time.sleep(0.025)
    raise OSError("clipboard is busy")


def _global(data):
    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    if not handle:
        raise MemoryError("GlobalAlloc failed")
    ptr = kernel32.GlobalLock(handle)
    ctypes.memmove(ptr, data, len(data))
    kernel32.GlobalUnlock(handle)
    return handle


def set_clipboard(payload):
    """Replace the clipboard with `payload`: {"PNG": bytes, "DIB": bytes}."""
    formats = [(CF_DIB if name == "DIB" else user32.RegisterClipboardFormatW(name), data)
               for name, data in payload.items()]
    _open_clipboard()
    try:
        user32.EmptyClipboard()
        for fmt, data in formats:
            handle = _global(data)
            if not user32.SetClipboardData(fmt, handle):
                kernel32.GlobalFree(handle)  # still ours only when SetClipboardData fails
                raise OSError(f"SetClipboardData({fmt}) failed")
    finally:
        user32.CloseClipboard()
