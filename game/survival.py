"""Survival mode: no opponent and no levels, just keep every ball alive.

A wall replaces the enemy at the top. Balls keep coming (one more every
little while, all of them faster and faster), but only the red one costs
a life when it gets past the paddle; letting a white one through breaks
the combo. Every so often the red ball hands its color to another one,
which blinks first as a warning, so the player has to watch them all.

It reuses the campaign scene (paddle control, pause, HUD, drawing helpers)
and replaces its rules.
"""

import math
import random
from dataclasses import dataclass

import pygame

from game import levels
from game.ball import Ball
from game.pong import Pong
from ui import TextButton
from utils import settings
from utils.i18n import t
from utils.text import render_fit
from config import FONTS, UI, GAME



@dataclass(frozen=True)
class Pace:
    """How a survival run plays at one difficulty (lives come from game/levels.py).

    Attributes:
        obstacles: Asteroids in the field (same layout every run, so records compare).
        serve_speed: Ball speed at the start (px/s).
        growth: Speed gained per second played, as a fraction of serve_speed...
        max_scale: ...up to this multiple of it.
        max_balls: Most balls in play at once.
    """

    obstacles: int
    serve_speed: float
    growth: float
    max_scale: float
    max_balls: int


PACES = {
    "easy": Pace(obstacles=1, serve_speed=270, growth=0.006, max_scale=1.6, max_balls=5),
    "normal": Pace(obstacles=3, serve_speed=300, growth=0.008, max_scale=1.8, max_balls=6),
    "hard": Pace(obstacles=4, serve_speed=330, growth=0.010, max_scale=2.0, max_balls=7),
}

# --- Rules shared by every difficulty (module level, so tests and tuning can reach them) ---
START_BALLS = 2          #: balls at the start (one of them red)
NEW_BALL_EVERY = 15.0    #: seconds between new balls
RED_SWITCH_EVERY = 15.0  #: seconds between changes of the red ball
RED_WARNING = 2.0        #: the next red ball blinks this long before taking the color
RESPAWN_DELAY = 1.0      #: a lost ball is served again after this long
RETURN_POINTS = 10       #: points per ball returned, times the combo multiplier
COMBO_STEP = 5           #: returns in a row needed for each multiplier step
MAX_MULTIPLIER = 5
MAX_ASTEROID_BOUNCES = 6  #: after this many asteroid bounces in a row, a ball heads for the paddle


def multiplier(streak):
    """Combo multiplier for a streak of returns without dropping a ball."""
    return min(MAX_MULTIPLIER, 1 + streak // COMBO_STEP)


def speed_scale(elapsed, pace):
    """How much faster than at the start the balls go after `elapsed` seconds."""
    return min(pace.max_scale, 1 + pace.growth * elapsed)


class Survival(Pong):
    """The survival scene: one endless run until the red ball runs out of lives."""

    MODE = "survival"
    GAME_OVER = "game_over"

    RED = (255, 70, 70)
    #: Asteroids keep farther from the paddle than in the campaign: with a wall
    #: above, low ones would keep balls bouncing up there, away from the player
    OBSTACLE_MARGIN_Y = 200
    WARNING_BLINK_MS = 150   #: blink period of the ball about to turn red
    COMBO_LOST_MS = 700      #: how long the multiplier shows in red after a drop

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def _setup_hud(self):
        super()._setup_hud()
        yellow = UI.COLORS["YELLOW"]
        self.overlay_titles[self.GAME_OVER] = self._title(t("game.game_over"), yellow)
        cx, cy = self.hud_pos["center"]
        self.overlay_buttons[self.GAME_OVER] = [TextButton(
            pos=(cx, cy + 100), text=t("game.continue"),
            font_config=(self.font_path, FONTS.MEDIUM), action=self._end_match,
            hover_color=yellow, audio=self.audio)]

        # The red ball: the same sprite, tinted
        self.red_ball_image = self.images["ball"].copy()
        self.red_ball_image.fill((*self.RED, 255), special_flags=pygame.BLEND_RGBA_MULT)

    def _reset_game(self):
        """Start a new run."""
        difficulty = settings.get("difficulty")
        if difficulty not in PACES:
            difficulty = "normal"
        self.pace = PACES[difficulty]
        self.rng = random.Random()
        self.points = 0
        self.elapsed = 0.0
        self.streak = 0
        self.lives = self.lives_start
        self.level = 1   # kept for the parts of Pong that read it
        self.match_state = self.PLAYING
        self.blink_until = 0
        self.combo_lost_until = 0
        # A fixed layout per difficulty: every run (and every record) faces the same field
        self.obstacles = self._generate_obstacles(
            100 + list(PACES).index(difficulty), self.pace.obstacles)
        self.blocker = None
        self.paddle_x = (self.paddle_min_x + self.paddle_max_x) / 2

        self.balls = []
        self.asteroid_bounces = {}   # Ball -> asteroid bounces since the player last touched it
        self.red = self.next_red = None
        self.red_timer = RED_SWITCH_EVERY
        self.new_ball_timer = NEW_BALL_EVERY
        self._serve(red=True, delay=self.LEVEL_INTRO_DELAY + self.SERVE_DELAY)
        for i in range(1, START_BALLS):
            self._serve(delay=self.LEVEL_INTRO_DELAY + self.SERVE_DELAY + i * self.SERVE_STAGGER)
        self._prepare_banner()
        self.paused = True   # the run waits for the player

    def _start_level(self, number):
        """No levels in survival (also disables the debug level keys)."""

    def _prepare_banner(self):
        self.banner_title = self._title(t("modes.survival"), UI.COLORS["YELLOW"])
        self.banner_name = render_fit(self.font_path, FONTS.LARGE, t("survival.banner_hint"),
                                      UI.COLORS["WHITE"], self.TITLE_MAX_WIDTH)
        self.banner_time = self.BANNER_TIME

    def _record_details(self):
        return {"seconds": int(self.elapsed)}

    # ------------------------------------------------------------------
    # Balls
    # ------------------------------------------------------------------
    def _current_speed(self):
        return self.pace.serve_speed * speed_scale(self.elapsed, self.pace)

    def _serve(self, red=False, delay=None):
        """Serve a ball from the center, toward the wall (giving the player time)."""
        x = GAME.SCREEN_WIDTH / 2 - self.ball_w / 2
        y = (self.FIELD_TOP + self.FIELD_BOTTOM) / 2 - self.ball_h / 2
        ball = Ball(x, y, self.ball_w, self.ball_h, self._current_speed(), direction=-1,
                    serve_delay=self.SERVE_DELAY if delay is None else delay)
        self.balls.append(ball)
        if red:
            self.red = ball
        return ball

    def _return_ball(self, ball):
        """The player returned a ball: angled bounce, current speed, combo points."""
        ball.y = self.paddle_y - ball.h
        ball.bounce_paddle(self.paddle_x, self.paddle_w, True, levels.MAX_BOUNCE_X)
        scale = self._current_speed() / ball.speed
        ball.vx *= scale
        ball.vy *= scale
        self.asteroid_bounces.pop(ball, None)
        self.streak += 1
        self.points += RETURN_POINTS * multiplier(self.streak)
        self.audio.play("hit_player")

    def _drop(self, ball):
        """A ball got past the paddle: the red one costs a life, any one the combo."""
        self.balls.remove(ball)
        self.asteroid_bounces.pop(ball, None)
        self.streak = 0
        self.combo_lost_until = pygame.time.get_ticks() + self.COMBO_LOST_MS
        if ball is self.next_red:
            self.next_red = None
        if ball is not self.red:
            self._serve(delay=RESPAWN_DELAY)
            return

        self.lives -= 1
        self.audio.play_error()
        self.blink_until = pygame.time.get_ticks() + self.HEART_BLINK_MS
        if self.lives <= 0:
            self.match_state = self.GAME_OVER
            self.paused = True
            return
        self._serve(red=True, delay=RESPAWN_DELAY)
        self.next_red = None
        self.red_timer = RED_SWITCH_EVERY

    def _update_balls(self, dt):
        """Move every ball: side walls, the top wall, the paddle and the asteroids."""
        for ball in list(self.balls):
            if self.match_state != self.PLAYING:
                break
            prev_y = ball.y
            ball.move(dt)
            if ball.waiting:
                continue

            self._collide_walls(ball)
            if ball.y < self.FIELD_TOP:
                ball.y = self.FIELD_TOP
                ball.vy = abs(ball.vy)
                self.audio.play_hit()

            # Same crossing test as the campaign: no saves from behind
            if (ball.vy > 0 and prev_y + ball.h <= self.paddle_y < ball.y + ball.h
                    and self._overlaps_x(ball, self.paddle_x, self.paddle_w)):
                self._return_ball(ball)
            elif ball.y > self.FIELD_BOTTOM:
                self._drop(ball)
                continue

            self._collide_obstacles(ball)

    def _collide_obstacles(self, ball):
        """Asteroid bounces, plus a way out of traps.

        With a wall above, a ball can get caught bouncing between asteroids
        and the wall without ever coming down. After a few asteroid bounces
        in a row, the next one sends it toward the paddle.
        """
        before = (ball.vx, ball.vy)
        super()._collide_obstacles(ball)
        if (ball.vx, ball.vy) == before:
            return
        bounces = self.asteroid_bounces.get(ball, 0) + 1
        if bounces >= MAX_ASTEROID_BOUNCES:
            angle = math.radians(self.rng.uniform(-35, 35))   # from the vertical, downward
            speed = ball.speed
            ball.vx, ball.vy = speed * math.sin(angle), speed * math.cos(angle)
            bounces = 0
        self.asteroid_bounces[ball] = bounces

    def _update_timers(self, dt):
        """New balls over time, and the red color moving to another ball."""
        if len(self.balls) < self.pace.max_balls:
            self.new_ball_timer -= dt
            if self.new_ball_timer <= 0:
                self._serve()
                self.new_ball_timer = NEW_BALL_EVERY

        self.red_timer -= dt
        if self.red_timer <= RED_WARNING and self.next_red is None:
            candidates = [b for b in self.balls if b is not self.red and not b.waiting]
            if candidates:
                self.next_red = self.rng.choice(candidates)
            else:
                self.red_timer = RED_WARNING + 1.0   # nobody to pass it to yet: try later
        if self.red_timer <= 0 and self.next_red is not None:
            self.red, self.next_red = self.next_red, None
            self.red_timer = RED_SWITCH_EVERY

    # ------------------------------------------------------------------
    # Scene hooks
    # ------------------------------------------------------------------
    def _toggle_pause(self):
        if self.match_state == self.GAME_OVER:
            self._end_match()
        else:
            super()._toggle_pause()

    def on_update(self):
        self._update_cursor()
        if self.paused:
            return
        dt = min(self.director.dt, self.MAX_DT)
        self.banner_time = max(0.0, self.banner_time - dt)
        self.elapsed += dt
        self.starfield.update(dt)
        for obstacle in self.obstacles:
            obstacle.update(dt)
        self._update_paddle(dt)
        self._update_balls(dt)
        if self.match_state == self.PLAYING:
            self._update_timers(dt)

    def on_draw(self, screen):
        screen.blit(self.images["background"], (0, 0))
        self.starfield.draw(screen)

        for obstacle in self.obstacles:
            self._draw_obstacle(screen, obstacle)

        now = pygame.time.get_ticks()
        blink_on = (now // self.BALL_BLINK_MS) % 2 == 0
        warning_on = (now // self.WARNING_BLINK_MS) % 2 == 0
        for ball in self.balls:
            if ball.waiting and not self.paused and not blink_on:
                continue   # a ball about to be served blinks
            red = ball is self.red or (ball is self.next_red and warning_on)
            self._draw_ball_trail(screen, ball, self.RED if red else None)
            screen.blit(self.red_ball_image if red else self.images["ball"], (ball.x, ball.y))
        screen.blit(self.images["paddle"], (self.paddle_x, self.paddle_y))

        self._draw_hud(screen)

        if self.match_state in self.overlay_titles:
            self._draw_overlay(screen)
        elif self.paused:
            self._draw_pause(screen)
        elif self.banner_time > 0:
            fade = min(1.0, self.banner_time / self.BANNER_FADE)
            self._draw_banner(screen, int(255 * fade))

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def _draw_overlay(self, screen):
        """Game over: final score and time survived."""
        screen.blit(self.overlay_backdrop, (0, 0))
        cx, cy = self.hud_pos["center"]
        title = self.overlay_titles[self.match_state]
        screen.blit(title, title.get_rect(center=(cx, cy - 40)))
        result = self._text("overlay_result",
                            t("survival.result", points=self.points, time=self._time_text()),
                            self.font_hud, UI.COLORS["WHITE"])
        screen.blit(result, result.get_rect(center=(cx, cy + 40)))
        for button in self.overlay_buttons[self.match_state]:
            button.draw(screen)

    def _time_text(self):
        seconds = int(self.elapsed)
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def _draw_hud(self, screen):
        """Hearts, points, the combo multiplier and the time survived."""
        white = UI.COLORS["WHITE"]
        hx, hy = self.hud_pos["hearts"]
        spacing = self.HEART_SIZE + 6
        for i in range(self.lives_start):
            screen.blit(self._heart_image(i), (hx + i * spacing, hy))

        points = self._text("points", f"{self.points:04d}", self.font_hud, white)
        screen.blit(points, points.get_rect(midleft=self.hud_pos["points"]))

        combo_lost = pygame.time.get_ticks() < self.combo_lost_until
        color = self.RED if combo_lost else UI.COLORS["YELLOW"]
        combo = self._text(f"combo_{combo_lost}", f"x{multiplier(self.streak)}",
                           self.font_score, color)
        screen.blit(combo, combo.get_rect(center=self.hud_pos["score"]))

        clock = self._text("time", self._time_text(), self.font_hud, white)
        screen.blit(clock, clock.get_rect(midleft=self.hud_pos["level_label"]))

        for button in self.hud_buttons:
            button.draw(screen)
