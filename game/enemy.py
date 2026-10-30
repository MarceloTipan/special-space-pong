"""Enemy paddles: the AI defending the top goal, and the midfield blocker."""

import random
from dataclasses import dataclass

from game import levels


def predict_landing(ball, center_y, left, right):
    """Where and when the ball's center will reach center_y.

    Side-wall bounces are included by unfolding them: the ball travels in a
    straight line through mirrored copies of the field, and the end point
    is folded back into the real one.

    Args:
        ball: The Ball.
        center_y: Height its center must reach.
        left, right: Side walls of the field.

    Returns:
        (x, seconds) of the ball's center at that height, or None if the
        ball isn't moving toward it.
    """
    dy = center_y - ball.cy
    if ball.vy == 0 or (dy > 0) != (ball.vy > 0):
        return None
    time = dy / ball.vy

    lo, hi = left + ball.w / 2, right - ball.w / 2   # range of the center
    span = hi - lo
    if span <= 0:
        return lo, time
    offset = (ball.cx + ball.vx * time - lo) % (2 * span)
    x = lo + (offset if offset <= span else 2 * span - offset)
    return x, time


def shot_difficulty(ball):
    """How hard a shot is to read, from its angle: 0 for a serve or a
    straight shot, 1 for the sharpest edge hit.

    The angle is squared, so slightly angled shots stay easy and only well
    aimed ones (near the paddle's edge) really trouble the enemy.
    """
    if ball.hits == 0 or ball.speed == 0:
        return 0.0   # a serve: nobody aimed it
    angle = min(1.0, abs(ball.vx) / ball.speed / levels.MAX_BOUNCE_X)
    return angle * angle


def rally_share(ball):
    """How far a rally has sped the ball up: 0 at serve speed, 1 at its top."""
    share = (ball.speed / ball.base_speed - 1) / (levels.RALLY_MAX - 1)
    return max(0.0, min(1.0, share))


@dataclass
class _Read:
    """The enemy's read of one incoming shot."""

    chance: float      #: chance it had of misreading the shot
    error: float       #: how far off its guess of the landing point is (px)
    aim: float         #: where on its paddle it means to hit the ball (px from the center)
    late_time: float   #: seconds before impact when it sees the true landing point
    age: float = 0.0   #: seconds since the shot was read


class Enemy:
    """The top paddle's AI: reads each shot, commits to a guess, then corrects.

    Its misses are designed, not noise. When a shot comes in, the enemy reads
    it once: with a chance that grows with the quality of the shot, the read
    is bad. It then moves to its guess of the landing point, and only in the
    last moments sees where the ball really goes and lunges for it. A good
    read is saved, sometimes at the last second; a bad one falls just out of
    reach, so a miss looks like effort, not a paddle parked beside the ball.
    """

    REACTION_TIME = 0.12     #: seconds before it moves after a new shot
    LATE_READ_TIME = 0.30    #: it sees the true landing point this long before impact...
    LATE_READ_SHARE = 0.35   #: ...or during this share of the flight, if shorter
    IDLE_SPEED = 0.5         #: share of its top speed used to drift back to the center
    MAX_MISS = 0.9           #: cap on the miss chance after difficulty scaling
    RALLY_MISS = 0.05        #: extra miss chance at the top speed of a rally
    SAVE_ERROR = 0.85        #: a good read is off by up to this share of its reach
    MISS_MARGIN = (15, 70)   #: a bad read leaves the ball this far out of reach (px)
    AIM_SPREAD = 0.6         #: it returns the ball off-center, up to this share of the half paddle

    def __init__(self, x, face_y, width, left, right, rng=None):
        """Create the enemy.

        Args:
            x: Initial left edge of the paddle.
            face_y: Height of the paddle's face (the side balls hit).
            width: Paddle width.
            left, right: Side walls of the field.
            rng: Random generator (a seeded one makes tests reproducible).
        """
        self.x = x
        self.face_y = face_y
        self.width = width
        self.left, self.right = left, right
        self.rng = rng or random.Random()
        self.speed = 0.0
        self.miss_easy = self.miss_hard = 0.0
        self._reads = {}     # Ball -> _Read, for balls heading toward the enemy
        self._surprise = {}  # Ball -> min miss chance for its next read (see forget)

    def configure(self, speed, miss_easy, miss_hard):
        """Set the skill for a level: top speed (px/s) and miss chances."""
        self.speed = speed
        self.miss_easy = min(self.MAX_MISS, miss_easy)
        self.miss_hard = min(self.MAX_MISS, miss_hard)
        self._reads.clear()
        self._surprise.clear()

    def center_on_field(self):
        self.x = (self.left + self.right - self.width) / 2

    def forget(self, ball):
        """Drop the read of a ball whose course changed unpredictably (an
        asteroid bounce): the enemy will read it again, and react again.

        The new read is never easier than the old one: a deflection can
        surprise the enemy, but can't spoil a well-aimed shot.
        """
        read = self._reads.pop(ball, None)
        if read is not None:
            self._surprise[ball] = max(read.chance, self._surprise.get(ball, 0.0))

    def miss_chance(self, ball):
        """Chance of misreading this shot: from miss_easy (straight) to
        miss_hard (sharpest angle), plus a little more in a fast rally."""
        chance = (self.miss_easy
                  + (self.miss_hard - self.miss_easy) * shot_difficulty(ball)
                  + self.RALLY_MISS * rally_share(ball))
        return min(self.MAX_MISS, chance)

    # ------------------------------------------------------------------
    # Per-frame update
    # ------------------------------------------------------------------
    def update(self, dt, balls):
        """Defend against the ball that will arrive first."""
        for read in self._reads.values():
            read.age += dt

        incoming = {}
        for ball in balls:
            if not ball.waiting:
                landing = predict_landing(ball, self.face_y + ball.h / 2,
                                          self.left, self.right)
                if landing is not None:
                    incoming[ball] = landing
        # Reads of balls no longer coming (returned, scored, removed) expire
        self._reads = {ball: read for ball, read in self._reads.items() if ball in incoming}
        self._surprise = {ball: c for ball, c in self._surprise.items() if ball in incoming}

        if not incoming:
            self._move_toward((self.left + self.right) / 2, self.speed * self.IDLE_SPEED, dt)
            return

        ball = min(incoming, key=lambda b: incoming[b][1])   # soonest, not nearest
        x, time_left = incoming[ball]
        read = self._reads.get(ball)
        if read is None:
            read = self._reads[ball] = self._read(ball, x, time_left)
        if read.age < self.REACTION_TIME:
            return   # still reacting to the shot
        if time_left > read.late_time:
            target = self._guess(x, read.error)
        else:
            # Seen where it really goes: meet it off-center, to send it back at
            # an angle (a dead-center hit would return it straight)
            target = x - read.aim
        self._move_toward(target, self.speed, dt)

    def _read(self, ball, x, time_left):
        """Read a new shot: decide, once, whether the enemy reads it well.

        "Reach" is how far from the landing point its guess can be and still
        be saved: half the paddle and half the ball, plus what it covers in
        the late lunge. A good read lands within reach; a bad one just
        beyond it, on a side of the landing point that fits in the field.
        """
        late = min(self.LATE_READ_TIME, time_left * self.LATE_READ_SHARE)
        reach = (self.width + ball.w) / 2 + self.speed * late
        chance = max(self.miss_chance(ball), self._surprise.pop(ball, 0.0))
        side = self.rng.choice((-1, 1))
        if self.rng.random() < chance:
            error = reach + self.rng.uniform(*self.MISS_MARGIN)
            lo, hi = self._center_range()
            if not lo <= x + side * error <= hi:
                side = -side   # no room on that side: misjudge it the other way
        else:
            error = self.rng.uniform(0, reach * self.SAVE_ERROR)
        aim = self.rng.uniform(-self.AIM_SPREAD, self.AIM_SPREAD) * self.width / 2
        return _Read(chance=chance, error=side * error, aim=aim, late_time=late)

    def _center_range(self):
        """Lowest and highest x the paddle's center can reach."""
        return self.left + self.width / 2, self.right - self.width / 2

    def _guess(self, x, error):
        """The guessed landing point, mirrored if it would fall off the field."""
        lo, hi = self._center_range()
        guess = x + error
        if not lo <= guess <= hi:
            guess = x - error
        return guess

    def _move_toward(self, center_x, speed, dt):
        """Move the paddle's center toward center_x, at most speed * dt."""
        step = center_x - self.width / 2 - self.x
        max_step = speed * dt
        self.x += max(-max_step, min(max_step, step))
        self.x = max(self.left, min(self.right - self.width, self.x))


class Blocker:
    """A second enemy paddle patrolling midfield (the secret level).

    It moves back and forth at a steady speed, so it is fair: the player can
    learn its rhythm and aim around it. Balls bounce off both of its faces.
    """

    def __init__(self, y, width, height, left, right, speed, rng=None):
        rng = rng or random.Random()
        self.y, self.w, self.h = y, width, height
        self.left, self.right = left, right
        self.speed = speed
        self.x = rng.uniform(left, right - width)
        self.direction = rng.choice((-1, 1))

    @property
    def top(self):
        return self.y

    @property
    def bottom(self):
        return self.y + self.h

    def update(self, dt):
        self.x += self.direction * self.speed * dt
        if self.x <= self.left:
            self.x, self.direction = self.left, 1
        elif self.x >= self.right - self.w:
            self.x, self.direction = self.right - self.w, -1
