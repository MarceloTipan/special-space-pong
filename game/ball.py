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
            speed: Base speed (px/s); a small jitter is applied.
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

        # Vary each ball's speed slightly so they don't move in lockstep
        self.speed = speed * (1 + random.uniform(-self.SPEED_JITTER,
                                                 self.SPEED_JITTER))
        if direction is None:
            direction = random.choice((-1, 1))
        self._launch(direction)

    def _launch(self, direction):
        """Set a random launch angle in the given vertical direction."""
        angle = math.radians(random.uniform(-35, 35))   # from the vertical
        self.vx = self.speed * math.sin(angle)
        self.vy = self.speed * math.cos(angle) * direction

    @property
    def waiting(self):
        """Whether the ball is still waiting to be launched."""
        return self.serve_delay > 0

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

    def time_to_reach_y(self, target_y):
        """Estimated seconds until the ball reaches target_y.

        Returns infinity if it's moving away from it. Used by the AI to
        pick which ball to defend against.
        """
        dy = target_y - self.cy
        if self.vy == 0 or (dy > 0) != (self.vy > 0):
            return float("inf")
        return dy / self.vy

    def bounce_paddle(self, paddle_x, paddle_w, upward, max_bounce_x):
        """Angular bounce based on where the ball hits the paddle.

        Center = vertical, edge = diagonal. Total speed is preserved.
        """
        paddle_center = paddle_x + paddle_w / 2
        hit = (self.cx - paddle_center) / (paddle_w / 2)
        hit = max(-1.0, min(1.0, hit))

        speed = math.hypot(self.vx, self.vy)
        self.vx = speed * hit * max_bounce_x
        vertical = math.sqrt(max(0.0, speed * speed - self.vx * self.vx))
        self.vy = -vertical if upward else vertical