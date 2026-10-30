"""Game scene: the match itself.

Ball physics with angular paddle bounces and rallies that speed up, an
enemy paddle whose misses depend on how good the player's shots are,
multiball, procedurally generated asteroids, a five-level campaign plus a
secret level, a top HUD bar, pause and per-level result screens. The
player's paddle follows the hand through the webcam (MotionController), the
mouse, or the arrow keys, depending on the control chosen in Settings.
Playing with the camera adds a calibration step and some assists, since a
hand tracked by a webcam is slower and less precise than a mouse.

Every balance number (speeds, balls, asteroids, enemy skill per level)
lives in game/levels.py.
"""

import math
import random

import pygame

from core import Scene
from game import levels, motion
from game.ball import Ball
from game.enemy import Blocker, Enemy, predict_landing
from game.obstacle import Obstacle
from game.starfield import Starfield
from ui import TextButton
from ui.pause_button import PauseButton
from utils import settings
from utils.i18n import t
from utils.text import render_fit
from config import FONTS, PATHS, UI, GAME


class Pong(Scene):
    """The game scene: one match, played level by level."""

    # --- Match states ---
    PLAYING = "playing"
    LEVEL_WON = "level_won"
    LEVEL_LOST = "level_lost"
    SECRET_FOUND = "secret_found"
    VICTORY = "victory"

    # --- Who hit the ball (for sounds, scoring and rally rules) ---
    PLAYER, ENEMY, BLOCKER = "player", "enemy", "blocker"

    #: Enables the level-skip keys (UP/DOWN). Set GAME.DEBUG = True while developing.
    DEBUG = getattr(GAME, "DEBUG", False)

    #: Largest timestep simulated in one frame. A hitch (e.g. right after the
    #: loading screen) would otherwise move a ball far enough to tunnel
    #: through an obstacle.
    MAX_DT = 0.05

    LIVES_MIN, LIVES_MAX = 2, 5

    # --- Scoring ---
    GOAL_POINTS = 100        #: points for each goal scored
    RETURN_POINTS = 10       #: points for each ball the player returns
    HEART_BONUS = 50         #: points per heart left when a level is won

    # --- Serves and level intro ---
    SERVE_DELAY = 0.6        #: seconds a new ball blinks before launching
    SERVE_STAGGER = 0.4      #: extra wait between balls served together
    LEVEL_INTRO_DELAY = 1.2  #: extra wait for the first serve, while the banner shows
    BANNER_TIME = 2.2        #: seconds the level banner stays on screen
    BANNER_FADE = 0.6        #: ...the last of which it fades out

    # --- Procedural obstacles ---
    OBSTACLE_W = (60, 110)       #: width range
    OBSTACLE_H = (16, 26)        #: height range
    OBSTACLE_GAP = 60            #: min spacing between obstacles and from the serve point
    OBSTACLE_MARGIN_Y = 110      #: obstacle-free band next to each paddle
    MIN_SIDEWAYS = 0.15          #: min horizontal share of a ball leaving an asteroid

    # --- Blocker (secret level) ---
    BLOCKER_WIDTH_SCALE = 0.8    #: blocker width relative to the enemy paddle
    BLOCKER_Y_SHARE = 0.3        #: height in the field (0 top, 1 bottom), above the serve

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
    #: How fast the paddle catches up with its target (1/s). The hand
    #: position arrives already filtered by the tracker (see game/motion.py).
    FOLLOW_RATE = {CONTROL_MOUSE: 30.0, CONTROL_CAMERA: 30.0}
    PREVIEW_SIZE = (192, 144)   #: camera preview on the pause screen

    # --- Camera assists: a webcam is slower and less precise than a mouse ---
    CAMERA_PADDLE_SCALE = 1.3   #: wider paddle
    CAMERA_BALL_SPEED = 0.85    #: slower balls
    MARKER_TIME = 1.2           #: show where a ball will land this long before it does

    # --- Camera calibration ---
    CALIBRATION_TIME = 4.0          #: seconds the player sweeps the hand
    CALIBRATION_MIN_SPAN = 0.2      #: narrower sweeps (image share) are rejected
    CALIBRATION_PERCENTILES = (5, 95)   #: ignore the outermost detections
    CALIBRATION_PREVIEW = (320, 240)

    # --- HUD ---
    HUD_CENTER_Y = 30
    HEART_SIZE = 32
    HEART_BLINK_MS = 720
    HEART_BLINK_INTERVAL = 120
    BALL_BLINK_MS = 100      #: blink period of a ball waiting to be served
    TITLE_MAX_WIDTH = int(GAME.SCREEN_WIDTH * 0.9)   #: big titles shrink to fit this

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
        paddle_top = load(PATHS.IMAGE_PATH_PADDLE_TOP)
        blocker_size = (int(paddle_top.get_width() * cls.BLOCKER_WIDTH_SCALE),
                        paddle_top.get_height())
        return {
            "background": pygame.transform.scale(
                pygame.image.load(PATHS.IMAGE_PATH_GAME).convert(), GAME.SCREEN_SIZE),
            "ball": load(PATHS.IMAGE_PATH_BALL),
            "paddle_top": paddle_top,
            # Plain (nearest-neighbor) scaling keeps the pixel art crisp
            "blocker": pygame.transform.scale(paddle_top, blocker_size),
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
        return motion.MotionController(mirror=not settings.get("camera_invert"),
                                       camera_range=settings.get("camera_range"),
                                       hand_height=settings.get("camera_height"))

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

        self.difficulty = levels.DIFFICULTIES.get(
            settings.get("difficulty"), levels.DIFFICULTIES["normal"])
        self.lives_start = max(self.LIVES_MIN, min(self.LIVES_MAX, self.difficulty.lives))

        self._text_cache = {}    # HUD text, re-rendered only when it changes
        self._trail_cache = {}   # trail dot surfaces, by (radius, alpha)

        self._setup_geometry()
        self._setup_hud()
        self.calibration = None        # {"time": s left, "samples": [...]} while calibrating
        self.calibration_note = None   # result of the last calibration, for the pause screen
        self._reset_game()
        if self.control == self.CONTROL_CAMERA and settings.get("camera_range") is None:
            self._start_calibration()   # first game with the camera

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
        """Cache sprite sizes, derive paddle positions and create the enemy."""
        self.ball_w = self.images["ball"].get_width()
        self.ball_h = self.images["ball"].get_height()
        self.paddle_image = self.images["paddle"]
        if self.control == self.CONTROL_CAMERA:
            size = (int(self.paddle_image.get_width() * self.CAMERA_PADDLE_SCALE),
                    self.paddle_image.get_height())
            self.paddle_image = pygame.transform.scale(self.paddle_image, size)
        self.paddle_w = self.paddle_image.get_width()
        self.enemy_w = self.images["paddle_top"].get_width()

        self.paddle_y = self.FIELD_BOTTOM - self.images["paddle"].get_height() - 10
        self.paddle_min_x = self.FIELD_LEFT
        self.paddle_max_x = self.FIELD_RIGHT - self.paddle_w

        self.enemy_y = self.FIELD_TOP + 5
        self.enemy_bottom = self.enemy_y + self.images["paddle_top"].get_height()
        self.enemy = Enemy(x=0, face_y=self.enemy_bottom, width=self.enemy_w,
                           left=self.FIELD_LEFT, right=self.FIELD_RIGHT)

        self.blocker_y = int(self.FIELD_TOP
                             + (self.FIELD_BOTTOM - self.FIELD_TOP) * self.BLOCKER_Y_SHARE)

    def _setup_hud(self):
        """Fonts, pre-rendered texts, HUD positions and buttons."""
        self.font_path = str(PATHS.FONT_PATH_ARCADE)
        self.font_hint = pygame.font.Font(self.font_path, FONTS.SMALL)
        self.font_hud = pygame.font.Font(self.font_path, FONTS.MEDIUM)
        self.font_score = pygame.font.Font(self.font_path, FONTS.LARGE)

        yellow, white, gray = UI.COLORS["YELLOW"], UI.COLORS["WHITE"], UI.COLORS["GRAY"]
        self.text_pause = self._title(t("game.paused"), yellow)
        self.text_pause_hint = self.font_hint.render(t("game.pause_hint"), True, white)
        # Which control is active (or why the camera isn't being used)
        control_line = (t("game.no_camera") if self.camera_missing
                        else t("game.control_hint", mode=t(f"control.{self.control}")))
        self.text_control = self.font_hint.render(control_line, True, gray)
        self.overlay_titles = {
            self.LEVEL_WON: self._title(t("game.level_won"), yellow),
            self.LEVEL_LOST: self._title(t("game.level_lost"), yellow),
            self.SECRET_FOUND: self._title(t("game.secret_found"), yellow),
            self.VICTORY: self._title(t("game.victory"), yellow),
        }
        self.text_secret_unlocked = self._note(t("game.secret_unlocked"), white)
        self.text_secret_hint = self._note(t("game.secret_hint"), gray)
        self.label_level = self.font_hud.render(t("game.hud_level"), True, white)
        self.text_calibration_title = self._title(t("game.calibration_title"), yellow)
        self.text_calibration_hint = self._note(t("game.calibration_hint"), white)
        self.text_calibration_done = self._note(t("game.calibration_done"), yellow)
        self.text_calibration_failed = self._note(t("game.calibration_failed"), yellow)
        self.landing_marker = self._make_landing_marker(yellow)

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
                font_config=(self.font_path, FONTS.MEDIUM),
                action=self._end_match,
                base_color=gray,
                hover_color=white,
                audio=self.audio),
        ]

        cx, cy = self.hud_pos["center"]

        def overlay_button(y_offset, text_key, action):
            return TextButton(
                pos=(cx, cy + y_offset), text=t(text_key),
                font_config=(self.font_path, FONTS.MEDIUM), action=action,
                hover_color=yellow, audio=self.audio)

        #: Shown on the pause screen when playing with the camera
        self.pause_buttons = [overlay_button(330, "game.calibrate", self._start_calibration)]

        self.overlay_buttons = {
            self.LEVEL_WON: [overlay_button(80, "game.continue", self._on_continue)],
            self.LEVEL_LOST: [overlay_button(80, "game.retry", self._on_retry),
                              overlay_button(130, "menu.exit", self._end_match)],
            self.SECRET_FOUND: [overlay_button(80, "game.continue", self._on_continue)],
            self.VICTORY: [overlay_button(80, "menu.exit", self._end_match)],
        }

    def _title(self, text, color):
        """A big title, shrunk if needed to fit the screen width."""
        return render_fit(self.font_path, FONTS.LARGE * 2, text, color, self.TITLE_MAX_WIDTH)

    def _note(self, text, color):
        """A small line of text, shrunk if needed to fit the screen width."""
        return render_fit(self.font_path, FONTS.SMALL, text, color, self.TITLE_MAX_WIDTH)

    # ------------------------------------------------------------------
    # Match flow
    # ------------------------------------------------------------------
    def _reset_game(self):
        """Start a whole new match from level 1."""
        self.points = 0
        self.retried = False   # winning the campaign without retries unlocks the secret
        self.show_secret_hint = False
        self._start_level(1)

    def _start_level(self, number):
        """Prepare a level: full hearts, clean scoreboard and a fresh serve."""
        # Score checkpoint, restored on retry: without it the record could be
        # inflated by replaying the same level over and over
        self.points_checkpoint = self.points
        self.level = max(1, min(levels.SECRET_LEVEL, number))
        self.config = levels.get(self.level)
        self.lives = self.lives_start
        self.goals_to_win = self.config.goals
        self.goals_player = 0
        self.goals_enemy = 0
        self.blink_until = 0
        self.match_state = self.PLAYING
        self.paddle_x = (self.paddle_min_x + self.paddle_max_x) / 2

        scale = self.difficulty.miss_scale
        self.enemy.configure(self.config.enemy_speed,
                             self.config.miss_easy * scale, self.config.miss_hard * scale)
        self.enemy.center_on_field()
        self.blocker = None
        if self.config.blocker_speed:
            self.blocker = Blocker(
                y=self.blocker_y, width=self.images["blocker"].get_width(),
                height=self.images["blocker"].get_height(),
                left=self.FIELD_LEFT, right=self.FIELD_RIGHT,
                speed=self.config.blocker_speed)

        self.obstacles = self._generate_obstacles(self.level, self.config.obstacles)
        self.balls = []
        self._refill_balls(extra_delay=self.LEVEL_INTRO_DELAY)
        self._prepare_banner()
        self.paused = True   # the level waits for the player

    def _prepare_banner(self):
        """Render the level banner: "LEVEL 3" and the level's name."""
        if self.level == levels.SECRET_LEVEL:
            title = t("game.secret_level")
        else:
            title = t("game.level_title", n=self.level)
        self.banner_title = self._title(title, UI.COLORS["YELLOW"])
        self.banner_name = render_fit(self.font_path, FONTS.LARGE,
                                      t(f"levels.{self.config.key}"),
                                      UI.COLORS["WHITE"], self.TITLE_MAX_WIDTH)
        self.banner_time = self.BANNER_TIME

    def _on_continue(self):
        self._start_level(self.level + 1)
        self.paused = False

    def _on_retry(self):
        self.retried = True
        self.points = self.points_checkpoint
        self._start_level(self.level)
        self.paused = False

    def _win_level(self):
        """The level is won: heart bonus, then the next step of the campaign."""
        self.points += self.lives * self.HEART_BONUS
        last = len(levels.CAMPAIGN)
        if self.level == last and not self.retried:
            self.match_state = self.SECRET_FOUND
        elif self.level >= last:
            self.match_state = self.VICTORY
            self.show_secret_hint = self.level == last   # won, but with retries
        else:
            self.match_state = self.LEVEL_WON
        self.paused = True

    def _toggle_pause(self):
        """SPACE or the pause button: toggle the pause while playing, or run
        the result screen's main action (continue, retry or finish)."""
        if self.calibration is not None:
            return   # finish calibrating first
        primary_action = {
            self.LEVEL_WON: self._on_continue,
            self.LEVEL_LOST: self._on_retry,
            self.SECRET_FOUND: self._on_continue,
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
    def _refill_balls(self, extra_delay=0.0):
        """Serve new balls from the center until the level's ball count is met.

        Balls served together launch one after another, so a multiball
        serve stays readable.
        """
        missing = self.config.balls - len(self.balls)
        if missing <= 0:
            return
        speed = self.config.ball_speed * self.difficulty.speed_scale
        if self.control == self.CONTROL_CAMERA:
            speed *= self.CAMERA_BALL_SPEED
        x = GAME.SCREEN_WIDTH / 2 - self.ball_w / 2
        y = (self.FIELD_TOP + self.FIELD_BOTTOM) / 2 - self.ball_h / 2
        for i in range(missing):
            delay = extra_delay + self.SERVE_DELAY + i * self.SERVE_STAGGER
            self.balls.append(Ball(x, y, self.ball_w, self.ball_h, speed, serve_delay=delay))

    def _player_scores(self, ball):
        """The enemy missed: goal for the player, and maybe the level is won."""
        self.balls.remove(ball)
        self.goals_player += 1
        self.points += self.GOAL_POINTS
        self.audio.play_goal()

        if self.goals_player >= self.goals_to_win:
            self._win_level()
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

    # ------------------------------------------------------------------
    # Obstacles
    # ------------------------------------------------------------------
    def _generate_obstacles(self, level, count):
        """Seeded procedural placement by rejection sampling.

        The same level always produces the same layout (reproducible and
        balanceable): each candidate is drawn at random, then rejected if it
        is too close to the serve point or to another obstacle.
        """
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
            if self.blocker is not None:
                self._collide_blocker(ball, prev_y)

            # A paddle only returns a ball whose edge crosses the paddle's face
            # THIS frame. Testing just "is it past the line" let a paddle
            # sliding under a ball that had already slipped by save it from behind.
            if (ball.vy < 0 and prev_y >= self.enemy_bottom > ball.y
                    and self._overlaps_x(ball, self.enemy.x, self.enemy_w)):
                ball.y = self.enemy_bottom
                self._bounce_off_paddle(ball, self.enemy.x, self.enemy_w,
                                        upward=False, hitter=self.ENEMY)
            elif ball.y < self.FIELD_TOP:
                self._player_scores(ball)
                continue

            if (ball.vy > 0 and prev_y + ball.h <= self.paddle_y < ball.y + ball.h
                    and self._overlaps_x(ball, self.paddle_x, self.paddle_w)):
                ball.y = self.paddle_y - ball.h
                self._bounce_off_paddle(ball, self.paddle_x, self.paddle_w,
                                        upward=True, hitter=self.PLAYER)
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

    def _collide_blocker(self, ball, prev_y):
        """Bounce a ball off either face of the midfield blocker."""
        blocker = self.blocker
        if not self._overlaps_x(ball, blocker.x, blocker.w):
            return
        if ball.vy < 0 and prev_y >= blocker.bottom > ball.y:
            ball.y = blocker.bottom          # blocked a shot: back to the player
            upward = False
        elif ball.vy > 0 and prev_y + ball.h <= blocker.top < ball.y + ball.h:
            ball.y = blocker.top - ball.h    # deflected the enemy's return
            upward = True
        else:
            return
        self._bounce_off_paddle(ball, blocker.x, blocker.w, upward, hitter=self.BLOCKER)

    def _bounce_off_paddle(self, ball, paddle_x, paddle_w, upward, hitter):
        """Angular bounce off a paddle, rally speed-up, scoring and sound.

        Every hit speeds the ball up a little, up to the rally's top speed.
        A player's hit near the paddle's edge is also a smash: extra speed,
        so aiming well is what beats the enemy.
        """
        hit = ball.bounce_paddle(paddle_x, paddle_w, upward, levels.MAX_BOUNCE_X)
        factor = 1 + levels.RALLY_ACCEL
        if hitter == self.PLAYER:
            self.points += self.RETURN_POINTS
            edge = (abs(hit) - levels.SMASH_FROM) / (1 - levels.SMASH_FROM)
            if edge > 0:
                factor += levels.SMASH_BOOST * edge
        ball.accelerate(factor, ball.base_speed * levels.RALLY_MAX)
        self.audio.play("hit_player" if hitter == self.PLAYER else "hit_enemy")

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

            self._unstick(ball, ball.cx - obstacle.rect.centerx)
            # An asteroid bounce can't be predicted: the enemy has to read
            # (and react to) the new course
            self.enemy.forget(ball)
            self.audio.play("hit_obstacle")
            break   # one bounce per frame is enough

    def _unstick(self, ball, side):
        """Give a ball leaving an asteroid some sideways motion.

        Without it, a ball moving straight up and down could bounce forever
        between an asteroid and a paddle.

        Args:
            side: Which way to push it if needed (sign: negative = left).
        """
        speed = ball.speed
        min_vx = speed * self.MIN_SIDEWAYS
        if abs(ball.vx) >= min_vx:
            return
        if side == 0:
            side = random.choice((-1, 1))
        ball.vx = math.copysign(min_vx, side)
        ball.vy = math.copysign(math.sqrt(speed * speed - min_vx * min_vx), ball.vy)

    # ------------------------------------------------------------------
    # Camera calibration
    # ------------------------------------------------------------------
    def _can_calibrate(self):
        """Calibration is offered on the pause screen when using the camera."""
        return (self.control == self.CONTROL_CAMERA and self.paused
                and self.match_state == self.PLAYING and self.calibration is None)

    def _start_calibration(self):
        """Ask the player to sweep the hand, to learn which part of the
        camera image it covers and at what height it plays."""
        self.paused = True
        self.calibration = {"time": self.CALIBRATION_TIME, "x": [], "y": []}
        self.calibration_note = None
        self.detector.calibrating = True   # follow the biggest movement: the sweeping hand

    def _update_calibration(self, dt):
        """Collect where the hand is seen; when time is up, save what was learned."""
        if self.detector.raw_x is not None and self.detector.blob is not None:
            _, y, _, h = self.detector.blob
            self.calibration["x"].append(self.detector.raw_x)
            self.calibration["y"].append(y + h / 2)
        self.calibration["time"] -= dt
        if self.calibration["time"] <= 0:
            self._finish_calibration()

    def _finish_calibration(self):
        """Map the span the hand swept to the whole field (outermost
        detections ignored) and remember the height it moved at."""
        xs, ys = sorted(self.calibration["x"]), sorted(self.calibration["y"])
        self.calibration = None
        self.detector.calibrating = False
        self.calibration_note = self.text_calibration_failed
        if len(xs) < 10:
            return
        low, high = self.CALIBRATION_PERCENTILES
        left = round(xs[int(len(xs) * low / 100)], 4)
        right = round(xs[min(len(xs) - 1, int(len(xs) * high / 100))], 4)
        if right - left < self.CALIBRATION_MIN_SPAN:
            return
        height = round(ys[len(ys) // 2], 4)   # median
        self.detector.set_calibration(left, right, height)
        settings.set("camera_range", [left, right])
        settings.set("camera_height", height)
        self.calibration_note = self.text_calibration_done

    # ------------------------------------------------------------------
    # Scene hooks
    # ------------------------------------------------------------------
    def on_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self._toggle_pause()
            elif event.key == pygame.K_ESCAPE:
                self._end_match()
            elif event.key == pygame.K_c and self._can_calibrate():
                self._start_calibration()
            elif self.DEBUG and event.key in (pygame.K_UP, pygame.K_KP_PLUS):
                self._start_level(self.level + 1)
            elif self.DEBUG and event.key in (pygame.K_DOWN, pygame.K_KP_MINUS):
                self._start_level(self.level - 1)
        elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            mouse_pos = pygame.mouse.get_pos()
            clicked = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
            buttons = [*self.hud_buttons, *self.overlay_buttons.get(self.match_state, ())]
            if self._can_calibrate():
                buttons += self.pause_buttons
            for button in buttons:
                button.update(mouse_pos, clicked)

    def on_update(self):
        self._update_cursor()
        if self.calibration is not None:
            self._update_calibration(self.director.dt)
        if self.paused:
            return
        dt = min(self.director.dt, self.MAX_DT)
        self.banner_time = max(0.0, self.banner_time - dt)
        self.starfield.update(dt)
        for obstacle in self.obstacles:
            obstacle.update(dt)
        if self.blocker is not None:
            self.blocker.update(dt)
        self._update_paddle(dt)
        self.enemy.update(dt, self.balls)
        self._update_balls(dt)

    def on_draw(self, screen):
        screen.blit(self.images["background"], (0, 0))
        self.starfield.draw(screen)

        for obstacle in self.obstacles:
            self._draw_obstacle(screen, obstacle)
        if self.blocker is not None:
            screen.blit(self.images["blocker"], (self.blocker.x, self.blocker.y))

        blink_on = (pygame.time.get_ticks() // self.BALL_BLINK_MS) % 2 == 0
        for ball in self.balls:
            if ball.waiting and not self.paused and not blink_on:
                continue   # a ball about to be served blinks
            self._draw_ball_trail(screen, ball)
            screen.blit(self.images["ball"], (ball.x, ball.y))
        if self.control == self.CONTROL_CAMERA:
            self._draw_landing_markers(screen)
        screen.blit(self.images["paddle_top"], (self.enemy.x, self.enemy_y))
        screen.blit(self.paddle_image, (self.paddle_x, self.paddle_y))

        self._draw_hud(screen)

        if self.calibration is not None:
            self._draw_calibration(screen)
        elif self.match_state in self.overlay_titles:
            self._draw_overlay(screen)
        elif self.paused:
            self._draw_pause(screen)
        elif self.banner_time > 0:
            fade = min(1.0, self.banner_time / self.BANNER_FADE)
            self._draw_banner(screen, int(255 * fade))

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

    def _draw_banner(self, screen, alpha=255):
        """The level's number and name, centered."""
        cx, cy = self.hud_pos["center"]
        for surface, y in ((self.banner_title, cy - 40), (self.banner_name, cy + 20)):
            surface.set_alpha(alpha)
            screen.blit(surface, surface.get_rect(center=(cx, y)))

    def _draw_pause(self, screen):
        cx, cy = self.hud_pos["center"]
        if self.banner_time > 0:
            self._draw_banner(screen)   # the level hasn't started yet: show which one
        else:
            screen.blit(self.text_pause, self.text_pause.get_rect(center=(cx, cy)))
        screen.blit(self.text_pause_hint, self.text_pause_hint.get_rect(center=(cx, cy + 70)))
        screen.blit(self.text_control, self.text_control.get_rect(center=(cx, cy + 105)))
        if self.control == self.CONTROL_CAMERA:
            if self.calibration_note is not None:
                note = self.calibration_note
                screen.blit(note, note.get_rect(center=(cx, cy + 135)))
            self._draw_camera_preview(screen, (cx, cy + 230), self.PREVIEW_SIZE)
            for button in self.pause_buttons:
                button.draw(screen)

    def _draw_calibration(self, screen):
        """Calibration screen: instructions, a progress bar and the camera
        view, with the span the hand has covered so far."""
        screen.blit(self.overlay_backdrop, (0, 0))
        cx, cy = self.hud_pos["center"]
        title, hint = self.text_calibration_title, self.text_calibration_hint
        screen.blit(title, title.get_rect(center=(cx, cy - 170)))
        screen.blit(hint, hint.get_rect(center=(cx, cy - 110)))

        bar = pygame.Rect(0, 0, self.CALIBRATION_PREVIEW[0], 12)
        bar.center = (cx, cy - 75)
        done = 1 - max(0.0, self.calibration["time"]) / self.CALIBRATION_TIME
        pygame.draw.rect(screen, UI.COLORS["GRAY"], bar, width=2)
        pygame.draw.rect(screen, UI.COLORS["YELLOW"],
                         (bar.x, bar.y, int(bar.width * done), bar.height))

        rect = self._draw_camera_preview(screen, (cx, cy + 70), self.CALIBRATION_PREVIEW)
        samples = self.calibration["x"]
        if rect is not None and samples:
            for x in (min(samples), max(samples)):
                px = rect.left + int(x * rect.width)
                pygame.draw.line(screen, UI.COLORS["YELLOW"], (px, rect.top), (px, rect.bottom), 2)

    def _make_landing_marker(self, color):
        """A ring the size of the ball: where it will meet the paddle."""
        size = max(self.ball_w, self.ball_h)
        marker = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(marker, color, (size // 2, size // 2), size // 2, width=2)
        return marker

    def _draw_landing_markers(self, screen):
        """Mark where each incoming ball will meet the paddle's line: a ring
        that grows brighter as the ball gets closer. Put the paddle under it.
        (An asteroid can still change the ball's course.)"""
        for ball in self.balls:
            if ball.waiting:
                continue
            landing = predict_landing(ball, self.paddle_y - ball.h / 2,
                                      self.FIELD_LEFT, self.FIELD_RIGHT)
            if landing is None or landing[1] > self.MARKER_TIME:
                continue
            x, seconds = landing
            self.landing_marker.set_alpha(int(80 + 175 * (1 - seconds / self.MARKER_TIME)))
            screen.blit(self.landing_marker, self.landing_marker.get_rect(
                midbottom=(x, self.paddle_y)))

    def _draw_camera_preview(self, screen, center, size):
        """What the camera sees and what the tracker makes of it.

        Lets the player check that the camera is picking them up: the gray
        lines mark the calibrated span (it covers the whole field) and the
        band where the hand is looked for, the cyan box is the detected hand
        and the yellow line its filtered position, the one the paddle follows.

        Returns:
            The preview's Rect, or None if there is no frame yet.
        """
        frame = self.detector.preview
        if frame is None:
            return None
        h, w = frame.shape[:2]
        image = pygame.transform.scale(
            pygame.image.frombuffer(frame.tobytes(), (w, h), "RGB"), size)
        rect = image.get_rect(center=center)
        screen.blit(image, rect)

        gray, yellow = UI.COLORS["GRAY"], UI.COLORS["YELLOW"]
        pygame.draw.rect(screen, gray, rect, width=2)
        for x in self.detector.range:
            px = rect.left + int(x * rect.width)
            pygame.draw.line(screen, gray, (px, rect.top), (px, rect.bottom), 1)
        height = self.detector.tracker.hand_height
        if height is not None and not self.detector.calibrating:
            band = self.detector.tracker.HEIGHT_BAND
            for y in (height - band, height + band):
                py = rect.top + int(min(1, max(0, y)) * rect.height)
                pygame.draw.line(screen, gray, (rect.left, py), (rect.right, py), 1)
        if self.detector.blob is not None:
            bx, by, bw, bh = self.detector.blob
            pygame.draw.rect(screen, (0, 220, 255),
                             (rect.left + bx * rect.width, rect.top + by * rect.height,
                              bw * rect.width, bh * rect.height), width=1)
        if self.detector.image_x is not None:
            px = rect.left + int(self.detector.image_x * rect.width)
            pygame.draw.line(screen, yellow, (px, rect.top), (px, rect.bottom), 3)
        return rect

    def _draw_overlay(self, screen):
        """Result screen: dimmed backdrop, title, final score, buttons and a note."""
        screen.blit(self.overlay_backdrop, (0, 0))
        cx, cy = self.hud_pos["center"]

        title = self.overlay_titles[self.match_state]
        screen.blit(title, title.get_rect(center=(cx, cy - 40)))

        score = self._text("overlay_score", f"{self.goals_player}  |  {self.goals_enemy}",
                           self.font_score, UI.COLORS["WHITE"])
        screen.blit(score, score.get_rect(center=(cx, cy + 25)))

        for button in self.overlay_buttons[self.match_state]:
            button.draw(screen)

        note = None
        if self.match_state == self.SECRET_FOUND:
            note = self.text_secret_unlocked
        elif self.match_state == self.VICTORY and self.show_secret_hint:
            note = self.text_secret_hint
        if note is not None:
            screen.blit(note, note.get_rect(center=(cx, cy + 130)))

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
        value = "??" if self.level == levels.SECRET_LEVEL else f"{self.level:02d}"
        level = self._text("level", value, self.font_hud, white)
        screen.blit(level, level.get_rect(midleft=self.hud_pos["level_value"]))

        for button in self.hud_buttons:
            button.draw(screen)
