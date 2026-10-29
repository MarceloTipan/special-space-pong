"""Game obstacle: a rectangular hitbox with an asteroid sprite on top.

Collision uses the Rect (predictable physics), but the sprite is drawn
over it, slightly larger and slowly spinning, so it looks organic.
Rotations are pre-computed once (caching beats rotating every frame).
"""

import pygame


class Obstacle:
    """Asteroid: a collision rectangle with a spinning sprite on top."""

    #: Pre-rendered rotation frames (one every 360/N degrees).
    ROTATION_STEPS = 36

    #: The sprite is drawn larger than the hitbox so its jagged edges stick
    #: out and the bounce never looks like it happens early.
    SPRITE_SCALE = 1.35

    #: Cache of pre-rotated sprites, shared by all asteroids using the same
    #: base image: {(image_id, size): [frames...]}.
    _rotation_cache = {}

    def __init__(self, rect, base_image, spin_speed=20, angle_offset=0):
        """Create an obstacle.

        Args:
            rect: pygame.Rect used for collision.
            base_image: Asteroid surface (with alpha), or None to draw a block.
            spin_speed: Spin rate in degrees per second.
            angle_offset: Starting angle, so they don't all spin in sync.
        """
        self.rect = rect
        self.spin_speed = spin_speed
        self.angle = angle_offset

        # No sprite: skip pre-rotation (the scene draws it as a neon block)
        if base_image is None:
            self.frames = None
            return

        sprite_size = int(max(rect.width, rect.height) * self.SPRITE_SCALE)
        self.frames = self._get_frames(base_image, sprite_size)

    @classmethod
    def _get_frames(cls, base_image, size):
        """Return (and cache) the list of pre-rotated sprites at 'size'."""
        key = (id(base_image), size)
        if key not in cls._rotation_cache:
            scaled = pygame.transform.smoothscale(base_image, (size, size))
            frames = [
                pygame.transform.rotozoom(scaled, i * (360 / cls.ROTATION_STEPS), 1.0)
                for i in range(cls.ROTATION_STEPS)
            ]
            cls._rotation_cache[key] = frames
        return cls._rotation_cache[key]

    def update(self, dt):
        self.angle = (self.angle + self.spin_speed * dt) % 360

    def draw(self, screen):
        if self.frames is None:
            return   # no sprite: the scene's neon fallback draws it
        index = int(self.angle / (360 / self.ROTATION_STEPS)) % self.ROTATION_STEPS
        frame = self.frames[index]
        screen.blit(frame, frame.get_rect(center=self.rect.center))

    # ------------------------------------------------------------------
    # Rect-like interface, so collision code can treat it as its hitbox
    # ------------------------------------------------------------------
    def colliderect(self, other):
        return self.rect.colliderect(other)

    def inflate(self, x, y):
        return self.rect.inflate(x, y)

    @property
    def left(self):
        return self.rect.left

    @property
    def right(self):
        return self.rect.right

    @property
    def top(self):
        return self.rect.top

    @property
    def bottom(self):
        return self.rect.bottom

    @property
    def centerx(self):
        return self.rect.centerx

    @property
    def centery(self):
        return self.rect.centery