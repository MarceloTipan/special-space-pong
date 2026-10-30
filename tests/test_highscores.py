"""Tests for the high score table: ordering, size limit and persistence."""

import pytest

from utils import highscores


@pytest.fixture
def hs(tmp_path, monkeypatch):
    """A clean table stored in a temporary file, different for every test."""
    monkeypatch.setattr(highscores, "SCORES_FILE", tmp_path / "highscores.json")
    monkeypatch.setattr(highscores, "_scores", None)   # force a reload
    return highscores


def fill(hs, count):
    """Add `count` entries scoring 100, 200, 300..."""
    for i in range(1, count + 1):
        hs.add("AAA", i * 100, 1)


def test_table_starts_empty(hs):
    assert hs.get_all() == []


def test_any_positive_score_qualifies_while_there_is_room(hs):
    assert hs.qualifies(1)


def test_zero_never_qualifies(hs):
    # Leaving a game right away must not create a record
    assert not hs.qualifies(0)


def test_add_returns_the_position(hs):
    assert hs.add("AAA", 500, 3) == 1
    assert hs.add("BBB", 900, 5) == 1
    assert hs.add("CCC", 100, 1) == 3


def test_table_is_sorted_from_highest_to_lowest(hs):
    for points in (300, 900, 600):
        hs.add("AAA", points, 1)
    assert [e["points"] for e in hs.get_all()] == [900, 600, 300]


def test_table_keeps_only_the_top_entries(hs):
    fill(hs, hs.MAX_ENTRIES + 5)
    table = hs.get_all()
    assert len(table) == hs.MAX_ENTRIES
    assert table[-1]["points"] == 600   # the 5 lowest (100..500) were dropped


def test_full_table_only_accepts_better_scores(hs):
    fill(hs, hs.MAX_ENTRIES)
    lowest = hs.get_all()[-1]["points"]
    assert not hs.qualifies(lowest)
    assert hs.qualifies(lowest + 1)


def test_score_that_does_not_make_the_table_returns_zero(hs):
    fill(hs, hs.MAX_ENTRIES)
    assert hs.add("ZZZ", 1, 1) == 0


def test_scores_persist_to_disk(hs):
    hs.add("MTP", 777, 4)
    hs._scores = None   # simulate closing and reopening the game
    assert hs.get_all()[0]["initials"] == "MTP"
    assert hs.get_all()[0]["points"] == 777


def test_initials_are_uppercased_and_trimmed_to_three(hs):
    hs.add("abcd", 100, 1)
    assert hs.get_all()[0]["initials"] == "ABC"


def test_corrupt_file_starts_an_empty_table(hs):
    hs.SCORES_FILE.write_text("not json", encoding="utf-8")
    assert hs.get_all() == []
