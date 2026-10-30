"""High scores screen: one table per game mode, chosen with tabs.

Shows the top scores (initials, points and how far the player got: level
reached or time survived). Can highlight a position (the record just
entered) or show a non-qualifying score below.
"""

import pygame

from scenes.static_screen import StaticScreen
from ui import TextButton
from utils import highscores
from utils.i18n import t
from config import FONTS, PATHS, UI, GAME


def format_time(seconds):
    """Seconds as MM:SS."""
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


class Highscores(StaticScreen):
    """Records tables, inheriting the Back button and ESC return."""

    BACKGROUND_PATH = getattr(PATHS, "IMAGE_PATH_HIGHSCORES", PATHS.IMAGE_PATH_MENU)
    STATUS = GAME.STATUS_HIGHSCORES

    TITLE_Y = 110
    TABS_Y = 170
    ROW_START_Y = 240
    ROW_SPACING = 42

    def __init__(self, director, mode=highscores.CAMPAIGN, highlight=0, last_score=None):
        """Build the records screen.

        Args:
            mode: Which table to show first (see utils.highscores).
            highlight: Position (1-based) to highlight; 0 for none.
            last_score: Score from the game just played that did NOT make
                the table; shown below the top if given.
        """
        super().__init__(director)
        self.mode = mode
        self.highlight = highlight

        font_title = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.LARGE)
        font_row = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.MEDIUM)
        white, yellow, gray = UI.COLORS["WHITE"], UI.COLORS["YELLOW"], UI.COLORS["GRAY"]

        cx = GAME.SCREEN_WIDTH // 2
        self.rendered = []

        title = font_title.render(t("highscores.title"), True, yellow)
        self.rendered.append((title, title.get_rect(center=(cx, self.TITLE_Y))))

        # Tabs: the active mode in yellow, the other one a button to switch
        tab_dx = GAME.SCREEN_WIDTH // 4
        for mode_key, x in ((highscores.CAMPAIGN, cx - tab_dx), (highscores.SURVIVAL, cx + tab_dx)):
            self.buttons.append(TextButton(
                pos=(x, self.TABS_Y), text=t(f"modes.{mode_key}"),
                font_config=(str(PATHS.FONT_PATH_ARCADE), FONTS.MEDIUM),
                action=lambda m=mode_key: self._show(m),
                base_color=yellow if mode_key == mode else gray,
                hover_color=yellow, audio=self.audio))

        entries = highscores.get_all(mode)
        if not entries:
            empty = font_row.render(t("highscores.empty"), True, gray)
            self.rendered.append(
                (empty, empty.get_rect(center=(cx, GAME.SCREEN_HEIGHT // 2))))
        else:
            # Rows pre-rendered, columns aligned by fixed-width formatting
            for i, entry in enumerate(entries):
                position = i + 1
                row_text = (f"{position:2d}.  {entry['initials']:<3s}   "
                            f"{entry['points']:06d}   {self._progress(entry)}")
                color = yellow if position == self.highlight else white
                surface = font_row.render(row_text, True, color)
                y = self.ROW_START_Y + i * self.ROW_SPACING
                self.rendered.append((surface, surface.get_rect(center=(cx, y))))

        # Score from the game that didn't make the table
        if last_score is not None:
            text = t("highscores.your_score", points=last_score)
            surface = font_row.render(text, True, gray)
            y = self.ROW_START_Y + (max(1, len(entries)) + 1) * self.ROW_SPACING
            self.rendered.append((surface, surface.get_rect(center=(cx, y))))

    def _progress(self, entry):
        """How far that player got: level reached or time survived."""
        if self.mode == highscores.SURVIVAL:
            return format_time(entry.get("seconds", 0))
        return f"{t('highscores.level_short')} {entry.get('level', 0):02d}"

    def _show(self, mode):
        if mode != self.mode:
            self.director.change_scene(Highscores(self.director, mode=mode))

    def on_event(self, event):
        super().on_event(event)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            other = [m for m in highscores.MODES if m != self.mode][0]
            self.audio.play_hover()
            self._show(other)

    def draw_content(self, screen):
        for surface, rect in self.rendered:
            screen.blit(surface, rect)
