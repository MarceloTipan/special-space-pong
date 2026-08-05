#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""! @brief Pantalla con la tabla de mejores puntajes."""

##
# @file highscores_screen.py
#
# @brief Define la clase Highscores.
#
# @section description_highscores Descripción
# Muestra el top 10 de puntajes (iniciales, puntos y nivel alcanzado).
# Puede resaltar una posición (el récord recién ingresado).
#
# @section author_highscores Autores
# - Marcelo Tipán
#
# Copyright (c) 2021 Proyecto_Pong.  All rights reserved.

import pygame

from scenes.static_screen import StaticScreen
from utils import highscores
from utils.i18n import t
from config import FONTS, PATHS, UI, GAME


class Highscores(StaticScreen):
    """! Tabla de récords, con botón VOLVER y ESC heredados."""

    BACKGROUND_PATH = getattr(PATHS, "IMAGE_PATH_HIGHSCORES", PATHS.IMAGE_PATH_MENU)
    STATUS = GAME.STATUS_HIGHSCORES

    ROW_START_Y = 190
    ROW_SPACING = 42

    def __init__(self, director, highlight=0, last_score=None):
        """! @param highlight   Posición (1-10) a resaltar; 0 = ninguna.
             @param last_score  Puntaje de la partida recién jugada que NO
                                entró a la tabla; se muestra debajo del top.
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

        ## Filas pre-renderizadas con columnas alineadas por formato fijo
        for i, entry in enumerate(entries):
            position = i + 1
            row_text = (f"{position:2d}.  {entry['initials']:<3s}   "
                        f"{entry['points']:06d}   "
                        f"{t('highscores.level_short')} {entry['level']:02d}")
            is_highlight = position == self.highlight
            color = UI.COLORS["YELLOW"] if is_highlight else UI.COLORS["WHITE"]
            surface = font_row.render(row_text, True, color)
            y = self.ROW_START_Y + i * self.ROW_SPACING
            self.rendered.append((surface, surface.get_rect(center=(cx, y))))

        ## Puntaje de la partida que no alcanzó la tabla
        if last_score is not None:
            text = t("highscores.your_score", points=last_score)
            surface = font_row.render(text, True, UI.COLORS["GRAY"])
            y = self.ROW_START_Y + (len(entries) + 1) * self.ROW_SPACING
            self.rendered.append((surface, surface.get_rect(center=(cx, y))))

    def draw_content(self, screen):
        for surface, rect in self.rendered:
            screen.blit(surface, rect)