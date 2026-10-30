"""Tests for the survival mode rules."""

import pytest

from game import survival


def test_the_multiplier_grows_every_few_returns_in_a_row():
    step = survival.COMBO_STEP
    assert survival.multiplier(0) == 1
    assert survival.multiplier(step - 1) == 1
    assert survival.multiplier(step) == 2
    assert survival.multiplier(3 * step) == 4


def test_the_multiplier_has_a_cap():
    assert survival.multiplier(1000) == survival.MAX_MULTIPLIER


def test_balls_speed_up_over_time_up_to_a_cap():
    pace = survival.PACES["normal"]
    assert survival.speed_scale(0, pace) == 1
    assert 1 < survival.speed_scale(30, pace) < survival.speed_scale(60, pace)
    assert survival.speed_scale(10_000, pace) == pytest.approx(pace.max_scale)


def test_harder_difficulties_are_harder_in_every_way():
    easy, normal, hard = (survival.PACES[k] for k in ("easy", "normal", "hard"))
    for field in ("obstacles", "serve_speed", "growth", "max_scale", "max_balls"):
        assert getattr(easy, field) <= getattr(normal, field) <= getattr(hard, field), field


def test_there_is_a_pace_for_every_difficulty():
    from game import levels
    assert set(survival.PACES) == set(levels.DIFFICULTIES)


def test_the_red_ball_warns_before_it_changes():
    assert 0 < survival.RED_WARNING < survival.RED_SWITCH_EVERY
