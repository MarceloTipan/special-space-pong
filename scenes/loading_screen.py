# -*- encoding: utf-8 -*-

"""! @brief La clase LoadingScreen crea una pantalla de carga."""

##
# @file loading_screen.py
#
# @brief Define la clase LoadingScreen.
#
# @section description_carga Descripción
# Muestra una barra de progreso mientras carga los recursos del juego
# (imágenes y cámara) por pasos, un paso por frame, sin congelar la UI.
#
# @section author_carga Autores
# - Marcelo Tipán
#
# Copyright (c) 2021 Proyecto_Pong.  All rights reserved.

import pygame

from core import scene
from game import pong
from config import PATHS, UI, GAME


class LoadingScreen(scene.Scene):
    """! Pantalla de carga con barra de progreso real (pygame 2D)."""

    ## Tiempo mínimo que la pantalla permanece visible, en segundos
    MIN_DURATION = 2.0

    ## Geometría de la barra
    BAR_WIDTH = 500
    BAR_HEIGHT = 14
    BAR_Y = int(GAME.SCREEN_HEIGHT * 0.78)

    def __init__(self, director):
        super().__init__(director)
        director.status = GAME.STATUS_LOADING

        ## Fondo cargado y escalado una sola vez
        self.background = pygame.transform.scale(
            pygame.image.load(PATHS.IMAGE_PATH_LOADING).convert(),
            GAME.SCREEN_SIZE,
        )

        self.progress = 0.0
        self.real_progress = 0.0
        self.loader = None
        self.loaded_scene = None
        self.start_ticks = 0

    def on_enter(self):
        """! Prepara el generador de pasos de carga del juego."""
        self.start_ticks = pygame.time.get_ticks()
        if hasattr(pong.Pong, "load_steps"):
            self.loader = pong.Pong.load_steps(self.director)
        else:
            self.loader = self._single_step_loader()

    def _single_step_loader(self):
        """! Fallback: toda la construcción de Pong como un único paso."""
        yield 0.1
        game_scene = pong.Pong(self.director)
        yield 0.95
        return game_scene

    # ------------------------------------------------------------------
    # Funciones heredadas de la clase Scene
    # ------------------------------------------------------------------
    def on_update(self):
        # Un paso de carga por frame; entre pasos la barra sigue dibujándose
        if self.loaded_scene is None:
            try:
                self.real_progress = next(self.loader)
            except StopIteration as done:
                self.loaded_scene = done.value
                self.real_progress = 1.0

        # Progreso por tiempo: garantiza la duración mínima visible
        elapsed = (pygame.time.get_ticks() - self.start_ticks) / 1000.0
        time_progress = min(elapsed / self.MIN_DURATION, 1.0)

        # La barra nunca supera lo cargado NI el mínimo de tiempo
        self.progress = min(self.real_progress, time_progress)

        if self.loaded_scene is not None and time_progress >= 1.0:
            self.director.change_scene(self.loaded_scene)

    def on_draw(self, screen):
        screen.blit(self.background, (0, 0))

        # Marco de la barra
        bar_x = (GAME.SCREEN_WIDTH - self.BAR_WIDTH) // 2
        frame_rect = pygame.Rect(bar_x, self.BAR_Y, self.BAR_WIDTH, self.BAR_HEIGHT)
        pygame.draw.rect(screen, UI.COLORS["GRAY"], frame_rect, border_radius=4)

        # Relleno según el progreso
        fill_width = int(self.BAR_WIDTH * self.progress)
        if fill_width > 0:
            fill_rect = pygame.Rect(bar_x, self.BAR_Y, fill_width, self.BAR_HEIGHT)
            pygame.draw.rect(screen, UI.COLORS["YELLOW"], fill_rect, border_radius=4)