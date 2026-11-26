"""Initials entry screen, shown when the player earns a record.

Classic arcade 3-initial selector: UP/DOWN change the active letter,
LEFT/RIGHT change position, typing a letter also works, and ENTER saves
the record. Every action also has an on-screen control (arrows above and
below each letter, tap a letter to select it, and a Save button), so it
works with a mouse or a touch screen, where there is no keyboard.
"""

import string

import pygame

from core import scene
from ui import TextButton
from utils import highscores
from utils.i18n import t
from utils.text import render_fit
from config import FONTS, PATHS, UI, GAME

ALPHABET = string.ascii_uppercase


class NameEntry(scene.Scene):
    """Three-initial selector for saving a record."""

    LETTER_SPACING = 120
    BLINK_MS = 400        #: active-letter cursor blink (ms)
    ARROW_GAP = 85        #: distance from a letter's center to its arrows
    ARROW_SIZE = (80, 56)  #: touch area of each arrow (big enough for a finger)

    def __init__(self, director, points, mode, **details):
        """Build the entry screen.

        Args:
            points: Score achieved in the game.
            mode: High score table to save it in (see utils.highscores).
            **details: How far the player got (level=... or seconds=...).
        """
        super().__init__(director)
        director.status = GAME.STATUS_NAME_ENTRY

        self.points = points
        self.mode = mode
        self.details = details

        self.background = pygame.transform.scale(
            pygame.image.load(PATHS.IMAGE_PATH_MENU).convert(),
            GAME.SCREEN_SIZE,
        )

        # Selector state: indices into ALPHABET and the active position
        self.letters = [0, 0, 0]     # "AAA"
        self.active = 0

        self.font_letters = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.LARGE * 2)
        font_medium = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.MEDIUM)

        cx = GAME.SCREEN_WIDTH // 2
        self.cx = cx
        self.letters_y = GAME.SCREEN_HEIGHT // 2

        max_width = int(GAME.SCREEN_WIDTH * 0.9)   # long texts shrink to fit
        self.title = render_fit(PATHS.FONT_PATH_ARCADE, FONTS.LARGE * 2, t("name_entry.title"),
                                UI.COLORS["YELLOW"], max_width)
        self.title_rect = self.title.get_rect(center=(cx, 140))

        self.score = font_medium.render(
            t("name_entry.score", points=self.points), True, UI.COLORS["WHITE"])
        self.score_rect = self.score.get_rect(center=(cx, 220))

        self.hint = render_fit(PATHS.FONT_PATH_ARCADE, FONTS.MEDIUM, t("name_entry.hint"),
                               UI.COLORS["GRAY"], max_width)
        self.hint_rect = self.hint.get_rect(center=(cx, GAME.SCREEN_HEIGHT - 80))

        # On-screen controls: an arrow above (+1) and below (-1) each letter
        self.arrows = []   # (rect, position, step)
        for i in range(3):
            x = self._letter_x(i)
            for step, dy in ((+1, -self.ARROW_GAP), (-1, self.ARROW_GAP)):
                rect = pygame.Rect((0, 0), self.ARROW_SIZE)
                rect.center = (x, self.letters_y + dy)
                self.arrows.append((rect, i, step))
        self.save_button = TextButton(
            pos=(cx, self.letters_y + 200), text=t("name_entry.save"),
            font_config=(str(PATHS.FONT_PATH_ARCADE), FONTS.LARGE),
            action=self._confirm, hover_color=UI.COLORS["YELLOW"],
            audio=director.audio)

    def _letter_x(self, position):
        return self.cx + (position - 1) * self.LETTER_SPACING

    def _change_letter(self, position, step):
        self.active = position
        self.letters[position] = (self.letters[position] + step) % len(ALPHABET)
        self.director.audio.play_hover()

    def _initials(self):
        return "".join(ALPHABET[i] for i in self.letters)

    def _confirm(self):
        """Save the record and go to the table, highlighting the position."""
        position = highscores.add(self._initials(), self.points, self.mode, **self.details)
        self.director.audio.play_click()
        from scenes import highscores_screen
        self.director.change_scene(
            highscores_screen.Highscores(self.director, mode=self.mode, highlight=position))

    # ------------------------------------------------------------------
    # Scene hooks
    # ------------------------------------------------------------------
    def on_event(self, event):
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            self._on_pointer(event)
            return
        if event.type != pygame.KEYDOWN:
            return

        audio = self.director.audio
        if event.key in (pygame.K_UP, pygame.K_w):
            self.letters[self.active] = (self.letters[self.active] + 1) % 26
            audio.play_hover()
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.letters[self.active] = (self.letters[self.active] - 1) % 26
            audio.play_hover()
        elif event.key in (pygame.K_RIGHT, pygame.K_TAB):
            self.active = (self.active + 1) % 3
            audio.play_hover()
        elif event.key in (pygame.K_LEFT, pygame.K_BACKSPACE):
            self.active = (self.active - 1) % 3
            audio.play_hover()
        elif event.key == pygame.K_RETURN:
            self._confirm()
        elif event.unicode and event.unicode.upper() in ALPHABET:
            # Direct typing: set the letter and advance position
            self.letters[self.active] = ALPHABET.index(event.unicode.upper())
            self.active = min(self.active + 1, 2)
            audio.play_hover()

    def _on_pointer(self, event):
        """Mouse or touch (browsers turn taps into mouse clicks)."""
        clicked = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
        self.save_button.update(event.pos, clicked)
        if not clicked:
            return
        for rect, position, step in self.arrows:
            if rect.collidepoint(event.pos):
                self._change_letter(position, step)
                return
        for i in range(3):   # tapping a letter selects it
            letter = pygame.Rect(0, 0, self.LETTER_SPACING - 10, 100)
            letter.center = (self._letter_x(i), self.letters_y)
            if letter.collidepoint(event.pos):
                self.active = i
                self.director.audio.play_hover()
                return

    def on_draw(self, screen):
        screen.blit(self.background, (0, 0))
        screen.blit(self.title, self.title_rect)
        screen.blit(self.score, self.score_rect)
        screen.blit(self.hint, self.hint_rect)

        # The three letters, with the active one blinking in yellow
        blink_on = (pygame.time.get_ticks() // self.BLINK_MS) % 2 == 0
        for rect, position, step in self.arrows:
            color = UI.COLORS["YELLOW"] if position == self.active else UI.COLORS["GRAY"]
            cx, cy = rect.center
            half = 22 * step   # points up for +1, down for -1
            pygame.draw.polygon(screen, color, [(cx - 26, cy + half // 2),
                                                (cx + 26, cy + half // 2), (cx, cy - half)])
        self.save_button.draw(screen)

        for i, letter_index in enumerate(self.letters):
            is_active = i == self.active
            color = UI.COLORS["YELLOW"] if is_active else UI.COLORS["WHITE"]
            surface = self.font_letters.render(ALPHABET[letter_index], True, color)
            x = self._letter_x(i)
            screen.blit(surface, surface.get_rect(center=(x, self.letters_y)))

            # Blinking underline cursor under the active position
            if is_active and blink_on:
                underline = pygame.Rect(0, 0, 50, 6)
                underline.center = (x, self.letters_y + 45)
                pygame.draw.rect(screen, UI.COLORS["YELLOW"], underline)
