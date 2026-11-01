import json
import threading
import time
from datetime import date, datetime, timedelta

from .config import FOCUS_LOG_PATH

DURATIONS = (15, 25, 45, 60)


class FocusManager:
    """Focus sessions and breaks, with a small log of finished and stopped sessions."""

    def __init__(self, push):
        self._push = push
        self._lock = threading.Lock()
        self._session = 0          # bumped on every start/stop so a stale timer thread knows to stop
        self.kind = None           # 'focus' or 'break' while running
        self._started = None
        self._total = 0
        self.last_minutes = 25

    @property
    def active(self):
        return self.kind is not None

    def start(self, minutes, kind='focus'):
        minutes = max(1, min(240, int(minutes)))
        with self._lock:
            self._log_stopped()
            self._session += 1
            session = self._session
            self.kind, self._started, self._total = kind, time.time(), minutes * 60
            if kind == 'focus': self.last_minutes = minutes
        threading.Thread(target=self._loop, args=(session, kind, minutes * 60), daemon=True).start()

    def stop(self):
        with self._lock:
            if not self.active:
                return
            self._log_stopped()
            self._session += 1
            kind, self.kind = self.kind, None
        self._push('focus_end', {'today': self.today(), 'stopped': True, 'kind': kind})

    def _log_stopped(self):
        # A focus session stopped early still counts the minutes actually spent
        if self.kind == 'focus' and self._started:
            done = int((time.time() - self._started) // 60)
            if done >= 1:
                self._append(done, completed=False)

    def _loop(self, session, kind, total):
        # Ticks update the countdown without taking over whatever panel is open
        seconds = total
        while self._session == session and seconds > 0:
            m, s = divmod(seconds, 60)
            self._push('focus_tick', {'timer': f'{m:02d}:{s:02d}', 'remaining': seconds, 'total': total, 'kind': kind})
            time.sleep(1)
            seconds -= 1
        with self._lock:
            finished = self._session == session and self.kind == kind
            if finished:
                self.kind = None
                if kind == 'focus': self._append(total // 60, completed=True)
        if finished:
            data = {'finished': True, 'kind': kind, 'minutes': total // 60, 'today': self.today()}
            if kind == 'focus':
                data['milestone'] = self._milestone()
            self._push('focus_end', data)

    # --- milestones ---
    def _milestone(self):
        """A short celebration line for 5 sessions in a day or each 7-day streak, each shown only once."""
        completed_today = sum(1 for e in self._read() if e.get('date') == date.today().isoformat() and e.get('completed'))
        streak = self.streak()
        candidates = []
        if completed_today == 5:
            candidates.append((f'five-{date.today().isoformat()}', 'Five focus sessions today. Impressive!'))
        if streak and streak % 7 == 0:
            candidates.append((f'streak-{streak}-{date.today().isoformat()}', f'{streak} days in a row of focus. Lovely streak!'))
        for key, text in candidates:
            if self.milestone_allowed is None or self.milestone_allowed(key):
                return text
        return None

    milestone_allowed = None  # set by the controller: records a milestone and says whether to show it

    def streak(self):
        """Days in a row, ending today (or yesterday, if nothing yet today), with a finished focus session."""
        days = {e['date'] for e in self._read() if e.get('completed') and e.get('date')}
        day = date.today()
        if day.isoformat() not in days:
            day -= timedelta(days=1)
        count = 0
        while day.isoformat() in days:
            count += 1
            day -= timedelta(days=1)
        return count

    def week_summary(self, weeks_ago=1):
        """Totals for an ISO week (1 = last week, 0 = this week so far)."""
        target = (date.today() - timedelta(weeks=weeks_ago)).isocalendar()[:2]
        entries = [e for e in self._read() if e.get('date') and date.fromisoformat(e['date']).isocalendar()[:2] == target]
        return {'minutes': sum(e.get('minutes', 0) for e in entries),
                'sessions': sum(1 for e in entries if e.get('completed')),
                'days': len({e['date'] for e in entries}),
                'streak': self.streak(),
                'week': f'{target[0]}-W{target[1]:02d}'}

    # --- log ---
    def _read(self):
        try:
            return json.loads(FOCUS_LOG_PATH.read_text(encoding='utf-8')) if FOCUS_LOG_PATH.exists() else []
        except Exception as e:
            print(f"Focus Log Error: {e}")
            return []

    def _append(self, minutes, completed):
        entries = self._read()[-999:]  # keep the log small
        entries.append({'date': date.today().isoformat(), 'time': datetime.now().strftime('%H:%M'),
                        'minutes': minutes, 'completed': completed})
        try: FOCUS_LOG_PATH.write_text(json.dumps(entries, indent=1), encoding='utf-8')
        except Exception as e: print(f"Focus Log Error: {e}")

    def today(self):
        today = date.today().isoformat()
        entries = [e for e in self._read() if e.get('date') == today]
        return {'minutes': sum(e.get('minutes', 0) for e in entries), 'sessions': len(entries)}

    def state(self):
        return {'running': self.active, 'kind': self.kind, 'today': self.today(),
                'last_minutes': self.last_minutes, 'durations': DURATIONS}
