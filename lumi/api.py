import os
import threading
from datetime import datetime
from urllib.parse import quote_plus

from . import credentials, providers
from .config import EDITABLE, LIVE_VOICE_NOTICE, LUMI_COLORS, NOTES_PATH, VOICE_NOTICE
from .providers import PROVIDERS
from .system import SystemHelpers, Volume

# Command-bar keywords, matched on the first word as you type
COMMANDS = [
    ('focus', 'Start focus', 'hourglass'),
    ('break', 'Take a 5-minute break', 'hourglass'),
    ('note', 'Add to your note', 'note'),
    ('chat', 'Chat with Lumi', 'lumi'),
    ('summary', 'Show your focus summary', 'hourglass'),
    ('play', 'Play or pause', 'playpause'),
    ('pause', 'Play or pause', 'playpause'),
    ('next', 'Next track', 'next'),
    ('previous', 'Previous track', 'prev'),
    ('music', 'Show what\'s playing', 'music'),
    ('settings', 'Open Settings', 'settings'),
    ('quit', 'Quit Lumi Island', 'power'),
]
# A query starting with one of these (or ending in "?") is probably meant for Lumi
QUESTION_WORDS = {'what', 'why', 'how', 'who', 'when', 'where', 'which', 'is', 'are', 'can', 'could', 'should',
                  'would', 'do', 'does', 'tell', 'explain', 'write', 'help', 'give', 'summarise', 'summarize',
                  'translate', 'remind', 'set', 'start', 'add', 'turn', 'make'}



def _whom(config, provider):
    """Where typed and spoken words go, for the privacy notice."""
    if provider == 'custom':
        url = config.get('custom_url') or ''
        return 'your own model on this PC' if '//localhost' in url or '//127.0.0.1' in url else 'the server at ' + url
    return PROVIDERS[provider]['label']

class IslandAPI:
    """Methods the island page can call. Underscore names keep pywebview from exposing (and recursively scanning) them."""

    def __init__(self, controller):
        self._ctrl = controller

    # --- startup ---
    def init(self):
        c = self._ctrl
        return {'prefs': c.prefs(), 'onboarding': not c.config.get('onboarding_done'), 'media': c.media.state,
                'hotkey_error': c.hotkey_error, 'greeting': self._daily_greeting()}

    def _daily_greeting(self):
        # Lumi says hello once a day, the first time the island loads
        today = datetime.now()
        if self._ctrl.config.get('last_greeting') == today.date().isoformat():
            return None
        self._ctrl.config['last_greeting'] = today.date().isoformat()
        self._ctrl.config.save()
        return 'Good morning' if today.hour < 12 else 'Good afternoon' if today.hour < 18 else 'Good evening'

    def finish_onboarding(self):
        self._ctrl.config['onboarding_done'] = True
        self._ctrl.config.save()

    # --- window plumbing ---
    def set_hit_areas(self, shapes, page_width, content_height=0):
        return self._ctrl.update_hit_areas(shapes, page_width, content_height)
    def track_pointer(self, on): self._ctrl.set_pointer_tracking(bool(on))
    def activity_snapshot(self): return self._ctrl.activity.snapshot()
    def cancel_run(self): return self._ctrl.cancel_run()
    def watch_stats(self, on): self._ctrl.set_stats_watching(bool(on))

    # --- panels ---
    def open_dashboard(self): self._ctrl.push('dashboard', SystemHelpers.get_stats())
    def open_menu(self): self._ctrl.push('menu', {})
    def open_music(self): self._ctrl.push('music', self._ctrl.media.state)
    def open_focus(self): self._ctrl.push('focus', self._ctrl.focus.state())
    def open_notes(self):
        content = ""
        if NOTES_PATH.exists(): content = NOTES_PATH.read_text(encoding='utf-8')
        self._ctrl.push('notes', {'note': content})
    def open_chat(self):
        chat = self._ctrl._chat
        self._ctrl.push('chat', {'messages': chat.messages if chat else []})
    def open_command_bar(self): self._ctrl.open_command_bar()
    def command_closed(self): self._ctrl.restore_foreground()
    def open_settings(self): self._ctrl.open_settings()
    def hide_for(self, minutes): self._ctrl.hide_for(float(minutes))
    def quit(self): self._ctrl.quit()

    # --- actions ---
    def save_note(self, text):
        try: NOTES_PATH.write_text(text, encoding='utf-8')
        except Exception as e: print(f"Note Save Error: {e}")
    def scroll(self, delta):
        if not self._ctrl.config.get('scroll_volume', True):
            return None
        return Volume.change(-1 if delta > 0 else 1)
    def media(self, action): self._ctrl.media.control(action)
    def start_focus(self, minutes): self._ctrl.focus.start(int(minutes))
    def start_break(self, minutes=5): self._ctrl.focus.start(int(minutes), kind='break')
    def stop_focus(self): self._ctrl.focus.stop()
    def stop_weekly_summaries(self): self._ctrl.apply_setting('weekly_summary', False)

    # --- Lumi ---
    def start_listening(self):
        c = self._ctrl
        provider = providers.chosen(c.config)
        # Live voice is Gemini Live; with any other provider the mic uses standard voice
        live = c.config.get('voice_mode') == 'live' and PROVIDERS[provider]['live']
        seen_key = 'live_notice_seen' if live else 'voice_notice_seen'
        if not c.config.get(seen_key):
            # First use: say where the audio goes before the mic ever opens
            c.config[seen_key] = True
            c.config.save()
            notice = LIVE_VOICE_NOTICE if live else VOICE_NOTICE.format(provider=_whom(c.config, provider))
            c.push('idle', {'status': 'notice', 'text': notice})
            return
        if live:
            c.live().toggle()
        else:
            threading.Thread(target=c.chat().listen_and_respond, daemon=True).start()

    def ask(self, text):
        """Typed chat: returns {'reply': ...} or {'error': ...}; Lumi may act on the island before replying."""
        return self._ctrl.chat().ask(text)

    # --- command bar ---
    def search(self, query):
        q = query.strip()
        if not q:
            return {'pins': self._ctrl.apps.pins(), 'results': []}
        results = []
        first, _, rest = q.partition(' ')
        for word, title, icon in COMMANDS:
            if not word.startswith(first.lower()) or (rest and first.lower() != word):
                continue
            if word == 'focus':
                minutes = int(rest) if rest.isdigit() and 0 < int(rest) <= 240 else 25
                if self._ctrl.focus.active:
                    results.append({'kind': 'command', 'id': 'stop_focus', 'title': 'Stop focus', 'glyph': icon})
                else:
                    results.append({'kind': 'command', 'id': 'focus', 'arg': minutes, 'title': f'Start focus · {minutes} min', 'glyph': icon})
            elif word == 'note':
                if rest:
                    results.append({'kind': 'command', 'id': 'note', 'arg': rest, 'title': f'Add "{rest}" to your note', 'glyph': icon})
                else:
                    results.append({'kind': 'command', 'id': 'open_note', 'title': 'Open your note', 'glyph': icon})
            elif not rest:
                results.append({'kind': 'command', 'id': word, 'title': title, 'glyph': icon})
        seen = set()
        results = [r for r in results if not (r['title'] in seen or seen.add(r['title']))]
        if not rest or not results:
            results += [{'kind': 'app', 'id': a['id'], 'title': a['name'], 'icon': a['icon']} for a in self._ctrl.apps.search(q)]
        # Asking Lumi is offered first for questions, otherwise just above the web search
        ask = {'kind': 'ask', 'id': 'ask', 'arg': q, 'title': f'Ask Lumi "{q}"', 'glyph': 'lumi'}
        looks_like_question = q.endswith('?') or first.lower() in QUESTION_WORDS or (len(q.split()) >= 4 and not results)
        web = {'kind': 'web', 'id': 'web', 'arg': q, 'title': f'Search the web for "{q}"', 'glyph': 'globe'}
        if looks_like_question:
            return {'pins': [], 'results': [ask] + results[:4] + [web]}
        return {'pins': [], 'results': results[:4] + [ask, web]}

    def run(self, item):
        """Runs a command-bar result; returns a short confirmation for the island, or None."""
        c = self._ctrl
        kind, ident, arg = item.get('kind'), item.get('id'), item.get('arg')
        try:
            if kind == 'app':
                c.apps.launch(ident)
                return f'Opening {item.get("title", "app")}'
            if kind == 'web':
                os.startfile('https://www.google.com/search?q=' + quote_plus(str(arg)))
                return 'Searching the web'
            if ident == 'focus':
                c.focus.start(int(arg or 25))
                return None  # the focus countdown takes over the island
            if ident == 'stop_focus': c.focus.stop(); return 'Focus stopped'
            if ident == 'break': c.focus.start(5, kind='break'); return None
            if ident == 'note':
                existing = NOTES_PATH.read_text(encoding='utf-8') if NOTES_PATH.exists() else ''
                NOTES_PATH.write_text((existing.rstrip('\n') + '\n' if existing.strip() else '') + str(arg), encoding='utf-8')
                return 'Added to your note'
            if ident == 'open_note': threading.Timer(0.3, self.open_notes).start(); return None
            if ident == 'chat': threading.Timer(0.3, self.open_chat).start(); return None
            if ident == 'summary': threading.Timer(0.3, c.offer_weekly_summary, kwargs={'force': True}).start(); return None
            if ident in ('play', 'pause'): c.media.control('play'); return None
            if ident == 'next': c.media.control('next'); return None
            if ident == 'previous': c.media.control('prev'); return None
            if ident == 'music': threading.Timer(0.3, self.open_music).start(); return None
            if ident == 'settings': c.open_settings(); return None
            if ident == 'quit': threading.Timer(0.2, c.quit).start(); return None
        except Exception as e:
            print(f"Command Error: {e}")
            return "That didn't work"
        return None


# What Settings can try out on Lumi (name -> label shown on the island)
PREVIEWS = {
    'greet': 'Greet', 'happy': 'Happy', 'giggle': 'Giggle', 'surprised': 'Surprised', 'shy': 'Shy', 'sad': 'Sad',
    'dizzy': 'Dizzy', 'yawn': 'Yawn', 'notice': 'Notice', 'success': 'Done', 'nod': 'Nod', 'reconsider': 'Rethink',
    'puzzled': 'Puzzled', 'celebrate': 'Celebrate',
    'listening': 'Listening', 'thinking': 'Thinking', 'checking': 'Checking', 'working': 'Working', 'replying': 'Replying',
    'speaking': 'Speaking', 'waiting': 'Waiting',
    'dance': 'Dancing', 'music': 'Music', 'focus': 'Focus', 'break': 'Break', 'sleepy': 'Sleepy',
}


class SettingsAPI:
    """Methods the settings window can call. The API key can be saved or removed, but never read back."""

    def __init__(self, controller):
        self._ctrl = controller

    def get(self):
        c = self._ctrl
        values = {k: c.config.get(k) for k in EDITABLE}
        keys = {name: {'set': credentials.has_stored_key(name), 'from_env': credentials.key_from_environment(name),
                       'env': credentials.ENVIRONMENT.get(name)} for name in PROVIDERS}
        return {'values': values, 'monitors': c.monitor_names(), 'hotkey_error': c.hotkey_error, 'colors': LUMI_COLORS,
                'providers': PROVIDERS, 'keys': keys}

    def set(self, key, value):
        if key not in EDITABLE:
            return {'ok': False, 'error': 'Unknown setting.'}
        try:
            value = EDITABLE[key](value)
        except (TypeError, ValueError):
            return {'ok': False, 'error': 'That value isn\'t valid.'}
        if key == 'hotkey':
            # " ctrl + alt + k " -> "Ctrl+Alt+K"
            parts = [p.strip() for p in value.split('+') if p.strip()]
            value = '+'.join(p.upper() if len(p) == 1 else p.capitalize() for p in parts)
        if isinstance(value, str):
            value = value.strip()
        error = self._ctrl.apply_setting(key, value)
        return {'ok': error is None, 'error': error}

    def set_api_key(self, value, provider='gemini'):
        if provider not in PROVIDERS:
            return {'ok': False, 'error': 'Unknown provider.'}
        error = credentials.set_api_key(str(value or '').strip(), provider)
        if not error:
            self._ctrl.reset_chat()
        return {'ok': error is None, 'error': error}

    def replay_tour(self): self._ctrl.push('onboard', {})

    def preview(self, name):
        """Plays a reaction, working state or mood on the real Lumi for a few seconds."""
        if name not in PREVIEWS:
            return {'ok': False, 'error': 'Unknown reaction.'}
        self._ctrl.push('preview', {'name': name, 'label': PREVIEWS[name]})
        return {'ok': True}
    def close(self): self._ctrl.close_settings()
