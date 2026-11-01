import array
import asyncio
import threading
import time

from .chat import SYSTEM_INSTRUCTION
from .levels import INTERVAL, LevelMeter

IN_RATE, OUT_RATE = 16000, 24000   # what the Live API takes in and sends back (16-bit mono PCM)
BLOCK = 1600                       # 0.1 s of microphone audio per message
IDLE_TIMEOUT = 30                  # seconds without either side speaking before the session closes
BARGE_IN_LEVEL = 1800              # while Lumi talks, only clearly louder speech counts (keeps Lumi from hearing itself)


def _level(data):
    samples = array.array('h', data)
    return (sum(s * s for s in samples) / max(1, len(samples))) ** 0.5


class Playback:
    """Plays Lumi's streamed voice; clear() stops it at once when the user interrupts."""

    def __init__(self):
        self._buffer = bytearray()
        self._lock = threading.Lock()
        self.last_audio = 0.0
        self.level = 0.0  # RMS of what the speakers are playing right now (drives Lumi's mouth)

    def add(self, data):
        with self._lock:
            self._buffer.extend(data)
        self.last_audio = time.time()

    def clear(self):
        with self._lock:
            self._buffer.clear()

    @property
    def playing(self):
        with self._lock:
            return len(self._buffer) > 0

    def fill(self, out, frames, *_):
        wanted = frames * 2
        with self._lock:
            chunk = bytes(self._buffer[:wanted])
            del self._buffer[:wanted]
        out[:len(chunk)] = chunk
        out[len(chunk):] = b'\x00' * (wanted - len(chunk))
        self.level = _level(chunk[:len(chunk) - len(chunk) % 2]) if len(chunk) >= 2 else 0.0


class LiveVoice:
    """A streaming conversation with Gemini Live. Click the mic to start; click again (or stay quiet) to end."""

    def __init__(self, ctrl, chat):
        self.ctrl = ctrl
        self.chat = chat
        self._stop = threading.Event()
        self._thread = None
        self._mic = LevelMeter(ctrl.push, 'mic')      # the listening ring
        self._voice = LevelMeter(ctrl.push, 'voice')  # the talking mouth

    @property
    def running(self):
        return bool(self._thread and self._thread.is_alive())

    def toggle(self):
        if self.running:
            self._stop.set()
            return
        if self.chat.error:
            self.ctrl.push('idle', {'status': 'error', 'text': self.chat.error, 'action': 'settings'})
            return
        if self.chat.provider_name != 'gemini':
            self.ctrl.push('idle', {'status': 'error', 'text': 'Live voice needs Gemini. Choose Gemini in Settings, or use standard voice.',
                                    'action': 'settings'})
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        # A whole live session is one activity run; its tool calls report through the same runner as typed chat
        with self.ctrl.activity.start('live') as run:
            self._activity = run
            try:
                asyncio.run(self._session())
            except Exception as e:
                print(f"Live Voice Error: {e}")
                run.status = 'error'
                self.ctrl.push('idle', {'status': 'error', 'text': "Live voice didn't connect. Check the live model in Settings.",
                                        'action': 'settings'})
                return
            if self._stop.is_set():
                run.status = 'cancelled'  # you turned the mic off (an idle timeout ends it normally)
        self.ctrl.push('idle', {'status': 'idle'})

    def _connect_config(self):
        types, client = self.chat.provider.types, self.chat.provider.client
        declarations = [types.FunctionDeclaration.from_callable(client=client, callable=f) for f in self.chat.tools.functions()]
        return types.LiveConnectConfig(
            response_modalities=['AUDIO'],
            system_instruction=SYSTEM_INSTRUCTION + ' You are speaking out loud, so keep answers short.',
            tools=[types.Tool(function_declarations=declarations)],
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
        )

    async def _session(self):
        import sounddevice as sd
        types = self.chat.provider.types
        model = self.ctrl.config.get('live_model')
        loop = asyncio.get_running_loop()
        mic = asyncio.Queue()
        playback = Playback()
        state = {'last_activity': time.time(), 'heard': '', 'said': '', 'responding': False}

        def on_mic(data, frames, _time, _status):
            loop.call_soon_threadsafe(mic.put_nowait, bytes(data))

        async with self.chat.provider.client.aio.live.connect(model=model, config=self._connect_config()) as session:
            self.ctrl.push('idle', {'status': 'listening'})
            self._activity.emit('listening')
            with sd.RawInputStream(samplerate=IN_RATE, channels=1, dtype='int16', blocksize=BLOCK, callback=on_mic), \
                    sd.RawOutputStream(samplerate=OUT_RATE, channels=1, dtype='int16', callback=playback.fill):
                sender = asyncio.create_task(self._send_mic(session, mic, playback, state))
                receiver = asyncio.create_task(self._receive(session, playback, state))
                levels = asyncio.create_task(self._levels(playback))
                while not self._stop.is_set() and not self._activity.cancelled and not receiver.done():
                    if time.time() - max(state['last_activity'], playback.last_audio) > IDLE_TIMEOUT:
                        break
                    await asyncio.sleep(0.2)
                sender.cancel()
                receiver.cancel()
                levels.cancel()
            self._mic.stop()
            self._voice.stop()

    async def _send_mic(self, session, mic, playback, state):
        types = self.chat.provider.types
        while True:
            data = await mic.get()
            level = _level(data)
            if playback.playing and level < BARGE_IN_LEVEL:
                continue  # Lumi's own voice coming back through the speakers
            if not playback.playing:
                self._mic.feed(level)
            if level > 600:
                state['last_activity'] = time.time()
            await session.send_realtime_input(audio=types.Blob(data=data, mime_type=f'audio/pcm;rate={IN_RATE}'))

    async def _receive(self, session, playback, state):
        types = self.chat.provider.types
        while True:
            async for msg in session.receive():  # one turn per pass
                if msg.data:
                    if not playback.playing:
                        self.ctrl.push('idle', {'status': 'speaking', 'text': state['said'] or '…'})
                    if not state['responding']:
                        state['responding'] = True
                        self._activity.emit('responding')
                    playback.add(msg.data)
                content = msg.server_content
                if content:
                    if content.interrupted:
                        # You started talking over Lumi: stop its voice and mouth at once and listen
                        playback.clear()
                        self._voice.stop()
                        state['responding'] = False
                        self.ctrl.push('idle', {'status': 'listening'})
                        self._activity.emit('listening')
                    if content.input_transcription and content.input_transcription.text:
                        state['heard'] += content.input_transcription.text
                    if content.output_transcription and content.output_transcription.text:
                        state['said'] += content.output_transcription.text
                        self.ctrl.push('idle', {'status': 'speaking', 'text': state['said']})
                    if content.turn_complete:
                        if state['heard'].strip(): self.chat._remember('user', state['heard'].strip())
                        if state['said'].strip(): self.chat._remember('lumi', state['said'].strip())
                        state['heard'] = state['said'] = ''
                        state['last_activity'] = time.time()
                if msg.tool_call:
                    responses = []
                    for call in msg.tool_call.function_calls:
                        result = self.chat.tools.run(self._activity, call.name, dict(call.args or {}))
                        responses.append(types.FunctionResponse(id=call.id, name=call.name, response={'result': result}))
                    await session.send_tool_response(function_responses=responses)
            # Wait for Lumi to finish speaking before showing "listening" again
            while playback.playing:
                await asyncio.sleep(0.1)
            if state['responding']:  # after an interruption Lumi is already listening
                self._activity.emit('listening')
            state['responding'] = False
            self.ctrl.push('idle', {'status': 'listening'})

    async def _levels(self, playback):
        """While Lumi talks, the mouth follows the audio being played; otherwise the ring follows your mic."""
        while True:
            if playback.playing:
                self._mic.stop()
                self._voice.feed(playback.level)
                self._voice.flush()
            else:
                self._voice.stop()
                self._mic.flush()
            await asyncio.sleep(INTERVAL)
