"""Text button with a hover effect (color change and slight zoom)."""

import pygame

from config import UI


class TextButton:
    """Clickable text label that highlights and grows on hover."""

    def __init__(self, pos, text, font_config, action,
                 base_color=UI.COLORS["GRAY"],
                 hover_color=UI.COLORS["WHITE"],
                 hover_scale=1.1,
                 audio=None):
        """Create a text button.

        Args:
            pos: Center (x, y) of the button.
            text: Button label.
            font_config: (font_path, size) tuple, or a pygame Font object.
            action: Callback run on click.
        """
        self.text = text
        self.action = action
        self.pos = pos
        self.base_color = base_color
        self.hover_color = hover_color
        self.hover_scale = hover_scale
        self.audio = audio

        self.hovered = False
        self._setup_fonts(font_config)
        self._update_surface()

    def _setup_fonts(self, font_config):
        """Build the normal and (larger) hover fonts."""
        if isinstance(font_config, tuple):
            font_path, font_size = font_config
            self.original_font = pygame.font.Font(font_path, font_size)
            self.hover_font = pygame.font.Font(
                font_path, int(font_size * self.hover_scale))
        else:
            # A ready-made Font was passed: no size info, so reuse it for hover
            self.original_font = font_config
            self.hover_font = font_config

    def _update_surface(self):
        font = self.hover_font if self.hovered else self.original_font
        color = self.hover_color if self.hovered else self.base_color
        self.text_surface = font.render(self.text, True, color)
        self.rect = self.text_surface.get_rect(center=self.pos)

    def draw(self, surface):
        surface.blit(self.text_surface, self.rect)

    def update(self, mouse_pos, clicked):
        was_hovered = self.hovered
        self.hovered = self.rect.collidepoint(mouse_pos)

        if self.hovered != was_hovered:   # state changed this frame
            if self.audio:
                self.audio.play_hover()
            self._update_surface()

        if self.hovered and clicked:
            if self.audio:
                self.audio.play_click()
            self.action()

    def set_position(self, pos):
        """Move the button to a new center position."""
        self.pos = pos
        self._update_surface()

    def set_text(self, text):
        """Change the button's label."""
        self.text = text
        self._update_surface()