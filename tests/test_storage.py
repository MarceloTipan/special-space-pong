"""Tests for persistent storage: files on desktop, localStorage in the browser."""

import platform

import pytest

from utils import storage


class FakeLocalStorage:
    def __init__(self):
        self.items = {}

    def getItem(self, key):
        return self.items.get(key)

    def setItem(self, key, value):
        self.items[key] = value


@pytest.fixture
def browser(monkeypatch):
    """Pretend to run in the browser, with an empty localStorage."""
    local = FakeLocalStorage()
    monkeypatch.setattr(storage, "WEB", True)
    monkeypatch.setattr(platform, "window", type("Window", (), {"localStorage": local}),
                        raising=False)
    return local


def test_desktop_round_trip(tmp_path):
    path = tmp_path / "data.json"
    storage.save(path, {"a": 1, "name": "Ñandú"})
    assert storage.load(path, None) == {"a": 1, "name": "Ñandú"}


def test_missing_or_corrupt_documents_give_the_default(tmp_path):
    assert storage.load(tmp_path / "nope.json", {"x": 0}) == {"x": 0}
    (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
    assert storage.load(tmp_path / "bad.json", []) == []


def test_in_the_browser_documents_go_to_local_storage(tmp_path, browser):
    path = tmp_path / "settings.json"
    storage.save(path, {"volume": 0.5})
    assert not path.exists()                  # nothing written to the (temporary) disk
    assert "settings.json" in browser.items   # stored under the file's name
    assert storage.load(path, None) == {"volume": 0.5}


def test_in_the_browser_a_missing_document_gives_the_default(tmp_path, browser):
    assert storage.load(tmp_path / "highscores.json", {}) == {}
