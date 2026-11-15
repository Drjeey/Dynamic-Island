"""Claude Code and Codex on the island: run them from Lumi, and follow the sessions you run yourself.

Every session becomes a short chain of *nodes* for the page: what you asked, then each step the agent takes
(thinking, reading a file, editing one, running a command, searching), then how it ended. A node is
{'id', 'kind', 'label', 'detail', 'state'} with state 'active', 'done' or 'failed'.

Sessions started here run the agent's own command-line tool headless (claude -p ... --output-format stream-json,
codex exec --json) and read its events as they arrive. Sessions you run yourself are followed by reading the logs
both tools already write (~/.claude/projects/*/*.jsonl and ~/.codex/sessions/**/rollout-*.jsonl; the Codex app's
list of conversations, ~/.codex/state_5.sqlite, read-only, says which Codex logs are in use). Nothing is
sent anywhere; labels hold only tool names, file names and the first words of commands.
"""
import json
import os
import re
import shutil
import sqlite3
import subprocess
import threading
import time
from datetime import date, timedelta
from pathlib import Path

AGENTS = {'claude': 'Claude Code', 'codex': 'Codex'}
MAX_NODES = 40          # kept per session; the page shows the last few
WATCH_FRESH = 20        # seconds: a log written this recently is a session that's running
WATCH_STALE = 600       # seconds: a running session silent this long is dropped
KEEP_FINISHED = 12      # seconds a finished session stays on the island
TEXT_MAX = 6000         # characters of an answer kept, so you can read it in full on the island
CREATE_NO_WINDOW = 0x08000000
HOST_ONLY_ENV = ('ANTHROPIC_BASE_URL', 'USE_LOCAL_OAUTH', 'USE_STAGING_OAUTH', 'CLAUDE_PREVIEW_CLASSIFIER_FLOOR')
TURN_ENDS = ('end_turn', 'stop_sequence')  # stop_sequence: a line the tool wrote itself ("No response requested.")
PASTED = re.compile(r'<pasted_content\b[^>]*>(.*?)</pasted_content\b[^>]*>', re.S)

HOME = Path.home()
CLAUDE_LOGS = HOME / '.claude' / 'projects'
CODEX_LOGS = HOME / '.codex' / 'sessions'
CODEX_THREADS = HOME / '.codex' / 'state_5.sqlite'  # the Codex app's list of conversations and where each one logs
READ_MAX = 4_000_000      # bytes read from one log per check; a big burst is read over the next checks
LINE_MAX = 16_000_000     # an unfinished line longer than this is skipped rather than waited for


# --- finding the tools ---
def _version_key(path):
    # .../claude-code/2.1.309/<hash>/claude.exe -> (2, 1, 309)
    for part in reversed(path.parts):
        if part[:1].isdigit() and '.' in part:
            return tuple(int(p) if p.isdigit() else 0 for p in part.split('.'))
    return ()


def find_cli(agent):
    """The newest installed claude / codex executable, or None. PATH first, then where the desktop apps keep theirs."""
    exe = shutil.which(agent)
    if exe:
        return exe
    local, roaming = Path(os.environ.get('LOCALAPPDATA', '')), Path(os.environ.get('APPDATA', ''))
    if agent == 'claude':
        candidates = list(local.glob('Claude-Data/*/claude-code/*/*/claude.exe')) + [
            HOME / '.local' / 'bin' / 'claude.exe', HOME / '.claude' / 'local' / 'claude.exe', roaming / 'npm' / 'claude.cmd']
    else:
        candidates = list(local.glob('OpenAI/Codex/bin/*/codex.exe')) + [roaming / 'npm' / 'codex.cmd']
    found = [c for c in candidates if c.is_file()]
    if not found:
        return None
    return str(max(found, key=lambda p: (_version_key(p), p.stat().st_mtime)))


_seen = {}  # agent -> (when checked, installed): looking for the tools walks the disk, and this is asked 4 times a second


def _installed(agent):
    checked, found = _seen.get(agent, (0, False))
    if time.time() - checked > 30:
        found = bool(find_cli(agent))
        _seen[agent] = (time.time(), found)
    return found


# --- labels ---
def _short(text, n=60):
    text = ' '.join(str(text or '').split())
    return text if len(text) <= n else text[:n - 1] + '…'


def _name(path):
    return Path(str(path)).name or str(path) if path else ''


MCP_SERVERS = {'cua_repl': 'Using the computer', 'node_repl': 'Running code', 'browser': 'Using the browser'}


def _tool_name(tool, server=''):
    """'google_drive.get_spreadsheet' -> 'Google drive: get spreadsheet'; a bare 'js' says what the server is for."""
    tool = str(tool or '').strip()
    if len(tool) <= 3 and server:
        return MCP_SERVERS.get(server) or 'Using ' + server.replace('_', ' ')
    text = tool.replace('_', ' ').replace('.', ': ') or 'Tool'
    return text[:1].upper() + text[1:]


def _command_words(cmd):
    """'"C:\\...\\powershell.exe" -Command \'Get-Content -Raw a.txt\'' -> 'Get-Content -Raw a.txt'"""
    if isinstance(cmd, list):
        cmd = cmd[-1] if len(cmd) > 1 and str(cmd[-2]).lower() in ('-command', '-c', '/c') else ' '.join(map(str, cmd))
    cmd = str(cmd or '').strip()
    for flag in (' -Command ', ' -c ', ' /c '):
        if flag in cmd:
            cmd = cmd.split(flag, 1)[1]
    return _short(cmd.strip('\'" '), 56)


def claude_tool_node(name, args):
    """(kind, label, detail) for one Claude Code tool call."""
    a = args if isinstance(args, dict) else {}
    path = a.get('file_path') or a.get('notebook_path') or a.get('path')
    if name == 'Read': return 'read', 'Reading ' + (_name(path) or 'a file'), ''
    if name in ('Edit', 'MultiEdit', 'NotebookEdit'): return 'edit', 'Editing ' + (_name(path) or 'a file'), ''
    if name == 'Write': return 'edit', 'Writing ' + (_name(path) or 'a file'), ''
    if name in ('Bash', 'PowerShell'):
        return 'run', _short(a.get('description') or 'Running a command', 48), _command_words(a.get('command'))
    if name in ('Grep', 'Glob'): return 'search', 'Searching files', _short(a.get('pattern'), 48)
    if name in ('WebSearch', 'WebFetch'): return 'web', 'Searching the web' if name == 'WebSearch' else 'Reading a page', _short(a.get('query') or a.get('url'), 48)
    if name in ('Task', 'Agent'): return 'agent', 'Starting a helper', _short(a.get('description'), 48)
    if name in ('TodoWrite', 'mcp__ccd_turn__update_plan'): return 'plan', 'Updating the plan', ''
    if name.startswith('mcp__'):
        parts = name.split('__')
        return 'tool', _short(parts[-1].replace('_', ' ').capitalize(), 40), ''
    return 'tool', _short(name, 40), ''


def codex_item_node(item):
    """(kind, label, detail) for one Codex item (both exec --json and rollout log spellings), or None to skip."""
    t = str(item.get('type', '')).lower().replace('_', '')
    if t == 'reasoning': return 'think', 'Thinking', ''
    if t == 'commandexecution': return 'run', 'Running a command', _command_words(item.get('command'))
    if t == 'filechange':
        changes = item.get('changes') or {}
        names = [_name(c.get('path')) for c in changes] if isinstance(changes, list) else [_name(p) for p in changes]
        return 'edit', 'Editing ' + (names[0] if len(names) == 1 else f'{len(names)} files' if names else 'files'), ', '.join(names[1:4])
    if t in ('mcptoolcall',):
        # The call's own title ("Checking connection dialog") reads better than the tool's name ("Js")
        args = item.get('arguments') if isinstance(item.get('arguments'), dict) else {}
        title = args.get('title') if isinstance(args.get('title'), str) else ''
        server = str(item.get('server') or '')
        return 'tool', _short(title or _tool_name(item.get('tool'), server), 40), _short(server.replace('_', ' '), 30)
    if t in ('websearch', 'extension'): return 'web', 'Searching the web', _short(item.get('query'), 48)
    if t == 'imageview': return 'read', 'Looking at an image', _name(item.get('path'))
    if t == 'todolist': return 'plan', 'Updating the plan', ''
    if t == 'contextcompaction': return 'think', 'Tidying its memory', ''
    if t == 'error': return 'error', 'Problem', _short(item.get('message'), 56)
    return None


# Failures you can fix yourself, said so you know how
HINTS = (
    ('credit balance is too low', "Claude Code's own login has no credit. In a terminal, run claude and type /login."),
    ('not logged in', 'Not signed in. In a terminal, run the tool once and sign in.'),
    ('/login', 'Not signed in. In a terminal, run claude and type /login.'),
    ('codex login', 'Codex isn\'t signed in. In a terminal, run codex login.'),
    *((key, 'No internet connection. Check your network, then try again.')
      for key in ('enotfound', 'getaddrinfo', 'econnrefused', 'etimedout', 'fetch failed', 'connection error', 'network error')),
)


def _explain(message):
    low = str(message or '').lower()
    return next((hint for key, hint in HINTS if key in low), message)


def _asked(text):
    """What a line of a Claude Code log asked: your own words beside any pasted text, or the paste if that's all
    there is. '' for the tool's bookkeeping lines, which also start with a tag (<task-notification>, <command-name>)."""
    text = text.strip()
    if text.startswith('<') and not text.startswith('<pasted_content'):
        return ''
    pasted = PASTED.search(text)
    return PASTED.sub('', text).strip() or (pasted.group(1).strip() if pasted else text)


# --- one session ---
class Session:
    def __init__(self, sid, agent, source, cwd=''):
        self.id, self.agent, self.source, self.cwd = sid, agent, source, str(cwd or '')
        self.title = ''
        self.status = 'running'     # running, done, failed, stopped
        self.message = ''           # the ending, in a few words
        self.nodes = []
        self.started = self.touched = time.time()
        self.ended = None
        self.stopping = False       # Stop was pressed
        self.stderr = ''            # the last thing the tool said on stderr
        self.chat_id = ''           # the agent's own id for this chat (a Codex thread, a Claude Code session)
        self.log_path = ''          # where the agent saves it, when known
        self._seq = 0
        self._by_key = {}           # tool call id -> node
        self._open = {}             # node id -> calls still running (repeats share a node)

    # building the chain
    def begin_turn(self, prompt):
        """A new question to the agent: the chain starts again from it."""
        self.nodes, self._by_key, self._open = [], {}, {}
        self.status, self.message, self.ended = 'running', '', None
        self.started = time.time()
        self.title = _short(prompt, 80)
        self.add('prompt', _short(prompt, 56) or 'New task', state='done', text=prompt)

    def continue_turn(self, prompt):
        """Your next message in the same chat: the earlier steps stay, and the new question follows them."""
        self.nodes = [n for n in self.nodes if not n.get('placeholder')]
        self._by_key, self._open = {}, {}
        self.status, self.message, self.ended, self.stopping = 'running', '', None, False
        self.started = time.time()
        self.add('prompt', _short(prompt, 56) or 'Next', state='done', text=prompt)

    def add(self, kind, label, detail='', state='active', key=None, placeholder=False, text=None):
        self._settle()
        self._seq += 1
        last = self.nodes[-1] if self.nodes else None
        if last and last['kind'] == kind and last['label'] == label and last['state'] != 'failed' and kind not in ('prompt', 'reply'):
            # The same step again (editing one file several times): one node with a count
            last.update(count=last.get('count', 1) + 1, state=state, detail=detail or last['detail'])
            node = last
        else:
            node = {'id': f'n{self._seq}', 'kind': kind, 'label': label, 'detail': detail, 'state': state}
            if placeholder: node['placeholder'] = True
            text = ' '.join(str(text or '').split(' ')).strip()
            if text and len(text) > len(detail or ''):
                node['text'] = text[:TEXT_MAX] + ('…' if len(text) > TEXT_MAX else '')  # shown in full when you open the step
            self.nodes.append(node)
            del self.nodes[:-MAX_NODES]
        if key:
            self._by_key[key] = node
            self._open[node['id']] = self._open.get(node['id'], 0) + 1
        self.touched = time.time()
        return node

    def finish(self, key, ok=True):
        node = self._by_key.pop(key, None)
        if node:
            self._open[node['id']] = left = self._open.get(node['id'], 1) - 1
            if node['state'] == 'active' and (left <= 0 or not ok):  # a shared step is done when its last call is
                node['state'] = 'done' if ok else 'failed'
        self.touched = time.time()

    def _settle(self):
        # A "thinking" step is over as soon as anything else happens; a stand-in for a step in progress goes
        self.nodes = [n for n in self.nodes if not n.get('placeholder')]
        for n in self.nodes:
            if n['state'] == 'active' and n['kind'] == 'think':
                n['state'] = 'done'

    def end(self, status, message=''):
        if self.status != 'running':
            return
        self.nodes = [n for n in self.nodes if not n.get('placeholder')]  # stand-ins don't belong in the finished chain
        if status == 'failed':
            message = _explain(message)
        for n in self.nodes:
            if n['state'] == 'active':
                n['state'] = 'done' if status == 'done' else 'failed'
        self.status, self.message, self.ended = status, _short(message, 90), time.time()
        label = {'done': 'Done', 'failed': 'Stopped with a problem', 'stopped': 'Stopped'}[status]
        node = {'id': f'n{self._seq + 1}', 'kind': 'end', 'label': label, 'detail': self.message,
                'state': 'done' if status == 'done' else 'failed'}
        full = str(message or '').strip()
        if len(full) > len(self.message):
            node['text'] = full[:TEXT_MAX] + ('…' if len(full) > TEXT_MAX else '')
        self.nodes.append(node)
        self._seq += 1

    def view(self):
        current = next((n for n in reversed(self.nodes) if n['state'] == 'active'), None)
        return {'id': self.id, 'agent': self.agent, 'agent_name': AGENTS[self.agent], 'source': self.source,
                'title': self.title, 'folder': _name(self.cwd), 'status': self.status, 'message': self.message,
                'current': current['label'] if current else (self.nodes[-1]['label'] if self.nodes else 'Starting…'),
                'nodes': self.nodes[-12:], 'steps': sum(1 for n in self.nodes if n['kind'] not in ('prompt', 'end')),
                'chat_id': self.chat_id, 'saved': bool(self.chat_id),
                'can_continue': self.source == 'island' and bool(self.chat_id) and self.status != 'running',
                'elapsed': int((self.ended or time.time()) - self.started)}

    # --- reading Claude Code (stream-json and transcript share the message shapes) ---
    def claude_line(self, o):
        t = o.get('type')
        if o.get('isSidechain'):
            return  # a helper's own steps; its "Starting a helper" node stands for them
        msg = o.get('message') if isinstance(o.get('message'), dict) else {}
        content = msg.get('content')
        self.cwd = o.get('cwd') or self.cwd   # transcript lines and stream-json's init both carry it
        if t == 'last-prompt' and not self.title:
            self.title = _short(o.get('lastPrompt'), 80)  # the log was picked up after the question was asked
        elif t == 'user':
            if isinstance(content, str):
                content = [{'type': 'text', 'text': content}]
            texts = [b.get('text', '') for b in content or [] if b.get('type') == 'text']
            if texts and texts[0].startswith('[Request interrupted'):
                self.end('stopped')
                return
            asked = _asked(texts[0]) if texts and len(texts) == len(content) and not o.get('isMeta') else ''
            if asked:
                self.begin_turn(asked)
                return
            for b in content or []:
                if b.get('type') == 'tool_result':
                    self.finish(b.get('tool_use_id'), ok=not b.get('is_error'))
        elif t == 'assistant':
            text = next((b.get('text') for b in reversed(content or []) if b.get('type') == 'text'), '')
            if o.get('isApiErrorMessage') or o.get('is_api_error_message'):  # the logs' spelling, then stream-json's
                self.end('failed', text or 'The session ended with an error')  # rate limit, no credit, server trouble
                return
            for b in content or []:
                if b.get('type') == 'thinking':
                    last = self.nodes[-1] if self.nodes else {}
                    if not (last.get('kind') == 'think' and last.get('state') == 'active' and not last.get('placeholder')):
                        self.add('think', 'Thinking')
                elif b.get('type') == 'tool_use':
                    kind, label, detail = claude_tool_node(b.get('name', ''), b.get('input'))
                    self.add(kind, label, detail, key=b.get('id'))
                elif b.get('type') == 'text' and b.get('text', '').strip():
                    if msg.get('stop_reason') not in TURN_ENDS:
                        self.add('reply', 'Writing a note', _short(b['text'], 56), state='done', text=b['text'])
            if msg.get('stop_reason') in TURN_ENDS:
                self.end('done', text)
        elif t == 'result':
            if o.get('is_error') or o.get('subtype') not in (None, 'success'):
                self.end('failed', o.get('result') or 'The session ended with an error')
            else:
                self.end('done', o.get('result') or '')

    # --- reading Codex: exec --json events ---
    def codex_event(self, o):
        t = o.get('type')
        item = o.get('item') or {}
        if t == 'item.started':
            node = codex_item_node(item)
            if node and node[0] != 'error':
                self.add(*node, key=item.get('id'))
        elif t == 'item.completed':
            if item.get('type') == 'agent_message':
                self.add('reply', 'Writing an answer', _short(item.get('text'), 56), state='done', text=item.get('text'))
                self.message = item.get('text') or ''
                return
            if item.get('id') in self._by_key:
                failed = item.get('status') == 'failed' or (item.get('exit_code') not in (None, 0))
                self.finish(item.get('id'), ok=not failed)
                return
            node = codex_item_node(item)
            if node and not (node[0] == 'error' and 'skills' in node[2].lower()):
                self.add(*node, state='failed' if node[0] == 'error' else 'done')
        elif t == 'turn.completed':
            self.end('done', self.message)
        elif t in ('turn.failed', 'error'):
            err = o.get('error') or {}
            self.end('failed', (err.get('message') if isinstance(err, dict) else err) or o.get('message') or 'Codex stopped')

    # --- reading Codex: its own session log ---
    def codex_rollout(self, o):
        p = o.get('payload') if isinstance(o.get('payload'), dict) else {}
        if o.get('type') == 'turn_context':
            self.cwd = p.get('cwd') or self.cwd
        if o.get('type') != 'event_msg':
            return
        t = p.get('type')
        if t == 'task_started':
            if self.ended:  # a new question in a finished conversation: don't show the old "Done" as still going
                self.nodes, self._by_key, self._open = [], {}, {}
                self.started = time.time()
                self.title = ''  # the last question's title would be wrong; the new question replaces this soon
                self.add('think', 'Starting', placeholder=True)
            self.status, self.ended, self.message = 'running', None, ''
        elif t == 'item_completed':
            item = p.get('item') or {}
            if item.get('type') == 'UserMessage':
                text = ' '.join(c.get('text', '') for c in item.get('content') or [] if isinstance(c, dict))
                self.begin_turn(text)
            elif item.get('type') == 'AgentMessage':
                text = ' '.join(c.get('text', '') for c in item.get('content') or [] if isinstance(c, dict))
                self.add('reply', 'Writing an answer', _short(text, 56), state='done', text=text)
            else:
                node = codex_item_node(item)
                if node and node[0] != 'error':
                    failed = item.get('status') == 'failed' or item.get('exit_code') not in (None, 0)
                    self.add(*node, state='failed' if failed else 'done')
            if self.status == 'running' and item.get('type') not in ('AgentMessage', 'UserMessage'):
                self.add('think', 'Working', placeholder=True)   # Codex logs a step once it's over; this stands for the next
        elif t == 'task_complete':
            self.end('done', p.get('last_agent_message') or '')
        elif t in ('turn_aborted', 'task_aborted'):
            self.end('stopped')


# --- the manager ---
class AgentManager:
    """Runs agent sessions from the island and follows the ones running elsewhere; pushes 'agents' to the page."""

    def __init__(self, ctrl):
        self._ctrl = ctrl
        self._lock = threading.RLock()
        self._sessions = {}          # id -> Session
        self._proc = None            # the session started here: (Session, Popen)
        self._starting = None        # the agent between "nothing's running" and its process existing
        self._own_ids = set()        # agent session ids started here, so the log watcher skips them
        self._files = {}             # watched log path -> {'pos', 'session'}
        self._codex_scan = (0, [])   # (when, every Codex log), for when the Codex app's list can't be read
        self._codex_meta = {}        # Codex log path -> (title, folder), from the Codex app's list
        self._last_push = 0
        self._push_timer = None

    # --- what the page sees ---
    def state(self):
        with self._lock:
            now = time.time()
            for sid in [s.id for s in self._sessions.values() if s.ended and now - s.ended > KEEP_FINISHED * 10]:
                del self._sessions[sid]
            sessions = sorted(self._sessions.values(), key=lambda s: (s.status != 'running', -s.touched))
            return {'sessions': [s.view() for s in sessions if s.nodes][:4],
                    'running': any(s.status == 'running' and s.nodes for s in sessions),
                    'available': {a: _installed(a) for a in AGENTS},
                    'cwd': self._ctrl.config.get('agent_cwd') or '', 'agent': self._ctrl.config.get('agent_kind', 'claude'),
                    'mode': self._ctrl.config.get('agent_mode', 'read'), 'own': bool(self._proc),
                    'edit_ok': list(self._ctrl.config.get('agent_edit_folders') or [])}

    def _changed(self, now=False):
        """Pushes the sessions to the page, at most 4 times a second."""
        with self._lock:
            if self._push_timer and not now:
                return
            wait = 0 if now else max(0, 0.25 - (time.time() - self._last_push))
            if wait > 0:
                self._push_timer = threading.Timer(wait, self._send)
                self._push_timer.daemon = True
                self._push_timer.start()
                return
            if self._push_timer: self._push_timer.cancel(); self._push_timer = None
        self._send()

    def _send(self):
        # The page is told outside the lock: a slow page must not hold up reading the agent's output
        with self._lock:
            self._push_timer = None
            self._last_push = time.time()
            st = self.state()
        self._ctrl.push('agents', st)

    # --- running a session here ---
    def edit_allowed(self, folder):
        """True when you've already said an agent may edit files in this folder."""
        key = os.path.normcase(os.path.abspath(str(folder)))
        return any(os.path.normcase(os.path.abspath(f)) == key for f in self._ctrl.config.get('agent_edit_folders') or [])

    def run(self, agent, prompt, cwd, mode='read', continue_id=None, confirmed=False):
        """Starts Claude Code or Codex on a task in a folder, or continues a chat started here (continue_id is the
        island's id for that session). Returns None, or an error for the page."""
        prompt = str(prompt or '').strip()
        if agent not in AGENTS: return 'Unknown agent.'
        if not prompt: return 'Type what the agent should do.'
        earlier = None
        if continue_id:
            with self._lock:
                earlier = self._sessions.get(str(continue_id))
            if not earlier or earlier.source != 'island' or earlier.agent != agent or not earlier.chat_id:
                return "That chat can't be continued from here. Start a new one."
            if earlier.status == 'running':
                return f'{AGENTS[agent]} is still answering in that chat.'
            cwd = earlier.cwd  # a chat stays in its own folder
            # The agent reports its answer a moment before its process exits, and the chat stays locked until it
            # does; a reply sent in that moment would come back empty
            with self._lock:
                last = self._proc[1] if self._proc and self._proc[0] is earlier else None
            if last:
                try:
                    last.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    return f'{AGENTS[agent]} is still finishing that chat. Try again in a moment.'
        folder = Path(str(cwd or '').strip()).expanduser()
        if not str(cwd or '').strip() or not folder.is_dir(): return 'Choose a folder for the agent to work in.'
        if mode == 'edit' and not confirmed and not self.edit_allowed(folder):
            # The first time an agent would change files in a folder, you say so first (the page shows the question)
            return 'CONFIRM_EDIT'
        exe = find_cli(agent)
        if not exe: return f"{AGENTS[agent]} isn't installed on this PC."
        with self._lock:
            # A session that has reported its end doesn't count, even if its process takes a moment to exit
            working = self._proc[0].agent if self._proc and self._proc[0].status == 'running' and self._proc[1].poll() is None else None
            if self._starting or working:
                return f'{AGENTS[self._starting or working]} is still working. Stop it first.'
            self._starting = agent
        # The task goes in on stdin, never on the command line: a launcher that is a .cmd file (an npm install) is run
        # by cmd.exe, which would treat & | < > ^ and %NAME% in the task as commands and variables
        if agent == 'claude':
            args = [exe, '-p', '--output-format', 'stream-json', '--verbose']
            if earlier:
                args += ['--resume', earlier.chat_id]
            if mode == 'edit':
                args += ['--permission-mode', 'acceptEdits']
            else:
                # "Read only" has to hold for a folder you don't trust: only the read tools exist, they need no asking,
                # and the folder's own .claude settings (permission rules, hooks) are not loaded. Headless runs skip
                # the workspace trust prompt, so nothing else would stop them.
                read_tools = 'Read,Grep,Glob,WebSearch,WebFetch'
                args += ['--tools', read_tools, '--allowedTools', read_tools, '--setting-sources', 'user',
                         '--permission-mode', 'dontAsk']
        elif earlier:
            # "exec resume" takes the sandbox as a setting, not -s
            sandbox = 'workspace-write' if mode == 'edit' else 'read-only'
            args = [exe, 'exec', 'resume', '--json', '--skip-git-repo-check', '-c', f'sandbox_mode="{sandbox}"',
                    earlier.chat_id, '-']  # "-": read the task from stdin
        else:
            args = [exe, 'exec', '--json', '--skip-git-repo-check', '-s', 'workspace-write' if mode == 'edit' else 'read-only',
                    '-']  # "-": read the task from stdin
        # Lumi may itself be started from inside an agent session; its markers must not leak into the child
        env = {k: v for k, v in os.environ.items() if not (k.startswith('CLAUDE_CODE_') or k in ('CLAUDECODE', 'CLAUDE_PID'))}
        if 'CLAUDECODE' in os.environ:
            # Started from inside a Claude desktop session: its private endpoint and sign-in settings belong to that
            # session, and would send the agent there instead of to your own login
            env = {k: v for k, v in env.items() if not (k.startswith('CLAUDE_AGENT_SDK_') or k in HOST_ONLY_ENV)}
        try:
            proc = subprocess.Popen(args, cwd=str(folder), env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
            try:
                proc.stdin.write(prompt.encode('utf-8'))
                proc.stdin.close()  # end of the task; the agent reads it and starts
            except OSError:
                proc.kill()  # it exited before reading the task; don't leave it running
                raise
        except OSError as e:
            with self._lock:
                self._starting = None
            return f"Couldn't start {AGENTS[agent]}: {e}"
        if earlier:
            s = earlier
            with self._lock:
                s.continue_turn(prompt)
        else:
            s = Session(f'own-{int(time.time() * 1000)}', agent, 'island', folder)
            s.begin_turn(prompt)
        s.add('think', 'Starting up', placeholder=True)
        with self._lock:
            self._sessions[s.id] = s
            self._proc = (s, proc)
            self._starting = None
        self._ctrl.config.update({'agent_cwd': str(folder), 'agent_kind': agent, 'agent_mode': mode})
        if mode == 'edit' and not self.edit_allowed(folder):
            self._ctrl.config['agent_edit_folders'] = list(self._ctrl.config.get('agent_edit_folders') or []) + [str(folder)]
        self._ctrl.config.save()
        threading.Thread(target=self._read, args=(s, proc), daemon=True).start()
        threading.Thread(target=self._read_errors, args=(s, proc), daemon=True).start()
        self._changed(now=True)
        return None

    def _read(self, s, proc):
        for raw in proc.stdout:
            line = raw.decode('utf-8', errors='replace').strip().lstrip('\ufeff')
            if not line.startswith('{'):
                continue
            try:
                o = json.loads(line)
            except (ValueError, RecursionError):
                continue
            if not isinstance(o, dict):
                continue
            with self._lock:
                try:
                    if s.agent == 'claude':
                        if o.get('session_id'):
                            self._own_ids.add(o['session_id'])
                            s.chat_id = s.chat_id or str(o['session_id'])
                        s.claude_line(o)
                    else:
                        if o.get('type') == 'thread.started' and o.get('thread_id'):
                            self._own_ids.add(o['thread_id'])
                            s.chat_id = s.chat_id or str(o['thread_id'])
                        s.codex_event(o)
                except Exception as e:  # keep reading: an unread pipe would stall the agent
                    print(f'Agent output line skipped ({s.agent}): {type(e).__name__}: {e}')
            self._changed()
        code = proc.wait()
        with self._lock:
            if s.status == 'running':
                if s.stopping:
                    s.end('stopped')
                else:
                    s.end('done' if code == 0 else 'failed', s.message or s.stderr or f'Exited with code {code}')
            if self._proc and self._proc[0] is s:
                self._proc = None
        self._changed(now=True)

    def _read_errors(self, s, proc):
        # The last thing said on stderr explains a failure that never reached the JSON (a bad login, say)
        for raw in proc.stderr:
            line = raw.decode('utf-8', errors='replace').strip()
            if line and 'ERROR' not in line[:40] and 'Reading additional input' not in line:
                s.stderr = _short(line, 90)

    def stop(self):
        with self._lock:
            if not self._proc:
                return False
            s, proc = self._proc
            s.stopping = True
        # The agent starts its own shells; end the whole tree
        subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True, creationflags=CREATE_NO_WINDOW)
        return True

    # --- where a chat is saved ---
    def chat_file(self, session_id):
        """The file the agent saved a session to, or None. Found from the session itself, never from the page."""
        with self._lock:
            s = self._sessions.get(str(session_id))
        if not s or not s.chat_id:
            return None
        if s.log_path and Path(s.log_path).is_file():
            return Path(s.log_path)
        if s.agent == 'claude':
            found = list(CLAUDE_LOGS.glob(f'*/{s.chat_id}.jsonl')) if CLAUDE_LOGS.is_dir() else []
        else:
            found = self._codex_log_for(s.chat_id)
        if found:
            s.log_path = str(found[0])
            return found[0]
        return None

    @staticmethod
    def _codex_log_for(thread_id):
        if CODEX_THREADS.is_file():
            try:
                db = sqlite3.connect(f'file:{CODEX_THREADS.as_posix()}?mode=ro', uri=True, timeout=0.5)
                try:
                    row = db.execute('SELECT rollout_path FROM threads WHERE id = ?', (thread_id,)).fetchone()
                finally:
                    db.close()
                if row and row[0]:
                    path = str(row[0])
                    path = Path(path[4:] if path.startswith('\\\\?\\') else path)
                    if path.is_file():
                        return [path]
            except sqlite3.Error:
                pass
        return list(CODEX_LOGS.glob(f'*/*/*/rollout-*{thread_id}.jsonl')) if CODEX_LOGS.is_dir() else []

    def resume_command(self, session_id):
        """What to type in a terminal to pick the chat up there, or None."""
        with self._lock:
            s = self._sessions.get(str(session_id))
        if not s or not s.chat_id:
            return None
        command = f'codex resume {s.chat_id}' if s.agent == 'codex' else f'claude --resume {s.chat_id}'
        return f'cd "{s.cwd}"; {command}' if s.cwd else command  # Claude Code finds a chat from the folder it was in

    # --- following sessions run elsewhere ---
    def forget_watched(self):
        """Following was turned off: the sessions it found leave the island."""
        with self._lock:
            for sid in [s.id for s in self._sessions.values() if s.source == 'watched']:
                del self._sessions[sid]
            self._files.clear()
        self._changed(now=True)

    def start(self):
        threading.Thread(target=self._watch, daemon=True).start()

    def _log_files(self):
        now = time.time()
        files = []
        if CLAUDE_LOGS.is_dir():
            for d in CLAUDE_LOGS.iterdir():
                if d.is_dir():
                    files += [('claude', f) for f in d.glob('*.jsonl')]
        files += [('codex', f) for f in self._codex_logs(now)]
        fresh = []
        for agent, f in files:
            try:
                if now - f.stat().st_mtime < WATCH_FRESH:
                    fresh.append((agent, f))
            except OSError:
                pass
        return fresh

    def _codex_logs(self, now):
        """The Codex logs that may be in use. A conversation keeps writing to the log in the folder of the day it
        started, so a week-old chat you're still in lives in last week's folder. The Codex app's own list of
        conversations says which logs those are; without it, every log is checked (listed once a minute)."""
        paths = self._codex_from_app(now)
        if paths is None:
            if now - self._codex_scan[0] > 60:
                found = list(CODEX_LOGS.glob('*/*/*/rollout-*.jsonl')) if CODEX_LOGS.is_dir() else []
                self._codex_scan = (now, found)
            paths = list(self._codex_scan[1])
        for day in (date.today(), date.today() - timedelta(days=1)):  # new ones, before the app has listed them
            folder = CODEX_LOGS / f'{day:%Y}' / f'{day:%m}' / f'{day:%d}'
            if folder.is_dir():
                paths += folder.glob('rollout-*.jsonl')
        return list(dict.fromkeys(paths))

    def _codex_from_app(self, now):
        """Logs of the conversations (not their helper reviews) the Codex app updated in the last hour, or None
        when its list can't be read (not installed, or a version that keeps it differently). Opened read-only."""
        if not CODEX_THREADS.is_file():
            return None
        try:
            db = sqlite3.connect(f'file:{CODEX_THREADS.as_posix()}?mode=ro', uri=True, timeout=0.5)
            try:
                rows = db.execute('SELECT rollout_path, source, title, cwd FROM threads WHERE archived = 0 AND updated_at > ?',
                                  (int(now) - 3600,)).fetchall()
            finally:
                db.close()
        except sqlite3.Error:
            return None
        paths = []
        for path, source, title, cwd in rows:
            if 'subagent' in str(source):
                continue  # a review Codex runs inside a conversation: not a session of its own
            path = str(path or '')
            if path.startswith('\\\\?\\'):
                path = path[4:]  # Windows long-path prefix
            paths.append(Path(path))
            cwd = str(cwd or '')
            # The title is often the whole first message: keep its first real line, not a ``` fence or a heading mark
            first = next((ln.strip(' #*>`-') for ln in str(title or '').splitlines()
                          if ln.strip(' #*>`-') and not ln.strip().startswith('```')), '')
            self._codex_meta[str(Path(path))] = (first, cwd[4:] if cwd.startswith('\\\\?\\') else cwd)
        return paths

    @staticmethod
    def _is_codex_helper(f):
        """True for a Codex log that belongs to a review run inside another conversation. Its first line says so."""
        try:
            with open(f, 'rb') as fh:
                first = fh.readline(LINE_MAX)
            meta = json.loads(first.decode('utf-8', errors='replace'))
        except (OSError, ValueError, RecursionError):
            return False
        if not isinstance(meta, dict) or meta.get('type') != 'session_meta' or not isinstance(meta.get('payload'), dict):
            return False
        p = meta['payload']
        return bool(p.get('parent_thread_id')) or 'subagent' in json.dumps(p.get('source'))

    def _watch(self):
        while True:
            time.sleep(1.5)
            if not self._ctrl.config.get('agent_watch', True):
                continue
            try:
                changed = self._watch_once()
            except Exception as e:
                print(f"Agent Watch Error: {e}")
                changed = False
            if changed:
                self._changed()

    def _watch_once(self):
        changed = False
        for agent, f in self._log_files():
            key = str(f)
            if any(i and i in f.name for i in self._own_ids):
                continue  # started from the island: already followed from its own output
            entry = self._files.get(key)
            if entry and entry.get('ignore'):
                continue
            if entry is None:
                if agent == 'codex' and self._is_codex_helper(f):
                    self._files[key] = {'ignore': True, 'session': None}
                    continue
                # First sight: read back far enough to find the question being worked on
                size = f.stat().st_size
                entry = self._files[key] = {'pos': max(0, size - 400_000), 'session': None, 'skip_partial': size > 400_000}
            changed |= self._read_log(agent, f, entry)
        with self._lock:
            now = time.time()
            for key, entry in list(self._files.items()):
                s = entry['session']
                if s and s.status == 'running' and now - s.touched > WATCH_STALE:
                    s.end('stopped', 'No news for a while')
                    changed = True
                if s and s.ended and now - s.ended > KEEP_FINISHED:
                    # Gone from the island; the file is still followed, so a new question starts a new chain
                    self._sessions.pop(s.id, None)
                    entry['session'] = None
                    changed = True
        return changed

    def _read_log(self, agent, f, entry):
        try:
            with open(f, 'rb') as fh:
                size = os.fstat(fh.fileno()).st_size
                if size < entry['pos']:
                    entry['pos'] = 0  # the log was cut short or replaced: read it again from the start
                fh.seek(entry['pos'])
                data = fh.read(READ_MAX)
        except OSError:
            return False
        end = data.rfind(b'\n')
        if end < 0:
            if len(data) >= READ_MAX:  # part of one very long line: wait for it to end, then skip it
                entry['waiting'] = entry.get('waiting', 0) + len(data)
                if entry['waiting'] > LINE_MAX:
                    entry.update(pos=size, waiting=0, skip_partial=True)
            return False
        entry['waiting'] = 0
        chunk, entry['pos'] = data[:end], entry['pos'] + end + 1
        lines = chunk.split(b'\n')
        if entry.pop('skip_partial', False):
            lines = lines[1:]  # started mid-line
        with self._lock:
            s = entry['session']
            if s is None:
                s = entry['session'] = Session(f'log-{f.stem[-12:]}-{int(time.time())}', agent, 'watched')
                # Claude Code names a log after its session id; a Codex log name ends in its thread id
                s.chat_id, s.log_path = (f.stem if agent == 'claude' else f.stem[-36:]), str(f)
            before = (s._seq, s.status)
            for raw in lines:
                try:
                    o = json.loads(raw.decode('utf-8', errors='replace'))
                except (ValueError, RecursionError):
                    continue
                if not isinstance(o, dict):
                    continue
                if agent == 'codex' and o.get('type') == 'session_meta' and isinstance(o.get('payload'), dict) \
                        and o['payload'].get('parent_thread_id'):
                    # A reviewer run inside a Codex session: not a session of its own
                    entry.update(ignore=True, session=None)
                    return False
                try:
                    s.claude_line(o) if agent == 'claude' else s.codex_rollout(o)
                except Exception as e:  # one odd line mustn't lose the rest
                    print(f'Agent log line skipped ({agent}): {type(e).__name__}: {e}')
            if not s.nodes:
                return False  # nothing worth showing yet (only bookkeeping lines)
            title, cwd = self._codex_meta.get(str(f), ('', '')) if agent == 'codex' else ('', '')
            s.cwd = s.cwd or cwd
            if not s.title and title:
                s.title = _short(title, 80)
            if not s.title:
                s.title = 'A session in ' + (_name(s.cwd) or 'a folder')
            if s.id not in self._sessions and not (s.ended and time.time() - s.ended > KEEP_FINISHED):
                self._sessions[s.id] = s
            return (s._seq, s.status) != before
