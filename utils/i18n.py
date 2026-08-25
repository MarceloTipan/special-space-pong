"""Internationalization: all game text lives in JSON, translated on the fly.

Usage:
    from utils.i18n import t, set_language

    set_language("es")           # once, at startup
    label = t("menu.start")      # -> "JUGAR"

Text lives in JSON files under locals/ (es.json, en.json, ...). Adding a
new language is just dropping in another JSON file; no code changes needed.
"""

import json
from config import PATHS

LOCALS_DIR = PATHS.LOCALS_DIR

#: Language used as fallback when a key or file is missing.
DEFAULT_LANGUAGE = "es"

_translations: dict = {}
_fallback: dict = {}
_current_language: str = DEFAULT_LANGUAGE


def _load_file(lang: str) -> dict:
    """Load a language's JSON file; return {} if it does not exist."""
    path = LOCALS_DIR / f"{lang}.json"
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[i18n] Warning: missing {path}")
        return {}


def set_language(lang: str) -> None:
    """Set the active language, loading the default one as fallback."""
    global _translations, _fallback, _current_language
    _current_language = lang
    _translations = _load_file(lang)
    _fallback = _translations if lang == DEFAULT_LANGUAGE else _load_file(DEFAULT_LANGUAGE)


def get_language() -> str:
    """Return the active language code."""
    return _current_language


def available_languages() -> list:
    """List available languages from the JSON files in locals/."""
    return sorted(p.stem for p in LOCALS_DIR.glob("*.json"))


def t(key: str, **kwargs) -> str:
    """Return the translated text for a dotted key, e.g. ``t("menu.start")``.

    Supports interpolation: ``t("game.score", points=10)`` with a value of
    ``"Score: {points}"``. If the key is missing, the key itself is returned
    so the error is visible on screen and easy to spot.
    """
    for source in (_translations, _fallback):
        node = source
        for part in key.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                node = None
                break
        if isinstance(node, str):
            return node.format(**kwargs) if kwargs else node
    return key


# Load the default language on import
set_language(DEFAULT_LANGUAGE)