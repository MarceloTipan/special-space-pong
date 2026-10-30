"""Tests for the enemy AI: prediction, shot difficulty and designed misses."""

import math
import random

import pytest

from game import levels
from game.ball import Ball
from game.enemy import Blocker, Enemy, predict_landing, rally_share, shot_difficulty

LEFT, RIGHT = 45, 755
BALL = 28
PADDLE = 102


def make_ball(x, y, vx, vy, hits=1):
    """A launched ball with an exact velocity (no serve jitter)."""
    ball = Ball(x, y, BALL, BALL, speed=1, serve_delay=0)
    ball.vx, ball.vy, ball.hits = vx, vy, hits
    ball.base_speed = math.hypot(vx, vy)
    return ball


def make_enemy(miss_easy=0.1, miss_hard=0.6, seed=1):
    enemy = Enemy(x=350, face_y=100, width=PADDLE, left=LEFT, right=RIGHT,
                  rng=random.Random(seed))
    enemy.configure(speed=450, miss_easy=miss_easy, miss_hard=miss_hard)
    return enemy


def reach(enemy, read):
    """How far off a guess can be and still be saved."""
    return (enemy.width + BALL) / 2 + enemy.speed * read.late_time


# --- Prediction ---

def test_a_straight_shot_lands_below_where_it_is():
    ball = make_ball(386, 600, 0, -300)
    x, seconds = predict_landing(ball, 100, LEFT, RIGHT)
    assert x == pytest.approx(400)
    assert seconds == pytest.approx((ball.cy - 100) / 300)


def test_prediction_folds_wall_bounces():
    # Center at (400, 600), moving 1 px right per px up: 500 px higher it
    # would be at x = 900 without walls. The center can't pass 741 (right
    # wall minus half the ball), so it bounces back to 741 - (900 - 741) = 582
    ball = make_ball(400 - BALL / 2, 600 - BALL / 2, 300, -300)
    x, _ = predict_landing(ball, 100, LEFT, RIGHT)
    assert x == pytest.approx(582)


def test_balls_moving_away_are_not_predicted():
    assert predict_landing(make_ball(400, 600, 0, 300), 100, LEFT, RIGHT) is None


# --- Shot difficulty ---

def test_serves_and_straight_shots_are_easy_edge_shots_hard():
    speed = 400
    edge_vx = speed * levels.MAX_BOUNCE_X
    edge = make_ball(400, 600, edge_vx, -math.sqrt(speed ** 2 - edge_vx ** 2))
    assert shot_difficulty(make_ball(400, 600, 200, -300, hits=0)) == 0   # serve
    assert shot_difficulty(make_ball(400, 600, 0, -speed)) == 0
    assert shot_difficulty(edge) == pytest.approx(1)


def test_rally_share_goes_from_serve_speed_to_top_speed():
    ball = make_ball(400, 600, 0, -300)
    assert rally_share(ball) == 0
    ball.vy *= levels.RALLY_MAX
    assert rally_share(ball) == pytest.approx(1)


# --- Designed misses ---

@pytest.mark.parametrize("vx_share", [0.0, 0.4, 0.75])
def test_misreads_happen_as_often_as_designed(vx_share):
    enemy = make_enemy(miss_easy=0.1, miss_hard=0.7)
    vx = 400 * vx_share
    ball = make_ball(400, 600, vx, -math.sqrt(400 ** 2 - vx ** 2))
    tries = 20000
    misses = sum(abs((read := enemy._read(ball, 400, 1.5)).error) > reach(enemy, read)
                 for _ in range(tries))
    assert misses / tries == pytest.approx(enemy.miss_chance(ball), abs=0.015)


def test_a_miss_falls_just_out_of_reach_inside_the_field():
    enemy = make_enemy(miss_easy=0.89, miss_hard=0.89)   # nearly every read is bad
    ball = make_ball(80, 600, 0, -300)                   # near the left wall
    for _ in range(500):
        read = enemy._read(ball, 94, 1.5)
        distance = abs(read.error)
        if distance > reach(enemy, read):
            low, high = Enemy.MISS_MARGIN
            assert reach(enemy, read) + low <= distance <= reach(enemy, read) + high
            assert read.error > 0   # no room on the left: misjudged to the right


def test_a_deflection_never_makes_a_shot_easier():
    enemy = make_enemy(miss_easy=0.0, miss_hard=0.8)
    vx = 400 * levels.MAX_BOUNCE_X
    ball = make_ball(400, 600, vx, -math.sqrt(400 ** 2 - vx ** 2))
    enemy.update(1 / 60, [ball])                 # reads the edge shot
    hard_chance = enemy._reads[ball].chance
    ball.vx, ball.vy = 0, -400                   # an asteroid sends it straight
    enemy.forget(ball)
    enemy.update(1 / 60, [ball])
    assert enemy._reads[ball].chance == pytest.approx(hard_chance)


def test_the_enemy_returns_to_the_center_when_nothing_comes():
    enemy = make_enemy()
    enemy.x = LEFT
    for _ in range(600):
        enemy.update(1 / 60, [])
    assert enemy.x + enemy.width / 2 == pytest.approx((LEFT + RIGHT) / 2)


# --- Blocker ---

def test_the_blocker_patrols_from_wall_to_wall():
    blocker = Blocker(y=300, width=80, height=12, left=LEFT, right=RIGHT,
                      speed=400, rng=random.Random(1))
    xs = []
    for _ in range(600):
        blocker.update(1 / 60)
        xs.append(blocker.x)
    assert min(xs) == LEFT
    assert max(xs) == RIGHT - 80
