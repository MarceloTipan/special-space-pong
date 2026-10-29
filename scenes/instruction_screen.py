"""Instructions screen.

Shows the game instructions. Each i18n line is word-wrapped automatically
to fit the screen width.
"""

import pygame

from scenes.static_screen import StaticScreen
from utils.i18n import t
from utils.text import wrap_text
from config import FONTS, PATHS, UI, GAME


class Instructions(StaticScreen):
    """Game instructions screen."""

    BACKGROUND_PATH = PATHS.IMAGE_PATH_INSTRUCTIONS
    STATUS = GAME.STATUS_INSTRUCTIONS

    TEXT_MARGIN = 0.08   #: side margin as a fraction of the width
    LINE_HEIGHT = 45
    PARAGRAPH_GAP = 14   #: extra space between separate instructions

    def __init__(self, director):
        super().__init__(director)

        w, h = GAME.SCREEN_WIDTH, GAME.SCREEN_HEIGHT
        cx = w // 2
        max_width = int(w * (1 - 2 * self.TEXT_MARGIN))

        font_title = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.LARGE)
        font_text = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.MEDIUM)

        self.rendered = []

        title = font_title.render(t("instructions.title"), True, UI.COLORS["YELLOW"])
        self.rendered.append((title, title.get_rect(center=(cx, int(h * 0.12)))))

        instruction_keys = [
            "instructions.line_move",
            "instructions.line_goal",
            "instructions.line_lives",
            "instructions.line_back",
        ]

        # Each instruction is wrapped into as many lines as needed
        y = int(h * 0.24)
        for key in instruction_keys:
            for line in wrap_text(t(key), font_text, max_width):
                surface = font_text.render(line, True, UI.COLORS["WHITE"])
                self.rendered.append((surface, surface.get_rect(center=(cx, y))))
                y += self.LINE_HEIGHT
            y += self.PARAGRAPH_GAP

    def draw_content(self, screen):
        for surface, rect in self.rendered:
            screen.blit(surface, rect)