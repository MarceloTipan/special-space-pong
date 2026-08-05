#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Pelota del juego: posición, velocidad y su propia física de rebote.

Encapsular la pelota como objeto permite tener varias a la vez (multibola
en niveles altos y en el nivel bonus) sin duplicar lógica.
"""

import math
import random

import pygame


class Ball:
    """! Una pelota con posición, velocidad y rebotes."""

    ## Variación de rapidez entre pelotas (±fracción respecto a la base)
    SPEED_JITTER = 0.15

    ## Cuántas posiciones pasadas se guardan para dibujar la estela
    TRAIL_LENGTH = 10

    def __init__(self, x, y, width, height, speed, direction=None):
        """! @param x, y            Posición inicial (esquina superior izq).
             @param width, height   Tamaño del sprite.
             @param speed           Rapidez base (px/s); se le aplica jitter.
             @param direction       +1 hacia abajo, -1 hacia arriba, None=azar.
        """
        self.x = float(x)
        self.y = float(y)
        self.w = width
        self.h = height

        ## Historial de centros para la estela (el más reciente al final)
        self.trail = []

        # Cada pelota varía un poco su rapidez, para que no vayan clonadas
        self.speed = speed * (1 + random.uniform(-self.SPEED_JITTER,
                                                 self.SPEED_JITTER))
        if direction is None:
            direction = random.choice((-1, 1))
        self._launch(direction)

    def _launch(self, direction):
        """! Lanza la pelota con un ángulo aleatorio en la dirección dada."""
        angle = math.radians(random.uniform(-35, 35))   # respecto a la vertical
        self.vx = self.speed * math.sin(angle)
        self.vy = self.speed * math.cos(angle) * direction

    # ------------------------------------------------------------------
    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def move(self, dt):
        # Guarda el centro actual antes de moverse (para la estela)
        self.trail.append((self.cx, self.cy))
        if len(self.trail) > self.TRAIL_LENGTH:
            self.trail.pop(0)
        self.x += self.vx * dt
        self.y += self.vy * dt

    def time_to_reach_y(self, target_y):
        """! Tiempo estimado (s) hasta que la pelota llegue a target_y.
             Devuelve infinito si se aleja de ese objetivo.
             Sirve para que la IA elija a qué pelota atender."""
        dy = target_y - self.cy
        if self.vy == 0 or (dy > 0) != (self.vy > 0):
            return float("inf")
        return dy / self.vy

    def set_speed_scale(self, scale):
        """! Reescala la velocidad conservando la dirección (cambio de nivel)."""
        self.vx *= scale
        self.vy *= scale
        self.speed *= scale

    def bounce_x(self):
        self.vx = -self.vx

    def bounce_paddle(self, paddle_x, paddle_w, upward, max_bounce_x):
        """! Rebote angular según el punto de impacto en la raqueta:
             centro = vertical, borde = diagonal. Conserva la rapidez."""
        paddle_center = paddle_x + paddle_w / 2
        hit = (self.cx - paddle_center) / (paddle_w / 2)
        hit = max(-1.0, min(1.0, hit))

        speed = math.hypot(self.vx, self.vy)
        self.vx = speed * hit * max_bounce_x
        vertical = math.sqrt(max(0.0, speed * speed - self.vx * self.vx))
        self.vy = -vertical if upward else vertical