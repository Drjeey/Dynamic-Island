import os

# API keys live in Windows Credential Manager (through keyring), never in config.json; one entry per provider.
# A provider's environment variable, if set, still wins.
SERVICE = 'LumiIsland'
ACCOUNTS = {'gemini': 'gemini_api_key', 'claude': 'claude_api_key', 'openai': 'openai_api_key', 'custom': 'custom_api_key'}
ENVIRONMENT = {'gemini': 'GEMINI_API_KEY', 'claude': 'ANTHROPIC_API_KEY', 'openai': 'OPENAI_API_KEY'}


def get_api_key(provider='gemini'):
    env = os.environ.get(ENVIRONMENT.get(provider, ''))
    if env:
        return env
    try:
        import keyring
        return keyring.get_password(SERVICE, ACCOUNTS[provider]) or ''
    except Exception as e:
        print(f"Credential Manager Error: {e}")
        return ''


def set_api_key(value, provider='gemini'):
    """Saves the key (or removes it when empty); returns an error message or None."""
    try:
        import keyring
        if value:
            keyring.set_password(SERVICE, ACCOUNTS[provider], value)
        else:
            try: keyring.delete_password(SERVICE, ACCOUNTS[provider])
            except keyring.errors.PasswordDeleteError: pass
        return None
    except Exception as e:
        print(f"Credential Manager Error: {e}")
        return "Couldn't save the key in Windows Credential Manager."


def has_stored_key(provider='gemini'):
    try:
        import keyring
        return bool(keyring.get_password(SERVICE, ACCOUNTS[provider]))
    except Exception:
        return False


def key_from_environment(provider='gemini'):
    return bool(os.environ.get(ENVIRONMENT.get(provider, '')))


def migrate_from_config(config):
    # Earlier versions kept the Gemini key in config.json; move it out the first time we start
    old = config.get('gemini_api_key')
    if old and not set_api_key(old):
        config['gemini_api_key'] = ''
        config.save()
