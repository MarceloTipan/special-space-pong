"""Tests for the i18n module: every language must stay complete and usable."""

import json
import string

import pytest

from utils import i18n

LANGUAGE_FILES = sorted(i18n.LOCALS_DIR.glob("*.json"))
DEFAULT_FILE = i18n.LOCALS_DIR / f"{i18n.DEFAULT_LANGUAGE}.json"


def _flatten(data, prefix=""):
    """{"menu": {"start": "PLAY"}} -> {"menu.start": "PLAY"}."""
    flat = {}
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(_flatten(value, full_key))
        else:
            flat[full_key] = str(value)
    return flat


def _load(path):
    with open(path, encoding="utf-8") as f:
        return _flatten(json.load(f))


def _placeholders(text):
    """Names of the {placeholders} in a string, e.g. {"points"}."""
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


@pytest.fixture(autouse=True)
def restore_default_language():
    yield
    i18n.set_language(i18n.DEFAULT_LANGUAGE)


def test_there_are_at_least_two_languages():
    assert len(LANGUAGE_FILES) >= 2


@pytest.mark.parametrize("path", LANGUAGE_FILES, ids=lambda p: p.stem)
def test_language_has_the_same_keys_as_the_default(path):
    # The classic i18n bug: adding a text in one language and forgetting another
    reference, keys = set(_load(DEFAULT_FILE)), set(_load(path))
    assert not reference - keys, f"{path.name} is missing: {sorted(reference - keys)}"
    assert not keys - reference, f"{path.name} has extra keys: {sorted(keys - reference)}"


@pytest.mark.parametrize("path", LANGUAGE_FILES, ids=lambda p: p.stem)
def test_language_uses_the_same_placeholders(path):
    # A placeholder the code doesn't pass (e.g. {score} instead of {points})
    # would crash the game when the text is formatted
    reference, texts = _load(DEFAULT_FILE), _load(path)
    for key in reference.keys() & texts.keys():
        assert _placeholders(texts[key]) == _placeholders(reference[key]), (
            f"{path.name}: '{key}' uses {_placeholders(texts[key])}, "
            f"expected {_placeholders(reference[key])}")


def test_switching_language_changes_the_text():
    i18n.set_language("es")
    spanish = i18n.t("menu.start")
    i18n.set_language("en")
    english = i18n.t("menu.start")
    assert "menu.start" not in (spanish, english)
    assert spanish != english


def test_missing_key_returns_the_key_itself():
    # Visible on screen, so a missing translation is easy to spot
    assert i18n.t("does.not.exist") == "does.not.exist"


def test_values_are_interpolated():
    assert "42" in i18n.t("highscores.your_score", points=42)


def test_unknown_language_falls_back_to_the_default():
    expected = i18n.t("menu.start")
    i18n.set_language("xx")   # no such file
    assert i18n.t("menu.start") == expected
