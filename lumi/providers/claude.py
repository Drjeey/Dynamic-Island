from .base import REQUEST_TIMEOUT, Declined, ToolCall, checked_args, tool_schemas

# Models that take server-side refusal fallbacks ("default" picks the fallback model by refusal category)
FALLBACK_MODELS = ('claude-opus-5-5', 'claude-opus-5', 'claude-fable-5-1', 'claude-sonnet-5-5')
FALLBACK_BETA = 'server-side-fallback-2026-07-01'
# Current-generation models take an effort setting; Lumi's answers are short, so low keeps them quick
EFFORT_MODELS = ('claude-opus-5', 'claude-sonnet-5', 'claude-haiku-5', 'claude-fable-5')
MAX_TOKENS = 16000
JSON_RETRIES = 2


class ClaudeProvider:
    """Anthropic's Claude through the official anthropic SDK."""

    label = 'Claude'

    def __init__(self, model, api_key, **_):
        import anthropic
        self.model = model
        # Without a saved key the SDK still finds ANTHROPIC_API_KEY or a signed-in `ant` profile
        self.client = (anthropic.Anthropic(api_key=api_key, timeout=REQUEST_TIMEOUT) if api_key
                       else anthropic.Anthropic(timeout=REQUEST_TIMEOUT))

    def new_chat(self, system, functions):
        return ClaudeChat(self, system, functions)


def _echoable(content):
    """The reply as it may be sent back next turn. After a mid-answer fallback, thinking and tool requests
    from before the switch belong to the model that declined, so they're left out."""
    boundary = max((i for i, b in enumerate(content) if b.type == 'fallback'), default=-1)
    return [b for i, b in enumerate(content)
            if i > boundary or b.type not in ('thinking', 'redacted_thinking', 'tool_use')]


class ClaudeChat:
    def __init__(self, provider, system, functions):
        self._client, self._model, self._system = provider.client, provider.model, system
        schemas = tool_schemas(functions)
        self._schemas = {s['name']: s for s in schemas}
        # Streamed requests with Lumi's own tools stream tool inputs as they're written (checked before use)
        self._tools = [{'name': s['name'], 'description': s['description'], 'input_schema': s['parameters'],
                        'eager_input_streaming': True} for s in schemas]
        self.history = []

    def _stream(self):
        params = dict(model=self._model, max_tokens=MAX_TOKENS, system=self._system,
                      tools=self._tools, messages=self.history)
        if self._model.startswith(EFFORT_MODELS):
            params['output_config'] = {'effort': 'low'}
        if self._model in FALLBACK_MODELS:
            return self._client.beta.messages.stream(betas=[FALLBACK_BETA], fallbacks='default', **params)
        return self._client.messages.stream(**params)

    def send(self, message, on_text):
        if isinstance(message, str):
            content = message
        else:
            content = [{'type': 'tool_result', 'tool_use_id': call.id, 'content': result,
                        **({'is_error': True} if call.args is None else {})} for call, result in message]
        self.history.append({'role': 'user', 'content': content})

        for attempt in range(JSON_RETRIES + 1):
            text = ''
            try:
                with self._stream() as stream:
                    for event in stream:
                        if event.type == 'text':
                            text += event.text
                            on_text(text)
                    response = stream.get_final_message()
                break
            except ValueError:
                # A tool input the SDK couldn't parse at all: ask again (API errors aren't ValueErrors)
                if attempt == JSON_RETRIES:
                    raise

        content = _echoable(response.content)
        self.history.append({'role': 'assistant', 'content': content})
        if response.stop_reason == 'refusal':
            raise Declined()
        uses = [b for b in content if b.type == 'tool_use']
        if uses and response.stop_reason == 'max_tokens':
            raise RuntimeError('A tool request was cut off')  # never run a half-written tool call
        return text, [ToolCall(b.id, b.name, checked_args(self._schemas.get(b.name), b.input)) for b in uses]
