"""Parallax star field for the game background.

Several star layers at different speeds and sizes create depth: distant
ones move slow and dim, near ones fast and bright. Generated procedurally
(no images to seam-match).
"""

import random

import pygame


class Starfield:
    """Animated, layered star background with a parallax effect."""

    #: Per layer, far to near: (count, speed px/s, radius, brightness).
    LAYERS = [
        (40, 8,  1, 110),
        (30, 18, 1, 170),
        (20, 34, 2, 230),
    ]

    def __init__(self, width, height, seed=None):
        """Create a star field covering width x height (seed for repeatability)."""
        self.width = width
        self.height = height
        # Own generator: visual randomness must not consume the global one
        # the gameplay uses, or the effect would change gameplay outcomes
        self.rng = random.Random(seed)

        # Each layer is a list of [x, y] stars; its speed/radius/color live
        # in self.meta in parallel
        self.layers = []
        self.meta = []
        for count, speed, radius, brightness in self.LAYERS:
            stars = [[self.rng.uniform(0, width), self.rng.uniform(0, height)]
                     for _ in range(count)]
            self.layers.append(stars)
            self.meta.append((speed, radius, (brightness,) * 3))

    def update(self, dt):
        """Scroll stars downward; those leaving the screen wrap to the top."""
        for stars, (speed, _radius, _color) in zip(self.layers, self.meta):
            for star in stars:
                star[1] += speed * dt
                if star[1] > self.height:
                    star[1] -= self.height
                    star[0] = self.rng.uniform(0, self.width)

    def draw(self, screen):
        for stars, (_speed, radius, color) in zip(self.layers, self.meta):
            for x, y in stars:
                if radius <= 1:
                    screen.set_at((int(x), int(y)), color)
                else:
                    pygame.draw.circle(screen, color, (int(x), int(y)), radius)