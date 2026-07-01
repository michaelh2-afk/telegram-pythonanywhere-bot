import json
from bot.clients import store

# Cap per user so one person can't grow the row unbounded.
MAX_NOTES = 25


def get_notes(user_id: int) -> list:
    """Return the user's saved notes (oldest first), or [] if none / no store."""
    if store is None:
        return []
    try:
        data = store.get(f"notes:{user_id}")
        return json.loads(data) if data else []
    except Exception as e:
        print(f"Store read error (notes): {e}")
        return []


def add_note(user_id: int, text: str) -> bool:
    """Append a note without replacing existing ones. Returns True on success."""
    if store is None:
        return False
    try:
        notes = get_notes(user_id)
        notes.append(text)
        store.set(f"notes:{user_id}", json.dumps(notes[-MAX_NOTES:]))
        return True
    except Exception as e:
        print(f"Store write error (notes): {e}")
        return False


def clear_notes(user_id: int) -> None:
    """Delete all of the user's saved notes."""
    if store is None:
        return
    try:
        store.delete(f"notes:{user_id}")
    except Exception as e:
        print(f"Store delete error (notes): {e}")
