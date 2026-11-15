"""Lumi's natural voice: Microsoft's online neural voices through edge-tts.

A reply is split into short pieces that are fetched at once and played by the page in order, so the first words start
before the rest is ready. The page plays the sound (and moves Lumi's mouth to it); see "SPEECH" in island.js.
The text of Lumi's reply goes to Microsoft to be spoken. The service is unofficial and needs the internet, so every
caller must be ready for None and fall back to the Windows voice (chat.py does).
"""
import asyncio
import re
import time
from concurrent.futures import ThreadPoolExecutor

# Voice id -> the name Settings shows. The first is the default.
VOICES = {'en-US-AvaNeural': 'Ava', 'en-US-AnaNeural': 'Ana', 'en-GB-SoniaNeural': 'Sonia', 'en-US-AndrewNeural': 'Andrew'}
DEFAULT_VOICE = 'en-US-AvaNeural'
FIRST_WAIT = 4.5       # seconds to wait for the first piece; past that, the Windows voice answers instead
WARM_FOR = 120         # seconds a warmed-up connection is counted as warm
PIECE_TIMEOUT = 6      # seconds to fetch a later piece
LONG_PIECE = 180       # later sentences are joined up to about this many characters

_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='lumi-voice')


def available():
    try:
        import edge_tts  # noqa: F401
        return True
    except ImportError:
        return False


def pieces(text):
    """The reply in speakable pieces: the first sentence alone (so speech starts soon), then the rest in longer runs."""
    sentences = [s.strip() for s in re.split(r'(?<=[.!?…])\s+', ' '.join(str(text).split())) if s.strip()]
    if not sentences:
        return []
    out, run = [sentences[0]], ''
    for sentence in sentences[1:]:
        if run and len(run) + len(sentence) > LONG_PIECE:
            out.append(run)
            run = ''
        run = (run + ' ' + sentence).strip()
    return out + ([run] if run else [])


def _fetch(text, voice):
    import edge_tts

    async def read():
        data = b''
        async for part in edge_tts.Communicate(text, voice).stream():
            if part['type'] == 'audio':
                data += part['data']
        return data

    return asyncio.run(asyncio.wait_for(read(), PIECE_TIMEOUT))


_warmed = 0.0


def warm_up(voice):
    """The first request after a while is slow (about twice the usual). Asking for one word while you're still
    talking gets that out of the way, at most once every couple of minutes."""
    global _warmed
    if not available() or time.time() - _warmed < WARM_FOR:
        return
    _warmed = time.time()

    def fetch():
        try: _fetch('Hi.', voice if voice in VOICES else DEFAULT_VOICE)
        except Exception: pass  # offline or slow: the real request will find out

    _pool.submit(fetch)


def synthesize(text, voice):
    """Starts fetching every piece of the reply at once. Returns [(piece text, future of MP3 bytes), ...] in speaking order."""
    voice = voice if voice in VOICES else DEFAULT_VOICE
    return [(piece, _pool.submit(_fetch, piece, voice)) for piece in pieces(text)]
