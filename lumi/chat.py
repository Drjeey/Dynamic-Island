import ctypes
import queue
import threading
import time

import pyttsx3
import speech_recognition as sr

from . import providers
from .activity import Cancelled
from .credentials import get_api_key
from .levels import QUIET, LevelMeter
from .tools import LumiTools

SYSTEM_INSTRUCTION = (
    "You are Lumi, a small, friendly assistant who lives under a Dynamic Island at the top of the user's "
    "Windows screen. Be warm and brief. When the user asks you to do something you have a tool for "
    "(focus sessions, the quick note, media, opening apps, volume, system status), use the tool and then "
    "say in a few words what you did. Never claim to have done something without calling the tool."
)
SPOKEN_HINT = "(Spoken aloud: answer in one or two short sentences.) "
MAX_TRANSCRIPT = 40  # messages kept for the chat panel
MAX_TOOL_ROUNDS = 5  # tool rounds per question before Lumi must answer in words


class ChatController:
    """One conversation with the chosen AI provider, shared by voice and typed chat, with Lumi's tools attached."""

    def __init__(self, ctrl):
        self.ctrl = ctrl
        self.error = None
        self.busy = threading.Lock()
        self.messages = []   # [{'role': 'user'|'lumi', 'text': str}] for the chat panel
        self._chat = None
        self._in_flight = None  # the conversation a question is using right now
        self.tools = LumiTools(ctrl)
        self.mic_level = LevelMeter(ctrl.push, 'mic')      # the listening ring
        self.voice_level = LevelMeter(ctrl.push, 'voice')  # the talking mouth
        self.speech_queue = queue.Queue()
        self._hush = threading.Event()  # set to stop speaking mid-sentence (the run was cancelled)
        threading.Thread(target=self._speech_worker, daemon=True).start()

        self.provider_name = providers.chosen(ctrl.config)
        self.label = providers.PROVIDERS[self.provider_name]['label']
        self.provider, self.error = providers.create(ctrl.config, get_api_key(self.provider_name))

    # --- asking ---
    def _session(self):
        if self._chat is None:
            self._chat = self.provider.new_chat(SYSTEM_INSTRUCTION, self.tools.functions())
        return self._chat

    def ask(self, text, spoken=False, run=None):
        """Sends one message; the model may call Lumi's tools before answering. Returns {'reply'} or {'error'}.
        A typed question is its own activity run; a voice question passes in the run it's already part of."""
        text = (text or '').strip()
        if not text:
            return {'error': 'Type something to ask me.'}
        if run is not None:
            return self._ask(run, text, spoken)
        with self.ctrl.activity.start('chat') as run:
            result = self._ask(run, text, spoken)
            if 'error' in result:
                run.status = 'error'
            return result

    def _ask(self, run, text, spoken):
        if self.error:
            return {'error': self.error, 'action': 'settings'}
        self._remember('user', text)
        try:
            chat = self._in_flight = self._session()
            if hasattr(chat, 'on_busy'):
                chat.on_busy = lambda: run.emit('understanding', label='Trying another model…')
            reply = self._converse(run, chat, (SPOKEN_HINT if spoken else '') + text, stream_to_page=not spoken)
        except Cancelled:
            if self._chat is chat:
                self._chat = None  # the model's history may be half-written; the next question starts afresh
            return {'cancelled': True}
        except providers.Declined:
            self._chat = None
            return {'error': "I can't help with that one."}
        except Exception as e:
            print(f"Response Error ({self.provider_name}): {e}")
            self._chat = None  # start a fresh session next time
            return {'error': f"{self.label} didn't answer. Check the key and model in Settings, or try again.",
                    'action': 'retry'}
        finally:
            self._in_flight = None
        self._remember('lumi', reply)
        return {'reply': reply}

    def _converse(self, run, chat, message, stream_to_page):
        """The tool loop: the model asks for tools, Lumi runs them (reporting each step), until it answers in words."""
        state = {'responding': False, 'last_push': 0.0, 'text': ''}

        def on_text(text):
            # The reply so far: Lumi starts "talking", and typed chat shows it as it arrives
            run.check()  # cancelled: stop reading the reply (this ends the stream)
            state['text'] = text
            if not state['responding']:
                state['responding'] = True
                run.emit('responding')
            if stream_to_page and time.time() - state['last_push'] > 0.08:
                state['last_push'] = time.time()
                self.ctrl.push('chat_delta', {'run': run.id, 'text': text})

        for round_number in range(MAX_TOOL_ROUNDS + 1):
            run.check()
            run.emit('understanding')
            text, calls = chat.send(message, on_text)
            run.check()  # a reply that arrives after Esc is dropped, and its tools never run
            if stream_to_page and state['responding']:
                self.ctrl.push('chat_delta', {'run': run.id, 'text': state['text']})
            if not calls:
                return text.strip() or 'Done.'
            if round_number == MAX_TOOL_ROUNDS:
                if self._chat is chat:
                    self._chat = None  # tool requests left unanswered; the next question starts afresh
                return text.strip() or 'Done.'
            message = [(call, self._run_tool(run, call)) for call in calls]

    def _run_tool(self, run, call):
        run.check()
        if call.args is None:  # arguments the model got wrong: tell it, without running anything
            return f'Failed: the arguments for {call.name} were missing or the wrong type; try again'
        return self.tools.run(run, call.name, call.args)

    def _remember(self, role, text):
        self.messages = (self.messages + [{'role': role, 'text': text}])[-MAX_TRANSCRIPT:]

    # --- voice ---
    def _speech_worker(self):
        # pyttsx3's run loop breaks when used from several threads, so all speech goes through this one
        ctypes.windll.ole32.CoInitialize(None)
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 160)
            # Windows speech reports each word as it starts, not how loud it is: the mouth opens per word
            engine.connect('started-word', self._on_word(engine))
        except Exception as e:
            print(f"TTS Init Error: {e}")
            engine = None
        while True:
            text, done = self.speech_queue.get()
            try:
                if engine:
                    engine.say(text)
                    engine.runAndWait()
            except Exception as e:
                print(f"TTS Error: {e}")
            finally:
                self.voice_level.stop()
                done.set()

    def _on_word(self, engine):
        def on_word(name, location, length):
            if self._hush.is_set():
                engine.stop()  # runs on the speech thread, between words
            else:
                self.voice_level.pulse()
        return on_word

    def hush(self):
        """Stops any speech in progress (Esc or the stop button while Lumi talks)."""
        self._hush.set()

    def drop_session(self):
        """A question was cancelled mid-request: its conversation may be half-written and is still in use by the
        stopped request, so the next question starts a fresh one instead of waiting or sharing it."""
        if self._in_flight is not None and self._chat is self._in_flight:
            self._chat = None

    def speak(self, text):
        self._hush.clear()
        done = threading.Event()
        self.speech_queue.put((text, done))
        done.wait()

    def listen_and_respond(self):
        if not self.busy.acquire(blocking=False):
            return  # already in a conversation
        try:
            if self.error:
                self.ctrl.push('idle', {'status': 'error', 'text': self.error, 'action': 'settings'})
                return
            # One voice question is one activity run: listening, understanding, tools, speaking
            with self.ctrl.activity.start('voice') as run:
                self._voice_turn(run)
        finally:
            self.busy.release()

    def _voice_turn(self, run):
        def fail(message, action=None):
            run.status = 'error'
            self.ctrl.push('idle', {'status': 'error', 'text': message, **({'action': action} if action else {})})

        r = sr.Recognizer()
        try:
            run.emit('listening')
            audio = self._record(r, run)
            run.check()
            run.emit('transcribing')
            text = r.recognize_google(audio)
            run.check()
        except Cancelled:
            return self.ctrl.push('idle', {'status': 'idle'})
        except sr.WaitTimeoutError:
            return fail("I didn't hear anything.")
        except sr.UnknownValueError:
            return fail("Sorry, I didn't catch that.")
        except sr.RequestError as e:
            print(f"Speech Service Error: {e}")
            return fail("Speech service is unreachable.")
        except Exception as e:
            print(f"Microphone Error: {e}")
            return fail("I can't reach your microphone.")
        result = self.ask(text, spoken=True, run=run)
        if 'cancelled' in result or run.cancelled:
            return self.ctrl.push('idle', {'status': 'idle'})
        if 'error' in result:
            return fail(result['error'], result.get('action'))
        self.ctrl.push('idle', {'status': 'speaking', 'text': result['reply'], 'heard': text})
        self.speak(result['reply'])
        self.ctrl.push('idle', {'status': 'idle'})

    def _record(self, r, run=None):
        try:
            import pyaudio  # noqa: F401  SpeechRecognition's own Microphone needs PyAudio
        except ImportError:
            return self._record_with_sounddevice(run)
        with sr.Microphone() as source:
            self.ctrl.push('idle', {'status': 'listening'})
            return r.listen(source, timeout=5, phrase_time_limit=10)

    def _record_with_sounddevice(self, run=None):
        try:
            return self._record_blocks(run)
        finally:
            self.mic_level.stop()

    def _record_blocks(self, run=None):
        # PyAudio has no ready-made wheels for every Python version; sounddevice ships its own PortAudio
        import array
        import sounddevice as sd
        rate, block = 16000, 1600  # 0.1 s blocks of 16-bit mono
        with sd.RawInputStream(samplerate=rate, channels=1, dtype='int16', blocksize=block) as stream:
            self.ctrl.push('idle', {'status': 'listening'})

            def read():
                if run:
                    run.check()  # Esc while listening stops within a tenth of a second
                data, _ = stream.read(block)
                data = bytes(data)
                samples = array.array('h', data)
                level = (sum(s * s for s in samples) / max(1, len(samples))) ** 0.5
                self.mic_level.feed(level)  # the ring follows your voice (10 blocks a second)
                self.mic_level.flush()
                return data, level

            # Speech is anything clearly louder than the first 0.3 s of room noise
            noise = max(read()[1] for _ in range(3))
            threshold = max(300, 2.5 * noise)
            self.mic_level.quiet = max(QUIET, noise * 1.5)  # the room's own noise doesn't move the ring
            frames, previous, silent_blocks = [], b'', 0
            for waited in range(50):  # wait up to 5 s for speech to start
                data, level = read()
                if level > threshold:
                    frames = [previous, data]
                    break
                previous = data
            else:
                raise sr.WaitTimeoutError("listening timed out while waiting for phrase to start")
            while len(frames) < 100 and silent_blocks < 10:  # stop after 1 s of silence, or 10 s in total
                data, level = read()
                frames.append(data)
                silent_blocks = silent_blocks + 1 if level < threshold else 0
        return sr.AudioData(b''.join(frames), rate, 2)
