"""Ball entity: position, velocity and its own bounce physics.

Encapsulating the ball as an object lets several coexist (multiball in
late levels and the bonus stage) without duplicating logic.
"""

import math
import random

import pygame


class Ball:
    """A single ball: position, velocity, trail and bounce handling."""

    #: Speed variation between balls (fraction around the base speed).
    SPEED_JITTER = 0.15

    #: How many past positions are kept to draw the trail.
    TRAIL_LENGTH = 10

    def __init__(self, x, y, width, height, speed, direction=None, serve_delay=0.0):
        """Create a ball.

        Args:
            x, y: Initial top-left position.
            width, height: Sprite size.
            speed: Serve speed (px/s); a small jitter is applied.
            direction: +1 down, -1 up, None for random.
            serve_delay: Seconds the ball waits in place before launching.
        """
        self.x = float(x)
        self.y = float(y)
        self.w = width
        self.h = height
        self.serve_delay = serve_delay

        # Trail history of centers (most recent last)
        self.trail = []

        #: Paddle hits since the serve: the length of the rally.
        self.hits = 0

        # Vary each ball's speed slightly so they don't move in lockstep
        self.base_speed = speed * (1 + random.uniform(-self.SPEED_JITTER,
                                                      self.SPEED_JITTER))
        if direction is None:
            direction = random.choice((-1, 1))
        self._launch(direction)

    def _launch(self, direction):
        """Set a random launch angle in the given vertical direction."""
        angle = math.radians(random.uniform(-35, 35))   # from the vertical
        self.vx = self.base_speed * math.sin(angle)
        self.vy = self.base_speed * math.cos(angle) * direction

    @property
    def waiting(self):
        """Whether the ball is still waiting to be launched."""
        return self.serve_delay > 0

    @property
    def speed(self):
        """Current speed (px/s)."""
        return math.hypot(self.vx, self.vy)

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def move(self, dt):
        """Advance the ball by dt seconds (or count down its serve delay)."""
        if self.serve_delay > 0:
            self.serve_delay = max(0.0, self.serve_delay - dt)
            return
        # Record the current center (for the trail) before moving
        self.trail.append((self.cx, self.cy))
        if len(self.trail) > self.TRAIL_LENGTH:
            self.trail.pop(0)
        self.x += self.vx * dt
        self.y += self.vy * dt

    def accelerate(self, factor, max_speed):
        """Multiply the speed by factor, without going past max_speed.

        The direction is kept; only the magnitude changes.
        """
        speed = self.speed
        if speed == 0:
            return
        scale = min(speed * factor, max(speed, max_speed)) / speed
        self.vx *= scale
        self.vy *= scale

    def bounce_paddle(self, paddle_x, paddle_w, upward, max_bounce_x):
        """Angular bounce based on where the ball hits the paddle.

        Center = vertical, edge = diagonal. Total speed is preserved.

        Returns:
            Where the ball hit, from -1 (left edge) to 1 (right edge).
        """
        paddle_center = paddle_x + paddle_w / 2
        hit = (self.cx - paddle_center) / (paddle_w / 2)
        hit = max(-1.0, min(1.0, hit))

        speed = self.speed
        self.vx = speed * hit * max_bounce_x
        vertical = math.sqrt(max(0.0, speed * speed - self.vx * self.vx))
        self.vy = -vertical if upward else vertical
        self.hits += 1
        return hit
