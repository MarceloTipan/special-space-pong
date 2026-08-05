#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""! @brief Slider horizontal arrastrable (para volumen, sensibilidad, etc.)."""

##
# @file slider.py
#
# @brief Define la clase Slider.
#
# @section author_slider Autores
# - Marcelo Tipán
#
# Copyright (c) 2021 Proyecto_Pong.  All rights reserved.

import pygame


class Slider:
    """! Barra horizontal con manija arrastrable. Valor entre 0.0 y 1.0.

    A diferencia de los botones, recibe los eventos crudos con
    handle_event(event), porque necesita distinguir presionar,
    arrastrar y soltar.
    """

    TRACK_HEIGHT = 6
    HANDLE_RADIUS = 12

    def __init__(self, pos, width, value, label, font_config,
                 track_color, fill_color, handle_color, text_color,
                 on_change=None, on_release=None):
        """! @param pos          Centro (x, y) del slider.
             @param width        Ancho de la pista en píxeles.
             @param value        Valor inicial (0.0 a 1.0).
             @param label        Texto sobre el slider (ej. "VOLUMEN").
             @param font_config  Tupla (ruta_fuente, tamaño).
             @param on_change    Callback(valor) mientras se arrastra.
             @param on_release   Callback(valor) al soltar la manija.
        """
        self.x, self.y = pos
        self.width = width
        self.value = max(0.0, min(1.0, value))
        self.dragging = False

        self.track_color = track_color
        self.fill_color = fill_color
        self.handle_color = handle_color
        self.text_color = text_color
        self.on_change = on_change
        self.on_release = on_release

        font = pygame.font.Font(*font_config)
        ## Etiqueta pre-renderizada (no cambia)
        self.label_surface = font.render(label, True, text_color)
        ## Fuente para el porcentaje (se re-renderiza solo al cambiar)
        self.pct_font = font
        self._pct_cache_value = None
        self._pct_surface = None

        ## Para centrar el CONJUNTO (pista + porcentaje) en self.x:
        ## se reserva el ancho máximo del porcentaje ("100%")
        self.pct_gap = 25
        self.pct_reserve = font.size("100%")[0]
        total = self.width + self.pct_gap + self.pct_reserve
        self._left = self.x - total // 2

    # ------------------------------------------------------------------
    @property
    def track_left(self):
        return self._left

    @property
    def handle_x(self):
        return self.track_left + int(self.value * self.width)

    def _value_from_mouse(self, mouse_x):
        rel = (mouse_x - self.track_left) / self.width
        return max(0.0, min(1.0, rel))

    # ------------------------------------------------------------------
    def handle_event(self, event):
        """! Procesa un evento crudo de pygame."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # Empieza a arrastrar si se presiona sobre la manija o la pista
            on_handle = (abs(mx - self.handle_x) <= self.HANDLE_RADIUS * 2
                         and abs(my - self.y) <= self.HANDLE_RADIUS * 2)
            on_track = (self.track_left <= mx <= self.track_left + self.width
                        and abs(my - self.y) <= self.HANDLE_RADIUS)
            if on_handle or on_track:
                self.dragging = True
                self._set_value(self._value_from_mouse(mx))

        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_value(self._value_from_mouse(event.pos[0]))

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False
                if self.on_release:
                    self.on_release(self.value)

    def _set_value(self, value):
        if value != self.value:
            self.value = value
            if self.on_change:
                self.on_change(value)

    # ------------------------------------------------------------------
    def draw(self, screen):
        # Etiqueta centrada sobre el centro del widget (no de la pista,
        # que está corrida a la izquierda por el hueco del porcentaje)
        label_rect = self.label_surface.get_rect(
            midbottom=(self.x, self.y - 18))
        screen.blit(self.label_surface, label_rect)

        # Pista completa (fondo) y porción llena
        track_rect = pygame.Rect(
            self.track_left, self.y - self.TRACK_HEIGHT // 2,
            self.width, self.TRACK_HEIGHT)
        pygame.draw.rect(screen, self.track_color, track_rect, border_radius=3)

        fill_rect = pygame.Rect(
            self.track_left, self.y - self.TRACK_HEIGHT // 2,
            self.handle_x - self.track_left, self.TRACK_HEIGHT)
        pygame.draw.rect(screen, self.fill_color, fill_rect, border_radius=3)

        # Manija (más grande mientras se arrastra)
        radius = self.HANDLE_RADIUS + (3 if self.dragging else 0)
        pygame.draw.circle(screen, self.handle_color, (self.handle_x, self.y), radius)

        # Porcentaje a la derecha (cacheado)
        pct = int(self.value * 100)
        if pct != self._pct_cache_value:
            self._pct_cache_value = pct
            self._pct_surface = self.pct_font.render(f"{pct}%", True, self.text_color)
        pct_rect = self._pct_surface.get_rect(
            midleft=(self.track_left + self.width + self.pct_gap, self.y))
        screen.blit(self._pct_surface, pct_rect)