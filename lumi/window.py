import ctypes
import json
import shutil
import sys
import tempfile
import threading
import time
import winreg
from ctypes import wintypes
from pathlib import Path

import webview

from .api import IslandAPI, SettingsAPI
from .activity import ActivityBus
from .providers import PROVIDERS
from .apps import AppIndex
from .credentials import migrate_from_config
from .focus import FocusManager
from .config import (AUTO_START_NAME, ENTRY_SCRIPT, HIT_COLOR, MIN_HEIGHT, STORAGE_PATH, TRANSPARENT_KEY,
                     LUMI_COLORS, WINDOW_TITLE, WINDOW_WIDTH, Config)
from .hotkey import GlobalHotkey
from .media import MediaWatcher
from .system import MONITORINFO, SystemHelpers, Volume, list_monitors

SWP_NOSIZE, SWP_NOMOVE, SWP_NOZORDER, SWP_NOACTIVATE = 0x1, 0x2, 0x4, 0x10
# A private copy of user32: declaring argument types on the shared ctypes.windll.user32 would change
# them for pywebview too, and break its own calls (dragging the window, for one)
user32 = ctypes.WinDLL('user32')
user32.GetForegroundWindow.restype = ctypes.c_void_p
user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.RECT)]
user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.IsWindow.argtypes = [ctypes.c_void_p]
user32.MonitorFromWindow.restype = ctypes.c_void_p
user32.MonitorFromWindow.argtypes = [ctypes.c_void_p, wintypes.DWORD]
user32.IsZoomed.argtypes = [ctypes.c_void_p]
user32.GetClassNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
user32.WindowFromPoint.restype = ctypes.c_void_p
user32.WindowFromPoint.argtypes = [wintypes.POINT]
user32.GetAncestor.restype = ctypes.c_void_p
user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]


# Settings that change who answers, or how: the conversation starts afresh when one changes
AI_KEYS = ('ai_provider', 'gemini_model', 'gemini_backup_model', 'claude_model', 'openai_model', 'custom_model', 'custom_url',
           'live_model', 'voice_mode')

class IslandController:
    def __init__(self):
        self.config = Config()
        self.window = None
        self.settings_window = None
        self._hwnd = None  # set once the window is shown
        self._scale = None  # physical pixels per CSS pixel, learned from the page
        self._pointer_tracking = threading.Event()  # set while a panel is open
        self._stats_watching = threading.Event()  # set while the dashboard is open
        self._hidden_until = 0
        self._previous_foreground = None
        self._snap_timer = None
        self._shake = {'x': None, 'dir': 0, 'turns': [], 'quiet_until': 0.0}
        self.hotkey_error = None
        self.api = IslandAPI(self)
        self.apps = AppIndex()
        self.media = MediaWatcher(lambda state: self.push('media', state))
        self.hotkey = GlobalHotkey(self.open_command_bar)
        self.focus = FocusManager(self.push)
        self.activity = ActivityBus(self.push)  # what Lumi is doing, as events for the page
        self.focus.milestone_allowed = self._milestone_allowed
        self._chat = None
        self._live = None
        self._chat_lock = threading.RLock()  # live() calls chat() while holding it

    # --- Lumi's conversation ---
    def chat(self):
        """The one conversation shared by voice and typed chat, created on first use."""
        with self._chat_lock:
            if self._chat is None:
                from .chat import ChatController
                self._chat = ChatController(self)
            return self._chat

    def live(self):
        with self._chat_lock:
            if self._live is None:
                from .live import LiveVoice
                self._live = LiveVoice(self, self.chat())
            return self._live

    def cancel_run(self):
        """Esc or the stop button while Lumi is working: the run ends now (the page goes back to normal at once)
        and its work stops at the next safe point. Speech stops between words; a live session closes."""
        cancelled = self.activity.cancel()
        with self._chat_lock:
            if self._chat:
                self._chat.hush()
                self._chat.drop_session()
            if self._live and self._live.running: self._live.toggle()
        return cancelled

    def reset_chat(self):
        # The key or a model changed: end any live session and start the conversation afresh
        with self._chat_lock:
            if self._live and self._live.running: self._live.toggle()
            self._chat = self._live = None

    # --- talking to the page ---
    def push(self, state, data=None):
        if self.window:
            safe_json = json.dumps({'state': state, 'data': data or {}})
            self.window.evaluate_js(f"window.updateState && window.updateState({safe_json})")

    PREF_KEYS = ('motion', 'lumi_visible', 'lumi_idle', 'scroll_volume', 'hotkey', 'lumi_color', 'celebrations')

    def prefs(self):
        values = {k: self.config.get(k) for k in self.PREF_KEYS}
        values['lumi_hex'] = LUMI_COLORS.get(values['lumi_color'], LUMI_COLORS['cloud'])
        return values

    # --- milestones and the weekly summary ---
    def _milestone_allowed(self, key):
        # Each milestone is celebrated once, and only if celebrations are on
        if not self.config.get('celebrations', True) or key in self.config['milestones_shown']:
            return False
        self.config['milestones_shown'] = (self.config['milestones_shown'] + [key])[-50:]
        self.config.save()
        return True

    def offer_weekly_summary(self, force=False):
        """Once per week (or when asked), Lumi offers last week's focus recap."""
        this_week = self.focus.week_summary(0)['week']
        if not force and (not self.config.get('weekly_summary', True) or self.config.get('last_summary_week') == this_week):
            return
        last = self.focus.week_summary(1)
        if not force and last['sessions'] == 0 and last['minutes'] == 0:
            return  # nothing to recap
        self.config['last_summary_week'] = this_week
        self.config.save()
        self.push('summary', {'last_week': last, 'this_week': self.focus.week_summary(0), 'asked': force})

    # --- settings ---
    def apply_setting(self, key, value):
        """Saves one setting and applies it straight away; returns an error message or None."""
        if key == 'hotkey':
            error = self.hotkey.register(value)
            if error:
                self.hotkey.register(self.config['hotkey'])  # keep the old one working
                return error
            self.hotkey_error = None
        if key == 'anchor' and value not in ('top_center', 'free'): return 'Unknown position.'
        if key == 'motion' and value not in ('system', 'full', 'subtle', 'off', 'reduced'): return 'Unknown motion setting.'
        if key == 'lumi_color' and value not in LUMI_COLORS: return 'Unknown colour.'
        if key == 'lumi_idle' and value not in ('peek', 'always'): return 'Unknown choice.'
        if key == 'voice_mode' and value not in ('standard', 'live'): return 'Unknown voice mode.'
        if key == 'ai_provider' and value not in PROVIDERS: return 'Unknown provider.'
        if key in AI_KEYS and key.endswith('_model') and key != 'gemini_backup_model' and not value.strip():
            return 'Enter a model name.'
        if key == 'custom_url' and not value.startswith(('http://', 'https://')): return 'Enter a URL starting with http:// or https://.'
        self.config[key] = value
        self.config.save()
        if key == 'auto_start': self._apply_auto_start()
        if key in ('anchor', 'monitor'): self._snap()
        if key in AI_KEYS: self.reset_chat()
        if key in self.PREF_KEYS: self.push('prefs', self.prefs())
        return None

    def open_settings(self):
        if self.settings_window:
            self.settings_window.show()
            self.settings_window.restore()
            self._bring_settings_forward()
            return
        dark = _windows_uses_dark_theme()
        self.settings_window = webview.create_window(
            'Lumi Island settings', url='ui/settings.html', js_api=SettingsAPI(self),
            width=760, height=640, min_size=(560, 480), background_color='#202020' if dark else '#F3F3F3')
        self.settings_window.events.closed += self._settings_closed
        self.settings_window.events.shown += self._bring_settings_forward

    def _bring_settings_forward(self, *args):
        # A new window otherwise opens behind whatever app was in front
        try:
            user32.SetForegroundWindow(ctypes.c_void_p(self.settings_window.native.Handle.ToInt64()))
        except Exception as e:
            print(f"Settings Window Error: {e}")

    def _settings_closed(self, *args):
        self.settings_window = None

    def close_settings(self):
        if self.settings_window: self.settings_window.destroy()

    def monitor_names(self):
        names = []
        for i, m in enumerate(list_monitors()):
            label = f"Display {i + 1} · {m['width']}×{m['height']}"
            names.append(label + (' (main)' if m['primary'] else ''))
        return names

    def _apply_auto_start(self):
        run_key = r'Software\Microsoft\Windows\CurrentVersion\Run'
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key, 0, winreg.KEY_SET_VALUE) as key:
                if self.config.get('auto_start'):
                    pythonw = Path(sys.executable).with_name('pythonw.exe')
                    exe = pythonw if pythonw.exists() else Path(sys.executable)
                    winreg.SetValueEx(key, AUTO_START_NAME, 0, winreg.REG_SZ, f'"{exe}" "{ENTRY_SCRIPT}"')
                else:
                    try: winreg.DeleteValue(key, AUTO_START_NAME)
                    except FileNotFoundError: pass
        except OSError as e:
            print(f"Auto Start Error: {e}")

    @staticmethod
    def _cleanup_old_storage():
        # Older versions created a new island_lumi_<8 random chars> folder on every launch
        for old in Path(tempfile.gettempdir()).glob('island_lumi_*'):
            if old.is_dir() and len(old.name) == len('island_lumi_') + 8:
                shutil.rmtree(old, ignore_errors=True)

    # --- command bar ---
    def open_command_bar(self):
        # The hotkey lets this process take the foreground; remember who had it so Esc can give it back
        fg = user32.GetForegroundWindow()
        if self._hwnd and fg != self._hwnd.value:
            self._previous_foreground = fg
        self._hidden_until = 0
        if self._hwnd:
            user32.ShowWindow(self._hwnd, 4)  # SW_SHOWNOACTIVATE, in case it was hidden
            user32.SetForegroundWindow(self._hwnd)
        self.push('command', {'pins': self.apps.pins() if self.apps.ready.is_set() else []})

    def restore_foreground(self):
        if self._previous_foreground and user32.IsWindow(self._previous_foreground):
            user32.SetForegroundWindow(self._previous_foreground)
        self._previous_foreground = None

    # --- hiding, quitting ---
    def hide_for(self, minutes):
        self._hidden_until = time.time() + minutes * 60

    def quit(self):
        self.hotkey.unregister()
        if self.settings_window: self.settings_window.destroy()
        if self.window: self.window.destroy()

    # --- watchers ---
    def set_pointer_tracking(self, on):
        if on: self._pointer_tracking.set()
        else: self._pointer_tracking.clear()

    def set_stats_watching(self, on):
        if on: self._stats_watching.set()
        else: self._stats_watching.clear()

    def _watch_pointer(self):
        # The page can't always tell when the mouse slides off the island onto see-through pixels,
        # so while a panel is open, check a few times a second whether the pointer is over our shapes
        GA_ROOT = 2
        last = None
        while True:
            if not self._pointer_tracking.is_set():
                last = None
                self._pointer_tracking.wait()
            pt = wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            inside = user32.GetAncestor(user32.WindowFromPoint(pt), GA_ROOT) == self._hwnd.value
            if inside != last:
                self.push('pointer', {'inside': inside})
                last = inside
            time.sleep(0.15)

    def _watch_stats(self):
        # Live numbers while the dashboard is open, nothing otherwise
        while True:
            self._stats_watching.wait()
            time.sleep(2)
            if self._stats_watching.is_set():
                self.push('stats', SystemHelpers.get_stats())

    def _fullscreen_app_in_front(self):
        # QUNS_BUSY, QUNS_RUNNING_D3D_FULL_SCREEN, QUNS_PRESENTATION_MODE: what Windows itself uses to hold back notifications
        state = ctypes.c_int(0)
        if ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(state)) == 0 and state.value in (2, 3, 4):
            return True
        # Fallback for full-screen browser video: a non-maximized foreground window covering the island's whole monitor
        fg = user32.GetForegroundWindow()
        if not fg or fg == self._hwnd.value or user32.IsZoomed(fg):
            return False
        cls = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(fg, cls, 64)
        if cls.value in ('Progman', 'WorkerW', 'Shell_TrayWnd'):
            return False
        MONITOR_DEFAULTTONEAREST = 2
        monitor = user32.MonitorFromWindow(fg, MONITOR_DEFAULTTONEAREST)
        if monitor != user32.MonitorFromWindow(self._hwnd, MONITOR_DEFAULTTONEAREST):
            return False
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        rect = wintypes.RECT()
        if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)) or not user32.GetWindowRect(fg, ctypes.byref(rect)):
            return False
        m = info.rcMonitor
        return rect.left <= m.left and rect.top <= m.top and rect.right >= m.right and rect.bottom >= m.bottom

    def _watch_visibility(self):
        # Step out of the way of full-screen apps (and while "Hide for 1 hour" runs); also re-snap if displays change
        SW_HIDE, SW_SHOWNOACTIVATE = 0, 4
        hidden = False
        away = False
        tick = 0
        while True:
            # Lumi gets sleepy after 10 minutes without any keyboard or mouse input, and wakes when you're back
            idle = _seconds_since_input()
            if (idle > AWAY_AFTER) != away:
                away = not away
                self.push('presence', {'away': away})
            try:
                busy = time.time() < self._hidden_until or (
                    self.config.get('hide_in_fullscreen', True) and self._fullscreen_app_in_front())
            except Exception as e:
                print(f"Full-screen Check Error: {e}")
                busy = False
            if busy != hidden:
                user32.ShowWindow(self._hwnd, SW_HIDE if busy else SW_SHOWNOACTIVATE)
                hidden = busy
            tick += 1
            if tick % 5 == 0 and not hidden:
                self._snap()
            time.sleep(1)

    # --- position and size ---
    def _window_rect(self):
        rect = wintypes.RECT()
        user32.GetWindowRect(self._hwnd, ctypes.byref(rect))
        return rect

    def _snap(self):
        """In top-centre mode, keeps the window centred at the top of the chosen display."""
        if not self._hwnd or self.config.get('anchor') != 'top_center':
            return
        monitors = list_monitors()
        if not monitors:
            return
        m = monitors[min(max(0, int(self.config.get('monitor', 0))), len(monitors) - 1)]
        r = self._window_rect()
        x = m['left'] + (m['width'] - (r.right - r.left)) // 2
        y = m['top']
        if (r.left, r.top) != (x, y):
            user32.SetWindowPos(self._hwnd, None, x, y, 0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE)

    def _on_moved(self, *args):
        # pywebview passes (x, y), newer versions may pass (window, x, y)
        x, y = args[-2:]
        self._watch_shake(int(x))
        if self.config.get('anchor') == 'free':
            self.config['geometry'].update({'x': int(x), 'y': int(y)})
            self.config.save_soon()
            return
        # In top-centre mode a drag picks the display; once it settles, snap to that display's top centre
        if self._snap_timer: self._snap_timer.cancel()
        self._snap_timer = threading.Timer(0.4, self._snap_to_nearest_display)
        self._snap_timer.daemon = True
        self._snap_timer.start()

    def _watch_shake(self, x):
        """Dragging the island quickly back and forth (4 turns within 1.2 s) makes Lumi dizzy."""
        now, s = time.monotonic(), self._shake
        if s['x'] is not None and abs(x - s['x']) >= 8:
            direction = 1 if x > s['x'] else -1
            if s['dir'] and direction != s['dir']:
                s['turns'].append(now)
            s['dir'] = direction
        if s['x'] is None or abs(x - s['x']) >= 8:
            s['x'] = x
        s['turns'] = [t for t in s['turns'] if now - t < 1.2]
        if len(s['turns']) >= 4 and now > s['quiet_until']:
            s['turns'], s['quiet_until'] = [], now + 3
            self.push('shake', {})

    def _snap_to_nearest_display(self):
        r = self._window_rect()
        cx, cy = (r.left + r.right) // 2, (r.top + r.bottom) // 2
        monitors = list_monitors()
        for i, m in enumerate(monitors):
            if m['left'] <= cx < m['left'] + m['width'] and m['top'] <= cy < m['top'] + m['height']:
                if i != self.config.get('monitor'):
                    self.config['monitor'] = i
                    self.config.save()
                break
        self._snap()

    def _fit_height(self, content_height):
        # Grow or shrink the window to what's on screen, so nothing (like a long reply) gets cut off
        if not self._hwnd or not self._scale:
            return
        wanted = int(max(MIN_HEIGHT, content_height + 16) * self._scale)
        r = self._window_rect()
        if abs((r.bottom - r.top) - wanted) > 4 * self._scale:
            user32.SetWindowPos(self._hwnd, None, 0, 0, r.right - r.left, wanted, SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE)

    # --- transparency and hit areas ---
    def _on_shown(self, *args):
        # With transparent=True, WebView2 shows the WinForms form behind the page (grey by default).
        # Paint that form in TRANSPARENT_KEY and make it a layered window where pixels of exactly
        # that color are invisible, leaving only the island and Lumi on screen
        try:
            form = self.window.native
            from System import Action
            from System.Drawing import ColorTranslator
            form.Invoke(Action(lambda: setattr(form, 'BackColor', ColorTranslator.FromHtml(TRANSPARENT_KEY))))
            hwnd = ctypes.c_void_p(form.Handle.ToInt64())
        except Exception as e:
            print(f"Transparency Error: {e}")
            return
        # pywebview gives windows a Mica backdrop in dark mode, which would fill the keyed-out pixels
        DWMWA_SYSTEMBACKDROP_TYPE, DWMSBT_NONE = 38, 1
        backdrop = ctypes.c_int(DWMSBT_NONE)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, ctypes.byref(backdrop), ctypes.sizeof(backdrop))

        GWL_EXSTYLE, WS_EX_LAYERED, LWA_COLORKEY = -20, 0x80000, 0x1
        user32.GetWindowLongW.restype = ctypes.c_long
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED)
        r, g, b = (int(TRANSPARENT_KEY[i:i + 2], 16) for i in (1, 3, 5))
        user32.SetLayeredWindowAttributes(hwnd, r | (g << 8) | (b << 16), 0, LWA_COLORKEY)

        self._hwnd = hwnd
        self._snap()
        for watcher in (self._watch_visibility, self._watch_pointer, self._watch_stats):
            threading.Thread(target=watcher, daemon=True).start()

    def update_hit_areas(self, shapes, page_width, content_height=0):
        # Keyed-out pixels let the mouse through, so paint the form behind the page in HIT_COLOR
        # wherever the page has a solid shape; returns False if the window isn't ready yet
        form = self.window.native if self.window else None
        if form is None or not page_width or not self._hwnd:
            return False
        from System import Action
        from System.Drawing import Bitmap, Graphics, SolidBrush, ColorTranslator, Rectangle
        from System.Drawing.Drawing2D import GraphicsPath

        self._scale = form.ClientSize.Width / page_width  # CSS pixels -> physical pixels
        if content_height:
            self._fit_height(content_height)

        def paint():
            w, h = form.ClientSize.Width, form.ClientSize.Height
            if w <= 0 or h <= 0:
                return
            scale = w / page_width
            bmp = Bitmap(w, h)
            g = Graphics.FromImage(bmp)
            g.Clear(ColorTranslator.FromHtml(TRANSPARENT_KEY))
            brush = SolidBrush(ColorTranslator.FromHtml(HIT_COLOR))
            for s in shapes:
                x, y, sw, sh = (int(round(s[k] * scale)) for k in ('x', 'y', 'w', 'h'))
                if sw <= 0 or sh <= 0:
                    continue
                if s.get('ellipse'):
                    g.FillEllipse(brush, Rectangle(x, y, sw, sh))
                    continue
                d = min(int(round(s.get('radius', 0) * scale)) * 2, sw, sh)
                if d <= 0:
                    g.FillRectangle(brush, Rectangle(x, y, sw, sh))
                    continue
                path = GraphicsPath()
                path.AddArc(Rectangle(x, y, d, d), 180.0, 90.0)
                path.AddArc(Rectangle(x + sw - d, y, d, d), 270.0, 90.0)
                path.AddArc(Rectangle(x + sw - d, y + sh - d, d, d), 0.0, 90.0)
                path.AddArc(Rectangle(x, y + sh - d, d, d), 90.0, 90.0)
                path.CloseFigure()
                g.FillPath(brush, path)
                path.Dispose()
            brush.Dispose()
            g.Dispose()
            old = form.BackgroundImage
            form.BackgroundImage = bmp
            if old is not None:
                old.Dispose()

        try:
            form.BeginInvoke(Action(paint))
        except Exception as e:
            print(f"Hit Area Error: {e}")
            return False
        return True

    # --- start ---
    def start(self):
        self._cleanup_old_storage()
        migrate_from_config(self.config)
        SystemHelpers.start_samplers()
        self._apply_auto_start()
        self.media.start()
        self.hotkey_error = self.hotkey.register(self.config.get('hotkey', 'Win+Alt+Space'))
        # Load the pinned apps' icons and open the audio device now, so the command bar and volume respond instantly
        threading.Thread(target=lambda: (self.apps.ready.wait(), self.apps.pins()), daemon=True).start()
        threading.Thread(target=Volume.warm_up, daemon=True).start()

        geo = self.config['geometry']
        free = self.config.get('anchor') == 'free'
        # ENABLED easy_drag=True for crash-proof moving
        # transparent=True alone leaves a grey background on Windows; see _on_shown
        self.window = webview.create_window(
            WINDOW_TITLE,
            url='ui/island.html',
            frameless=True, easy_drag=True, on_top=True, shadow=False,
            transparent=True, background_color=TRANSPARENT_KEY,
            width=WINDOW_WIDTH, height=360,
            x=geo.get('x') if free else None, y=geo.get('y') if free else 0,
            js_api=self.api
        )
        self.window.events.moved += self._on_moved
        self.window.events.shown += self._on_shown
        webview.start(debug=False, http_server=True, storage_path=str(STORAGE_PATH))
        self.hotkey.unregister()


AWAY_AFTER = 600  # seconds


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [('cbSize', ctypes.c_uint), ('dwTime', ctypes.c_uint)]


def _seconds_since_input():
    info = LASTINPUTINFO(ctypes.sizeof(LASTINPUTINFO), 0)
    if not user32.GetLastInputInfo(ctypes.byref(info)):
        return 0
    return ((ctypes.windll.kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000


def _windows_uses_dark_theme():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as k:
            return winreg.QueryValueEx(k, 'AppsUseLightTheme')[0] == 0
    except OSError:
        return True
