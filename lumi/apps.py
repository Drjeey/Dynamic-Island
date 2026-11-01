import base64
import ctypes
import os
import queue
import struct
import threading
import winreg
import zlib
from ctypes import wintypes

# Default pins for the command bar; the browser pin follows the user's default browser
PINNED = ['File Explorer', 'Terminal', 'Calculator']
BROWSERS = {'chrome': 'Google Chrome', 'msedge': 'Microsoft Edge', 'firefox': 'Firefox', 'brave': 'Brave',
            'opera': 'Opera', 'vivaldi': 'Vivaldi'}


class AppIndex:
    """Installed apps from Windows' Apps folder (includes Store apps like Calculator), with their real icons."""

    def __init__(self):
        self.apps = []          # [{'id': AppUserModelID, 'name': str}]
        self._icons = {}        # id -> data URI (or None)
        self._jobs = queue.Queue()
        self.ready = threading.Event()
        # All shell COM work happens on this one thread
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        import pythoncom
        pythoncom.CoInitialize()
        try:
            import win32com.client
            items = win32com.client.Dispatch('Shell.Application').NameSpace('shell:AppsFolder').Items()
            apps = [{'id': i.Path, 'name': i.Name} for i in items]
            self.apps = sorted((a for a in apps if a['name'] and 'uninstall' not in a['name'].lower()),
                               key=lambda a: a['name'].lower())
        except Exception as e:
            print(f"App List Error: {e}")
        self.ready.set()
        while True:
            app_id, done = self._jobs.get()
            if app_id not in self._icons:
                self._icons[app_id] = _icon_data_uri('shell:AppsFolder\\' + app_id)
            done.set()

    def icon(self, app_id):
        if app_id not in self._icons:
            done = threading.Event()
            self._jobs.put((app_id, done))
            done.wait(2)
        return self._icons.get(app_id)

    def find(self, name):
        return next((a for a in self.apps if a['name'].lower() == name.lower()), None)

    def search(self, query, limit=5):
        q = query.strip().lower()
        if not q:
            return []
        scored = []
        for a in self.apps:
            name = a['name'].lower()
            if name.startswith(q): score = 0
            elif any(word.startswith(q) for word in name.split()): score = 1
            elif q in name: score = 2
            else: continue
            scored.append((score, len(name), a))
        scored.sort(key=lambda s: (s[0], s[1]))
        return [self.describe(a) for _, _, a in scored[:limit]]

    def pins(self):
        names = [default_browser_name()] + PINNED
        return [self.describe(a) for a in (self.find(n) for n in names) if a]

    def describe(self, app):
        return {'id': app['id'], 'name': app['name'], 'icon': self.icon(app['id'])}

    @staticmethod
    def launch(app_id):
        os.startfile('shell:AppsFolder\\' + app_id)


def default_browser_name():
    try:
        key = r'Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
            prog_id = winreg.QueryValueEx(k, 'ProgId')[0].lower()
        return next((name for key, name in BROWSERS.items() if key in prog_id), 'Microsoft Edge')
    except OSError:
        return 'Microsoft Edge'


# --- ICONS ---
# IShellItemImageFactory gives the same icon Windows shows in Start; it comes back as a 32-bit bitmap,
# which is converted to PNG here (Python has no image library to lean on)

class SIZE(ctypes.Structure):
    _fields_ = [('cx', ctypes.c_long), ('cy', ctypes.c_long)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [('biSize', wintypes.DWORD), ('biWidth', ctypes.c_long), ('biHeight', ctypes.c_long),
                ('biPlanes', wintypes.WORD), ('biBitCount', wintypes.WORD), ('biCompression', wintypes.DWORD),
                ('biSizeImage', wintypes.DWORD), ('biXPelsPerMeter', ctypes.c_long), ('biYPelsPerMeter', ctypes.c_long),
                ('biClrUsed', wintypes.DWORD), ('biClrImportant', wintypes.DWORD)]


def _icon_data_uri(parsing_name, size=40):
    try:
        from comtypes import COMMETHOD, GUID, HRESULT, IUnknown

        class IShellItemImageFactory(IUnknown):
            _iid_ = GUID('{bcc18b79-ba16-442f-80c4-8a59c30c463b}')
            _methods_ = [COMMETHOD([], HRESULT, 'GetImage', (['in'], SIZE, 'size'), (['in'], ctypes.c_int, 'flags'),
                                   (['out'], ctypes.POINTER(wintypes.HBITMAP), 'phbm'))]

        factory = ctypes.POINTER(IShellItemImageFactory)()
        hr = ctypes.windll.shell32.SHCreateItemFromParsingName(
            ctypes.c_wchar_p(parsing_name), None, ctypes.byref(IShellItemImageFactory._iid_), ctypes.byref(factory))
        if hr != 0 or not factory:
            return None
        SIIGBF_BIGGERSIZEOK = 0x1
        hbitmap = factory.GetImage(SIZE(size, size), SIIGBF_BIGGERSIZEOK)
        try:
            return 'data:image/png;base64,' + base64.b64encode(_hbitmap_to_png(hbitmap)).decode()
        finally:
            gdi32.DeleteObject(hbitmap)
    except Exception as e:
        print(f"App Icon Error: {e}")
        return None


# Private copies, so these declarations don't change the shared ctypes.windll functions other code relies on.
# Handles are 64-bit; without the declarations ctypes squeezes them into 32-bit ints.
gdi32, user32 = ctypes.WinDLL('gdi32'), ctypes.WinDLL('user32')
gdi32.GetObjectW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
gdi32.GetDIBits.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
gdi32.DeleteObject.argtypes = [ctypes.c_void_p]
user32.GetDC.restype = ctypes.c_void_p
user32.GetDC.argtypes = [ctypes.c_void_p]
user32.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]


def _hbitmap_to_png(hbitmap):

    class BITMAP(ctypes.Structure):
        _fields_ = [('bmType', ctypes.c_long), ('bmWidth', ctypes.c_long), ('bmHeight', ctypes.c_long),
                    ('bmWidthBytes', ctypes.c_long), ('bmPlanes', wintypes.WORD), ('bmBitsPixel', wintypes.WORD),
                    ('bmBits', ctypes.c_void_p)]

    bm = BITMAP()
    gdi32.GetObjectW(hbitmap, ctypes.sizeof(bm), ctypes.byref(bm))
    w, h = bm.bmWidth, bm.bmHeight
    header = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)  # negative height: top-down rows
    pixels = ctypes.create_string_buffer(w * h * 4)
    hdc = user32.GetDC(None)
    gdi32.GetDIBits(hdc, hbitmap, 0, h, pixels, ctypes.byref(header), 0)
    user32.ReleaseDC(None, hdc)

    raw = bytearray()
    data = pixels.raw
    for y in range(h):
        raw.append(0)  # PNG filter type: none
        for x in range(w):
            b, g, r, a = data[(y * w + x) * 4:(y * w + x) * 4 + 4]
            if 0 < a < 255:  # the shell hands back premultiplied alpha
                r, g, b = (min(255, c * 255 // a) for c in (r, g, b))
            raw += bytes((r, g, b, a))

    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)

    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(bytes(raw))) + chunk(b'IEND', b''))
