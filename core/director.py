# -*- encoding: utf-8 -*-

"""! @brief La clase Director se encarga del funcionamiento del juego."""

##
# @file director.py
#
# @brief Define la clase Director.
#
# @section description_director Descripción
# Mantiene el bucle principal: actualiza, dibuja y propaga los eventos
# reales de pygame a la escena activa. Todo el juego es pygame 2D.
#
# @section notes_director Notas
# - Mantiene la única instancia de Sonido (director.sonido).
# - Expone director.dt (segundos del último frame) para la física.
# - El estado continuo del teclado se lee en on_update de cada escena.
#
# @section author_director Autores
# - Marcelo Tipán
#
# Copyright (c) 2021 Proyecto_Pong.  All rights reserved.

import pygame
from pygame.locals import DOUBLEBUF, FULLSCREEN, SCALED

from config import GAME, PATHS
from utils import settings
from utils.sonido import Sonido


class Director:
    """! Objeto principal del juego: actualiza, dibuja y propaga eventos."""

    ## Título de la ventana por estado
    CAPTIONS = {
        GAME.STATUS_MENU:         "Pong Menú",
        GAME.STATUS_INSTRUCTIONS: "Pong Instrucciones",
        GAME.STATUS_CREDITS:      "Pong Créditos",
        GAME.STATUS_SETTINGS:     "Pong Configuración",
        GAME.STATUS_LOADING:      "Pong Loading",
        GAME.STATUS_GAME:         "Pong Juego",
        GAME.STATUS_HIGHSCORES:   "Pong Récords",
        GAME.STATUS_NAME_ENTRY:   "Pong Nuevo Récord",
    }

    ## Estados que comparten la música de menú
    MENU_STATUSES = {
        GAME.STATUS_MENU, GAME.STATUS_INSTRUCTIONS,
        GAME.STATUS_CREDITS, GAME.STATUS_SETTINGS,
        GAME.STATUS_HIGHSCORES, GAME.STATUS_NAME_ENTRY,
    }

    def __init__(self):
        """! Inicializa la ventana, el sonido y las variables del bucle."""
        self.SCREEN_SIZE = GAME.SCREEN_SIZE

        icon = pygame.image.load(PATHS.IMAGE_PATH_ICON)
        pygame.display.set_icon(icon)

        self._current_flags = self._compute_flags()
        self.screen = pygame.display.set_mode(self.SCREEN_SIZE, self._current_flags)

        ## Única instancia de Sonido para todo el juego
        self.sonido = Sonido()

        self.scene = None
        self.quit_flag = False
        self.clock = pygame.time.Clock()

        ## Estado actual (lo fija cada escena en su __init__)
        self.status = 0
        ## Segundos transcurridos en el último frame (para la física)
        self.dt = 0.0
        ## Tiempo acumulado en segundos
        self.TIME = 0.0

    # ------------------------------------------------------------------
    # Bucle principal
    # ------------------------------------------------------------------
    def loop(self):
        """! Pone en funcionamiento el juego."""
        while not self.quit_flag:
            self.dt = self.clock.tick(GAME.FPS) / 1000.0
            self.TIME += self.dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                else:
                    self.scene.on_event(event)

            self.scene.on_update()
            self.scene.on_draw(self.screen)

            pygame.display.flip()

    # ------------------------------------------------------------------
    # Cambio de escena
    # ------------------------------------------------------------------
    def change_scene(self, scene):
        """! Altera la escena actual, reconfigura la ventana, ajusta la
             música y carga los recursos de la escena (on_enter)."""
        self.scene = scene
        self._apply_display_config()
        self._update_music()
        scene.on_enter()

    def _compute_flags(self):
        ## SCALED: el juego se programa en la resolución lógica de
        ## GAME.SCREEN_SIZE y pygame escala la ventana para caber en
        ## cualquier monitor (incluido el mouse, traducido solo).
        flags = DOUBLEBUF | SCALED
        if settings.get("fullscreen"):
            flags |= FULLSCREEN
        return flags

    def _apply_display_config(self):
        """! Actualiza el título y recrea la ventana solo si cambió el modo
             (por ejemplo, al alternar pantalla completa)."""
        pygame.display.set_caption(self.CAPTIONS.get(self.status, "Pong"))

        flags = self._compute_flags()
        if flags != self._current_flags:
            # Si lo ÚNICO que cambió es fullscreen, usar la vía nativa:
            # alterna sin recrear la ventana (recrearla con set_mode en
            # Windows la deja mal posicionada / descentrada)
            only_fullscreen = (flags ^ self._current_flags) == FULLSCREEN
            self._current_flags = flags
            if only_fullscreen:
                pygame.display.toggle_fullscreen()
            else:
                self.screen = pygame.display.set_mode(self.SCREEN_SIZE, flags)

    def _update_music(self):
        """! Reproduce la música según el grupo de la escena: una para
             los menús, otra para el juego, silencio (fade) en la carga."""
        if self.status in self.MENU_STATUSES:
            self.sonido.play_music(PATHS.MUSIC_PATH_MENU)
        elif self.status == GAME.STATUS_GAME:
            self.sonido.play_music(PATHS.MUSIC_PATH_GAME)
        else:
            self.sonido.stop_music()

    def quit(self):
        """! Cierra el programa."""
        self.quit_flag = True