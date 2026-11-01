import ctypes
import queue
import socket
import threading
import time
from ctypes import wintypes


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD), ("ullTotalPhys", ctypes.c_uint64),
                ("ullAvailPhys", ctypes.c_uint64), ("ullTotalPageFile", ctypes.c_uint64), ("ullAvailPageFile", ctypes.c_uint64),
                ("ullTotalVirtual", ctypes.c_uint64), ("ullAvailVirtual", ctypes.c_uint64), ("ullAvailExtendedVirtual", ctypes.c_uint64)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]


class POWER(ctypes.Structure):
    _fields_ = [('AC', ctypes.c_ubyte), ('Flag', ctypes.c_ubyte), ('Percent', ctypes.c_ubyte), ('R1', ctypes.c_ubyte),
                ('L', ctypes.c_ulong), ('F', ctypes.c_ulong)]


class SystemHelpers:
    _ram_history = []    # one sample every 10 s, last minute only
    _online = None       # None until the first check finishes

    @staticmethod
    def read_memory_load():
        try:
            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
            return mem.dwMemoryLoad
        except Exception: return 0

    @staticmethod
    def start_samplers():
        # High memory is normal on Windows; only flag it when it stays above 90% for a full minute.
        # Connectivity is a plain reachable/unreachable check, not a ping number.
        def sample():
            while True:
                SystemHelpers._ram_history = (SystemHelpers._ram_history + [SystemHelpers.read_memory_load()])[-6:]
                try:
                    socket.create_connection(("1.1.1.1", 443), timeout=2).close()
                    SystemHelpers._online = True
                except OSError:
                    SystemHelpers._online = False
                time.sleep(10)
        threading.Thread(target=sample, daemon=True).start()

    @staticmethod
    def get_stats():
        ram = SystemHelpers.read_memory_load()
        history = SystemHelpers._ram_history
        ram_high = len(history) == 6 and min(history) >= 90 and ram >= 90
        try:
            p = POWER()
            ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(p))
            # Percent 255 = unknown, Flag 128 = no battery (desktop PC): report None so the UI shows "Plugged in"
            bat = None if p.Percent == 255 or p.Flag & 128 else p.Percent
            charging = p.AC == 1
        except Exception:
            bat, charging = None, False
        return {'ram': ram, 'ram_high': ram_high, 'bat': bat, 'charging': charging, 'online': SystemHelpers._online}

    @staticmethod
    def send_key(vk):
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0); ctypes.windll.user32.keybd_event(vk, 0, 2, 0)


class Volume:
    """System volume through Core Audio, falling back to the volume keys if that isn't available.

    Opening the audio device takes a few hundred milliseconds and COM objects belong to the thread that
    made them, so one worker thread keeps the device open and handles every change."""

    _requests = None

    @staticmethod
    def _worker():
        ctypes.windll.ole32.CoInitialize(None)
        endpoint = None
        while True:
            steps, reply = Volume._requests.get()
            try:
                if endpoint is None:
                    from pycaw.pycaw import AudioUtilities
                    endpoint = AudioUtilities.GetSpeakers().EndpointVolume
                level = min(1.0, max(0.0, endpoint.GetMasterVolumeLevelScalar() + 0.02 * steps))
                endpoint.SetMasterVolumeLevelScalar(level, None)
                if steps > 0 and endpoint.GetMute():
                    endpoint.SetMute(0, None)
                reply.put({'level': round(level * 100), 'muted': bool(endpoint.GetMute())})
            except Exception as e:
                print(f"Volume Error: {e}")
                endpoint = None  # e.g. the default speakers changed; reopen next time
                SystemHelpers.send_key(0xAF if steps > 0 else 0xAE)
                reply.put(None)

    @staticmethod
    def change(steps):
        """Moves the volume by 2% per step; returns the new level (0-100) and mute state, or None."""
        if Volume._requests is None:
            Volume._requests = queue.Queue()
            threading.Thread(target=Volume._worker, daemon=True).start()
        reply = queue.Queue()
        Volume._requests.put((steps, reply))
        try:
            return reply.get(timeout=2)
        except queue.Empty:
            return None

    @staticmethod
    def warm_up():
        # Opens the audio device in the background so the first scroll is instant
        Volume.change(0)


def list_monitors():
    """Displays as physical-pixel rectangles, primary first."""
    user32 = ctypes.windll.user32
    monitors = []
    MONITORENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(wintypes.RECT), ctypes.c_void_p)

    def callback(hmon, hdc, rect, data):
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(ctypes.c_void_p(hmon), ctypes.byref(info)):
            m = info.rcMonitor
            monitors.append({'left': m.left, 'top': m.top, 'width': m.right - m.left, 'height': m.bottom - m.top,
                             'primary': bool(info.dwFlags & 1)})
        return 1

    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(callback), 0)
    monitors.sort(key=lambda m: (not m['primary'], m['left'], m['top']))
    return monitors
