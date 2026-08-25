#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""! @brief La clase Menu muestra la pantalla de Inicio."""

##
# @file menu.py
#
# @brief Define la clase Menu.
#
# @section description_menu Descripción
# Carga la pantalla de inicio, con el fondo y los botones de navegación.
# - Menu (clase)
#
# @section notes_menu Notas
# - Reacciona a eventos de ratón (movimiento y clic) para navegar entre pantallas.
# - Los textos provienen del módulo i18n (locales/*.json).
#
# @section author_menu Autores
# - Marcelo Tipán
#
# Copyright (c) 2021 Proyecto_Pong.  All rights reserved.

import pygame

from core import Scene
from scenes import instruction_screen, credits_screen, loading_screen, settings_screen
from ui import TextButton
from ui.icon_button import IconButton
from config import FONTS, PATHS, UI, GAME
from utils.i18n import t


class Menu(Scene):
    """! Escena inicial del juego, la primera que se carga al iniciar."""

    def __init__(self, director):
        """! Inicializa recursos (fondo, fuente, sonido) y crea los botones.
             @param director  Objeto de la clase Director.
        """
        super().__init__(director)
        director.status = GAME.STATUS_MENU

        # --- Recursos cargados UNA sola vez (no en cada frame) ---
        ## Fondo ya escalado al tamaño de la pantalla
        self.background = pygame.transform.scale(
            pygame.image.load(PATHS.IMAGE_PATH_MENU).convert(),
            GAME.SCREEN_SIZE,
        )

        ## Sonido único del juego, propiedad del Director
        self.audio = director.audio

        font_config = (str(PATHS.FONT_PATH_ARCADE), FONTS.LARGE)

        # --- Definición declarativa de los botones ---
        # (offset vertical, clave de texto i18n, acción, kwargs extra)
        cx = GAME.SCREEN_WIDTH // 2
        cy = GAME.SCREEN_HEIGHT // 2
        ## Solo las acciones primarias como botones grandes
        button_defs = [
            (-20, "menu.start", self._go_to_loading, {"hover_color": UI.COLORS["YELLOW"]}),
            ( 30, "menu.exit",  director.quit,       {}),
        ]

        ## Botones del menú, generados desde button_defs
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

        ## Acciones secundarias: fila de íconos abajo a la derecha
        ## (de izquierda a derecha: como jugar, records, créditos, config)
        icon_defs = [
            ("info",     "ICON_INFO",     self._go_to_instructions),
            ("trophy",   "ICON_TROPHY",   self._go_to_highscores),
            ("question", "ICON_CREDITS",  self._go_to_credits),
            ("gear",     "ICON_SETTINGS", self._go_to_settings),
        ]
        icon_y = GAME.SCREEN_HEIGHT - 45
        icon_x = GAME.SCREEN_WIDTH - 45
        for i, (icon, path_name, action) in enumerate(reversed(icon_defs)):
            self.menu_buttons.append(IconButton(
                pos=(icon_x - i * 62, icon_y),
                action=action,
                size=48,
                icon=icon,
                image_path=getattr(PATHS, path_name, None),
                hover_color=UI.COLORS["YELLOW"],
                audio=self.audio,
            ))

    # ------------------------------------------------------------------
    # Acciones de los botones
    # ------------------------------------------------------------------
    def _go_to_loading(self):
        self.director.change_scene(loading_screen.LoadingScreen(self.director))

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
    # Funciones heredadas de la clase Scene
    # ------------------------------------------------------------------
    def on_update(self):
        pass

    def on_event(self, event):
        """! Solo procesa los eventos relevantes en lugar de hacer polling."""
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            mouse_pos = pygame.mouse.get_pos()
            clicked = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
            for button in self.menu_buttons:
                button.update(mouse_pos, clicked)

    def on_draw(self, screen):
        screen.blit(self.background, (0, 0))
        for button in self.menu_buttons:
            button.draw(screen)