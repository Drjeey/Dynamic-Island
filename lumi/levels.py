"""How loud the microphone and Lumi's voice are, for the listening ring and the talking mouth.

Levels go to the page as {'kind': 'mic'|'voice', 'value': 0..1}, at most 12 times a second, only while audio is
actually flowing; {'end': True} says it stopped, and {'pulse': True} marks a single word starting (standard voice,
where Windows text-to-speech reports words but not loudness). They carry no audio and no words.
"""
import math
import time

INTERVAL = 1 / 12   # seconds between updates
QUIET = 150         # 16-bit RMS of a quiet room: level 0
LOUD = 6000         # clearly speaking close to the mic: level 1


def loudness(rms, quiet=QUIET):
    """RMS of 16-bit samples -> 0..1 on a log scale (how loud it sounds, not raw amplitude)."""
    if rms <= quiet:
        return 0.0
    return min(1.0, math.log(rms / quiet) / math.log(max(LOUD, quiet * 4) / quiet))


class LevelMeter:
    def __init__(self, push, kind):
        self._push, self.kind = push, kind
        self.quiet = QUIET
        self._peak = 0.0
        self._fed = False      # something to send since the last update
        self._active = False   # levels were sent and no 'end' yet
        self._last_push = 0.0

    def feed(self, rms):
        """Adds a block of audio's RMS; the loudest block since the last update is what's shown."""
        self._peak = max(self._peak, loudness(rms, self.quiet))
        self._fed = True

    def flush(self, now=None):
        """Sends the level if a twelfth of a second has passed since the last update."""
        now = time.monotonic() if now is None else now
        if not self._fed or now - self._last_push < INTERVAL:
            return
        self._push('level', {'kind': self.kind, 'value': round(self._peak, 2)})
        self._peak, self._fed, self._active, self._last_push = 0.0, False, True, now

    def pulse(self):
        """A word started (no loudness available): the mouth opens, then the page lets it close."""
        self._push('level', {'kind': self.kind, 'value': 1.0, 'pulse': True})
        self._active = True

    def stop(self):
        if self._active:
            self._push('level', {'kind': self.kind, 'value': 0, 'end': True})
        self._peak, self._fed, self._active = 0.0, False, False
