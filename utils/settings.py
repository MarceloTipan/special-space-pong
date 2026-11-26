"""Persistent user settings (volume, language, display, difficulty, controls).

Stored in settings.json at the project root (in the browser, in its
local storage; see utils.storage). Usage:

    from utils import settings

    settings.load()                 # once, at startup
    vol = settings.get("volume")    # read
    settings.set("volume", 0.5)     # write (saved automatically)
"""

from config import PATHS
from utils import storage
from utils.runtime import CAMERA_SUPPORTED

SETTINGS_FILE = PATHS.SETTINGS_FILE

#: Default values; this dict also defines which keys are valid.
DEFAULTS = {
    "volume": 0.8,
    "language": "es",
    "fullscreen": False,
    "difficulty": "normal",
    "control": "camera",        # camera | mouse | keyboard
    "camera_invert": False,     # for cameras whose driver already mirrors the image
}

_data = dict(DEFAULTS)


def load():
    """Load settings.json, falling back to defaults if missing or corrupt."""
    global _data
    _data = dict(DEFAULTS)
    stored = storage.load(SETTINGS_FILE, {})
    if isinstance(stored, dict):
        # Only accept known keys (ignores leftovers from older versions)
        _data.update({k: v for k, v in stored.items() if k in DEFAULTS})
    if _data["control"] == "camera" and not CAMERA_SUPPORTED:
        _data["control"] = "mouse"   # the browser build has no camera control


def save():
    """Write the current settings to disk."""
    storage.save(SETTINGS_FILE, _data)


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
