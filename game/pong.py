#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""! @brief La clase Pong es la escena del juego."""

##
# @file pong.py
#
# @brief Define la clase Pong.
#
# @section description_pong Descripción
# Escena del juego: física de la pelota con rebote angular según el punto
# de impacto en la raqueta, raqueta enemiga como entidad propia, HUD en
# barra superior, pausa y game over.
#
# @section author_pong Autores
# - Marcelo Tipán
#
# Copyright (c) 2021 Proyecto_Pong.  All rights reserved.

import math
import random

import pygame

from core import scene
from game import movimiento
from game.ball import Ball
from game.starfield import Starfield
from game.obstacle import Obstacle
from ui import TextButton
from utils.i18n import t
from config import FONTS, PATHS, UI, GAME


class PauseButton:
    """! Botón de pausa/reanudar con ícono dibujado (misma interfaz
    update/draw que los demás botones)."""

    def __init__(self, pos, size, action, is_paused, sonido):
        self.rect = pygame.Rect(0, 0, size, size)
        self.rect.center = pos
        self.action = action
        self.is_paused = is_paused
        self.sonido = sonido
        self.hovered = False
        self._was_hovered = False

    def update(self, mouse_pos, clicked):
        self.hovered = self.rect.collidepoint(mouse_pos)
        if self.hovered and not self._was_hovered and self.sonido:
            self.sonido.play_hover()
        self._was_hovered = self.hovered
        if self.hovered and clicked:
            self.action()

    def draw(self, screen):
        color = UI.COLORS["WHITE"] if self.hovered else UI.COLORS["YELLOW"]
        pygame.draw.rect(screen, color, self.rect, width=3, border_radius=4)
        cx, cy = self.rect.center
        s = self.rect.width // 4
        if self.is_paused():
            pygame.draw.polygon(screen, color, [
                (cx - s + 2, cy - s), (cx - s + 2, cy + s), (cx + s, cy)])
        else:
            pygame.draw.rect(screen, color, (cx - s, cy - s, s - 2, 2 * s))
            pygame.draw.rect(screen, color, (cx + 2, cy - s, s - 2, 2 * s))


class Pong(scene.Scene):
    """! Escena del juego."""

    # ------------------------------------------------------------------
    # Vidas: configurables desde GAME.LIVES, limitadas de 2 a 5
    # ------------------------------------------------------------------
    LIVES_MIN, LIVES_MAX = 2, 5

    ## Presets de dificultad: vidas, goles para ganar y multiplicadores IA.
    ## error > 1 = enemigo más torpe; speed > 1 = enemigo más rápido.
    DIFFICULTY_PRESETS = {
        "easy":   {"lives": 5, "goals": 1, "enemy_error": 1.4, "enemy_speed": 0.85},
        "normal": {"lives": 3, "goals": 5, "enemy_error": 1.0, "enemy_speed": 1.0},
        "hard":   {"lives": 2, "goals": 7, "enemy_error": 0.7, "enemy_speed": 1.15},
    }

    # ------------------------------------------------------------------
    # Niveles y puntaje
    # ------------------------------------------------------------------
    LEVEL_MAX = 10
    LEVEL_SECONDS = 60          # segundos para subir de nivel
    BASE_SPEED = 80             # velocidad base por eje en nivel 0 (px/s)
    SPEED_PER_LEVEL = 30        # incremento por nivel
    POINT_EVERY = 5             # segundos por punto

    ## Máxima componente horizontal del rebote en raqueta (0 a 1).
    ## 0.75 garantiza que la pelota siempre conserve avance vertical.
    MAX_BOUNCE_X = 0.75

    ## Cantidad de pelotas simultáneas según el nivel. Los últimos niveles
    ## suben a 2 y 3 para exigir dividir la atención.
    def _balls_for_level(self, level):
        if level >= self.LEVEL_MAX:          # nivel 10
            return 3
        if level >= self.LEVEL_MAX - 1:      # nivel 9
            return 2
        return 1

    # ------------------------------------------------------------------
    # IA del enemigo: tres perillas que escalan con el nivel.
    # El fallo EMERGE de estas limitaciones, nunca de un dado por frame.
    # ------------------------------------------------------------------
    ## Velocidad de la raqueta enemiga (px/s): base + incremento por nivel
    ENEMY_SPEED_BASE = 200
    ENEMY_SPEED_PER_LEVEL = 30
    ## Error de puntería (px): se sortea UNA vez por jugada y se reduce
    ## con el nivel (nivel 1 ~120px de error, nivel 10 ~20px)
    ENEMY_ERROR_BASE = 130
    ENEMY_ERROR_PER_LEVEL = 11
    ## Solo reacciona cuando la pelota viene hacia ella y ya cruzó esta
    ## fracción del campo (más bajo = reacciona antes = más difícil)
    ENEMY_REACT_FRACTION_BASE = 0.75
    ENEMY_REACT_PER_LEVEL = 0.04

    # ------------------------------------------------------------------
    # Obstáculos procedurales
    # ------------------------------------------------------------------
    ## Nivel a partir del cual aparecen
    OBSTACLE_START_LEVEL = 3
    ## Cantidad: uno más cada 2 niveles, con tope
    OBSTACLE_MAX = 5
    ## Rango de tamaños (ancho, alto)
    OBSTACLE_W = (70, 130)
    OBSTACLE_H = (16, 26)
    ## Separación mínima entre obstáculos y respecto al punto de saque
    OBSTACLE_GAP = 60
    ## Franja vertical libre junto a cada raqueta (zona de juego limpio)
    OBSTACLE_MARGIN_Y = 110

    # ------------------------------------------------------------------
    # Geometría del campo, relativa a la pantalla.
    # ------------------------------------------------------------------
    FIELD_LEFT = 45
    FIELD_RIGHT = GAME.SCREEN_WIDTH - 45
    FIELD_TOP = 90
    FIELD_BOTTOM = GAME.SCREEN_HEIGHT - 45

    PADDLE_KEY_SPEED = 400      # velocidad con teclado (px/s)
    HEART_SIZE = 32
    HEART_BLINK_MS = 720
    HEART_BLINK_INTERVAL = 120

    ## Altura de la barra del HUD
    HUD_CENTER_Y = 30

    # ------------------------------------------------------------------
    # Carga por pasos (consumida por LoadingScreen)
    # ------------------------------------------------------------------
    @classmethod
    def load_steps(cls, director):
        """! Generador de carga: yield progreso tras cada trozo de trabajo."""
        yield 0.05
        images = cls._load_images()
        yield 0.35
        detector = movimiento.Movimiento()   # lo más lento: la cámara
        yield 0.95
        return cls(director, images=images, detector=detector)

    @staticmethod
    def _load_images():
        """! Carga y prepara todas las imágenes del juego."""
        background = pygame.transform.scale(
            pygame.image.load(PATHS.IMAGE_PATH_GAME).convert(),
            GAME.SCREEN_SIZE,
        )
        heart_size = (Pong.HEART_SIZE, Pong.HEART_SIZE)
        return {
            "background": background,
            "ball": pygame.image.load(PATHS.IMAGE_PATH_BALL).convert_alpha(),
            "paddle_top": pygame.image.load(PATHS.IMAGE_PATH_PADDLE_TOP).convert_alpha(),
            "paddle": pygame.image.load(PATHS.IMAGE_PATH_PADDLE).convert_alpha(),
            "heart": pygame.transform.smoothscale(
                pygame.image.load(PATHS.IMAGE_PATH_HEART).convert_alpha(), heart_size),
            "heart_empty": pygame.transform.smoothscale(
                pygame.image.load(PATHS.IMAGE_PATH_HEART_EMPTY).convert_alpha(), heart_size),
            "asteroid": Pong._load_asteroid(),
        }

    @staticmethod
    def _load_asteroid():
        """! Carga el sprite del asteroide; si no existe, devuelve None y
             los obstáculos se dibujan como bloques neón (fallback)."""
        path = getattr(PATHS, "IMAGE_PATH_ASTEROID", None)
        if not path:
            return None
        try:
            return pygame.image.load(str(path)).convert_alpha()
        except (pygame.error, FileNotFoundError):
            return None

    # ------------------------------------------------------------------
    def __init__(self, director, images=None, detector=None):
        super().__init__(director)
        director.status = GAME.STATUS_GAME

        self.images = images if images is not None else self._load_images()
        self.detector = detector if detector is not None else movimiento.Movimiento()
        self.sonido = director.sonido

        ## Campo de estrellas con parallax, sobre el fondo del juego
        self.starfield = Starfield(GAME.SCREEN_WIDTH, GAME.SCREEN_HEIGHT)

        ## Dificultad elegida en configuración
        from utils import settings
        preset = self.DIFFICULTY_PRESETS.get(
            settings.get("difficulty"), self.DIFFICULTY_PRESETS["normal"])
        self.lives_start = max(self.LIVES_MIN, min(self.LIVES_MAX, preset["lives"]))
        self.goals_to_win = preset["goals"]
        self.enemy_error_mult = preset["enemy_error"]
        self.enemy_speed_mult = preset["enemy_speed"]

        ## Dimensiones cacheadas
        self.ball_w = self.images["ball"].get_width()
        self.ball_h = self.images["ball"].get_height()
        self.paddle_w = self.images["paddle"].get_width()
        paddle_h = self.images["paddle"].get_height()
        self.enemy_w = self.images["paddle_top"].get_width()
        enemy_h = self.images["paddle_top"].get_height()

        ## Posiciones derivadas del campo
        self.paddle_y = self.FIELD_BOTTOM - paddle_h - 10
        self.paddle_min_x = self.FIELD_LEFT
        self.paddle_max_x = self.FIELD_RIGHT - self.paddle_w

        ## Raqueta enemiga: entidad propia con sus límites
        self.enemy_y = self.FIELD_TOP + 5
        self.enemy_bottom = self.enemy_y + enemy_h   # línea de rebote superior
        self.enemy_min_x = self.FIELD_LEFT
        self.enemy_max_x = self.FIELD_RIGHT - self.enemy_w

        ## Fuentes (una vez)
        self.font_hud = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.MEDIUM)
        self.font_score = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.LARGE)
        self.font_big = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.LARGE * 2)

        ## Textos fijos pre-renderizados
        yellow = UI.COLORS["YELLOW"]
        self.text_pause = self.font_big.render(t("game.paused"), True, yellow)
        self.overlay_titles = {
            "level_won": self.font_big.render(t("game.level_won"), True, yellow),
            "level_lost": self.font_big.render(t("game.level_lost"), True, yellow),
            "victory": self.font_big.render(t("game.victory"), True, yellow),
        }
        self.label_level = self.font_hud.render(t("game.hud_level"), True, UI.COLORS["WHITE"])

        ## Fondo semitransparente para los overlays
        self.overlay_backdrop = pygame.Surface(GAME.SCREEN_SIZE)
        self.overlay_backdrop.set_alpha(160)
        self.overlay_backdrop.fill((0, 0, 0))

        ## Posiciones del HUD
        w = GAME.SCREEN_WIDTH
        self.hud_pos = {
            "hearts": (int(w * 0.16), self.HUD_CENTER_Y - self.HEART_SIZE // 2),
            "points": (int(w * 0.31), self.HUD_CENTER_Y),
            "score": (w // 2, self.HUD_CENTER_Y),
            "level_label": (int(w * 0.61), self.HUD_CENTER_Y),
            "level_value": (int(w * 0.68), self.HUD_CENTER_Y),
            "center": (w // 2, GAME.SCREEN_HEIGHT // 2 - 40),
        }

        ## Botones del HUD
        self.pause_button = PauseButton(
            pos=(int(w * 0.79), self.HUD_CENTER_Y), size=36,
            action=self._toggle_pause,
            is_paused=lambda: self.paused,
            sonido=self.sonido)
        self.exit_button = TextButton(
            pos=(int(w * 0.90), self.HUD_CENTER_Y),
            text=t("menu.exit"),
            font_config=(str(PATHS.FONT_PATH_ARCADE), FONTS.MEDIUM),
            action=self._go_to_menu,
            base_color=UI.COLORS["GRAY"],
            hover_color=UI.COLORS["WHITE"],
            sonido=self.sonido)
        self.hud_buttons = [self.pause_button, self.exit_button]

        ## Botones de los overlays de resultado
        cx, cy = self.hud_pos["center"]
        font_cfg = (str(PATHS.FONT_PATH_ARCADE), FONTS.MEDIUM)

        def make_button(y_off, text_key, action):
            return TextButton(
                pos=(cx, cy + y_off), text=t(text_key), font_config=font_cfg,
                action=action, hover_color=UI.COLORS["YELLOW"], sonido=self.sonido)

        self.overlay_buttons = {
            "level_won": [make_button(80, "game.continue", self._on_continue)],
            "level_lost": [make_button(80, "game.retry", self._on_retry),
                           make_button(130, "menu.exit", self._go_to_menu)],
            "victory": [make_button(80, "menu.exit", self._go_to_menu)],
        }

        self._reset_game()

    def _level_speed(self):
        """! Rapidez total (magnitud del vector velocidad) para el nivel
             actual. Equivale a la diagonal del (80+30n, 80+30n) original."""
        component = self.BASE_SPEED + self.SPEED_PER_LEVEL * self.level
        return math.hypot(component, component)

    def _reset_game(self):
        """! Restaura el estado inicial de una partida completa."""
        self.points = 0
        self.time = 0.0
        self.last_point_second = -1
        self._start_level(1)

    def _serve_balls(self, count):
        """! Crea 'count' pelotas nuevas en el CENTRO del campo, cada una
             con dirección aleatoria (arriba o abajo) y rapidez ligeramente
             distinta. Reemplaza cualquier pelota anterior."""
        cx = GAME.SCREEN_WIDTH / 2 - self.ball_w / 2
        cy = (self.FIELD_TOP + self.FIELD_BOTTOM) / 2 - self.ball_h / 2
        speed = self._level_speed()
        self.balls = [
            Ball(cx, cy, self.ball_w, self.ball_h, speed)
            for _ in range(count)
        ]
        self._roll_enemy_error()

    def _add_ball(self):
        """! Añade una pelota extra en el centro (nivel bonus)."""
        cx = GAME.SCREEN_WIDTH / 2 - self.ball_w / 2
        cy = (self.FIELD_TOP + self.FIELD_BOTTOM) / 2 - self.ball_h / 2
        self.balls.append(
            Ball(cx, cy, self.ball_w, self.ball_h, self._level_speed()))

    # ------------------------------------------------------------------
    # Navegación y control
    # ------------------------------------------------------------------
    def _go_to_menu(self):
        """! Termina la partida: si el puntaje entra al top 10, pasa por
             el ingreso de iniciales; si no, directo al menú."""
        self.detector.release()
        # Imports locales: evitan el ciclo menu <-> pong
        from scenes import menu, name_entry_screen
        from utils import highscores
        if highscores.qualifies(self.points):
            self.director.change_scene(
                name_entry_screen.NameEntry(self.director, self.points, self.level))
        else:
            # Sin récord igual se muestra la tabla, con el puntaje de esta
            # partida debajo: ver la vara invita a intentarlo de nuevo
            from scenes import highscores_screen
            self.director.change_scene(
                highscores_screen.Highscores(self.director, last_score=self.points))

    def _toggle_pause(self):
        """! SPACE / botón de pausa: en juego alterna la pausa; en las
             pantallas de resultado ejecuta la acción principal."""
        if self.match_state == "level_won":
            self._next_level()
            self.paused = False
        elif self.match_state == "level_lost":
            self._retry_level()
            self.paused = False
        elif self.match_state == "victory":
            self._go_to_menu()
        else:
            self.paused = not self.paused

    # ------------------------------------------------------------------
    # Lógica del juego
    # ------------------------------------------------------------------
    def _set_level(self, level):
        """! Cambia de nivel (debug con flechas): ajusta la rapidez de
             todas las pelotas a la del nivel nuevo, conservando su ángulo."""
        self.level = max(1, min(self.LEVEL_MAX, level))
        target = self._level_speed()
        for ball in self.balls:
            current = math.hypot(ball.vx, ball.vy)
            if current > 0:
                ball.set_speed_scale(target / current)

    def _player_scores(self, ball):
        """! Gol del jugador (la pelota cruzó arriba): puntos y quizás
             nivel superado. La pelota se retira; si no quedan, saca de nuevo."""
        self.goals_player += 1
        self.points += 50
        self.sonido.start_golpe()
        self._remove_ball(ball)

        if self.goals_player >= self.goals_to_win:
            if self.level >= self.LEVEL_MAX:
                self.match_state = "victory"
            else:
                self.match_state = "level_won"
            self.paused = True
        elif not self.balls:
            self._serve_balls(self._balls_for_level(self.level))

    def _lose_life(self, ball):
        """! Gol del enemigo (la pelota cruzó abajo): cuesta un corazón.
             Sin corazones, nivel perdido; si no, la pelota vuelve a sacar."""
        self.lives -= 1
        self.goals_enemy += 1
        self.sonido.start_error()
        self.blink_until = pygame.time.get_ticks() + self.HEART_BLINK_MS
        self._remove_ball(ball)

        if self.lives <= 0:
            self.match_state = "level_lost"
            self.paused = True
        elif not self.balls:
            self._serve_balls(self._balls_for_level(self.level))

    def _remove_ball(self, ball):
        """! Retira una pelota de la lista (si sigue presente)."""
        if ball in self.balls:
            self.balls.remove(ball)

    def _start_level(self, level):
        """! Prepara un nivel: corazones y marcador limpios, velocidad nueva."""
        ## Checkpoint del puntaje al entrar al nivel (para reintentos)
        self.points_checkpoint = self.points
        self.level = max(1, min(self.LEVEL_MAX, level))
        self.lives = self.lives_start
        self.goals_player = 0
        self.goals_enemy = 0
        self.match_state = "playing"
        self.blink_until = 0
        self.paddle_x = float(GAME.SCREEN_WIDTH / 2)
        self.enemy_x = float(GAME.SCREEN_WIDTH / 2)
        self.obstacles = self._generate_obstacles(self.level)
        self._serve_balls(self._balls_for_level(self.level))
        self.paused = True   # el nivel espera al jugador

    def _obstacle_count(self, level):
        """! Cantidad de obstáculos para un nivel dado."""
        if level < self.OBSTACLE_START_LEVEL:
            return 0
        return min(self.OBSTACLE_MAX,
                   1 + (level - self.OBSTACLE_START_LEVEL) // 2)

    def _generate_obstacles(self, level):
        """! Generación procedural con semilla: el mismo nivel produce
             SIEMPRE la misma disposición (reproducible y balanceable).
             Coloca por muestreo con rechazo: sortea, valida, reintenta."""
        count = self._obstacle_count(level)
        if count == 0:
            return []

        rng = random.Random(1000 + level)   # semilla derivada del nivel
        zone_top = self.enemy_bottom + self.OBSTACLE_MARGIN_Y
        zone_bottom = self.paddle_y - self.OBSTACLE_MARGIN_Y
        # Las pelotas nacen del centro: no poner obstáculos ahí
        serve_x = GAME.SCREEN_WIDTH / 2
        serve_y = (self.FIELD_TOP + self.FIELD_BOTTOM) / 2

        obstacles = []
        rects = []
        attempts = 0
        while len(obstacles) < count and attempts < 200:
            attempts += 1
            w = rng.randint(*self.OBSTACLE_W)
            h = rng.randint(*self.OBSTACLE_H)
            x = rng.randint(self.FIELD_LEFT, self.FIELD_RIGHT - w)
            y = rng.randint(zone_top, zone_bottom - h)
            candidate = pygame.Rect(x, y, w, h)

            # Regla 1: lejos del punto de saque
            near_serve = candidate.inflate(
                self.OBSTACLE_GAP * 2, self.OBSTACLE_GAP * 2
            ).collidepoint(serve_x, serve_y)
            # Regla 2: separación mínima entre obstáculos
            overlaps = any(
                candidate.colliderect(r.inflate(self.OBSTACLE_GAP, self.OBSTACLE_GAP))
                for r in rects)

            if not near_serve and not overlaps:
                rects.append(candidate)
                # Cada asteroide gira a distinta velocidad/sentido y arranca
                # en un ángulo distinto, todo derivado del rng (reproducible)
                spin = rng.choice((-1, 1)) * rng.uniform(12, 30)
                obstacles.append(Obstacle(
                    candidate, self.images.get("asteroid"),
                    spin_speed=spin, angle_offset=rng.uniform(0, 360)))
        return obstacles

    def _next_level(self):
        self._start_level(self.level + 1)

    def _retry_level(self):
        ## Reintentar restaura el puntaje del inicio del nivel: sin esto,
        ## se podría inflar el récord repitiendo niveles infinitamente
        self.points = self.points_checkpoint
        self._start_level(self.level)

    def _on_continue(self):
        self._next_level()
        self.paused = False

    def _on_retry(self):
        self._retry_level()
        self.paused = False

    def _bounce_off_paddle(self, ball, paddle_x, paddle_w, upward):
        """! Rebote angular de una pelota contra una raqueta (delega el
             cálculo en el propio objeto Ball) y dispara el sonido."""
        ball.bounce_paddle(paddle_x, paddle_w, upward, self.MAX_BOUNCE_X)
        self.sonido.play("hit" if upward else "hit_enemy")
        if upward:
            # Cada devolución del jugador es una jugada nueva para la IA
            self._roll_enemy_error()

    def _enemy_speed(self):
        base = self.ENEMY_SPEED_BASE + self.ENEMY_SPEED_PER_LEVEL * self.level
        return base * self.enemy_speed_mult

    def _enemy_react_y(self):
        """! Altura del campo a partir de la cual el enemigo reacciona."""
        fraction = max(0.2, self.ENEMY_REACT_FRACTION_BASE
                       - self.ENEMY_REACT_PER_LEVEL * self.level)
        return self.FIELD_TOP + (self.FIELD_BOTTOM - self.FIELD_TOP) * fraction

    def _roll_enemy_error(self):
        """! Sortea el error de puntería para la jugada actual."""
        max_error = max(15, (self.ENEMY_ERROR_BASE
                        - self.ENEMY_ERROR_PER_LEVEL * self.level)
                        * self.enemy_error_mult)
        self.enemy_aim_error = random.uniform(-max_error, max_error)

    def _ball_for_enemy(self):
        """! Elige a qué pelota atender la IA: la que llegará ANTES a su
             línea (menor tiempo de llegada), no la más cercana. Devuelve
             None si ninguna se dirige hacia el enemigo."""
        best, best_time = None, float("inf")
        for ball in self.balls:
            tt = ball.time_to_reach_y(self.enemy_bottom)
            if tt < best_time:
                best, best_time = ball, tt
        return best

    def _update_enemy(self, dt):
        """! IA del enemigo: persigue —con velocidad limitada y error de
             puntería fijo por jugada— la pelota que llegará primero; si
             ninguna se acerca, deriva hacia el centro."""
        target_ball = self._ball_for_enemy()
        if target_ball is not None and target_ball.cy < self._enemy_react_y():
            target = target_ball.cx - self.enemy_w / 2 + self.enemy_aim_error
        else:
            target = (self.enemy_min_x + self.enemy_max_x) / 2

        max_step = self._enemy_speed() * dt
        delta = target - self.enemy_x
        self.enemy_x += max(-max_step, min(max_step, delta))
        self.enemy_x = max(self.enemy_min_x, min(self.enemy_max_x, self.enemy_x))

    def _update_balls(self, dt):
        """! Mueve y resuelve colisiones de TODAS las pelotas. Recorre una
             copia de la lista porque los goles la modifican al vuelo."""
        for ball in list(self.balls):
            ball.move(dt)

            # Paredes laterales
            if ball.x > self.FIELD_RIGHT - ball.w:
                ball.x = self.FIELD_RIGHT - ball.w
                ball.bounce_x()
                self.sonido.start_golpe()
            elif ball.x < self.FIELD_LEFT:
                ball.x = self.FIELD_LEFT
                ball.bounce_x()
                self.sonido.start_golpe()

            # Raqueta enemiga (rebote en su borde inferior)
            if (ball.y < self.enemy_bottom
                    and ball.x + ball.w > self.enemy_x
                    and ball.x < self.enemy_x + self.enemy_w
                    and ball.vy < 0):
                ball.y = self.enemy_bottom
                self._bounce_off_paddle(ball, self.enemy_x, self.enemy_w, upward=False)
            elif ball.y < self.FIELD_TOP:
                self._player_scores(ball)     # el enemigo falló
                continue

            # Raqueta del jugador (rebote en su borde superior)
            if (ball.y > self.paddle_y - ball.h
                    and ball.x + ball.w > self.paddle_x
                    and ball.x < self.paddle_x + self.paddle_w
                    and ball.vy > 0):
                ball.y = self.paddle_y - ball.h
                self._bounce_off_paddle(ball, self.paddle_x, self.paddle_w, upward=True)
            elif ball.y > self.FIELD_BOTTOM:
                self._lose_life(ball)
                continue

            self._collide_obstacles(ball)

    def _collide_obstacles(self, ball):
        """! Rebote de una pelota contra los obstáculos, por eje de mínima
             penetración: se invierte el eje de menor solapamiento y se la
             empuja fuera del bloque."""
        rect = ball.rect
        for obstacle in self.obstacles:
            if not rect.colliderect(obstacle):
                continue

            overlap_x = min(rect.right, obstacle.right) - max(rect.left, obstacle.left)
            overlap_y = min(rect.bottom, obstacle.bottom) - max(rect.top, obstacle.top)

            if overlap_x < overlap_y:
                if rect.centerx < obstacle.centerx:
                    ball.x = obstacle.left - ball.w
                    ball.vx = -abs(ball.vx)
                else:
                    ball.x = obstacle.right
                    ball.vx = abs(ball.vx)
            else:
                if rect.centery < obstacle.centery:
                    ball.y = obstacle.top - ball.h
                    ball.vy = -abs(ball.vy)
                else:
                    ball.y = obstacle.bottom
                    ball.vy = abs(ball.vy)

            self.sonido.play("hit_obstacle")
            break   # un rebote por frame es suficiente

    def _update_paddle(self, dt):
        self.paddle_x += self.detector.deteccion()

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.paddle_x -= self.PADDLE_KEY_SPEED * dt
        if keys[pygame.K_RIGHT]:
            self.paddle_x += self.PADDLE_KEY_SPEED * dt

        self.paddle_x = max(self.paddle_min_x, min(self.paddle_max_x, self.paddle_x))

    def _update_clock_and_score(self, dt):
        ## El nivel ya no sube por tiempo: se GANA anotando goals_to_win.
        self.time += dt
        if self.time >= 60:
            self.time -= 60
            self.last_point_second = -1

        second = int(self.time)
        if second % self.POINT_EVERY == 0 and second != self.last_point_second:
            self.last_point_second = second
            self.points += 1

    # ------------------------------------------------------------------
    # Funciones heredadas de la clase Scene
    # ------------------------------------------------------------------
    def on_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self._toggle_pause()
            elif event.key == pygame.K_ESCAPE:
                self._go_to_menu()
            elif event.key in (pygame.K_UP, pygame.K_KP_PLUS):
                self._set_level(self.level + 1)
            elif event.key in (pygame.K_DOWN, pygame.K_KP_MINUS):
                self._set_level(self.level - 1)
        elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            mouse_pos = pygame.mouse.get_pos()
            clicked = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
            for button in self.hud_buttons:
                button.update(mouse_pos, clicked)
            for button in self.overlay_buttons.get(self.match_state, []):
                button.update(mouse_pos, clicked)

    def on_update(self):
        if self.paused:
            return
        dt = self.director.dt
        self.starfield.update(dt)
        for obstacle in self.obstacles:
            obstacle.update(dt)
        self._update_paddle(dt)
        self._update_enemy(dt)
        self._update_balls(dt)
        self._update_clock_and_score(dt)

    def on_draw(self, screen):
        screen.blit(self.images["background"], (0, 0))
        self.starfield.draw(screen)

        for obstacle in self.obstacles:
            self._draw_obstacle(screen, obstacle)

        for ball in self.balls:
            self._draw_ball_trail(screen, ball)
            screen.blit(self.images["ball"], (ball.x, ball.y))
        screen.blit(self.images["paddle_top"], (self.enemy_x, self.enemy_y))
        screen.blit(self.images["paddle"], (self.paddle_x, self.paddle_y))

        self._draw_hud(screen)

        if self.match_state in self.overlay_titles:
            self._draw_overlay(screen)
        elif self.paused:
            rect = self.text_pause.get_rect(center=self.hud_pos["center"])
            screen.blit(self.text_pause, rect)

    def _draw_ball_trail(self, screen, ball):
        """! Estela: círculos decrecientes y cada vez más tenues detrás de
             la pelota (los más viejos, más pequeños y transparentes)."""
        n = len(ball.trail)
        if n < 2:
            return
        base = max(ball.w, ball.h) / 2
        for i, (tx, ty) in enumerate(ball.trail):
            frac = (i + 1) / n                    # 0 (viejo) .. 1 (reciente)
            radius = max(1, int(base * frac * 0.8))
            alpha = int(120 * frac)
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*UI.COLORS["WHITE"], alpha),
                               (radius, radius), radius)
            screen.blit(surf, (tx - radius, ty - radius))

    def _draw_overlay(self, screen):
        """! Pantalla de resultado: fondo oscuro, título, marcador y botones."""
        screen.blit(self.overlay_backdrop, (0, 0))
        cx, cy = self.hud_pos["center"]

        title = self.overlay_titles[self.match_state]
        screen.blit(title, title.get_rect(center=(cx, cy - 40)))

        score = self.font_score.render(
            f"{self.goals_player}  |  {self.goals_enemy}", True, UI.COLORS["WHITE"])
        screen.blit(score, score.get_rect(center=(cx, cy + 25)))

        for button in self.overlay_buttons.get(self.match_state, []):
            button.draw(screen)

    def _draw_obstacle(self, screen, obstacle):
        """! Dibuja un asteroide. Si no hay sprite cargado, cae a un bloque
             neón (relleno tenue + borde brillante)."""
        if self.images.get("asteroid") is not None:
            obstacle.draw(screen)
        else:
            neon = UI.COLORS.get("NEON_BLUE", (80, 200, 255))
            dim = tuple(c // 4 for c in neon)
            pygame.draw.rect(screen, dim, obstacle.rect, border_radius=6)
            pygame.draw.rect(screen, neon, obstacle.rect, width=3, border_radius=6)

    # ------------------------------------------------------------------
    # HUD
    # ------------------------------------------------------------------
    def _heart_image(self, index):
        """! Imagen del corazón, con parpadeo del recién perdido."""
        now = pygame.time.get_ticks()
        lost_index = self.lives
        if index == lost_index and now < self.blink_until:
            phase = (self.blink_until - now) // self.HEART_BLINK_INTERVAL
            return self.images["heart"] if phase % 2 else self.images["heart_empty"]
        return self.images["heart"] if index < self.lives else self.images["heart_empty"]

    def _draw_hud(self, screen):
        white = UI.COLORS["WHITE"]
        red = UI.COLORS.get("RED", (200, 40, 40))

        hx, hy = self.hud_pos["hearts"]
        spacing = self.HEART_SIZE + 6
        for i in range(self.lives_start):
            screen.blit(self._heart_image(i), (hx + i * spacing, hy))

        points = self.font_hud.render(f"{self.points:04d}", True, white)
        screen.blit(points, points.get_rect(midleft=self.hud_pos["points"]))

        score = self.font_score.render(
            f"{self.goals_player}  |  {self.goals_enemy}", True, red)
        screen.blit(score, score.get_rect(center=self.hud_pos["score"]))

        screen.blit(self.label_level,
                    self.label_level.get_rect(midleft=self.hud_pos["level_label"]))
        level = self.font_hud.render(f"{self.level:02d}", True, white)
        screen.blit(level, level.get_rect(midleft=self.hud_pos["level_value"]))

        for button in self.hud_buttons:
            button.draw(screen)