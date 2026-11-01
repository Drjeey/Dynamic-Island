"""What Lumi is doing, as small user-safe events for the page.

One request (typed question, voice question, live session) is one *run*. Every event carries the run id and an
increasing sequence number, so the page can ignore late or duplicate events, and every run ends with exactly one
"run_finished", even if something throws. Events never contain prompts, model output or tool arguments; labels come
only from the fixed tables below and in tools.py.
"""
import itertools
import threading
import time

SCHEMA_VERSION = 1
PHASES = ('run_started', 'listening', 'transcribing', 'understanding', 'tool_started', 'tool_finished',
          'responding', 'needs_input', 'run_finished')
PHASE_LABELS = {'listening': 'Listening', 'transcribing': 'Thinking…', 'understanding': 'Thinking…'}


class Cancelled(Exception):
    """The run was cancelled (Esc, the stop button, or a newer run); raised at the next safe point."""


class Run:
    """Handle for one run; set .status to 'error' before leaving the block to report a failure.
    .cancelled turns true when the run is cancelled; long work calls check() between steps to stop there."""

    def __init__(self, bus, run_id, source):
        self.bus, self.id, self.source = bus, run_id, source
        self.status = 'ok'
        self.cancelled = False

    def emit(self, phase, **fields):
        self.bus.emit(self.id, phase, **fields)

    def check(self):
        if self.cancelled:
            raise Cancelled()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.bus.finish(self.id, 'error' if exc_type else self.status)
        return False  # never swallow exceptions


class ActivityBus:
    def __init__(self, push):
        self._push = push
        self._lock = threading.Lock()
        self._ids = itertools.count(1)
        self._current = None   # (run id, source)
        self._run = None       # the open Run, so it can be told it was cancelled
        self._seq = 0
        self._last = None      # last event sent, for page reloads

    def start(self, source):
        """Begins a run (use as a context manager). Any run still open is finished as cancelled first."""
        self.cancel()
        with self._lock:
            run_id = f'r-{next(self._ids):04d}'
            self._current, self._seq = (run_id, source), 0
            run = self._run = Run(self, run_id, source)
        self.emit(run_id, 'run_started')
        return run

    def cancel(self):
        """Ends the open run now as "cancelled" (the page goes back to normal at once) and flags it, so its
        work stops at the next check. Returns whether there was a run to cancel."""
        with self._lock:
            run = self._run
        if not run or self.current() != run.id:
            return False
        run.cancelled = True
        self.finish(run.id, 'cancelled')
        return True

    def emit(self, run_id, phase, **fields):
        with self._lock:
            if not self._current or self._current[0] != run_id:
                return  # a stale run (already finished or replaced): never reaches the page
            self._seq += 1
            event = {'v': SCHEMA_VERSION, 'run': run_id, 'seq': self._seq, 'phase': phase,
                     'source': self._current[1], 'ts': round(time.time(), 3)}
            label = fields.pop('label', None) or PHASE_LABELS.get(phase)
            if label: event['label'] = label
            event.update({k: v for k, v in fields.items() if k in ('tool', 'kind', 'status', 'reaction', 'receipt')})
            self._last = event
        self._push('activity', event)

    def finish(self, run_id, status='ok'):
        with self._lock:
            if not self._current or self._current[0] != run_id:
                return  # finished already
        self.emit(run_id, 'run_finished', status=status)
        with self._lock:
            if self._current and self._current[0] == run_id:
                self._current = self._run = None

    def current(self):
        with self._lock:
            return self._current[0] if self._current else None

    def snapshot(self):
        """The open run's last event (or None), for a page that reloads mid-run."""
        with self._lock:
            return dict(self._last) if self._current and self._last and self._last['run'] == self._current[0] else None
