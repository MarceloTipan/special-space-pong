#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""! @brief La clase Instructions carga la pantalla de Instrucciones."""

##
# @file instruction_screen.py
#
# @brief Define la clase Instructions.
#
# @section description_instrucciones Descripción
# Muestra las instrucciones del juego. Cada línea del i18n se parte
# automáticamente (word-wrap) para caber en el ancho de la pantalla.
#
# @section author_instrucciones Autores
# - Marcelo Tipán
#
# Copyright (c) 2021 Proyecto_Pong.  All rights reserved.

import pygame

from scenes.static_screen import StaticScreen
from utils.i18n import t
from config import FONTS, PATHS, UI, GAME


def wrap_text(text, font, max_width):
    """! Parte un texto en líneas que caben en max_width píxeles.
        @param text       Texto a partir.
        @param font       Fuente con la que se medirá (font.size).
        @param max_width  Ancho máximo por línea, en píxeles.
        @return Lista de líneas.
    """
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if font.size(candidate)[0] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


class Instructions(StaticScreen):
    """! Escena de instrucciones del juego."""

    BACKGROUND_PATH = PATHS.IMAGE_PATH_INSTRUCTIONS
    STATUS = GAME.STATUS_INSTRUCTIONS

    ## Margen lateral del texto como fracción del ancho
    TEXT_MARGIN = 0.08
    LINE_HEIGHT = 45
    ## Espacio extra entre instrucciones distintas
    PARAGRAPH_GAP = 14

    def __init__(self, director):
        super().__init__(director)

        w, h = GAME.SCREEN_WIDTH, GAME.SCREEN_HEIGHT
        cx = w // 2
        max_width = int(w * (1 - 2 * self.TEXT_MARGIN))

        font_title = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.LARGE)
        font_text = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.MEDIUM)

        self.rendered = []

        title = font_title.render(t("instructions.title"), True, UI.COLORS["YELLOW"])
        self.rendered.append((title, title.get_rect(center=(cx, int(h * 0.12)))))

        instruction_keys = [
            "instructions.line_move",
            "instructions.line_goal",
            "instructions.line_lives",
            "instructions.line_back",
        ]

        ## Cada instrucción se parte en las líneas que hagan falta
        y = int(h * 0.24)
        for key in instruction_keys:
            for line in wrap_text(t(key), font_text, max_width):
                surface = font_text.render(line, True, UI.COLORS["WHITE"])
                self.rendered.append((surface, surface.get_rect(center=(cx, y))))
                y += self.LINE_HEIGHT
            y += self.PARAGRAPH_GAP

    def draw_content(self, screen):
        for surface, rect in self.rendered:
            screen.blit(surface, rect)