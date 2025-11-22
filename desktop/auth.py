# desktop/auth.py
from pathlib import Path
import json
from typing import Optional

TOKEN_CACHE = Path.home() / ".equipment_visualizer_token.json"

def save_token(username: str, token: str):
    try:
        TOKEN_CACHE.write_text(json.dumps({"username": username, "token": token}))
    except Exception:
        # ignore caching errors
        pass

def load_cached_token() -> Optional[dict]:
    try:
        if TOKEN_CACHE.exists():
            j = json.loads(TOKEN_CACHE.read_text())
            return j
    except Exception:
        return None
    return None

def clear_cached_token():
    try:
        if TOKEN_CACHE.exists():
            TOKEN_CACHE.unlink()
    except Exception:
        pass
