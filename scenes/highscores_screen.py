"""High scores table screen.

Shows the top scores (initials, points and level reached). Can highlight a
position (the record just entered) or show a non-qualifying score below.
"""

import pygame

from scenes.static_screen import StaticScreen
from utils import highscores
from utils.i18n import t
from config import FONTS, PATHS, UI, GAME


class Highscores(StaticScreen):
    """Records table, inheriting the Back button and ESC return."""

    BACKGROUND_PATH = getattr(PATHS, "IMAGE_PATH_HIGHSCORES", PATHS.IMAGE_PATH_MENU)
    STATUS = GAME.STATUS_HIGHSCORES

    ROW_START_Y = 190
    ROW_SPACING = 42

    def __init__(self, director, highlight=0, last_score=None):
        """Build the records screen.

        Args:
            highlight: Position (1-based) to highlight; 0 for none.
            last_score: Score from the game just played that did NOT make
                the table; shown below the top if given.
        """
        super().__init__(director)
        self.highlight = highlight

        font_title = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.LARGE)
        font_row = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.MEDIUM)

        cx = GAME.SCREEN_WIDTH // 2
        self.rendered = []

        title = font_title.render(t("highscores.title"), True, UI.COLORS["YELLOW"])
        self.rendered.append((title, title.get_rect(center=(cx, 110))))

        entries = highscores.get_all()
        if not entries:
            empty = font_row.render(t("highscores.empty"), True, UI.COLORS["GRAY"])
            self.rendered.append(
                (empty, empty.get_rect(center=(cx, GAME.SCREEN_HEIGHT // 2))))
            return

        # Rows pre-rendered, columns aligned by fixed-width formatting
        for i, entry in enumerate(entries):
            position = i + 1
            row_text = (f"{position:2d}.  {entry['initials']:<3s}   "
                        f"{entry['points']:06d}   "
                        f"{t('highscores.level_short')} {entry['level']:02d}")
            color = UI.COLORS["YELLOW"] if position == self.highlight else UI.COLORS["WHITE"]
            surface = font_row.render(row_text, True, color)
            y = self.ROW_START_Y + i * self.ROW_SPACING
            self.rendered.append((surface, surface.get_rect(center=(cx, y))))

        # Score from the game that didn't make the table
        if last_score is not None:
            text = t("highscores.your_score", points=last_score)
            surface = font_row.render(text, True, UI.COLORS["GRAY"])
            y = self.ROW_START_Y + (len(entries) + 1) * self.ROW_SPACING
            self.rendered.append((surface, surface.get_rect(center=(cx, y))))

    def draw_content(self, screen):
        for surface, rect in self.rendered:
            screen.blit(surface, rect)