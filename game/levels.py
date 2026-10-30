"""Campaign balance: every number that shapes a level, in one place.

Tuning the game means editing these tables, not the game code. To see how
a change plays out, run ``python tools/balance_report.py``: it simulates
every level and prints how often the enemy misses and how long goals take.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Level:
    """One level of the campaign.

    Attributes:
        key: Name of the level under "levels." in the locale files.
        ball_speed: Serve speed (px/s). Every hit speeds the ball up from here.
        balls: Balls in play at once.
        obstacles: Asteroids in the field.
        goals: Goals the player needs to win the level.
        enemy_speed: Top speed of the enemy paddle (px/s).
        miss_easy: Chance the enemy misses an easy shot (a serve, or a
            straight return).
        miss_hard: Chance it misses the sharpest edge hit. Shots in between
            are interpolated, and fast rallies add a little (see Enemy).
        blocker_speed: Speed of a second enemy paddle patrolling midfield
            (px/s); 0 for none.
    """

    key: str
    ball_speed: float
    balls: int
    obstacles: int
    goals: int
    enemy_speed: float
    miss_easy: float
    miss_hard: float
    blocker_speed: float = 0


#: The five levels of the campaign. Each one adds something new, and the
#: multiball levels serve slower balls: the challenge there is the count.
CAMPAIGN = (
    Level("warmup", ball_speed=320, balls=1, obstacles=0, goals=3,
          enemy_speed=460, miss_easy=0.08, miss_hard=0.80),
    Level("asteroids", ball_speed=370, balls=1, obstacles=2, goals=3,
          enemy_speed=500, miss_easy=0.07, miss_hard=0.70),
    Level("double", ball_speed=330, balls=2, obstacles=1, goals=3,
          enemy_speed=520, miss_easy=0.04, miss_hard=0.60),
    Level("storm", ball_speed=360, balls=2, obstacles=3, goals=3,
          enemy_speed=550, miss_easy=0.04, miss_hard=0.55),
    Level("chaos", ball_speed=340, balls=3, obstacles=4, goals=5,
          enemy_speed=580, miss_easy=0.03, miss_hard=0.50),
)

#: Unlocked by winning the campaign without retrying any level.
SECRET = Level("secret", ball_speed=380, balls=2, obstacles=0, goals=5,
               enemy_speed=600, miss_easy=0.03, miss_hard=0.50, blocker_speed=230)

SECRET_LEVEL = len(CAMPAIGN) + 1   #: level number of the secret level


def get(number):
    """The Level for a level number (1-based; past the campaign: the secret)."""
    if number > len(CAMPAIGN):
        return SECRET
    return CAMPAIGN[max(1, number) - 1]


@dataclass(frozen=True)
class Difficulty:
    """How a difficulty setting scales the levels.

    Attributes:
        lives: Hearts per level.
        miss_scale: Multiplies how often the enemy misses.
        speed_scale: Multiplies the ball speed.
    """

    lives: int
    miss_scale: float
    speed_scale: float


DIFFICULTIES = {
    "easy": Difficulty(lives=5, miss_scale=1.4, speed_scale=0.9),
    "normal": Difficulty(lives=3, miss_scale=1.0, speed_scale=1.0),
    "hard": Difficulty(lives=2, miss_scale=0.7, speed_scale=1.1),
}

# --- Rules shared by every level ---
MAX_BOUNCE_X = 0.75   #: max horizontal share of a paddle bounce (edge hit)
RALLY_ACCEL = 0.04    #: speed gained on every paddle hit (fraction)
RALLY_MAX = 1.6       #: top speed of a rally, as a multiple of the serve speed
SMASH_FROM = 0.6      #: player hits beyond this share of the half paddle are smashes
SMASH_BOOST = 0.12    #: extra speed of a smash at the very edge (fraction)
