import json

from .base import REQUEST_TIMEOUT, ToolCall, checked_args, tool_schemas


class OpenAICompatibleProvider:
    """OpenAI, or any server that speaks the same chat API: Ollama, LM Studio, OpenRouter, Groq and others."""

    def __init__(self, model, api_key, base_url=None, label='OpenAI', **_):
        import openai
        self._openai = openai
        self.label = label
        self.model = model
        # Local servers ignore the key, but the SDK insists on one
        self.client = openai.OpenAI(api_key=api_key or 'not-needed', base_url=base_url or None, timeout=REQUEST_TIMEOUT)

    def new_chat(self, system, functions):
        return OpenAIChat(self, system, functions)


class OpenAIChat:
    def __init__(self, provider, system, functions):
        self._provider = provider
        schemas = tool_schemas(functions)
        self._schemas = {s['name']: s for s in schemas}
        self._tools = [{'type': 'function', 'function': s} for s in schemas]
        self.history = [{'role': 'system', 'content': system}]

    def _create(self):
        p = self._provider
        try:
            return p.client.chat.completions.create(model=p.model, messages=self.history, stream=True,
                                                    **({'tools': self._tools} if self._tools else {}))
        except p._openai.BadRequestError as e:
            # Some local models can't call tools at all; Lumi can still chat with them
            if self._tools and 'tool' in str(e).lower():
                print(f"{p.label}: {p.model} doesn't support tools, chatting without them")
                self._tools = None
                return self._create()
            raise

    def send(self, message, on_text):
        if isinstance(message, str):
            self.history.append({'role': 'user', 'content': message})
        else:
            self.history += [{'role': 'tool', 'tool_call_id': call.id, 'content': result} for call, result in message]

        text, pieces = '', {}  # tool calls arrive in pieces, keyed by their index
        for chunk in self._create():
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                text += delta.content
                on_text(text)
            for piece in delta.tool_calls or []:
                call = pieces.setdefault(piece.index, {'id': '', 'name': '', 'arguments': ''})
                if piece.id:
                    call['id'] = piece.id
                if piece.function:
                    call['name'] += piece.function.name or ''
                    call['arguments'] += piece.function.arguments or ''

        requested = [{'id': c['id'] or f'call_{i}', 'type': 'function',
                      'function': {'name': c['name'], 'arguments': c['arguments'] or '{}'}}
                     for i, c in sorted(pieces.items())]
        entry = {'role': 'assistant', 'content': text or None}
        if requested:
            entry['tool_calls'] = requested
        self.history.append(entry)

        calls = []
        for r in requested:
            try:
                args = json.loads(r['function']['arguments'])
            except json.JSONDecodeError:
                args = None
            name = r['function']['name']
            calls.append(ToolCall(r['id'], name, checked_args(self._schemas.get(name), args) if args is not None else None))
        return text, calls
