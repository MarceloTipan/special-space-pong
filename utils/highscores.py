"""High score table, persisted to highscores.json.

Usage:
    from utils import highscores

    if highscores.qualifies(points):
        position = highscores.add("MTP", points, level)
    table = highscores.get_all()
"""

import json
from config import PATHS
from datetime import date

SCORES_FILE = PATHS.HIGHSCORES_FILE

#: Maximum number of entries kept in the table.
MAX_ENTRIES = 10

_scores = None


def _load():
    global _scores
    if _scores is not None:
        return _scores
    try:
        with open(SCORES_FILE, encoding="utf-8") as f:
            _scores = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        _scores = []
    return _scores


def _save():
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump(_scores, f, ensure_ascii=False, indent=2)


def get_all():
    """Return the table, ordered from highest to lowest score."""
    return list(_load())


def qualifies(points):
    """Whether this score makes the table (there's room or it beats the last)."""
    scores = _load()
    if points <= 0:
        return False
    if len(scores) < MAX_ENTRIES:
        return True
    return points > scores[-1]["points"]


def add(initials, points, level):
    """Insert an entry, keep only the top MAX_ENTRIES, and persist.

    Returns the 1-based position where the entry landed (1 = first place).
    """
    scores = _load()
    entry = {
        "initials": initials.upper()[:3],
        "points": int(points),
        "level": int(level),
        "date": date.today().isoformat(),
    }
    scores.append(entry)
    scores.sort(key=lambda e: e["points"], reverse=True)
    del scores[MAX_ENTRIES:]
    _save()
    return scores.index(entry) + 1 if entry in scores else 0