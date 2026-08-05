#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Campo de estrellas con scroll parallax para el fondo del juego.

Varias capas de estrellas a distinta velocidad y tamaño crean sensación
de profundidad: las lejanas se mueven lento y tenues, las cercanas rápido
y brillantes. Se genera por procedimiento (sin imágenes que costurar).
"""

import random

import pygame


class Starfield:
    """! Fondo animado de estrellas en capas con efecto parallax."""

    ## (cantidad, velocidad px/s, radio, brillo) por capa: de lejana a cercana
    LAYERS = [
        (40, 8,  1, 110),
        (30, 18, 1, 170),
        (20, 34, 2, 230),
    ]

    def __init__(self, width, height, seed=None):
        """! @param width, height  Tamaño del área a cubrir.
             @param seed           Semilla opcional (para reproducibilidad).
        """
        self.width = width
        self.height = height
        rng = random.Random(seed)

        ## Cada capa es una lista de estrellas [x, y]; el color/velocidad
        ## son propios de la capa (guardados en paralelo en self.meta)
        self.layers = []
        self.meta = []
        for count, speed, radius, brightness in self.LAYERS:
            stars = [[rng.uniform(0, width), rng.uniform(0, height)]
                     for _ in range(count)]
            self.layers.append(stars)
            self.meta.append((speed, radius, (brightness,) * 3))

    def update(self, dt):
        """! Desplaza las estrellas hacia abajo; las que salen reaparecen
             arriba (scroll infinito)."""
        for stars, (speed, _radius, _color) in zip(self.layers, self.meta):
            for star in stars:
                star[1] += speed * dt
                if star[1] > self.height:
                    star[1] -= self.height
                    star[0] = random.uniform(0, self.width)

    def draw(self, screen):
        for stars, (_speed, radius, color) in zip(self.layers, self.meta):
            for x, y in stars:
                if radius <= 1:
                    screen.set_at((int(x), int(y)), color)
                else:
                    pygame.draw.circle(screen, color, (int(x), int(y)), radius)