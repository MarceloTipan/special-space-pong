#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""! @brief La clase Credits carga la pantalla de Créditos."""

##
# @file credits_screen.py
#
# @brief Define la clase Credits.
#
# @section description_creditos Descripción
# Muestra los créditos con desplazamiento automático estilo película.
# Los textos provienen del i18n, por lo que se traducen automáticamente.
#
# @section author_creditos Autores
# - Marcelo Tipán
#
# Copyright (c) 2021 Proyecto_Pong.  All rights reserved.

import pygame

from scenes.static_screen import StaticScreen
from utils.i18n import t
from config import FONTS, PATHS, UI, GAME


class Credits(StaticScreen):
    """! Escena de créditos con scroll automático."""

    BACKGROUND_PATH = PATHS.IMAGE_PATH_CREDITS
    STATUS = GAME.STATUS_CREDITS

    ## Velocidad del scroll en píxeles por segundo
    SCROLL_SPEED = 40

    ## Franja vertical donde los créditos son visibles
    BAND_TOP = int(GAME.SCREEN_HEIGHT * 0.18)
    BAND_BOTTOM = int(GAME.SCREEN_HEIGHT * 0.80)
    ## Alto de la zona de desvanecimiento en cada borde de la franja
    FADE_ZONE = 60

    def __init__(self, director):
        super().__init__(director)

        # Fuentes para títulos de sección y nombres
        self.font_title = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.LARGE)
        self.font_name = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.MEDIUM)

        ## Líneas de los créditos: (texto, es_titulo)
        # Vienen del i18n para que se traduzcan solas
        credit_lines = [
            (t("credits.roles.development"), True),
            ("Marcelo Tipan", False),
            ("", False),
            (t("credits.roles.original_team"), True),
            ("Marcelo Tipan", False),
            ("", False),
            (t("credits.roles.thanks"), True),
            (t("credits.thanks_text"), False),
        ]

        ## Superficies pre-renderizadas (renderizar texto es costoso,
        ## se hace UNA vez aquí y no en cada frame)
        self.rendered_lines = []
        for text, is_title in credit_lines:
            if not text:
                self.rendered_lines.append(None)  # línea en blanco
                continue
            font = self.font_title if is_title else self.font_name
            color = UI.COLORS["YELLOW"] if is_title else UI.COLORS["WHITE"]
            self.rendered_lines.append(font.render(text, True, color))

        self.line_spacing = 50
        self.total_height = len(self.rendered_lines) * self.line_spacing

        ## El scroll parte desde abajo de la pantalla
        self.scroll_start = pygame.time.get_ticks()

    def _alpha_at(self, y):
        """! Devuelve la opacidad (0-255) de una línea según su posición.
             Fuera de la franja: invisible. Dentro de la zona de fade:
             interpolación lineal. En el centro: opaca.
             @param y  Posición vertical del centro de la línea.
        """
        if y < self.BAND_TOP or y > self.BAND_BOTTOM:
            return 0
        # Distancia al borde más cercano de la franja
        dist = min(y - self.BAND_TOP, self.BAND_BOTTOM - y)
        if dist >= self.FADE_ZONE:
            return 255
        return int(255 * dist / self.FADE_ZONE)

    def draw_content(self, screen):
        # Desplazamiento basado en tiempo real (independiente de FPS)
        elapsed = (pygame.time.get_ticks() - self.scroll_start) / 1000.0
        offset = elapsed * self.SCROLL_SPEED

        # Cuando todo el bloque salió de la franja, reinicia el ciclo
        band_height = self.BAND_BOTTOM - self.BAND_TOP
        cycle = band_height + self.total_height
        offset %= cycle

        # Las líneas nacen justo debajo de la franja y suben
        y = self.BAND_BOTTOM - offset
        for surface in self.rendered_lines:
            if surface is not None:
                alpha = self._alpha_at(y)
                if alpha > 0:
                    surface.set_alpha(alpha)
                    rect = surface.get_rect(center=(GAME.SCREEN_WIDTH // 2, int(y)))
                    screen.blit(surface, rect)
            y += self.line_spacing