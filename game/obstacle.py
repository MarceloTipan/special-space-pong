#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Obstáculo del juego: hitbox rectangular + sprite de asteroide.

La colisión usa el Rect (física predecible), pero el sprite se dibuja
encima, ligeramente más grande y rotando lento, para que se vea orgánico.
Las rotaciones se pre-calculan una sola vez (cachear en vez de rotar cada
frame, que sería costoso).
"""

import math

import pygame


class Obstacle:
    """! Asteroide: rectángulo de colisión con sprite rotatorio encima."""

    ## Cuántos fotogramas de rotación se pre-generan (uno cada 360/N grados)
    ROTATION_STEPS = 36

    ## El sprite se dibuja un poco más grande que la hitbox, para que los
    ## picos irregulares sobresalgan y el rebote nunca se vea adelantado
    SPRITE_SCALE = 1.35

    ## Caché de sprites pre-rotados, compartida por todos los asteroides
    ## que usan la misma imagen base: {(id_imagen, tam): [frames...]}
    _rotation_cache = {}

    def __init__(self, rect, base_image, spin_speed=20, angle_offset=0):
        """! @param rect         pygame.Rect de colisión.
             @param base_image   Superficie del asteroide (con alpha).
             @param spin_speed    Velocidad de giro en grados/segundo.
             @param angle_offset  Ángulo inicial (para que no giren iguales).
        """
        self.rect = rect
        self.spin_speed = spin_speed
        self.angle = angle_offset

        sprite_size = int(max(rect.width, rect.height) * self.SPRITE_SCALE)
        self.frames = self._get_frames(base_image, sprite_size)

    @classmethod
    def _get_frames(cls, base_image, size):
        """! Devuelve (y cachea) la lista de sprites pre-rotados a 'size'."""
        key = (id(base_image), size)
        if key not in cls._rotation_cache:
            scaled = pygame.transform.smoothscale(base_image, (size, size))
            frames = [
                pygame.transform.rotozoom(scaled, i * (360 / cls.ROTATION_STEPS), 1.0)
                for i in range(cls.ROTATION_STEPS)
            ]
            cls._rotation_cache[key] = frames
        return cls._rotation_cache[key]

    def update(self, dt):
        self.angle = (self.angle + self.spin_speed * dt) % 360

    def draw(self, screen):
        # Elegir el fotograma pre-rotado más cercano al ángulo actual
        index = int(self.angle / (360 / self.ROTATION_STEPS)) % self.ROTATION_STEPS
        frame = self.frames[index]
        # Centrar el sprite (más grande) sobre el centro de la hitbox
        screen.blit(frame, frame.get_rect(center=self.rect.center))

    # Compatibilidad: permite tratar el obstáculo como su rect en colisiones
    def colliderect(self, other):
        return self.rect.colliderect(other)

    @property
    def left(self): return self.rect.left
    @property
    def right(self): return self.rect.right
    @property
    def top(self): return self.rect.top
    @property
    def bottom(self): return self.rect.bottom
    @property
    def centerx(self): return self.rect.centerx
    @property
    def centery(self): return self.rect.centery

    def inflate(self, x, y):
        return self.rect.inflate(x, y)