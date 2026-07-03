from bot.clients import store
from bot.config import DEFAULT_LEVEL, DEFAULT_PROVIDER, HF_SPACE_ID

VALID_PROVIDERS = ("main", "hf")
VALID_LEVELS = ("beginner", "elementary", "intermediate")


def get_provider(user_id: int) -> str:
    """Return the user's chosen provider, or DEFAULT_PROVIDER.

    Falls back to DEFAULT_PROVIDER if storage is not configured,
    storage is down, the user has no saved preference, or the saved
    preference is "hf" but HF_SPACE_ID is not configured.
    """
    if store is None:
        return DEFAULT_PROVIDER
    try:
        value = store.get(f"provider:{user_id}")
    except Exception as e:
        print(f"Store read error (preferences): {e}")
        return DEFAULT_PROVIDER
    if value not in VALID_PROVIDERS:
        return DEFAULT_PROVIDER
    if value == "hf" and not HF_SPACE_ID:
        return DEFAULT_PROVIDER
    return value


def set_provider(user_id: int, provider: str) -> bool:
    """Save the user's provider choice. Returns True on success."""
    if provider not in VALID_PROVIDERS:
        return False
    if store is None:
        return False
    try:
        store.set(f"provider:{user_id}", provider)
        return True
    except Exception as e:
        print(f"Store write error (preferences): {e}")
        return False


def get_level(user_id: int) -> str:
    """Return the user's saved learning level, or DEFAULT_LEVEL.

    Falls back to DEFAULT_LEVEL if storage is not configured, storage is
    down, the user has no saved level, or the saved value is unrecognized.
    """
    if store is None:
        return DEFAULT_LEVEL
    try:
        value = store.get(f"level:{user_id}")
    except Exception as e:
        print(f"Store read error (preferences): {e}")
        return DEFAULT_LEVEL
    if value not in VALID_LEVELS:
        return DEFAULT_LEVEL
    return value


def set_level(user_id: int, level: str) -> bool:
    """Save the user's learning level. Returns True on success."""
    if level not in VALID_LEVELS:
        return False
    if store is None:
        return False
    try:
        store.set(f"level:{user_id}", level)
        return True
    except Exception as e:
        print(f"Store write error (preferences): {e}")
        return False
