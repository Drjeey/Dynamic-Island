from .base import REQUEST_TIMEOUT, ToolCall, checked_args, tool_schemas

BUSY_CODES = (429, 500, 503, 504)  # rate-limited, overloaded or too slow at Google: worth one try elsewhere
# With a backup, the chosen model gets this long to start answering before Lumi asks the backup instead, so the
# switch happens well inside the page's 45 s "that took too long" watchdog
FIRST_TRY_TIMEOUT = 25


def _busy(error):
    """Google couldn't serve the model right now (as opposed to a bad key, a bad request or a retired model)."""
    from google.genai import errors
    if isinstance(error, errors.APIError):
        return getattr(error, 'code', None) in BUSY_CODES
    return 'timeout' in type(error).__name__.lower()


class GeminiProvider:
    """Google Gemini through google-genai. Also the only provider with live voice (live.py uses .client and .types)."""

    label = 'Gemini'

    def __init__(self, model, api_key, backup=None, **_):
        from google import genai  # about a second to import, so only when Gemini is the chosen provider
        from google.genai import types
        self.types = types
        self.model = model
        self.backup = backup if backup and backup != model else None  # used when the model is busy
        self.client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT * 1000))
        self.first_client = (genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=FIRST_TRY_TIMEOUT * 1000))
                             if self.backup else self.client)

    def new_chat(self, system, functions):
        return GeminiChat(self, system, functions)


class GeminiChat:
    def __init__(self, provider, system, functions):
        types = self._types = provider.types
        self._provider = provider
        self.model = provider.model
        # Lumi runs the tool loop itself (chat.py) so each step can be shown as it happens
        self._config = types.GenerateContentConfig(
            system_instruction=system, tools=functions,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
        self._chat = getattr(provider, 'first_client', provider.client).chats.create(model=self.model, config=self._config)
        self.on_busy = None  # set by chat.py: shows that Lumi is asking the backup (and counts as progress)
        self._schemas = {s['name']: s for s in tool_schemas(functions)}

    def send(self, message, on_text):
        if not isinstance(message, str):
            message = [self._types.Part.from_function_response(name=call.name, response={'result': result})
                       for call, result in message]
        try:
            return self._read(message, on_text)
        except Exception as e:
            backup = self._provider.backup
            if not backup or self.model == backup or not _busy(e):
                raise
            # The model is busy: carry the conversation over to the backup and ask again. The rest of this
            # conversation stays on the backup; a new conversation tries the chosen model first again.
            print(f"Gemini: {self.model} is busy ({type(e).__name__}); asking {backup} instead")
            if self.on_busy:
                self.on_busy()
            history = self._chat.get_history()
            self.model = backup
            self._chat = self._provider.client.chats.create(model=backup, config=self._config, history=history)
            return self._read(message, on_text)

    def _read(self, message, on_text):
        text, calls = '', []
        for chunk in self._chat.send_message_stream(message):
            for candidate in chunk.candidates or []:
                for part in (candidate.content.parts if candidate.content else None) or []:
                    if part.function_call:
                        fc = part.function_call
                        calls.append(ToolCall(fc.id or fc.name, fc.name,
                                              checked_args(self._schemas.get(fc.name), dict(fc.args or {}))))
                    elif part.text and not getattr(part, 'thought', False):
                        text += part.text
                        on_text(text)
        return text, calls
