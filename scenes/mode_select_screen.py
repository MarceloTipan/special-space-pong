"""Game mode selection, shown after Play: campaign or survival.

Each mode is a big button with a line below explaining it. Back (or ESC)
returns to the main menu.
"""

from game.pong import Pong
from game.survival import Survival
from scenes.static_screen import StaticScreen
from scenes import loading_screen
from ui import TextButton
from utils.i18n import t
from utils.text import render_fit
from config import FONTS, PATHS, UI, GAME


class ModeSelect(StaticScreen):
    """Two big buttons, one per game mode."""

    BACKGROUND_PATH = PATHS.IMAGE_PATH_MENU
    STATUS = GAME.STATUS_MENU   # keeps the menu music playing

    TITLE_Y = 0.22      #: rows as a fraction of the screen height
    FIRST_MODE_Y = 0.42
    MODE_SPACING = 0.18
    DESCRIPTION_GAP = 45

    def __init__(self, director):
        super().__init__(director)
        h = GAME.SCREEN_HEIGHT
        cx = GAME.SCREEN_WIDTH // 2
        max_width = int(GAME.SCREEN_WIDTH * 0.9)
        font_path = str(PATHS.FONT_PATH_ARCADE)
        yellow, gray = UI.COLORS["YELLOW"], UI.COLORS["GRAY"]

        self.texts = []
        title = render_fit(font_path, FONTS.LARGE, t("modes.title"), yellow, max_width)
        self.texts.append((title, title.get_rect(center=(cx, int(h * self.TITLE_Y)))))

        modes = (("campaign", Pong), ("survival", Survival))
        for i, (key, scene_class) in enumerate(modes):
            y = int(h * (self.FIRST_MODE_Y + i * self.MODE_SPACING))
            self.buttons.append(TextButton(
                pos=(cx, y), text=t(f"modes.{key}"), font_config=self.font_config,
                action=lambda cls=scene_class: self._play(cls),
                hover_color=yellow, audio=self.audio))
            description = render_fit(font_path, FONTS.SMALL, t(f"modes.{key}_hint"),
                                     gray, max_width)
            self.texts.append(
                (description, description.get_rect(center=(cx, y + self.DESCRIPTION_GAP))))

    def _play(self, scene_class):
        self.director.change_scene(loading_screen.LoadingScreen(self.director, scene_class))

    def draw_content(self, screen):
        for surface, rect in self.texts:
            screen.blit(surface, rect)
