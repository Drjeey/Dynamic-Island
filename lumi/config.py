import json
import tempfile
import threading
from pathlib import Path

# --- PATHS ---
BASE_DIR = Path(__file__).resolve().parent.parent
ENTRY_SCRIPT = BASE_DIR / 'island7.py'
UI_DIR = BASE_DIR / 'ui'
CONFIG_PATH = BASE_DIR / 'config.json'
NOTES_PATH = BASE_DIR / 'notes.txt'
FOCUS_LOG_PATH = BASE_DIR / 'focus_log.json'
STORAGE_PATH = Path(tempfile.gettempdir()) / 'island_lumi_storage'

# --- WINDOW ---
WINDOW_TITLE = 'DynamicIsland'
WINDOW_WIDTH = 600   # CSS pixels; wide enough for the widest panel
MIN_HEIGHT = 200     # CSS pixels; the window grows to fit what's on screen
# Window pixels of exactly this color become see-through; the UI must never use it
TRANSPARENT_KEY = '#010101'
# Painted behind the island and Lumi so those areas catch the mouse; hidden by the shapes on top
HIT_COLOR = '#0c0c0c'
AUTO_START_NAME = 'DynamicIslandLumi'

# The Gemini API key is read from the GEMINI_API_KEY environment variable, or from Windows Credential
# Manager (set in Settings; see credentials.py). Never paste it into the code or config.json.
DEFAULT_CONFIG = {
    "geometry": {"x": None, "y": 0},   # used when "anchor" is "free"
    "anchor": "top_center",            # "top_center" snaps to the top centre of "monitor"; "free" stays where dragged
    "monitor": 0,                      # index into the display list; 0 is the primary display
    "auto_start": False,
    "hide_in_fullscreen": True,
    "scroll_volume": True,
    "motion": "system",                # "system" follows Windows; or "full" / "subtle" / "off"
    "lumi_visible": True,
    "lumi_idle": "peek",               # "peek": tucked under the island until Lumi has something to say; "always"
    "lumi_color": "cloud",             # one of LUMI_COLORS
    "celebrations": True,              # a short moment for focus milestones
    "weekly_summary": True,            # Lumi offers last week's focus recap once a week
    "last_summary_week": "",
    "last_greeting": "",               # date of the last daily greeting
    "milestones_shown": [],            # milestone keys already celebrated
    "hotkey": "Win+Alt+Space",         # Ctrl+Alt+Space is taken by the Claude desktop app on some PCs
    "gemini_api_key": "",              # only read once, to move an old key into Credential Manager
    "ai_provider": "gemini",           # who answers: gemini, claude, openai or custom (any OpenAI-compatible server)
    "gemini_model": "gemini-3.5-flash",
    "gemini_backup_model": "gemini-3.5-flash-lite",  # asked instead when the chosen model is busy; "" for none
    "claude_model": "claude-opus-5-5",
    "openai_model": "gpt-5-mini",
    "custom_model": "llama3.2",
    "custom_url": "http://localhost:11434/v1",  # Ollama's default; LM Studio uses http://localhost:1234/v1
    "voice_mode": "standard",          # "standard": record, then reply; "live": streaming conversation (Gemini Live)
    "live_model": "gemini-2.5-flash-native-audio-preview-09-2025",
    "voice_notice_seen": False,
    "live_notice_seen": False,
    "onboarding_done": False,
}

VOICE_NOTICE = ("Before we chat: your voice goes to Google to turn it into text, "
                "and your words go to {provider} for my reply. Click the mic again to start.")
LIVE_VOICE_NOTICE = ("Before we chat: in live mode your voice streams straight to Gemini while the mic is on. "
                     "Click the mic again to start.")

# Settings the settings window may change, and the type each must have.
# The API key is handled separately (credentials.py) so it never lands in config.json.
EDITABLE = {
    'anchor': str, 'monitor': int, 'auto_start': bool, 'hide_in_fullscreen': bool, 'scroll_volume': bool,
    'motion': str, 'lumi_visible': bool, 'hotkey': str, 'voice_mode': str, 'live_model': str,
    'ai_provider': str, 'gemini_model': str, 'gemini_backup_model': str, 'claude_model': str, 'openai_model': str, 'custom_model': str, 'custom_url': str,
    'lumi_color': str, 'celebrations': bool, 'weekly_summary': bool, 'lumi_idle': str,
}

# Lumi's colour presets (soft, light tints so the dark eyes stay readable)
LUMI_COLORS = {'cloud': '#F2F2F7', 'peach': '#FFD9C4', 'mint': '#C9F0DA', 'sky': '#CFE2FF', 'lilac': '#E2D6FF', 'butter': '#FFF0B8'}


class Config(dict):
    """Settings loaded from config.json, saved back a moment after the last change."""

    def __init__(self):
        super().__init__(json.loads(json.dumps(DEFAULT_CONFIG)))  # deep copy so the defaults are never mutated
        self._timer = None
        if CONFIG_PATH.exists():
            try:
                saved = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
                self['geometry'].update({k: v for k, v in saved.pop('geometry', {}).items() if k in ('x', 'y')})
                self.update({k: v for k, v in saved.items() if k in DEFAULT_CONFIG})
            except Exception as e:
                print(f"Config Load Error: {e}")

    def save(self):
        try: CONFIG_PATH.write_text(json.dumps(self, indent=2), encoding='utf-8')
        except Exception as e: print(f"Config Save Error: {e}")

    def save_soon(self, delay=0.5):
        # Dragging fires many events per second; only write once things settle
        if self._timer: self._timer.cancel()
        self._timer = threading.Timer(delay, self.save)
        self._timer.daemon = True
        self._timer.start()
