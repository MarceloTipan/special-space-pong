#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""! @brief Toggle switch (píldora con perilla deslizante) para booleanos."""

##
# @file toggle.py
#
# @brief Define la clase Toggle.
#
# @section description_toggle Descripción
# Interruptor visual de encendido/apagado: una píldora cuyo color indica
# el estado y una perilla que se desliza animada al alternar. Misma
# interfaz update/draw que los demás componentes de ui.
#
# @section author_toggle Autores
# - Marcelo Tipán
#
# Copyright (c) 2021 Proyecto_Pong.  All rights reserved.

import pygame


class Toggle:
    """! Interruptor de píldora con perilla animada."""

    def __init__(self, pos, get_state, action, sonido=None,
                 width=72, height=34, on_text=None, off_text=None,
                 font_path=None,
                 on_color=(255, 220, 0), off_color=(90, 90, 90),
                 knob_color=(255, 255, 255)):
        """! @param pos        Centro (x, y) del interruptor.
             @param get_state  Función sin argumentos que devuelve el
                               estado actual (True = encendido).
             @param action     Función a ejecutar al hacer clic (debe
                               alternar el estado que get_state lee).
             @param on_text    Texto dentro de la píldora al estar
                               encendido (ej. "ON"); None = sin texto.
             @param off_text   Ídem, apagado.
             @param font_path  Fuente para el texto interior (None usa
                               la fuente por defecto de pygame).
        """
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = pos
        self.get_state = get_state
        self.action = action
        self.sonido = sonido
        self.on_color = on_color
        self.off_color = off_color
        self.knob_color = knob_color

        self.hovered = False
        self._was_hovered = False

        ## Posición animada de la perilla (0.0 = izquierda, 1.0 = derecha)
        self.knob_t = 1.0 if get_state() else 0.0

        ## Textos interiores pre-renderizados (tono derivado del color de
        ## la píldora, como marca de agua)
        font_size = max(9, int(height * 0.38))
        font = (pygame.font.Font(str(font_path), font_size) if font_path
                else pygame.font.Font(None, font_size + 6))
        dark_on = tuple(c // 2 for c in on_color)
        dark_off = tuple(min(255, c + 70) for c in off_color)
        self.on_surface = font.render(on_text, True, dark_on) if on_text else None
        self.off_surface = font.render(off_text, True, dark_off) if off_text else None

        ## La píldora se ensancha si el texto no cabe junto a la perilla:
        ## perilla (≈alto) + texto más ancho + márgenes
        widest = max((s.get_width() for s in (self.on_surface, self.off_surface)
                      if s is not None), default=0)
        needed = height + widest + 18
        if needed > self.rect.width:
            self.rect.width = needed
            self.rect.center = pos

    def update(self, mouse_pos, clicked):
        self.hovered = self.rect.collidepoint(mouse_pos)
        if self.hovered and not self._was_hovered and self.sonido:
            self.sonido.play_hover()
        self._was_hovered = self.hovered
        if self.hovered and clicked:
            if self.sonido:
                self.sonido.play_click()
            self.action()

    def draw(self, screen):
        state = self.get_state()

        # La perilla se desliza suavemente hacia su lado (interpolación)
        target = 1.0 if state else 0.0
        self.knob_t += (target - self.knob_t) * 0.25
        if abs(self.knob_t - target) < 0.01:
            self.knob_t = target

        # Píldora: el color comunica el estado
        pill_color = self.on_color if state else self.off_color
        radius = self.rect.height // 2
        pygame.draw.rect(screen, pill_color, self.rect, border_radius=radius)
        if self.hovered:
            pygame.draw.rect(screen, self.knob_color, self.rect,
                             width=2, border_radius=radius)

        # Perilla deslizante
        margin = 4
        knob_radius = radius - margin
        left_x = self.rect.left + margin + knob_radius
        right_x = self.rect.right - margin - knob_radius
        knob_x = left_x + (right_x - left_x) * self.knob_t

        # Texto interior centrado en el hueco que deja la perilla
        text = self.on_surface if state else self.off_surface
        if text is not None:
            gap_left = self.rect.left + margin
            gap_right = knob_x - knob_radius
            if not state:   # perilla a la izquierda: hueco a la derecha
                gap_left = knob_x + knob_radius
                gap_right = self.rect.right - margin
            center_x = (gap_left + gap_right) / 2
            screen.blit(text, text.get_rect(
                center=(int(center_x), self.rect.centery)))

        pygame.draw.circle(screen, self.knob_color,
                           (int(knob_x), self.rect.centery), knob_radius)