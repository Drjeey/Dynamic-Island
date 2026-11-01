import ctypes
import threading
from ctypes import wintypes

MODIFIERS = {'alt': 0x1, 'ctrl': 0x2, 'control': 0x2, 'shift': 0x4, 'win': 0x8}
MOD_NOREPEAT = 0x4000
KEYS = {'space': 0x20, 'enter': 0x0D, 'tab': 0x09, 'esc': 0x1B, 'escape': 0x1B}
KEYS.update({f'f{n}': 0x6F + n for n in range(1, 13)})
WM_HOTKEY, WM_QUIT = 0x0312, 0x0012


def parse(text):
    """'Ctrl+Alt+Space' -> (modifiers, virtual key), or None if it isn't a valid shortcut."""
    parts = [p.strip().lower() for p in text.split('+') if p.strip()]
    if len(parts) < 2:
        return None
    mods = 0
    for p in parts[:-1]:
        if p not in MODIFIERS:
            return None
        mods |= MODIFIERS[p]
    key = parts[-1]
    if key in KEYS: vk = KEYS[key]
    elif len(key) == 1 and key.isalnum(): vk = ord(key.upper())
    else: return None
    return mods, vk


class GlobalHotkey:
    """One system-wide shortcut. RegisterHotKey delivers to the thread that registered it, so it gets its own."""

    def __init__(self, on_press):
        self._on_press = on_press
        self._thread_id = None
        self._thread = None

    def register(self, text):
        """Replaces the current shortcut; returns None on success or a message saying why it failed."""
        self.unregister()
        parsed = parse(text)
        if not parsed:
            return f'"{text}" isn\'t a shortcut I understand. Try something like Win+Alt+Space.'
        result, ready = {}, threading.Event()
        self._thread = threading.Thread(target=self._loop, args=(parsed, result, ready), daemon=True)
        self._thread.start()
        ready.wait(2)
        return result.get('error')

    def unregister(self):
        if self._thread_id:
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
            self._thread.join(1)
            self._thread_id = None

    def _loop(self, parsed, result, ready):
        user32 = ctypes.windll.user32
        mods, vk = parsed
        if not user32.RegisterHotKey(None, 1, mods | MOD_NOREPEAT, vk):
            result['error'] = 'That shortcut is already used by another app. Choose a different one in Settings.'
            ready.set()
            return
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        ready.set()
        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY:
                    try: self._on_press()
                    except Exception as e: print(f"Hotkey Error: {e}")
        finally:
            user32.UnregisterHotKey(None, 1)
