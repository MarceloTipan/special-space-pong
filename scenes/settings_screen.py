#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""! @brief La clase Settings muestra la pantalla de Configuración."""

##
# @file settings_screen.py
#
# @brief Define la clase Settings.
#
# @section description_settings Descripción
# Volumen (slider), idioma, pantalla completa y dificultad. Todo el
# layout es proporcional a la resolución: centrado horizontal y filas
# como fracciones del alto de pantalla.
#
# @section author_settings Autores
# - Marcelo Tipán
#
# Copyright (c) 2021 Proyecto_Pong.  All rights reserved.

import pygame

from scenes.static_screen import StaticScreen
from ui import TextButton
from ui.slider import Slider
from ui.toggle import Toggle
from utils import settings
from utils.i18n import t, set_language, available_languages, get_language
from config import FONTS, PATHS, UI, GAME


class Settings(StaticScreen):
    """! Escena de configuración del juego."""

    BACKGROUND_PATH = getattr(PATHS, "IMAGE_PATH_SETTINGS", PATHS.IMAGE_PATH_MENU)
    STATUS = GAME.STATUS_SETTINGS

    DIFFICULTIES = ["easy", "normal", "hard"]

    ## Filas del layout como fracción del alto de pantalla
    ROWS = {
        "title": 0.10,
        "volume": 0.23,
        "lang_label": 0.33, "lang_value": 0.39,
        "fullscreen": 0.50,
        "diff_label": 0.60, "diff_value": 0.66,
    }

    def __init__(self, director):
        super().__init__(director)

        w, h = GAME.SCREEN_WIDTH, GAME.SCREEN_HEIGHT
        self.cx = w // 2
        ## y absoluta de cada fila, derivada de las fracciones
        self.row_y = {name: int(h * frac) for name, frac in self.ROWS.items()}
        ## Separación de las flechas < > respecto al centro
        arrow_dx = max(120, int(w * 0.13))

        font_medium = (str(PATHS.FONT_PATH_ARCADE), FONTS.MEDIUM)
        self.font_medium_obj = pygame.font.Font(*font_medium)
        font_title = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.LARGE)

        ## Textos estáticos, TODOS centrados: (superficie, fila)
        white = UI.COLORS["WHITE"]
        self.static_texts = [
            (font_title.render(t("settings.title"), True, UI.COLORS["YELLOW"]), "title"),
            (self.font_medium_obj.render(t("settings.language"), True, white), "lang_label"),
            (self.font_medium_obj.render(t("settings.difficulty"), True, white), "diff_label"),
        ]

        ## --- Volumen: slider centrado (con su etiqueta integrada) ---
        self.volume_slider = Slider(
            pos=(self.cx, self.row_y["volume"]),
            width=min(300, int(w * 0.4)),
            value=settings.get("volume"),
            label=t("settings.volume"),
            font_config=font_medium,
            track_color=UI.COLORS["GRAY"],
            fill_color=UI.COLORS["YELLOW"],
            handle_color=white,
            text_color=white,
            on_change=self._apply_volume,
            on_release=self._save_volume,
        )

        ## --- Selectores con flechas: idioma y dificultad ---
        self._render_language_value()
        self._render_difficulty_value()
        for row, prev_action, next_action in (
                ("lang_value", self._prev_language, self._next_language),
                ("diff_value", self._prev_difficulty, self._next_difficulty)):
            for text, dx, action in (("<", -arrow_dx, prev_action),
                                     (">", arrow_dx, next_action)):
                self.buttons.append(TextButton(
                    pos=(self.cx + dx, self.row_y[row]),
                    text=text, font_config=font_medium, action=action,
                    hover_color=UI.COLORS["YELLOW"], sonido=self.sonido))

        ## --- Pantalla completa: etiqueta + toggle en la misma fila,
        ## centrados como grupo ---
        self.fullscreen_label = self.font_medium_obj.render(
            t("settings.fullscreen"), True, white)
        toggle_w, gap = 72, 30
        group_w = self.fullscreen_label.get_width() + gap + toggle_w
        group_left = self.cx - group_w // 2
        fs_y = self.row_y["fullscreen"]
        self.fullscreen_label_rect = self.fullscreen_label.get_rect(
            midleft=(group_left, fs_y))
        self.buttons.append(Toggle(
            pos=(group_left + self.fullscreen_label.get_width() + gap
                 + toggle_w // 2, fs_y),
            get_state=lambda: settings.get("fullscreen"),
            action=self._toggle_fullscreen,
            sonido=self.sonido,
            width=toggle_w,
            on_text=t("common.on"),
            off_text=t("common.off"),
            font_path=PATHS.FONT_PATH_ARCADE,
            on_color=UI.COLORS["YELLOW"],
            off_color=UI.COLORS["GRAY"]))

    # ------------------------------------------------------------------
    # Volumen
    # ------------------------------------------------------------------
    def _apply_volume(self, value):
        self.sonido.set_volume(value)

    def _save_volume(self, value):
        settings.set("volume", value)
        self.sonido.play_hover()

    # ------------------------------------------------------------------
    # Idioma
    # ------------------------------------------------------------------
    def _render_language_value(self):
        self.language_value = self.font_medium_obj.render(
            t("language_name"), True, UI.COLORS["YELLOW"])

    def _change_language(self, step):
        langs = available_languages()
        idx = (langs.index(get_language()) + step) % len(langs)
        set_language(langs[idx])
        settings.set("language", langs[idx])
        self.director.change_scene(Settings(self.director))

    def _prev_language(self):
        self._change_language(-1)

    def _next_language(self):
        self._change_language(+1)

    # ------------------------------------------------------------------
    # Dificultad
    # ------------------------------------------------------------------
    def _render_difficulty_value(self):
        self.difficulty_value = self.font_medium_obj.render(
            t(f"difficulty.{settings.get('difficulty')}"), True, UI.COLORS["YELLOW"])

    def _change_difficulty(self, step):
        current = settings.get("difficulty")
        idx = (self.DIFFICULTIES.index(current) + step) % len(self.DIFFICULTIES)
        settings.set("difficulty", self.DIFFICULTIES[idx])
        self.director.change_scene(Settings(self.director))

    def _prev_difficulty(self):
        self._change_difficulty(-1)

    def _next_difficulty(self):
        self._change_difficulty(+1)

    # ------------------------------------------------------------------
    # Pantalla completa
    # ------------------------------------------------------------------
    def _toggle_fullscreen(self):
        settings.set("fullscreen", not settings.get("fullscreen"))
        # Sin reconstruir la escena: el toggle lee el estado en vivo y
        # así se ve la animación de la perilla; solo se reaplica la ventana
        self.director._apply_display_config()

    # ------------------------------------------------------------------
    # Funciones heredadas
    # ------------------------------------------------------------------
    def on_event(self, event):
        super().on_event(event)
        self.volume_slider.handle_event(event)

    def draw_content(self, screen):
        for surface, row in self.static_texts:
            screen.blit(surface, surface.get_rect(center=(self.cx, self.row_y[row])))
        self.volume_slider.draw(screen)
        screen.blit(self.fullscreen_label, self.fullscreen_label_rect)
        screen.blit(self.language_value, self.language_value.get_rect(
            center=(self.cx, self.row_y["lang_value"])))
        screen.blit(self.difficulty_value, self.difficulty_value.get_rect(
            center=(self.cx, self.row_y["diff_value"])))