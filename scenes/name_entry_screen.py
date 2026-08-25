#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""! @brief Pantalla de ingreso de iniciales al lograr un récord."""

##
# @file name_entry_screen.py
#
# @brief Define la clase NameEntry.
#
# @section description_name_entry Descripción
# Selector arcade clásico de 3 iniciales: flechas ARRIBA/ABAJO cambian la
# letra activa, IZQUIERDA/DERECHA cambian de posición, también se puede
# escribir directo con el teclado, y ENTER guarda el récord.
#
# @section author_name_entry Autores
# - Marcelo Tipán
#
# Copyright (c) 2021 Proyecto_Pong.  All rights reserved.

import string

import pygame

from core import scene
from utils import highscores
from utils.i18n import t
from config import FONTS, PATHS, UI, GAME

ALPHABET = string.ascii_uppercase


class NameEntry(scene.Scene):
    """! Selector de 3 iniciales para guardar un récord."""

    LETTER_SPACING = 90
    ## Parpadeo del cursor de la letra activa (ms)
    BLINK_MS = 400

    def __init__(self, director, points, level):
        """! @param points  Puntaje logrado en la partida.
             @param level   Nivel máximo alcanzado.
        """
        super().__init__(director)
        director.status = GAME.STATUS_NAME_ENTRY

        self.points = points
        self.level = level

        self.background = pygame.transform.scale(
            pygame.image.load(PATHS.IMAGE_PATH_MENU).convert(),
            GAME.SCREEN_SIZE,
        )

        ## Estado del selector: índices en ALPHABET y posición activa
        self.letters = [0, 0, 0]     # "AAA"
        self.active = 0

        font_big = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.LARGE * 2)
        self.font_letters = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.LARGE * 2)
        font_medium = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.MEDIUM)

        cx = GAME.SCREEN_WIDTH // 2
        self.cx = cx
        self.letters_y = GAME.SCREEN_HEIGHT // 2

        self.title = font_big.render(t("name_entry.title"), True, UI.COLORS["YELLOW"])
        self.title_rect = self.title.get_rect(center=(cx, 140))

        score_text = t("name_entry.score", points=self.points)
        self.score = font_medium.render(score_text, True, UI.COLORS["WHITE"])
        self.score_rect = self.score.get_rect(center=(cx, 220))

        self.hint = font_medium.render(t("name_entry.hint"), True, UI.COLORS["GRAY"])
        self.hint_rect = self.hint.get_rect(
            center=(cx, GAME.SCREEN_HEIGHT - 80))

    # ------------------------------------------------------------------
    def _initials(self):
        return "".join(ALPHABET[i] for i in self.letters)

    def _confirm(self):
        """! Guarda el récord y pasa a la tabla, resaltando la posición."""
        position = highscores.add(self._initials(), self.points, self.level)
        self.sonido_click()
        from scenes import highscores_screen
        self.director.change_scene(
            highscores_screen.Highscores(self.director, highlight=position))

    def sonido_click(self):
        self.director.audio.play_click()

    # ------------------------------------------------------------------
    # Funciones heredadas de la clase Scene
    # ------------------------------------------------------------------
    def on_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        sonido = self.director.audio
        if event.key in (pygame.K_UP, pygame.K_w):
            self.letters[self.active] = (self.letters[self.active] + 1) % 26
            sonido.play_hover()
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.letters[self.active] = (self.letters[self.active] - 1) % 26
            sonido.play_hover()
        elif event.key in (pygame.K_RIGHT, pygame.K_TAB):
            self.active = (self.active + 1) % 3
            sonido.play_hover()
        elif event.key in (pygame.K_LEFT, pygame.K_BACKSPACE):
            self.active = (self.active - 1) % 3
            sonido.play_hover()
        elif event.key == pygame.K_RETURN:
            self._confirm()
        elif event.unicode and event.unicode.upper() in ALPHABET:
            # Escritura directa: fija la letra y avanza de posición
            self.letters[self.active] = ALPHABET.index(event.unicode.upper())
            self.active = min(self.active + 1, 2)
            sonido.play_hover()

    def on_draw(self, screen):
        screen.blit(self.background, (0, 0))
        screen.blit(self.title, self.title_rect)
        screen.blit(self.score, self.score_rect)
        screen.blit(self.hint, self.hint_rect)

        # Las tres letras, con la activa parpadeando en amarillo
        blink_on = (pygame.time.get_ticks() // self.BLINK_MS) % 2 == 0
        start_x = self.cx - self.LETTER_SPACING
        for i, letter_index in enumerate(self.letters):
            is_active = i == self.active
            color = UI.COLORS["YELLOW"] if is_active else UI.COLORS["WHITE"]
            surface = self.font_letters.render(ALPHABET[letter_index], True, color)
            x = start_x + i * self.LETTER_SPACING
            rect = surface.get_rect(center=(x, self.letters_y))
            screen.blit(surface, rect)

            # Subrayado/cursor de la posición activa
            if is_active and blink_on:
                underline = pygame.Rect(0, 0, 50, 6)
                underline.center = (x, self.letters_y + 45)
                pygame.draw.rect(screen, UI.COLORS["YELLOW"], underline)