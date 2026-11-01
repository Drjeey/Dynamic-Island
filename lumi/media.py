import asyncio
import base64
import threading

from .system import SystemHelpers

# Media keys, used when Windows reports no media session
MEDIA_KEYS = {'play': 0xB3, 'next': 0xB0, 'prev': 0xB1}


class MediaWatcher:
    """Follows Windows' current media session (any app that shows in the volume flyout) and reports changes."""

    def __init__(self, on_change):
        self._on_change = on_change
        self._loop = None
        self._session = None
        self._last = None
        self._art_key = None
        self._art = None
        self.state = {'active': False}

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as Manager
        except ImportError:
            print("Media Info Unavailable: install winrt-Windows.Media.Control")
            return
        self._loop = asyncio.new_event_loop()
        self._loop.run_until_complete(self._poll(Manager))

    async def _poll(self, Manager):
        manager = await Manager.request_async()
        while True:
            try:
                await self._refresh(manager)
            except Exception as e:
                print(f"Media Info Error: {e}")
            await asyncio.sleep(1)

    async def _refresh(self, manager):
        session = manager.get_current_session()
        self._session = session
        if not session:
            state = {'active': False}
        else:
            props = await session.try_get_media_properties_async()
            info = session.get_playback_info()
            PLAYING = 4  # GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING
            key = (props.title, props.artist)
            if key != self._art_key:
                self._art_key = key
                self._art = await self._read_art(props.thumbnail)
            state = {
                'active': bool(props.title),
                'title': props.title or '',
                'artist': props.artist or '',
                'app': _app_name(session.source_app_user_model_id),
                'playing': info.playback_status == PLAYING,
                'art': self._art,
            }
        if state != self._last:
            self._last = state
            self.state = state
            self._on_change(state)

    @staticmethod
    async def _read_art(thumbnail):
        # Artwork arrives as a stream; send it to the page as a small data URI
        if thumbnail is None:
            return None
        try:
            from winrt.windows.storage.streams import Buffer, InputStreamOptions
            stream = await thumbnail.open_read_async()
            size = min(stream.size, 2_000_000)
            buffer = Buffer(size)
            await stream.read_async(buffer, size, InputStreamOptions.READ_AHEAD)
            data = bytes(memoryview(buffer))[:buffer.length]
            mime = 'image/png' if data[:4] == b'\x89PNG' else 'image/jpeg'
            return f'data:{mime};base64,' + base64.b64encode(data).decode()
        except Exception as e:
            print(f"Media Artwork Error: {e}")
            return None

    def control(self, action):
        session = self._session
        if session is None or self._loop is None:
            if action in MEDIA_KEYS: SystemHelpers.send_key(MEDIA_KEYS[action])
            return
        calls = {'play': session.try_toggle_play_pause_async, 'next': session.try_skip_next_async,
                 'prev': session.try_skip_previous_async}
        if action in calls:
            asyncio.run_coroutine_threadsafe(self._press(calls[action], action), self._loop)

    async def _press(self, start, action):
        try:
            if not await start():
                raise RuntimeError('the app ignored the request')
        except Exception as e:
            print(f"Media Control Error ({action}): {e}")
            if action in MEDIA_KEYS: SystemHelpers.send_key(MEDIA_KEYS[action])  # the keyboard media keys still work


def _app_name(app_id):
    # "Spotify.exe" -> "Spotify"; "Microsoft.ZuneMusic_8wekyb3d8bbwe!Microsoft.ZuneMusic" -> "ZuneMusic"
    name = (app_id or '').split('!')[-1].split('\\')[-1]
    name = name.rsplit('.', 1)[-1] if '.' in name and not name.lower().endswith('.exe') else name
    return name[:-4] if name.lower().endswith('.exe') else name
