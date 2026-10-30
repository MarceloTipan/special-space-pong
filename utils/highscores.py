"""High score tables, one per game mode, persisted to highscores.json.

Usage:
    from utils import highscores

    if highscores.qualifies(points, highscores.SURVIVAL):
        position = highscores.add("MTP", points, highscores.SURVIVAL, seconds=95)
    table = highscores.get_all(highscores.CAMPAIGN)

Each entry also stores how far the player got: the level reached in the
campaign, the seconds survived in survival.
"""

import json
from datetime import date
# from pathlib import Path

from config import PATHS


SCORES_FILE = PATHS.HIGHSCORES_FILE

# SCORES_FILE = Path(__file__).resolve().parent.parent / "highscores.json"

CAMPAIGN = "campaign"
SURVIVAL = "survival"
MODES = (CAMPAIGN, SURVIVAL)

#: Maximum number of entries kept in each table.
MAX_ENTRIES = 5

_scores = None


def _load():
    """The tables, {mode: [entries]}, read from disk once."""
    global _scores
    if _scores is not None:
        return _scores
    try:
        with open(SCORES_FILE, encoding="utf-8") as f:
            stored = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        stored = {}
    if isinstance(stored, list):
        stored = {CAMPAIGN: stored}   # older versions had a single campaign table
    _scores = {mode: list(stored.get(mode, [])) for mode in MODES}
    return _scores


def _save():
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump(_scores, f, ensure_ascii=False, indent=2)


def get_all(mode=CAMPAIGN):
    """Return a mode's table, ordered from highest to lowest score."""
    return list(_load()[mode])


def qualifies(points, mode=CAMPAIGN):
    """Whether this score makes the mode's table (there's room or it beats the last)."""
    scores = _load()[mode]
    if points <= 0:
        return False
    if len(scores) < MAX_ENTRIES:
        return True
    return points > scores[-1]["points"]


def add(initials, points, mode=CAMPAIGN, level=None, seconds=None):
    """Insert an entry, keep only the top MAX_ENTRIES, and persist.

    Args:
        initials: Player initials (uppercased, first three kept).
        points: Score.
        mode: Which table (CAMPAIGN or SURVIVAL).
        level: Level reached (campaign).
        seconds: Time survived (survival).

    Returns:
        The 1-based position where the entry landed (1 = first place), or
        0 if it didn't make the table.
    """
    scores = _load()[mode]
    entry = {
        "initials": initials.upper()[:3],
        "points": int(points),
        "date": date.today().isoformat(),
    }
    if level is not None:
        entry["level"] = int(level)
    if seconds is not None:
        entry["seconds"] = int(seconds)
    scores.append(entry)
    scores.sort(key=lambda e: e["points"], reverse=True)
    del scores[MAX_ENTRIES:]
    _save()
    return scores.index(entry) + 1 if entry in scores else 0
