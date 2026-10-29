"""Pause/resume button with a drawn icon (pause bars or a play triangle)."""

import pygame

from config import UI


class PauseButton:
    """Square button whose icon reflects the pause state.

    Same update/draw interface as the other ui components, so it can live in
    the same button list.
    """

    def __init__(self, pos, size, action, is_paused, audio=None):
        """Create a pause button.

        Args:
            pos: Center (x, y) of the button.
            size: Side of the square, in pixels.
            action: Callback run on click.
            is_paused: Callable returning whether the game is paused; picks
                the icon (play triangle while paused, pause bars otherwise).
        """
        self.rect = pygame.Rect(0, 0, size, size)
        self.rect.center = pos
        self.action = action
        self.is_paused = is_paused
        self.audio = audio
        self.hovered = False

    def update(self, mouse_pos, clicked):
        was_hovered = self.hovered
        self.hovered = self.rect.collidepoint(mouse_pos)
        if self.hovered and not was_hovered and self.audio:
            self.audio.play_hover()
        if self.hovered and clicked:
            if self.audio:
                self.audio.play_click()
            self.action()

    def draw(self, screen):
        color = UI.COLORS["WHITE"] if self.hovered else UI.COLORS["YELLOW"]
        pygame.draw.rect(screen, color, self.rect, width=3, border_radius=4)
        cx, cy = self.rect.center
        s = self.rect.width // 4
        if self.is_paused():
            pygame.draw.polygon(screen, color, [
                (cx - s + 2, cy - s), (cx - s + 2, cy + s), (cx + s, cy)])
        else:
            pygame.draw.rect(screen, color, (cx - s, cy - s, s - 2, 2 * s))
            pygame.draw.rect(screen, color, (cx + 2, cy - s, s - 2, 2 * s))