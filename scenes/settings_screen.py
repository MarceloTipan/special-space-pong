"""Settings screen: volume, language, fullscreen, difficulty and controls.

The whole layout is proportional to the resolution: horizontally centered,
with rows placed as fractions of the screen height.
"""

import pygame

from scenes.static_screen import StaticScreen
from ui import TextButton
from ui.slider import Slider
from ui.toggle import Toggle
from utils import settings
from utils.i18n import t, set_language, available_languages, get_language
from config import FONTS, PATHS, UI, GAME


class Settings(StaticScreen):
    """Game settings screen."""

    BACKGROUND_PATH = getattr(PATHS, "IMAGE_PATH_SETTINGS", PATHS.IMAGE_PATH_MENU)
    STATUS = GAME.STATUS_SETTINGS

    DIFFICULTIES = ["easy", "normal", "hard"]
    CONTROLS = ["camera", "mouse", "keyboard"]

    #: Layout rows as a fraction of the screen height.
    ROWS = {
        "title": 0.08,
        "volume": 0.19,
        "lang_label": 0.28, "lang_value": 0.33,
        "fullscreen": 0.42,
        "diff_label": 0.51, "diff_value": 0.56,
        "control_label": 0.65, "control_value": 0.70,
        "camera_invert": 0.79,
    }

    TOGGLE_GAP = 30   #: space between a toggle and its label

    def __init__(self, director):
        super().__init__(director)

        w, h = GAME.SCREEN_WIDTH, GAME.SCREEN_HEIGHT
        self.cx = w // 2
        self.row_y = {name: int(h * frac) for name, frac in self.ROWS.items()}
        self.arrow_dx = max(120, int(w * 0.13))   # arrow offset from the center

        self.font_config = (str(PATHS.FONT_PATH_ARCADE), FONTS.MEDIUM)
        self.font = pygame.font.Font(*self.font_config)
        font_title = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.LARGE)

        white, yellow = UI.COLORS["WHITE"], UI.COLORS["YELLOW"]
        control = settings.get("control")

        # Text drawn every frame: (surface, rect)
        self.texts = []
        self._add_text(font_title.render(t("settings.title"), True, yellow), "title")

        self.volume_slider = Slider(
            pos=(self.cx, self.row_y["volume"]),
            width=min(300, int(w * 0.4)),
            value=settings.get("volume"),
            label=t("settings.volume"),
            font_config=self.font_config,
            track_color=UI.COLORS["GRAY"],
            fill_color=yellow,
            handle_color=white,
            text_color=white,
            on_change=self._apply_volume,
            on_release=self._save_volume,
        )

        self._add_selector("lang_label", "settings.language", "lang_value",
                           t("language_name"), self._change_language)
        self._add_selector("diff_label", "settings.difficulty", "diff_value",
                           t(f"difficulty.{settings.get('difficulty')}"),
                           lambda step: self._cycle("difficulty", self.DIFFICULTIES, step))
        self._add_selector("control_label", "settings.control", "control_value",
                           t(f"control.{control}"),
                           lambda step: self._cycle("control", self.CONTROLS, step))

        self._add_toggle("fullscreen", "settings.fullscreen", "fullscreen",
                         self._toggle_fullscreen)
        # Only relevant (and only shown) when playing with the camera
        if control == "camera":
            self._add_toggle("camera_invert", "settings.camera_invert", "camera_invert",
                             lambda: settings.set("camera_invert",
                                                  not settings.get("camera_invert")))

    # ------------------------------------------------------------------
    # Row builders
    # ------------------------------------------------------------------
    def _add_text(self, surface, row, **anchor):
        """Queue a pre-rendered text, centered on its row unless anchored."""
        anchor = anchor or {"center": (self.cx, self.row_y[row])}
        self.texts.append((surface, surface.get_rect(**anchor)))

    def _add_selector(self, label_row, label_key, value_row, value_text, change):
        """Label on one row, then "< value >" below it.

        Args:
            change: Callback taking -1 (previous) or +1 (next).
        """
        white, yellow = UI.COLORS["WHITE"], UI.COLORS["YELLOW"]
        self._add_text(self.font.render(t(label_key), True, white), label_row)
        self._add_text(self.font.render(value_text, True, yellow), value_row)
        for text, dx, step in (("<", -self.arrow_dx, -1), (">", self.arrow_dx, +1)):
            self.buttons.append(TextButton(
                pos=(self.cx + dx, self.row_y[value_row]), text=text,
                font_config=self.font_config, action=lambda s=step: change(s),
                hover_color=yellow, audio=self.audio))

    def _add_toggle(self, row, label_key, setting_key, action):
        """Label and toggle on the same row, centered together as a group."""
        y = self.row_y[row]
        label = self.font.render(t(label_key), True, UI.COLORS["WHITE"])
        toggle = Toggle(
            pos=(0, y), get_state=lambda: settings.get(setting_key), action=action,
            audio=self.audio, on_text=t("common.on"), off_text=t("common.off"),
            font_path=PATHS.FONT_PATH_ARCADE,
            on_color=UI.COLORS["YELLOW"], off_color=UI.COLORS["GRAY"])

        # The toggle sizes itself to its text, so measure it before centering
        left = self.cx - (label.get_width() + self.TOGGLE_GAP + toggle.rect.width) // 2
        self._add_text(label, row, midleft=(left, y))
        toggle.rect.midleft = (left + label.get_width() + self.TOGGLE_GAP, y)
        self.buttons.append(toggle)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _apply_volume(self, value):
        self.audio.set_volume(value)

    def _save_volume(self, value):
        settings.set("volume", value)
        self.audio.play_hover()

    def _change_language(self, step):
        langs = available_languages()
        idx = (langs.index(get_language()) + step) % len(langs)
        set_language(langs[idx])
        settings.set("language", langs[idx])
        self.director.change_scene(Settings(self.director))

    def _cycle(self, key, options, step):
        """Move a setting to the previous/next option and rebuild the screen."""
        current = settings.get(key)
        idx = options.index(current) if current in options else 0
        settings.set(key, options[(idx + step) % len(options)])
        self.director.change_scene(Settings(self.director))

    def _toggle_fullscreen(self):
        settings.set("fullscreen", not settings.get("fullscreen"))
        # Don't rebuild the scene: the toggle reads the state live, so its
        # knob animates; only re-apply the window config
        self.director._apply_display_config()

    # ------------------------------------------------------------------
    # Scene hooks
    # ------------------------------------------------------------------
    def on_event(self, event):
        super().on_event(event)
        self.volume_slider.handle_event(event)

    def draw_content(self, screen):
        for surface, rect in self.texts:
            screen.blit(surface, rect)
        self.volume_slider.draw(screen)