#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""! @brief Botón de ícono (imagen) con hover, para la rueda de configuración."""

##
# @file icon_button.py
#
# @brief Define la clase IconButton.
#
# @section author_icon Autores
# - Marcelo Tipán
#
# Copyright (c) 2021 Proyecto_Pong.  All rights reserved.

import math
import pygame


class IconButton:
    """! Botón cuadrado con un ícono. Si no hay imagen, dibuja un
    engranaje de placeholder para que funcione mientras diseñas el asset.

    Implementa la misma interfaz que TextButton: update(mouse_pos, clicked)
    y draw(screen), así puede convivir en la misma lista de botones.
    """

    ## Tipos de placeholder disponibles cuando no hay imagen
    ICONS = ("gear", "info", "trophy", "question")

    def __init__(self, pos, action, size=48, image_path=None, icon="gear",
                 color=(200, 200, 200), hover_color=(255, 255, 0), sonido=None):
        """! @param pos         Centro (x, y) del botón.
             @param action      Función a ejecutar al hacer clic.
             @param size        Lado del área clicable en píxeles.
             @param image_path  Ruta del ícono (opcional).
             @param icon        Placeholder si no hay imagen: gear, info,
                                trophy o question.
        """
        self.icon = icon if icon in self.ICONS else "gear"
        self.pos = pos
        self.action = action
        self.size = size
        self.color = color
        self.hover_color = hover_color
        self.sonido = sonido
        self.hovered = False
        self._was_hovered = False

        self.image = None
        if image_path:
            try:
                img = pygame.image.load(str(image_path)).convert_alpha()
                self.image = pygame.transform.smoothscale(img, (size, size))
            except (pygame.error, FileNotFoundError):
                print(f"[IconButton] No se pudo cargar {image_path}, uso placeholder")

        self.rect = pygame.Rect(0, 0, size, size)
        self.rect.center = pos

    def update(self, mouse_pos, clicked):
        self.hovered = self.rect.collidepoint(mouse_pos)
        # Sonido solo al ENTRAR al botón, no en cada frame encima
        if self.hovered and not self._was_hovered and self.sonido:
            self.sonido.play_hover()
        self._was_hovered = self.hovered

        if self.hovered and clicked:
            self.action()

    def draw(self, screen):
        if self.image:
            img = self.image
            if self.hovered:
                # Leve agrandado al pasar el mouse
                grow = int(self.size * 1.12)
                img = pygame.transform.smoothscale(self.image, (grow, grow))
            rect = img.get_rect(center=self.pos)
            screen.blit(img, rect)
        else:
            self._draw_placeholder(screen)

    def _draw_placeholder(self, screen):
        """! Dibuja el ícono de placeholder según self.icon."""
        color = self.hover_color if self.hovered else self.color
        draw = {
            "gear": self._draw_gear,
            "info": self._draw_info,
            "trophy": self._draw_trophy,
            "question": self._draw_question,
        }[self.icon]
        draw(screen, color)

    def _glyph(self, screen, color, char):
        """! Círculo con un carácter centrado (para info y question)."""
        cx, cy = self.pos
        radius = self.size // 2 - 4
        pygame.draw.circle(screen, color, (cx, cy), radius, 4)
        font = pygame.font.Font(None, int(self.size * 0.8))
        surface = font.render(char, True, color)
        screen.blit(surface, surface.get_rect(center=(cx, cy + 1)))

    def _draw_info(self, screen, color):
        self._glyph(screen, color, "i")

    def _draw_question(self, screen, color):
        self._glyph(screen, color, "?")

    def _draw_trophy(self, screen, color):
        """! Copa simple: cuerpo, asas, tallo y base."""
        cx, cy = self.pos
        s = self.size
        body = pygame.Rect(0, 0, int(s * 0.44), int(s * 0.38))
        body.midtop = (cx, cy - int(s * 0.38))
        pygame.draw.rect(screen, color, body, 4,
                         border_bottom_left_radius=10, border_bottom_right_radius=10)
        # Asas
        for side in (-1, 1):
            handle_x = cx + side * (body.width // 2 + 5)
            pygame.draw.circle(screen, color, (handle_x, body.centery - 3), 7, 3)
        # Tallo y base
        pygame.draw.rect(screen, color,
                         (cx - 3, body.bottom, 6, int(s * 0.16)))
        base = pygame.Rect(0, 0, int(s * 0.4), 5)
        base.midtop = (cx, body.bottom + int(s * 0.16))
        pygame.draw.rect(screen, color, base)

    def _draw_gear(self, screen, color):
        """! Dibuja un engranaje simple con primitivas de pygame."""
        cx, cy = self.pos
        outer = self.size // 2 - 6
        # Dientes: 8 líneas gruesas radiales
        for i in range(8):
            angle = math.radians(i * 45)
            x1 = cx + math.cos(angle) * (outer - 4)
            y1 = cy + math.sin(angle) * (outer - 4)
            x2 = cx + math.cos(angle) * (outer + 5)
            y2 = cy + math.sin(angle) * (outer + 5)
            pygame.draw.line(screen, color, (x1, y1), (x2, y2), 6)
        # Cuerpo y agujero central
        pygame.draw.circle(screen, color, (cx, cy), outer, 6)
        pygame.draw.circle(screen, color, (cx, cy), outer // 3, 4)