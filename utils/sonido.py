#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""! @brief La clase Sonido reproduce los audios del juego."""

##
# @file sonido.py
#
# @brief Define la clase Sonido.
#
# @section description_sonido Descripción
# Controla los efectos de sonido (diccionario de pygame.mixer.Sound) y la
# música de fondo (canal mixer.music, exclusivo para eso). Existe UNA sola
# instancia, creada por el Director; las escenas la usan vía director.sonido.
#
# @section notes_sonido Notas
# - Para agregar un efecto nuevo: una línea en EFFECTS y su ruta en PATHS.
#
# @section author_sonido Autores
# - Marcelo Tipán
#
# Copyright (c) 2021 Proyecto_Pong.  All rights reserved.

import pygame

from config import PATHS
from utils import settings


class Sonido:
    """! Control del sonido del juego (una sola instancia, en el Director)."""

    ## Efectos disponibles: nombre -> ruta del archivo.
    ## Agregar aquí cualquier efecto nuevo.
    EFFECTS = {
        "click":        PATHS.SOUND_PATH_CLIC,
        "hover":        PATHS.SOUND_PATH_HOVER,
        "hit":          PATHS.SOUND_PATH_HIT,           # raqueta jugador / paredes
        "hit_enemy":    PATHS.SOUND_PATH_HIT_ENEMY,     # raqueta enemiga
        "hit_obstacle": PATHS.SOUND_PATH_HIT_OBSTACLE,  # obstáculos
        "error":        PATHS.SOUND_PATH_ERROR,         # punto perdido
    }

    def __init__(self):
        """! Carga los efectos una sola vez y aplica el volumen guardado."""
        self.sounds = {
            name: pygame.mixer.Sound(str(path))
            for name, path in self.EFFECTS.items()
        }

        ## Ruta de la música que está sonando (evita reiniciarla)
        self.current_music = None

        self.volumen = 1.0
        self.set_volume(settings.get("volume"))

    def set_volume(self, volume):
        """! Establece el volumen de la música y de todos los efectos.
             @param volume  Volumen entre 0.0 y 1.0.
        """
        self.volumen = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.volumen)
        for sound in self.sounds.values():
            sound.set_volume(self.volumen)

    # ------------------------------------------------------------------
    # Efectos
    # ------------------------------------------------------------------
    def play(self, name):
        """! Reproduce un efecto por su nombre (clave de EFFECTS)."""
        self.sounds[name].play()

    ## Alias de compatibilidad usados por los botones y escenas
    def play_click(self):
        self.play("click")

    def play_hover(self):
        self.play("hover")

    def start_golpe(self):
        self.play("hit")

    def start_error(self):
        self.play("error")

    # ------------------------------------------------------------------
    # Música de fondo (canal mixer.music, exclusivo para esto)
    # ------------------------------------------------------------------
    def play_music(self, path, fade_ms=1000):
        """! Reproduce música de fondo en bucle con fade in. Si esa música
             ya está sonando, no hace nada (no se corta al navegar).
             @param path     Ruta del archivo (usar .ogg).
             @param fade_ms  Duración del fade in en milisegundos.
        """
        if self.current_music == str(path):
            return
        self.current_music = str(path)
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.set_volume(self.volumen)
        pygame.mixer.music.play(loops=-1, fade_ms=fade_ms)

    def stop_music(self, fade_ms=1000):
        """! Detiene la música de fondo con fade out."""
        self.current_music = None
        pygame.mixer.music.fadeout(fade_ms)