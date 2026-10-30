"""Instructions screen: an animated carousel of how to play.

Five pages (campaign, edge shots, survival, controls, keys), each a small
looping demo drawn with the game's sprites, sliding over a parallax star
field. Pages advance on their own; the player can also use the arrows,
the dots, LEFT/RIGHT or drag them.
"""

import pygame

from game.starfield import Starfield
from scenes.static_screen import StaticScreen
from scenes.instruction_slides import build_pages
from ui.carousel import Carousel
from utils.i18n import t
from config import FONTS, PATHS, UI, GAME


class Instructions(StaticScreen):
    """How to play, as a carousel."""

    BACKGROUND_PATH = PATHS.IMAGE_PATH_INSTRUCTIONS
    STATUS = GAME.STATUS_INSTRUCTIONS

    TITLE_Y = 0.07        #: rows as a fraction of the screen height
    CAROUSEL_TOP = 0.13
    CAROUSEL_BOTTOM = 0.82
    DOTS_Y = 0.86
    SIDE_MARGIN = 0.09    #: leaves room for the < > arrows
    PARALLAX = 0.15       #: how much the stars shift with the pages

    def __init__(self, director):
        super().__init__(director)
        w, h = GAME.SCREEN_WIDTH, GAME.SCREEN_HEIGHT

        font_title = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.LARGE)
        self.title = font_title.render(t("instructions.title"), True, UI.COLORS["YELLOW"])
        self.title_rect = self.title.get_rect(center=(w // 2, int(h * self.TITLE_Y)))

        self.starfield = Starfield(w, h, seed=7)
        margin = int(w * self.SIDE_MARGIN)
        area = pygame.Rect(margin, int(h * self.CAROUSEL_TOP), w - 2 * margin,
                           int(h * (self.CAROUSEL_BOTTOM - self.CAROUSEL_TOP)))
        self.carousel = Carousel(
            build_pages(), area, dots_y=int(h * self.DOTS_Y),
            colors={"active": UI.COLORS["YELLOW"], "idle": (70, 90, 120),
                    "accent": (80, 200, 255)},
            audio=self.audio)

    def on_event(self, event):
        super().on_event(event)
        self.carousel.handle_event(event)

    def on_update(self):
        dt = min(self.director.dt, 0.05)
        self.starfield.update(dt)
        self.carousel.update(dt)

    def draw_content(self, screen):
        self.starfield.draw(screen, shift=self.carousel.offset * self.PARALLAX)
        screen.blit(self.title, self.title_rect)
        self.carousel.draw(screen)
