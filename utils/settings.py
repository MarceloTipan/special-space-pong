"""Persistent user settings (volume, language, fullscreen, difficulty).

Stored in settings.json at the project root. Usage:

    from utils import settings

    settings.load()                 # once, at startup
    vol = settings.get("volume")    # read
    settings.set("volume", 0.5)     # write (saved automatically)
"""

import json
from config import PATHS

SETTINGS_FILE = PATHS.SETTINGS_FILE

#: Default values; this dict also defines which keys are valid.
DEFAULTS = {
    "volume": 0.8,
    "language": "es",
    "fullscreen": False,
    "difficulty": "normal",
}

_data = dict(DEFAULTS)


def load():
    """Load settings.json, falling back to defaults if missing or corrupt."""
    global _data
    _data = dict(DEFAULTS)
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            stored = json.load(f)
        # Only accept known keys (ignores leftovers from older versions)
        _data.update({k: v for k, v in stored.items() if k in DEFAULTS})
    except (FileNotFoundError, json.JSONDecodeError):
        pass


def save():
    """Write the current settings to disk."""
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(_data, f, indent=2)


def get(key):
    """Return the value of a setting."""
    return _data[key]


def set(key, value):
    """Change a setting and persist it immediately.

    Raises KeyError if the key is not defined in DEFAULTS.
    """
    if key not in DEFAULTS:
        raise KeyError(f"Unknown setting: {key}")
    _data[key] = value
    save()