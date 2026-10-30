"""Tests for the campaign tables: every level must be valid and translated."""

import json

import pytest

from game import levels
from utils import i18n

ALL_LEVELS = (*levels.CAMPAIGN, levels.SECRET)


def test_campaign_has_five_levels_then_the_secret():
    assert len(levels.CAMPAIGN) == 5
    assert levels.SECRET_LEVEL == 6
    assert levels.get(1) is levels.CAMPAIGN[0]
    assert levels.get(5) is levels.CAMPAIGN[-1]
    assert levels.get(6) is levels.SECRET


@pytest.mark.parametrize("level", ALL_LEVELS, ids=lambda level: level.key)
def test_level_values_are_valid(level):
    assert level.balls >= 1
    assert level.goals >= 1
    assert level.ball_speed > 0 and level.enemy_speed > 0
    assert 0 <= level.miss_easy < level.miss_hard < 1


def test_only_the_secret_level_has_a_blocker():
    assert all(level.blocker_speed == 0 for level in levels.CAMPAIGN)
    assert levels.SECRET.blocker_speed > 0


def test_difficulties_are_the_ones_settings_offers():
    assert set(levels.DIFFICULTIES) == {"easy", "normal", "hard"}


def test_harder_difficulties_scale_the_right_way():
    easy, normal, hard = (levels.DIFFICULTIES[k] for k in ("easy", "normal", "hard"))
    assert easy.lives > normal.lives > hard.lives
    assert easy.miss_scale > normal.miss_scale > hard.miss_scale
    assert easy.speed_scale < normal.speed_scale < hard.speed_scale


@pytest.mark.parametrize("path", sorted(i18n.LOCALS_DIR.glob("*.json")), ids=lambda p: p.stem)
def test_every_level_has_a_name(path):
    with open(path, encoding="utf-8") as f:
        names = json.load(f).get("levels", {})
    missing = [level.key for level in ALL_LEVELS if level.key not in names]
    assert not missing, f"{path.name} has no name for: {missing}"
