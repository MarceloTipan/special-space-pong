"""Balance report: simulate every level and print how the enemy holds up.

A bot plays the player's side without ever missing, always with the same
kind of shot, so the table shows how each level responds to how well the
player aims:

    straight  hits near the center of the paddle
    mixed     hits anywhere on the paddle
    edge      hits near the edges (smashes)

For each level it prints the enemy's miss rate per shot that reaches it
(target: low for straight shots, high for edge shots) and the average
seconds of play per goal with mixed shots (how long a level lasts).

Run it from the project root after changing game/levels.py:

    python tools/balance_report.py
    python tools/balance_report.py --difficulty hard --seconds 600
"""

import argparse
import os
import random
import sys
from pathlib import Path

# Headless: no window and no audio device needed
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402  (after the SDL environment variables)

FPS = 60
#: Where on the paddle each bot style hits the ball (share of the half paddle).
SHOTS = {"straight": (0.0, 0.2), "mixed": (0.0, 1.0), "edge": (0.75, 1.0)}


class _SilentAudio:
    """Stands in for the game's Audio: every play_* call does nothing."""

    def play(self, name):
        pass

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class _Director:
    def __init__(self):
        self.audio = _SilentAudio()
        self.dt = 1 / FPS
        self.status = None


class _NoCamera:
    """Makes the scene skip the webcam, whatever control is configured."""

    available = False
    hand_x = None

    def release(self):
        pass


def make_game(difficulty):
    """A Pong scene ready to be driven by the bot."""
    from game import levels
    from game.pong import Pong

    game = Pong(_Director(), detector=_NoCamera())
    game.control = Pong.CONTROL_KEYBOARD   # no keys pressed: only the bot moves it
    game.difficulty = levels.DIFFICULTIES[difficulty]
    return game


def _move_bot(game, aims, shot, rng):
    """Put the player's paddle where the next ball lands, hitting it as the
    shot style says."""
    from game.enemy import predict_landing

    soonest = None
    for ball in game.balls:
        if ball.waiting:
            continue
        landing = predict_landing(ball, game.paddle_y - ball.h / 2,
                                  game.FIELD_LEFT, game.FIELD_RIGHT)
        if landing is not None and (soonest is None or landing[1] < soonest[2]):
            soonest = (ball, landing[0], landing[1])
    if soonest is None:
        return

    ball, x, _ = soonest
    key = (id(ball), ball.hits)   # a new aim for every pass of every ball
    if key not in aims:
        if len(aims) > 1000:
            aims.clear()
        low, high = SHOTS[shot]
        aims[key] = rng.choice((-1, 1)) * rng.uniform(low, high)
    game.paddle_x = x - (aims[key] + 1) * game.paddle_w / 2


def simulate(game, level, shot, seconds, rng):
    """Play one level for a while with one shot style.

    Returns:
        (enemy miss rate, seconds per goal)
    """
    game._start_level(level)
    game.goals_to_win = float("inf")   # keep playing: the level never ends
    game.paused = False

    enemy_returns = 0
    bounce = type(game)._bounce_off_paddle

    def counting_bounce(ball, paddle_x, paddle_w, upward, hitter):
        nonlocal enemy_returns
        if hitter == game.ENEMY:
            enemy_returns += 1
        bounce(game, ball, paddle_x, paddle_w, upward, hitter)

    game._bounce_off_paddle = counting_bounce
    aims = {}
    for _ in range(int(seconds * FPS)):
        game.lives = 10 ** 6   # the bot may still miss in multiball; never end the level
        _move_bot(game, aims, shot, rng)
        game.on_update()
    del game._bounce_off_paddle

    misses = game.goals_player
    reached = misses + enemy_returns
    return (misses / reached if reached else 0.0), seconds / max(1, misses)


def main():
    from game import levels

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--difficulty", default="normal", choices=sorted(levels.DIFFICULTIES))
    parser.add_argument("--seconds", type=float, default=600,
                        help="simulated seconds per level and shot style")
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()

    from config import GAME
    from utils import i18n
    pygame.init()
    pygame.display.set_mode(GAME.SCREEN_SIZE)
    i18n.set_language("en")
    random.seed(args.seed)   # serve angles and ball speed jitter
    rng = random.Random(args.seed)
    game = make_game(args.difficulty)
    game.enemy.rng = random.Random(args.seed)

    print(f"Difficulty: {args.difficulty}, {args.seconds:.0f} s per level and shot style\n")
    print(f"{'level':<14}{'serve':>6}{'balls':>6}   "
          f"{'enemy misses: straight / mixed / edge':<40}{'s per goal':>10}")
    speed_scale = levels.DIFFICULTIES[args.difficulty].speed_scale
    for number in range(1, levels.SECRET_LEVEL + 1):
        config = levels.get(number)
        rates = {}
        for shot in SHOTS:
            rates[shot], per_goal = simulate(game, number, shot, args.seconds, rng)
            if shot == "mixed":
                mixed_per_goal = per_goal
        misses = " / ".join(f"{rates[shot]:4.0%}" for shot in SHOTS)
        print(f"{number} {config.key:<12}{config.ball_speed * speed_scale:>6.0f}{config.balls:>6}   "
              f"{misses:<40}{mixed_per_goal:>10.1f}")


if __name__ == "__main__":
    main()
