from dataclasses import dataclass

from .config import NOTES_PATH
from .system import SystemHelpers, Volume


class ToolFailed(Exception):
    """A tool couldn't do what was asked; the message goes back to Gemini and, briefly, to the user."""


@dataclass(frozen=True)
class ToolSpec:
    kind: str       # 'action' changes something; 'lookup' only reads
    label: str      # shown while the tool runs: verb + noun, short enough for the compact pill (never model text)
    reaction: str   # Lumi's reaction when it succeeds: 'success' (hop) or 'nod'
    receipt: str = ''  # for lookups: the receipt line; actions use the tool's own confirmation


TOOL_SPECS = {
    'start_focus':    ToolSpec('action', 'Starting focus…', 'success'),
    'stop_focus':     ToolSpec('action', 'Stopping focus…', 'success'),
    'add_to_note':    ToolSpec('action', 'Adding to note…', 'success'),
    'control_media':  ToolSpec('action', 'Adjusting music…', 'nod'),
    'open_app':       ToolSpec('action', 'Opening app…', 'success'),
    'change_volume':  ToolSpec('action', 'Setting volume…', 'nod'),
    'read_note':      ToolSpec('lookup', 'Reading note…', 'nod', 'Checked your note'),
    'now_playing':    ToolSpec('lookup', 'Checking music…', 'nod', "Checked what's playing"),
    'system_status':  ToolSpec('lookup', 'Checking PC…', 'nod', 'Checked your PC'),
}
UNKNOWN_SPEC = ToolSpec('action', 'Working…', 'nod')


class LumiTools:
    """What Lumi may do on the island when asked. Gemini sees each method's name, type hints and docstring,
    so those are written for the model. Tools don't talk to the page themselves: run() reports their progress."""

    def __init__(self, ctrl):
        self._ctrl = ctrl

    def functions(self):
        return [self.start_focus, self.stop_focus, self.add_to_note, self.read_note, self.control_media,
                self.now_playing, self.open_app, self.system_status, self.change_volume]

    def run(self, run, name, args):
        """Runs one tool inside an activity run; returns the text for Gemini. Never raises."""
        spec = TOOL_SPECS.get(name, UNKNOWN_SPEC)
        tools = {f.__name__: f for f in self.functions()}
        run.emit('tool_started', tool=name, kind=spec.kind, label=spec.label)
        try:
            if name not in tools:
                raise ToolFailed(f'Unknown tool {name}')
            result = str(tools[name](**(args or {})))
        except ToolFailed as e:
            run.emit('tool_finished', tool=name, kind=spec.kind, status='failed', reaction='reconsider', receipt=str(e))
            return f'Failed: {e}'
        except Exception as e:
            print(f"Tool Error ({name}): {e}")
            run.emit('tool_finished', tool=name, kind=spec.kind, status='failed', reaction='reconsider',
                     receipt="That didn't work")
            return f'Failed: {e}'
        receipt = spec.receipt if spec.kind == 'lookup' else result
        run.emit('tool_finished', tool=name, kind=spec.kind, status='ok', reaction=spec.reaction, receipt=receipt)
        return result

    # --- the tools ---
    def start_focus(self, minutes: int) -> str:
        """Starts a focus session (a countdown shown in the island) for the given number of minutes, 1 to 240."""
        minutes = max(1, min(240, int(minutes)))
        self._ctrl.focus.start(minutes)
        return f'Focus started for {minutes} minutes'

    def stop_focus(self) -> str:
        """Stops the current focus session or break, if one is running."""
        if not self._ctrl.focus.active:
            raise ToolFailed('No focus session is running')
        self._ctrl.focus.stop()
        return 'Focus stopped'

    def add_to_note(self, text: str) -> str:
        """Adds a line of text to the end of the user's quick note."""
        existing = NOTES_PATH.read_text(encoding='utf-8') if NOTES_PATH.exists() else ''
        NOTES_PATH.write_text((existing.rstrip('\n') + '\n' if existing.strip() else '') + text.strip(), encoding='utf-8')
        return 'Added to your note'

    def read_note(self) -> str:
        """Returns the text of the user's quick note."""
        text = NOTES_PATH.read_text(encoding='utf-8') if NOTES_PATH.exists() else ''
        return text.strip() or 'The note is empty'

    def control_media(self, action: str) -> str:
        """Controls whatever music or video is playing. action is one of: play_pause, next, previous."""
        keys = {'play_pause': 'play', 'play': 'play', 'pause': 'play', 'next': 'next', 'previous': 'prev', 'prev': 'prev'}
        if action not in keys:
            raise ToolFailed('Unknown media action; use play_pause, next or previous')
        self._ctrl.media.control(keys[action])
        return {'play': 'Play or pause', 'next': 'Next track', 'prev': 'Previous track'}[keys[action]]

    def now_playing(self) -> str:
        """Returns what is playing right now (title, artist, app) and whether it is playing or paused."""
        m = self._ctrl.media.state
        if not m.get('active'):
            return 'Nothing is playing'
        who = ' by ' + m['artist'] if m.get('artist') else ''
        return f"{m['title']}{who} in {m.get('app') or 'an app'} ({'playing' if m.get('playing') else 'paused'})"

    def open_app(self, name: str) -> str:
        """Opens an installed app by its name, for example Calculator, Notepad or Spotify."""
        matches = self._ctrl.apps.search(name, limit=1)
        if not matches:
            raise ToolFailed(f'No installed app matches "{name}"')
        self._ctrl.apps.launch(matches[0]['id'])
        return f"Opening {matches[0]['name']}"

    def system_status(self) -> str:
        """Returns the PC's memory use, battery level (or that it is plugged in) and whether it is online."""
        s = SystemHelpers.get_stats()
        battery = 'plugged in, no battery' if s['bat'] is None else f"battery {s['bat']}%{' and charging' if s['charging'] else ''}"
        online = {True: 'online', False: 'offline', None: 'network not checked yet'}[s['online']]
        return f"Memory {s['ram']}% used, {battery}, {online}"

    def change_volume(self, percent_change: int) -> str:
        """Raises (positive) or lowers (negative) the system volume by the given number of percentage points."""
        result = Volume.change(round(percent_change / 2))
        if not result:
            raise ToolFailed("Couldn't change the volume")
        return f"Volume {result['level']}%"
