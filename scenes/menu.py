"""Main menu: the first screen shown at startup.

Background plus navigation buttons. The two primary actions (Play, Exit)
are large text buttons; the secondary ones (how to play, credits, high
scores, settings) are a column of icon buttons. All text comes from i18n.
"""

import pygame

from core import Scene
from scenes import instruction_screen, credits_screen, mode_select_screen, settings_screen
from ui import TextButton
from ui.icon_button import IconButton
from config import FONTS, PATHS, UI, GAME
from utils.i18n import t


class Menu(Scene):
    """Initial game scene, loaded first on startup."""

    def __init__(self, director):
        super().__init__(director)
        director.status = GAME.STATUS_MENU

        # Background loaded and scaled once (not every frame)
        self.background = pygame.transform.scale(
            pygame.image.load(PATHS.IMAGE_PATH_MENU).convert(),
            GAME.SCREEN_SIZE,
        )

        self.audio = director.audio
        font_config = (str(PATHS.FONT_PATH_ARCADE), FONTS.LARGE)

        # Primary actions as large buttons: (vertical offset, i18n key, action, extra kwargs)
        cx = GAME.SCREEN_WIDTH // 2
        cy = GAME.SCREEN_HEIGHT // 2
        button_defs = [
            (-20, "menu.start", self._go_to_mode_select, {"hover_color": UI.COLORS["YELLOW"]}),
            (30, "menu.exit", director.quit, {}),
        ]
        self.menu_buttons = [
            TextButton(
                pos=(cx, cy + offset),
                text=t(text_key),
                font_config=font_config,
                action=action,
                audio=self.audio,
                **extra,
            )
            for offset, text_key, action, extra in button_defs
        ]

        # Secondary actions: column of icons at the bottom-right
        icon_defs = [
            ("info", "ICON_INFO", self._go_to_instructions),
            ("question", "ICON_CREDITS", self._go_to_credits),
            ("trophy", "ICON_TROPHY", self._go_to_highscores),
            ("gear", "ICON_SETTINGS", self._go_to_settings),
        ]
        icon_x = GAME.SCREEN_WIDTH - 45
        icon_y = GAME.SCREEN_HEIGHT - 45
        icon_spacing = 45
        for i, (icon, path_name, action) in enumerate(reversed(icon_defs)):
            self.menu_buttons.append(IconButton(
                pos=(icon_x, icon_y - i * icon_spacing),
                action=action,
                size=35,
                icon=icon,
                image_path=getattr(PATHS, path_name, None),
                hover_color=UI.COLORS["YELLOW"],
                audio=self.audio,
            ))

    # ------------------------------------------------------------------
    # Button actions
    # ------------------------------------------------------------------
    def _go_to_mode_select(self):
        self.director.change_scene(mode_select_screen.ModeSelect(self.director))

    def _go_to_instructions(self):
        self.director.change_scene(instruction_screen.Instructions(self.director))

    def _go_to_credits(self):
        self.director.change_scene(credits_screen.Credits(self.director))

    def _go_to_settings(self):
        self.director.change_scene(settings_screen.Settings(self.director))

    def _go_to_highscores(self):
        from scenes import highscores_screen
        self.director.change_scene(highscores_screen.Highscores(self.director))

    # ------------------------------------------------------------------
    # Scene hooks
    # ------------------------------------------------------------------
    def on_event(self, event):
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            mouse_pos = pygame.mouse.get_pos()
            clicked = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
            for button in self.menu_buttons:
                button.update(mouse_pos, clicked)

    def on_draw(self, screen):
        screen.blit(self.background, (0, 0))
        for button in self.menu_buttons:
            button.draw(screen)
