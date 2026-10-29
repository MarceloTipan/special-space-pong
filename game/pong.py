"""Game scene: the match itself.

Ball physics with angular paddle bounces, an enemy paddle driven by a
deliberately imperfect AI, multiball in the last levels, procedurally
generated asteroids, a top HUD bar, pause and per-level result screens.
The player's paddle follows the hand through the webcam (MotionController),
the mouse, or the arrow keys, depending on the control chosen in Settings.
"""

import math
import random

import pygame

from core import Scene
from game import motion
from game.ball import Ball
from game.obstacle import Obstacle
from game.starfield import Starfield
from ui import TextButton
from ui.pause_button import PauseButton
from utils import settings
from utils.i18n import t
from config import FONTS, PATHS, UI, GAME


class Pong(Scene):
    """The game scene: one match, played level by level."""

    # --- Match states ---
    PLAYING = "playing"
    LEVEL_WON = "level_won"
    LEVEL_LOST = "level_lost"
    VICTORY = "victory"

    #: Enables the level-skip keys (UP/DOWN). Set GAME.DEBUG = True while developing.
    DEBUG = getattr(GAME, "DEBUG", False)

    #: Largest timestep simulated in one frame. A hitch (e.g. right after the
    #: loading screen) would otherwise move a ball far enough to tunnel
    #: through an obstacle.
    MAX_DT = 0.05

    # --- Difficulty ---
    LIVES_MIN, LIVES_MAX = 2, 5
    #: Lives, goals to win a level and AI multipliers per difficulty.
    #: enemy_error > 1 = clumsier enemy; enemy_speed > 1 = faster enemy.
    DIFFICULTY_PRESETS = {
        "easy":   {"lives": 5, "goals": 3, "enemy_error": 1.4, "enemy_speed": 0.85},
        "normal": {"lives": 3, "goals": 5, "enemy_error": 1.0, "enemy_speed": 1.0},
        "hard":   {"lives": 2, "goals": 7, "enemy_error": 0.7, "enemy_speed": 1.15},
    }

    # --- Levels and scoring ---
    LEVEL_MAX = 10
    BASE_SPEED = 80          #: per-axis ball speed at level 0 (px/s)
    SPEED_PER_LEVEL = 30     #: per-axis speed added each level
    GOAL_POINTS = 50         #: points for each goal scored
    POINT_EVERY = 5          #: seconds of play per survival point
    MAX_BOUNCE_X = 0.75      #: max horizontal share of a paddle bounce
    SERVE_DELAY = 0.6        #: seconds a new ball blinks before launching
    SERVE_STAGGER = 0.4      #: extra wait between balls served together

    # --- Enemy AI: three knobs that scale with the level. Misses emerge
    # from these limits, never from a per-frame dice roll ---
    ENEMY_SPEED_BASE = 200              #: enemy paddle speed (px/s)
    ENEMY_SPEED_PER_LEVEL = 30
    ENEMY_ERROR_BASE = 130              #: aim error (px), rolled once per play
    ENEMY_ERROR_PER_LEVEL = 11
    ENEMY_REACT_FRACTION_BASE = 0.75    #: reacts once the ball is above this fraction of the field
    ENEMY_REACT_PER_LEVEL = 0.04

    # --- Procedural obstacles ---
    OBSTACLE_START_LEVEL = 3
    OBSTACLE_MAX = 5
    OBSTACLE_W = (70, 130)       #: width range
    OBSTACLE_H = (16, 26)        #: height range
    OBSTACLE_GAP = 60            #: min spacing between obstacles and from the serve point
    OBSTACLE_MARGIN_Y = 110      #: obstacle-free band next to each paddle

    # --- Field geometry, relative to the screen ---
    FIELD_LEFT = 45
    FIELD_RIGHT = GAME.SCREEN_WIDTH - 45
    FIELD_TOP = 90
    FIELD_BOTTOM = GAME.SCREEN_HEIGHT - 45

    # --- Paddle control ---
    CONTROL_CAMERA, CONTROL_MOUSE, CONTROL_KEYBOARD = "camera", "mouse", "keyboard"
    CONTROLS = (CONTROL_CAMERA, CONTROL_MOUSE, CONTROL_KEYBOARD)
    PADDLE_KEY_SPEED = 400    #: keyboard paddle speed (px/s)
    PADDLE_MAX_SPEED = 1600   #: speed cap when following the mouse or the hand (px/s)
    #: How fast the paddle catches up with its target (1/s). The hand gets a
    #: softer follow because its detection is noisier than the mouse.
    FOLLOW_RATE = {CONTROL_MOUSE: 30.0, CONTROL_CAMERA: 14.0}
    PREVIEW_SIZE = (192, 144)   #: camera preview on the pause screen

    # --- HUD ---
    HUD_CENTER_Y = 30
    HEART_SIZE = 32
    HEART_BLINK_MS = 720
    HEART_BLINK_INTERVAL = 120
    BALL_BLINK_MS = 100      #: blink period of a ball waiting to be served

    # ------------------------------------------------------------------
    # Loading (consumed step by step by LoadingScreen)
    # ------------------------------------------------------------------
    @classmethod
    def load_steps(cls, director):
        """Generator that loads the scene in steps, yielding progress (0-1)."""
        yield 0.05
        images = cls._load_images()
        yield 0.35
        detector = cls._make_detector()   # the slowest step: opening the camera
        yield 0.95
        return cls(director, images=images, detector=detector)

    @classmethod
    def _load_images(cls):
        """Load and prepare every image the scene uses."""
        def load(path):
            return pygame.image.load(path).convert_alpha()

        heart_size = (cls.HEART_SIZE, cls.HEART_SIZE)
        return {
            "background": pygame.transform.scale(
                pygame.image.load(PATHS.IMAGE_PATH_GAME).convert(), GAME.SCREEN_SIZE),
            "ball": load(PATHS.IMAGE_PATH_BALL),
            "paddle_top": load(PATHS.IMAGE_PATH_PADDLE_TOP),
            "paddle": load(PATHS.IMAGE_PATH_PADDLE),
            "heart": pygame.transform.smoothscale(load(PATHS.IMAGE_PATH_HEART), heart_size),
            "heart_empty": pygame.transform.smoothscale(
                load(PATHS.IMAGE_PATH_HEART_EMPTY), heart_size),
            "asteroid": cls._load_asteroid(),
        }

    @classmethod
    def _make_detector(cls):
        """Open the camera only if the camera control is selected."""
        if settings.get("control") != cls.CONTROL_CAMERA:
            return None
        return motion.MotionController(mirror=not settings.get("camera_invert"))

    @staticmethod
    def _load_asteroid():
        """Load the asteroid sprite, or None so obstacles fall back to neon blocks."""
        path = getattr(PATHS, "IMAGE_PATH_ASTEROID", None)
        if not path:
            return None
        try:
            return pygame.image.load(str(path)).convert_alpha()
        except (pygame.error, OSError):
            return None

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def __init__(self, director, images=None, detector=None):
        """Build the scene.

        Args:
            director: The game Director.
            images: Images preloaded by load_steps (loaded here if None).
            detector: MotionController preloaded by load_steps (opened here if
                the camera control is selected and none was given).
        """
        super().__init__(director)
        director.status = GAME.STATUS_GAME

        self.images = images if images is not None else self._load_images()
        self.audio = director.audio
        self.starfield = Starfield(GAME.SCREEN_WIDTH, GAME.SCREEN_HEIGHT)
        self._setup_control(detector)

        preset = self.DIFFICULTY_PRESETS.get(
            settings.get("difficulty"), self.DIFFICULTY_PRESETS["normal"])
        self.lives_start = max(self.LIVES_MIN, min(self.LIVES_MAX, preset["lives"]))
        self.goals_to_win = preset["goals"]
        self.enemy_error_mult = preset["enemy_error"]
        self.enemy_speed_mult = preset["enemy_speed"]

        self._text_cache = {}    # HUD text, re-rendered only when it changes
        self._trail_cache = {}   # trail dot surfaces, by (radius, alpha)

        self._setup_geometry()
        self._setup_hud()
        self._reset_game()

    def _setup_control(self, detector):
        """Pick the paddle control, falling back to the mouse without a camera."""
        self.control = settings.get("control")
        if self.control not in self.CONTROLS:
            self.control = self.CONTROL_MOUSE
        if self.control == self.CONTROL_CAMERA and detector is None:
            detector = self._make_detector()
        self.detector = detector
        self.camera_missing = (self.control == self.CONTROL_CAMERA
                               and not (detector and detector.available))
        if self.camera_missing:
            self.control = self.CONTROL_MOUSE
        self._cursor_visible = True

    def _setup_geometry(self):
        """Cache sprite sizes and derive paddle positions and limits."""
        self.ball_w = self.images["ball"].get_width()
        self.ball_h = self.images["ball"].get_height()
        self.paddle_w = self.images["paddle"].get_width()
        self.enemy_w = self.images["paddle_top"].get_width()

        self.paddle_y = self.FIELD_BOTTOM - self.images["paddle"].get_height() - 10
        self.paddle_min_x = self.FIELD_LEFT
        self.paddle_max_x = self.FIELD_RIGHT - self.paddle_w

        self.enemy_y = self.FIELD_TOP + 5
        self.enemy_bottom = self.enemy_y + self.images["paddle_top"].get_height()
        self.enemy_min_x = self.FIELD_LEFT
        self.enemy_max_x = self.FIELD_RIGHT - self.enemy_w

    def _setup_hud(self):
        """Fonts, pre-rendered texts, HUD positions and buttons."""
        font_path = str(PATHS.FONT_PATH_ARCADE)
        self.font_hint = pygame.font.Font(font_path, FONTS.SMALL)
        self.font_hud = pygame.font.Font(font_path, FONTS.MEDIUM)
        self.font_score = pygame.font.Font(font_path, FONTS.LARGE)
        self.font_big = pygame.font.Font(font_path, FONTS.LARGE * 2)

        yellow, white, gray = UI.COLORS["YELLOW"], UI.COLORS["WHITE"], UI.COLORS["GRAY"]
        self.text_pause = self.font_big.render(t("game.paused"), True, yellow)
        self.text_pause_hint = self.font_hint.render(t("game.pause_hint"), True, white)
        # Which control is active (or why the camera isn't being used)
        control_line = (t("game.no_camera") if self.camera_missing
                        else t("game.control_hint", mode=t(f"control.{self.control}")))
        self.text_control = self.font_hint.render(control_line, True, gray)
        self.overlay_titles = {
            self.LEVEL_WON: self.font_big.render(t("game.level_won"), True, yellow),
            self.LEVEL_LOST: self.font_big.render(t("game.level_lost"), True, yellow),
            self.VICTORY: self.font_big.render(t("game.victory"), True, yellow),
        }
        self.label_level = self.font_hud.render(t("game.hud_level"), True, white)

        self.overlay_backdrop = pygame.Surface(GAME.SCREEN_SIZE)
        self.overlay_backdrop.set_alpha(160)
        self.overlay_backdrop.fill((0, 0, 0))

        w = GAME.SCREEN_WIDTH
        self.hud_pos = {
            "hearts": (int(w * 0.16), self.HUD_CENTER_Y - self.HEART_SIZE // 2),
            "points": (int(w * 0.31), self.HUD_CENTER_Y),
            "score": (w // 2, self.HUD_CENTER_Y),
            "level_label": (int(w * 0.61), self.HUD_CENTER_Y),
            "level_value": (int(w * 0.68), self.HUD_CENTER_Y),
            "center": (w // 2, GAME.SCREEN_HEIGHT // 2 - 40),
        }

        self.hud_buttons = [
            PauseButton(
                pos=(int(w * 0.79), self.HUD_CENTER_Y), size=36,
                action=self._toggle_pause,
                is_paused=lambda: self.paused,
                audio=self.audio),
            TextButton(
                pos=(int(w * 0.90), self.HUD_CENTER_Y),
                text=t("menu.exit"),
                font_config=(font_path, FONTS.MEDIUM),
                action=self._end_match,
                base_color=gray,
                hover_color=white,
                audio=self.audio),
        ]

        cx, cy = self.hud_pos["center"]

        def overlay_button(y_offset, text_key, action):
            return TextButton(
                pos=(cx, cy + y_offset), text=t(text_key),
                font_config=(font_path, FONTS.MEDIUM), action=action,
                hover_color=yellow, audio=self.audio)

        self.overlay_buttons = {
            self.LEVEL_WON: [overlay_button(80, "game.continue", self._on_continue)],
            self.LEVEL_LOST: [overlay_button(80, "game.retry", self._on_retry),
                              overlay_button(130, "menu.exit", self._end_match)],
            self.VICTORY: [overlay_button(80, "menu.exit", self._end_match)],
        }

    # ------------------------------------------------------------------
    # Match flow
    # ------------------------------------------------------------------
    def _reset_game(self):
        """Start a whole new match from level 1."""
        self.points = 0
        self._start_level(1)

    def _start_level(self, level):
        """Prepare a level: full hearts, clean scoreboard and a fresh serve."""
        # Score checkpoint, restored on retry: without it the record could be
        # inflated by replaying the same level over and over
        self.points_checkpoint = self.points
        self.level = max(1, min(self.LEVEL_MAX, level))
        self.lives = self.lives_start
        self.goals_player = 0
        self.goals_enemy = 0
        self.point_timer = 0.0
        self.blink_until = 0
        self.match_state = self.PLAYING
        self.paddle_x = (self.paddle_min_x + self.paddle_max_x) / 2
        self.enemy_x = (self.enemy_min_x + self.enemy_max_x) / 2
        self.obstacles = self._generate_obstacles(self.level)
        self.balls = []
        self._refill_balls()
        self.paused = True   # the level waits for the player

    def _on_continue(self):
        self._start_level(self.level + 1)
        self.paused = False

    def _on_retry(self):
        self.points = self.points_checkpoint
        self._start_level(self.level)
        self.paused = False

    def _toggle_pause(self):
        """SPACE or the pause button: toggle the pause while playing, or run
        the result screen's main action (continue, retry or finish)."""
        primary_action = {
            self.LEVEL_WON: self._on_continue,
            self.LEVEL_LOST: self._on_retry,
            self.VICTORY: self._end_match,
        }.get(self.match_state)
        if primary_action:
            primary_action()
        else:
            self.paused = not self.paused

    def _end_match(self):
        """End the match and show the results.

        Goes to initials entry if the score makes the high score table,
        otherwise straight to the table, with this score shown below it.
        """
        if self.detector is not None:
            self.detector.release()
        self._set_cursor_visible(True)
        # Local imports: the menu imports this module (through the loading
        # screen), so importing these at the top would be circular
        from scenes import highscores_screen, name_entry_screen
        from utils import highscores
        if highscores.qualifies(self.points):
            scene = name_entry_screen.NameEntry(self.director, self.points, self.level)
        else:
            scene = highscores_screen.Highscores(self.director, last_score=self.points)
        self.director.change_scene(scene)

    # ------------------------------------------------------------------
    # Balls and scoring
    # ------------------------------------------------------------------
    def _level_speed(self):
        """Total ball speed for the current level (diagonal of the per-axis speed)."""
        component = self.BASE_SPEED + self.SPEED_PER_LEVEL * self.level
        return math.hypot(component, component)

    def _balls_for_level(self):
        """Simultaneous balls: the last two levels add a second and a third."""
        if self.level >= self.LEVEL_MAX:
            return 3
        if self.level >= self.LEVEL_MAX - 1:
            return 2
        return 1

    def _refill_balls(self):
        """Serve new balls from the center until the level's ball count is met.

        Balls served together launch one after another, so a multiball
        serve stays readable.
        """
        missing = self._balls_for_level() - len(self.balls)
        if missing <= 0:
            return
        x = GAME.SCREEN_WIDTH / 2 - self.ball_w / 2
        y = (self.FIELD_TOP + self.FIELD_BOTTOM) / 2 - self.ball_h / 2
        for i in range(missing):
            delay = self.SERVE_DELAY + i * self.SERVE_STAGGER
            self.balls.append(Ball(x, y, self.ball_w, self.ball_h,
                                   self._level_speed(), serve_delay=delay))
        self._roll_enemy_error()

    def _player_scores(self, ball):
        """The enemy missed: goal for the player, and maybe the level is won."""
        self.balls.remove(ball)
        self.goals_player += 1
        self.points += self.GOAL_POINTS
        self.audio.play_goal()

        if self.goals_player >= self.goals_to_win:
            self.match_state = self.VICTORY if self.level >= self.LEVEL_MAX else self.LEVEL_WON
            self.paused = True
        else:
            self._refill_balls()

    def _lose_life(self, ball):
        """The player missed: lose a heart; with none left the level is lost."""
        self.balls.remove(ball)
        self.lives -= 1
        self.goals_enemy += 1
        self.audio.play_error()
        self.blink_until = pygame.time.get_ticks() + self.HEART_BLINK_MS

        if self.lives <= 0:
            self.match_state = self.LEVEL_LOST
            self.paused = True
        else:
            self._refill_balls()

    def _update_survival_points(self, dt):
        """Award one point for every POINT_EVERY seconds of play."""
        self.point_timer += dt
        while self.point_timer >= self.POINT_EVERY:
            self.point_timer -= self.POINT_EVERY
            self.points += 1

    # ------------------------------------------------------------------
    # Obstacles
    # ------------------------------------------------------------------
    def _obstacle_count(self, level):
        """Obstacles for a level: one more every two levels, capped."""
        if level < self.OBSTACLE_START_LEVEL:
            return 0
        return min(self.OBSTACLE_MAX, 1 + (level - self.OBSTACLE_START_LEVEL) // 2)

    def _generate_obstacles(self, level):
        """Seeded procedural placement by rejection sampling.

        The same level always produces the same layout (reproducible and
        balanceable): each candidate is drawn at random, then rejected if it
        is too close to the serve point or to another obstacle.
        """
        count = self._obstacle_count(level)
        if count == 0:
            return []

        rng = random.Random(1000 + level)   # seed derived from the level
        zone_top = self.enemy_bottom + self.OBSTACLE_MARGIN_Y
        zone_bottom = self.paddle_y - self.OBSTACLE_MARGIN_Y
        serve_x = GAME.SCREEN_WIDTH / 2
        serve_y = (self.FIELD_TOP + self.FIELD_BOTTOM) / 2

        obstacles, rects = [], []
        for _ in range(200):   # bounded attempts, so a crowded layout can't hang
            if len(obstacles) == count:
                break
            w = rng.randint(*self.OBSTACLE_W)
            h = rng.randint(*self.OBSTACLE_H)
            candidate = pygame.Rect(rng.randint(self.FIELD_LEFT, self.FIELD_RIGHT - w),
                                    rng.randint(zone_top, zone_bottom - h), w, h)

            near_serve = candidate.inflate(
                self.OBSTACLE_GAP * 2, self.OBSTACLE_GAP * 2).collidepoint(serve_x, serve_y)
            too_close = any(
                candidate.colliderect(r.inflate(self.OBSTACLE_GAP, self.OBSTACLE_GAP))
                for r in rects)
            if near_serve or too_close:
                continue

            rects.append(candidate)
            # Spin speed, direction and start angle also come from the seeded rng
            spin = rng.choice((-1, 1)) * rng.uniform(12, 30)
            obstacles.append(Obstacle(candidate, self.images.get("asteroid"),
                                      spin_speed=spin, angle_offset=rng.uniform(0, 360)))
        return obstacles

    # ------------------------------------------------------------------
    # Enemy AI
    # ------------------------------------------------------------------
    def _enemy_speed(self):
        base = self.ENEMY_SPEED_BASE + self.ENEMY_SPEED_PER_LEVEL * self.level
        return base * self.enemy_speed_mult

    def _enemy_react_y(self):
        """Field height above which the enemy starts chasing the ball."""
        fraction = max(0.2, self.ENEMY_REACT_FRACTION_BASE
                       - self.ENEMY_REACT_PER_LEVEL * self.level)
        return self.FIELD_TOP + (self.FIELD_BOTTOM - self.FIELD_TOP) * fraction

    def _roll_enemy_error(self):
        """Roll the enemy's aim error for the current play."""
        max_error = max(15, (self.ENEMY_ERROR_BASE
                             - self.ENEMY_ERROR_PER_LEVEL * self.level)
                        * self.enemy_error_mult)
        self.enemy_aim_error = random.uniform(-max_error, max_error)

    def _ball_for_enemy(self):
        """The ball that will reach the enemy first (soonest, not nearest).

        Returns None if no ball is heading toward the enemy.
        """
        best, best_time = None, float("inf")
        for ball in self.balls:
            arrival = ball.time_to_reach_y(self.enemy_bottom)
            if arrival < best_time:
                best, best_time = ball, arrival
        return best

    def _update_enemy(self, dt):
        """Chase the incoming ball with limited speed and a fixed aim error;
        drift back to the center when nothing is coming."""
        target_ball = self._ball_for_enemy()
        if target_ball is not None and target_ball.cy < self._enemy_react_y():
            target = target_ball.cx - self.enemy_w / 2 + self.enemy_aim_error
        else:
            target = (self.enemy_min_x + self.enemy_max_x) / 2

        max_step = self._enemy_speed() * dt
        self.enemy_x += max(-max_step, min(max_step, target - self.enemy_x))
        self.enemy_x = max(self.enemy_min_x, min(self.enemy_max_x, self.enemy_x))

    # ------------------------------------------------------------------
    # Physics
    # ------------------------------------------------------------------
    def _update_paddle(self, dt):
        if self.control == self.CONTROL_KEYBOARD:
            keys = pygame.key.get_pressed()
            direction = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
            self.paddle_x += direction * self.PADDLE_KEY_SPEED * dt
        else:
            target = self._control_target()
            if target is not None:
                # Ease toward the target (frame-rate independent), capped so
                # the paddle never teleports into a ball
                follow = 1 - math.exp(-self.FOLLOW_RATE[self.control] * dt)
                step = (target - self.paddle_w / 2 - self.paddle_x) * follow
                max_step = self.PADDLE_MAX_SPEED * dt
                self.paddle_x += max(-max_step, min(max_step, step))

        self.paddle_x = max(self.paddle_min_x, min(self.paddle_max_x, self.paddle_x))

    def _control_target(self):
        """Screen x the paddle's center should move to (None: stay put)."""
        if self.control == self.CONTROL_MOUSE:
            return pygame.mouse.get_pos()[0]
        hand_x = self.detector.hand_x
        if hand_x is None:
            return None   # the hand hasn't been seen yet
        return self.FIELD_LEFT + hand_x * (self.FIELD_RIGHT - self.FIELD_LEFT)

    def _set_cursor_visible(self, visible):
        if visible != self._cursor_visible:
            pygame.mouse.set_visible(visible)
            self._cursor_visible = visible

    def _update_cursor(self):
        """Hide the cursor over the field while playing with the mouse."""
        over_field = pygame.mouse.get_pos()[1] > self.FIELD_TOP
        playing_with_mouse = self.control == self.CONTROL_MOUSE and not self.paused
        self._set_cursor_visible(not (playing_with_mouse and over_field))

    def _update_balls(self, dt):
        """Move every ball and resolve its collisions.

        Iterates over a copy because goals remove balls from the list.
        """
        for ball in list(self.balls):
            if self.match_state != self.PLAYING:
                break   # an earlier goal this frame already ended the level
            prev_y = ball.y
            ball.move(dt)
            if ball.waiting:
                continue

            self._collide_walls(ball)

            # A paddle only returns a ball whose edge crosses the paddle's face
            # THIS frame. Testing just "is it past the line" let a paddle
            # sliding under a ball that had already slipped by save it from behind.
            if (ball.vy < 0 and prev_y >= self.enemy_bottom > ball.y
                    and self._overlaps_x(ball, self.enemy_x, self.enemy_w)):
                ball.y = self.enemy_bottom
                self._bounce_off_paddle(ball, self.enemy_x, self.enemy_w, upward=False)
            elif ball.y < self.FIELD_TOP:
                self._player_scores(ball)
                continue

            if (ball.vy > 0 and prev_y + ball.h <= self.paddle_y < ball.y + ball.h
                    and self._overlaps_x(ball, self.paddle_x, self.paddle_w)):
                ball.y = self.paddle_y - ball.h
                self._bounce_off_paddle(ball, self.paddle_x, self.paddle_w, upward=True)
            elif ball.y > self.FIELD_BOTTOM:
                self._lose_life(ball)
                continue

            self._collide_obstacles(ball)

    @staticmethod
    def _overlaps_x(ball, x, width):
        """Whether the ball overlaps the horizontal span [x, x + width]."""
        return ball.x + ball.w > x and ball.x < x + width

    def _collide_walls(self, ball):
        # Set the direction explicitly rather than flipping it, so a ball that
        # ends up past a wall can never get stuck bouncing inside it
        if ball.x > self.FIELD_RIGHT - ball.w:
            ball.x = self.FIELD_RIGHT - ball.w
            ball.vx = -abs(ball.vx)
        elif ball.x < self.FIELD_LEFT:
            ball.x = self.FIELD_LEFT
            ball.vx = abs(ball.vx)
        else:
            return
        self.audio.play_hit()

    def _bounce_off_paddle(self, ball, paddle_x, paddle_w, upward):
        """Angular bounce off a paddle (computed by the Ball) plus its sound."""
        ball.bounce_paddle(paddle_x, paddle_w, upward, self.MAX_BOUNCE_X)
        self.audio.play("hit_player" if upward else "hit_enemy")
        if upward:
            self._roll_enemy_error()   # each return is a new play for the AI

    def _collide_obstacles(self, ball):
        """Bounce a ball off obstacles along the axis of least penetration.

        The axis with the smaller overlap is the side the ball came in from:
        that velocity component is reflected and the ball pushed out.
        """
        rect = ball.rect
        for obstacle in self.obstacles:
            if not rect.colliderect(obstacle.rect):
                continue

            overlap_x = min(rect.right, obstacle.right) - max(rect.left, obstacle.left)
            overlap_y = min(rect.bottom, obstacle.bottom) - max(rect.top, obstacle.top)
            if overlap_x < overlap_y:
                if rect.centerx < obstacle.centerx:
                    ball.x, ball.vx = obstacle.left - ball.w, -abs(ball.vx)
                else:
                    ball.x, ball.vx = obstacle.right, abs(ball.vx)
            else:
                if rect.centery < obstacle.centery:
                    ball.y, ball.vy = obstacle.top - ball.h, -abs(ball.vy)
                else:
                    ball.y, ball.vy = obstacle.bottom, abs(ball.vy)

            self.audio.play("hit_obstacle")
            break   # one bounce per frame is enough

    # ------------------------------------------------------------------
    # Scene hooks
    # ------------------------------------------------------------------
    def on_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self._toggle_pause()
            elif event.key == pygame.K_ESCAPE:
                self._end_match()
            elif self.DEBUG and event.key in (pygame.K_UP, pygame.K_KP_PLUS):
                self._start_level(self.level + 1)
            elif self.DEBUG and event.key in (pygame.K_DOWN, pygame.K_KP_MINUS):
                self._start_level(self.level - 1)
        elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            mouse_pos = pygame.mouse.get_pos()
            clicked = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
            for button in (*self.hud_buttons, *self.overlay_buttons.get(self.match_state, ())):
                button.update(mouse_pos, clicked)

    def on_update(self):
        self._update_cursor()
        if self.paused:
            return
        dt = min(self.director.dt, self.MAX_DT)
        self.starfield.update(dt)
        for obstacle in self.obstacles:
            obstacle.update(dt)
        self._update_paddle(dt)
        self._update_enemy(dt)
        self._update_balls(dt)
        if not self.paused:   # a goal this frame may have ended the level
            self._update_survival_points(dt)

    def on_draw(self, screen):
        screen.blit(self.images["background"], (0, 0))
        self.starfield.draw(screen)

        for obstacle in self.obstacles:
            self._draw_obstacle(screen, obstacle)

        blink_on = (pygame.time.get_ticks() // self.BALL_BLINK_MS) % 2 == 0
        for ball in self.balls:
            if ball.waiting and not self.paused and not blink_on:
                continue   # a ball about to be served blinks
            self._draw_ball_trail(screen, ball)
            screen.blit(self.images["ball"], (ball.x, ball.y))
        screen.blit(self.images["paddle_top"], (self.enemy_x, self.enemy_y))
        screen.blit(self.images["paddle"], (self.paddle_x, self.paddle_y))

        self._draw_hud(screen)

        if self.match_state in self.overlay_titles:
            self._draw_overlay(screen)
        elif self.paused:
            self._draw_pause(screen)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def _text(self, key, text, font, color):
        """Render text through a cache, re-rendering only when it changes."""
        cached = self._text_cache.get(key)
        if cached is None or cached[0] != text:
            cached = (text, font.render(text, True, color))
            self._text_cache[key] = cached
        return cached[1]

    def _trail_dot(self, radius, alpha):
        """A translucent trail dot, created once per (radius, alpha) and reused."""
        dot = self._trail_cache.get((radius, alpha))
        if dot is None:
            dot = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(dot, (*UI.COLORS["WHITE"], alpha), (radius, radius), radius)
            self._trail_cache[(radius, alpha)] = dot
        return dot

    def _draw_ball_trail(self, screen, ball):
        """Shrinking, fading dots behind the ball (older ones smaller and fainter)."""
        n = len(ball.trail)
        if n < 2:
            return
        base = max(ball.w, ball.h) / 2
        for i, (tx, ty) in enumerate(ball.trail):
            frac = (i + 1) / n   # oldest -> newest
            radius = max(1, int(base * frac * 0.8))
            screen.blit(self._trail_dot(radius, int(120 * frac)), (tx - radius, ty - radius))

    def _draw_obstacle(self, screen, obstacle):
        """Draw an asteroid sprite, or a neon block if there is no sprite."""
        if obstacle.frames is not None:
            obstacle.draw(screen)
            return
        neon = UI.COLORS.get("NEON_BLUE", (80, 200, 255))
        pygame.draw.rect(screen, tuple(c // 4 for c in neon), obstacle.rect, border_radius=6)
        pygame.draw.rect(screen, neon, obstacle.rect, width=3, border_radius=6)

    def _draw_pause(self, screen):
        cx, cy = self.hud_pos["center"]
        screen.blit(self.text_pause, self.text_pause.get_rect(center=(cx, cy)))
        screen.blit(self.text_pause_hint, self.text_pause_hint.get_rect(center=(cx, cy + 70)))
        screen.blit(self.text_control, self.text_control.get_rect(center=(cx, cy + 105)))
        if self.control == self.CONTROL_CAMERA:
            self._draw_camera_preview(screen, (cx, cy + 230))

    def _draw_camera_preview(self, screen, center):
        """What the camera sees, its active zone and where it detects the hand.

        Lets the player check that the camera is picking them up before
        playing: the yellow line is the detected hand, the gray lines mark
        the zone that covers the whole field.
        """
        frame = self.detector.preview
        if frame is None:
            return
        h, w = frame.shape[:2]
        image = pygame.transform.scale(
            pygame.image.frombuffer(frame.tobytes(), (w, h), "RGB"), self.PREVIEW_SIZE)
        rect = image.get_rect(center=center)
        screen.blit(image, rect)

        gray, yellow = UI.COLORS["GRAY"], UI.COLORS["YELLOW"]
        pygame.draw.rect(screen, gray, rect, width=2)
        margin = int(rect.width * (1 - self.detector.REACH) / 2)
        for x in (rect.left + margin, rect.right - margin):
            pygame.draw.line(screen, gray, (x, rect.top), (x, rect.bottom), 1)
        if self.detector.raw_x is not None:
            x = rect.left + int(self.detector.raw_x * rect.width)
            pygame.draw.line(screen, yellow, (x, rect.top), (x, rect.bottom), 3)

    def _draw_overlay(self, screen):
        """Result screen: dimmed backdrop, title, final score and buttons."""
        screen.blit(self.overlay_backdrop, (0, 0))
        cx, cy = self.hud_pos["center"]

        title = self.overlay_titles[self.match_state]
        screen.blit(title, title.get_rect(center=(cx, cy - 40)))

        score = self._text("overlay_score", f"{self.goals_player}  |  {self.goals_enemy}",
                           self.font_score, UI.COLORS["WHITE"])
        screen.blit(score, score.get_rect(center=(cx, cy + 25)))

        for button in self.overlay_buttons[self.match_state]:
            button.draw(screen)

    def _heart_image(self, index):
        """Full or empty heart; the one just lost blinks for a moment."""
        now = pygame.time.get_ticks()
        if index == self.lives and now < self.blink_until:
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

        points = self._text("points", f"{self.points:04d}", self.font_hud, white)
        screen.blit(points, points.get_rect(midleft=self.hud_pos["points"]))

        score = self._text("score", f"{self.goals_player}  |  {self.goals_enemy}",
                           self.font_score, red)
        screen.blit(score, score.get_rect(center=self.hud_pos["score"]))

        screen.blit(self.label_level,
                    self.label_level.get_rect(midleft=self.hud_pos["level_label"]))
        level = self._text("level", f"{self.level:02d}", self.font_hud, white)
        screen.blit(level, level.get_rect(midleft=self.hud_pos["level_value"]))

        for button in self.hud_buttons:
            button.draw(screen)