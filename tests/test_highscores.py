"""Tests for the high score tables: ordering, size limit, modes and persistence."""

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
        hs.add("AAA", i * 100, level=1)


def test_table_starts_empty(hs):
    assert hs.get_all() == []


def test_any_positive_score_qualifies_while_there_is_room(hs):
    assert hs.qualifies(1)


def test_zero_never_qualifies(hs):
    # Leaving a game right away must not create a record
    assert not hs.qualifies(0)


def test_add_returns_the_position(hs):
    assert hs.add("AAA", 500, level=3) == 1
    assert hs.add("BBB", 900, level=5) == 1
    assert hs.add("CCC", 100, level=1) == 3


def test_table_is_sorted_from_highest_to_lowest(hs):
    for points in (300, 900, 600):
        hs.add("AAA", points, level=1)
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
    assert hs.add("ZZZ", 1, level=1) == 0


def test_scores_persist_to_disk(hs):
    hs.add("MTP", 777, level=4)
    hs._scores = None   # simulate closing and reopening the game
    assert hs.get_all()[0]["initials"] == "MTP"
    assert hs.get_all()[0]["points"] == 777


def test_initials_are_uppercased_and_trimmed_to_three(hs):
    hs.add("abcd", 100, level=1)
    assert hs.get_all()[0]["initials"] == "ABC"


def test_corrupt_file_starts_an_empty_table(hs):
    hs.SCORES_FILE.write_text("not json", encoding="utf-8")
    assert hs.get_all() == []


def test_each_mode_has_its_own_table(hs):
    hs.add("AAA", 500, hs.CAMPAIGN, level=3)
    hs.add("BBB", 900, hs.SURVIVAL, seconds=95)
    assert [e["initials"] for e in hs.get_all(hs.CAMPAIGN)] == ["AAA"]
    assert [e["initials"] for e in hs.get_all(hs.SURVIVAL)] == ["BBB"]
    assert hs.get_all(hs.SURVIVAL)[0]["seconds"] == 95


def test_a_full_campaign_table_does_not_block_survival(hs):
    fill(hs, hs.MAX_ENTRIES)
    assert hs.qualifies(1, hs.SURVIVAL)


def test_old_single_table_files_become_the_campaign_table(hs):
    hs.SCORES_FILE.write_text('[{"initials": "OLD", "points": 300, "level": 2}]',
                              encoding="utf-8")
    assert hs.get_all(hs.CAMPAIGN)[0]["initials"] == "OLD"
    assert hs.get_all(hs.SURVIVAL) == []
