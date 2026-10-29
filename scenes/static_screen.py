"""Base class for static screens (background + buttons).

Shared base for simple screens like Instructions, Credits and High Scores:
loads the background once, manages the buttons, and returns to the menu on
the Back button or the ESC key. Subclasses add content via draw_content.
"""

import pygame

from core import Scene
from ui import TextButton
from utils.i18n import t
from config import FONTS, PATHS, UI, GAME


class StaticScreen(Scene):
    """Screen with a fixed background, buttons and menu return (click or ESC)."""

    BACKGROUND_PATH = None         #: background image path (set by each subclass)
    STATUS = None                  #: director status for this screen (set by subclass)
    BACK_TEXT_KEY = "common.back"  #: i18n key for the Back button

    def __init__(self, director):
        super().__init__(director)
        director.status = self.STATUS

        # Background loaded and scaled once (not every frame)
        self.background = pygame.transform.scale(
            pygame.image.load(self.BACKGROUND_PATH).convert(),
            GAME.SCREEN_SIZE,
        )

        self.audio = director.audio
        self.font_config = (str(PATHS.FONT_PATH_ARCADE), FONTS.LARGE)

        self.buttons = [
            TextButton(
                pos=(GAME.SCREEN_WIDTH // 2, GAME.SCREEN_HEIGHT - 60),
                text=t(self.BACK_TEXT_KEY),
                font_config=self.font_config,
                action=self.go_back,
                hover_color=UI.COLORS["YELLOW"],
                audio=self.audio,
            )
        ]

    def go_back(self):
        """Return to the main menu."""
        # Local import to avoid the menu <-> static_screen cycle
        from scenes import menu
        self.director.change_scene(menu.Menu(self.director))

    # ------------------------------------------------------------------
    # Scene hooks
    # ------------------------------------------------------------------
    def on_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.go_back()
        elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            mouse_pos = pygame.mouse.get_pos()
            clicked = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
            for button in self.buttons:
                button.update(mouse_pos, clicked)

    def on_draw(self, screen):
        screen.blit(self.background, (0, 0))
        self.draw_content(screen)
        for button in self.buttons:
            button.draw(screen)

    def draw_content(self, screen):
        """Extension point: subclasses draw their own content here."""