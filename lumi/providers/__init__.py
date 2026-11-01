"""The AI behind Lumi's chat, chosen in Settings. Each provider's SDK is imported only when it's the chosen one."""
from .base import Declined, ToolCall  # noqa: F401  (used by chat.py)

# label, config key for its model, whether it needs a key, whether it can do live voice, and model suggestions
PROVIDERS = {
    'gemini': {'label': 'Gemini', 'model_key': 'gemini_model', 'needs_key': True, 'live': True,
               'models': ['gemini-3.5-flash', 'gemini-3.8-flash', 'gemini-3.5-flash-lite']},
    'claude': {'label': 'Claude', 'model_key': 'claude_model', 'needs_key': True, 'live': False,
               'models': ['claude-opus-5-5', 'claude-sonnet-5-5', 'claude-haiku-5-5']},
    'openai': {'label': 'OpenAI', 'model_key': 'openai_model', 'needs_key': True, 'live': False,
               'models': ['gpt-5-mini', 'gpt-5']},
    'custom': {'label': 'Other (OpenAI-compatible)', 'model_key': 'custom_model', 'needs_key': False, 'live': False,
               'models': ['llama3.2', 'qwen2.5']},
}
PACKAGES = {'gemini': 'google-genai', 'claude': 'anthropic', 'openai': 'openai', 'custom': 'openai'}


def chosen(config):
    name = config.get('ai_provider')
    return name if name in PROVIDERS else 'gemini'


def create(config, api_key):
    """Builds the chosen provider. Returns (provider, None) or (None, a message for the user)."""
    name = chosen(config)
    info = PROVIDERS[name]
    model = config.get(info['model_key'])
    if info['needs_key'] and not api_key and name != 'claude':  # Claude's SDK can also use a signed-in profile
        return None, f"Add your {info['label']} API key in Settings so I can chat!"
    try:
        if name == 'gemini':
            from .gemini import GeminiProvider
            return GeminiProvider(model, api_key, backup=config.get('gemini_backup_model')), None
        if name == 'claude':
            from .claude import ClaudeProvider
            return ClaudeProvider(model, api_key), None
        from .openai_compat import OpenAICompatibleProvider
        if name == 'openai':
            return OpenAICompatibleProvider(model, api_key), None
        return OpenAICompatibleProvider(model, api_key, base_url=config.get('custom_url'), label='your model'), None
    except ImportError:
        return None, f"Install {PACKAGES[name]} so I can chat!"
    except Exception as e:
        print(f"AI Init Error ({name}): {e}")
        if name == 'claude' and not api_key:
            return None, "Add your Claude API key in Settings so I can chat!"
        return None, f"I couldn't connect to {info['label']}."
