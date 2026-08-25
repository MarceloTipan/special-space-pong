#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""! @brief Clase base para pantallas estáticas (fondo + botones)."""

##
# @file static_screen.py
#
# @brief Define la clase StaticScreen.
#
# @section description_static Descripción
# Base compartida para pantallas simples como Instrucciones y Créditos:
# carga el fondo una sola vez, gestiona los botones y permite volver
# al menú con el botón o con la tecla ESC.
#
# @section author_static Autores
# - Marcelo Tipán
#
# Copyright (c) 2021 Proyecto_Pong.  All rights reserved.

import pygame

from core import Scene
from ui import TextButton
from utils.i18n import t
from config import FONTS, PATHS, UI, GAME


class StaticScreen(Scene):
    """! Pantalla con fondo fijo, botones y regreso al menú (clic o ESC)."""

    ## Ruta de la imagen de fondo (la define cada subclase)
    BACKGROUND_PATH = None
    ## Estado del director asociado a la pantalla (lo define cada subclase)
    STATUS = None
    ## Clave i18n del botón de volver
    BACK_TEXT_KEY = "common.back"

    def __init__(self, director):
        """! Carga fondo, fuente y botón de volver.
             @param director  Objeto de la clase Director.
        """
        super().__init__(director)
        director.status = self.STATUS

        ## Fondo cargado y escalado UNA sola vez
        self.background = pygame.transform.scale(
            pygame.image.load(self.BACKGROUND_PATH).convert(),
            GAME.SCREEN_SIZE,
        )

        ## Sonido único del juego, propiedad del Director
        self.audio = director.audio
        self.font_config = (str(PATHS.FONT_PATH_ARCADE), FONTS.LARGE)

        ## Botón de volver, con la misma fuente arcade del menú
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
        """! Regresa al menú principal."""
        # Import local para evitar el ciclo menu <-> static_screen
        from scenes import menu
        self.director.change_scene(menu.Menu(self.director))

    # ------------------------------------------------------------------
    # Funciones heredadas de la clase Scene
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
        """! Punto de extensión: las subclases dibujan aquí su contenido
             (texto de instrucciones, créditos con scroll, etc.)."""
        pass