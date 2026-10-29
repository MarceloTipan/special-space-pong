"""Loading screen with a real progress bar.

Consumes the game's step loader (one step per frame) so the bar animates
while resources load — all on the main thread — without freezing the UI.
"""

import pygame

from core import scene
from game import pong
from config import PATHS, UI, GAME


class LoadingScreen(scene.Scene):
    """Loading screen with a time-floored progress bar (2D pygame)."""

    MIN_DURATION = 2.0   #: minimum seconds the screen stays visible

    BAR_WIDTH = 500
    BAR_HEIGHT = 14
    BAR_Y = int(GAME.SCREEN_HEIGHT * 0.78)

    def __init__(self, director):
        super().__init__(director)
        director.status = GAME.STATUS_LOADING

        # Background loaded and scaled once
        self.background = pygame.transform.scale(
            pygame.image.load(PATHS.IMAGE_PATH_LOADING).convert(),
            GAME.SCREEN_SIZE,
        )

        self.progress = 0.0
        self.real_progress = 0.0
        self.loader = None
        self.loaded_scene = None
        self.start_ticks = 0

    def on_enter(self):
        """Prepare the game's step-loader generator."""
        self.start_ticks = pygame.time.get_ticks()
        if hasattr(pong.Pong, "load_steps"):
            self.loader = pong.Pong.load_steps(self.director)
        else:
            self.loader = self._single_step_loader()

    def _single_step_loader(self):
        """Fallback: build Pong in a single step."""
        yield 0.1
        game_scene = pong.Pong(self.director)
        yield 0.95
        return game_scene

    # ------------------------------------------------------------------
    # Scene hooks
    # ------------------------------------------------------------------
    def on_update(self):
        # One load step per frame; the bar keeps drawing between steps
        if self.loaded_scene is None:
            try:
                self.real_progress = next(self.loader)
            except StopIteration as done:
                self.loaded_scene = done.value
                self.real_progress = 1.0

        # Time-based progress guarantees the minimum visible duration
        elapsed = (pygame.time.get_ticks() - self.start_ticks) / 1000.0
        time_progress = min(elapsed / self.MIN_DURATION, 1.0)

        # The bar never exceeds what's loaded NOR the time floor
        self.progress = min(self.real_progress, time_progress)

        if self.loaded_scene is not None and time_progress >= 1.0:
            self.director.change_scene(self.loaded_scene)

    def on_draw(self, screen):
        screen.blit(self.background, (0, 0))

        bar_x = (GAME.SCREEN_WIDTH - self.BAR_WIDTH) // 2
        frame_rect = pygame.Rect(bar_x, self.BAR_Y, self.BAR_WIDTH, self.BAR_HEIGHT)
        pygame.draw.rect(screen, UI.COLORS["GRAY"], frame_rect, border_radius=4)

        fill_width = int(self.BAR_WIDTH * self.progress)
        if fill_width > 0:
            fill_rect = pygame.Rect(bar_x, self.BAR_Y, fill_width, self.BAR_HEIGHT)
            pygame.draw.rect(screen, UI.COLORS["YELLOW"], fill_rect, border_radius=4)