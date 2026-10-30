"""The pages of the instructions carousel, each with a small animated demo.

Every page is a looping animation drawn with the game's own sprites (top)
plus a title and a short text (bottom). The demos are scripted or use a
tiny local physics, independent from the real game: they only need to
look like it.
"""

import math
import random

import pygame

from utils.i18n import t
from utils.text import wrap_text
from config import FONTS, PATHS, UI

NEON = (80, 200, 255)
STEP = 1 / 120       #: fixed physics step of the demos (frame-rate independent)
RED = (255, 70, 70)
SCENE_SHARE = 0.62   #: share of the page height used by the demo; the rest is text
SPRITE_SCALE = 0.75  #: demo sprites are smaller than in the game


def _load_sprites():
    def load(path, scale=SPRITE_SCALE):
        image = pygame.image.load(str(path)).convert_alpha()
        size = (max(1, int(image.get_width() * scale)), max(1, int(image.get_height() * scale)))
        return pygame.transform.scale(image, size)

    ball = load(PATHS.IMAGE_PATH_BALL)
    red_ball = ball.copy()
    red_ball.fill((*RED, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return {
        "ball": ball,
        "red_ball": red_ball,
        "paddle": load(PATHS.IMAGE_PATH_PADDLE),
        "paddle_top": load(PATHS.IMAGE_PATH_PADDLE_TOP),
    }


class Page:
    """A carousel page: a framed demo on top, title and text below."""

    TITLE_KEY = None   #: i18n keys, set by each page
    TEXT_KEY = None

    def __init__(self, sprites, fonts):
        self.sprites = sprites
        self.fonts = fonts
        self.time = 0.0
        self._text_cache = None   # (width, [(surface, offset_y)])

    def update(self, dt):
        self.time += dt

    def restart(self):
        """Play the demo from the beginning (the page is about to be shown)."""
        self.time = 0.0
        self.reset()

    def reset(self):
        """Extension point: clear the demo's own state."""

    def draw(self, screen, rect, appear):
        # A dark card behind the whole page keeps the text readable on any background
        screen.blit(self._card(rect.size), rect)
        scene = pygame.Rect(rect.x + 10, rect.y + 10, rect.width - 20,
                            int(rect.height * SCENE_SHARE) - 10)
        self._draw_frame(screen, scene)
        clip = screen.get_clip()
        screen.set_clip(scene.clip(clip) if clip else scene)
        self.draw_scene(screen, scene)
        screen.set_clip(clip)

        for surface, offset_y in self._texts(rect.width - 40):
            surface.set_alpha(int(255 * appear))
            # Text rises a little while it fades in
            y = scene.bottom + offset_y + int((1 - appear) * 12)
            screen.blit(surface, surface.get_rect(midtop=(rect.centerx, y)))

    def _texts(self, width):
        """Title and wrapped text, rendered once per width."""
        if self._text_cache is None or self._text_cache[0] != width:
            title_font, text_font = self.fonts["title"], self.fonts["text"]
            items = [(title_font.render(t(self.TITLE_KEY), True, UI.COLORS["YELLOW"]), 28)]
            y = 28 + title_font.get_height() + 22
            for line in wrap_text(t(self.TEXT_KEY), text_font, width):
                items.append((text_font.render(line, True, UI.COLORS["WHITE"]), y))
                y += text_font.get_height() + 12
            self._text_cache = (width, items)
        return self._text_cache[1]

    _cards = {}   #: card surfaces by size, shared by all pages

    @classmethod
    def _card(cls, size):
        card = cls._cards.get(size)
        if card is None:
            card = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.rect(card, (5, 10, 25, 170), card.get_rect(), border_radius=12)
            cls._cards[size] = card
        return card

    @staticmethod
    def _draw_frame(screen, rect):
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        panel.fill((5, 10, 25, 190))
        screen.blit(panel, rect)
        pygame.draw.rect(screen, NEON, rect, width=2, border_radius=8)

    def draw_scene(self, screen, rect):
        """Extension point: the page's animation, inside rect."""

    # --- small drawing helpers shared by the pages ---
    def _blit_center(self, screen, image, x, y):
        screen.blit(image, image.get_rect(center=(int(x), int(y))))

    @staticmethod
    def _trail(screen, points, color, radius):
        n = len(points)
        for i, (x, y) in enumerate(points):
            frac = (i + 1) / n
            r = max(1, int(radius * frac * 0.8))
            dot = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(dot, (*color, int(110 * frac)), (r, r), r)
            screen.blit(dot, (x - r, y - r))

    def _flash_text(self, screen, text, center, age, color=UI.COLORS["YELLOW"]):
        """A word that pops in and fades out (age in seconds since it appeared)."""
        if not 0 <= age < 1.0:
            return
        surface = self.fonts["title"].render(text, True, color)
        scale = 1 + 0.4 * max(0.0, 0.25 - age) / 0.25
        if scale != 1:
            size = (int(surface.get_width() * scale), int(surface.get_height() * scale))
            surface = pygame.transform.scale(surface, size)
        surface.set_alpha(int(255 * min(1.0, (1 - age) / 0.4)))
        screen.blit(surface, surface.get_rect(center=center))


class _Rally:
    """Tiny local physics for the demo fields: a ball bouncing between walls
    and paddles inside a box (coordinates relative to the box)."""

    def __init__(self, width, height, speed, rng):
        self.w, self.h = width, height
        self.speed = speed
        self.rng = rng
        self.serve()

    def serve(self, direction=None):
        self.x, self.y = self.w / 2, self.h / 2
        angle = math.radians(self.rng.uniform(-35, 35))
        direction = direction or self.rng.choice((-1, 1))
        self.vx = self.speed * math.sin(angle)
        self.vy = self.speed * math.cos(angle) * direction
        self.trail = []

    def move(self, dt, margin):
        self.trail = (self.trail + [(self.x, self.y)])[-8:]
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.x < margin or self.x > self.w - margin:
            self.x = min(max(self.x, margin), self.w - margin)
            self.vx = -self.vx

    def bounce(self, paddle_x, half_width, upward):
        hit = max(-1.0, min(1.0, (self.x - paddle_x) / half_width))
        self.vx = self.speed * hit * 0.75
        vertical = math.sqrt(max(0.0, self.speed ** 2 - self.vx ** 2))
        self.vy = -vertical if upward else vertical


class CampaignPage(Page):
    """A match in miniature: two paddles, a rally, a goal now and then."""

    TITLE_KEY = "instructions.campaign_title"
    TEXT_KEY = "instructions.campaign_text"
    MISS_EVERY = 3   #: the top paddle lets every third ball through

    def __init__(self, sprites, fonts):
        super().__init__(sprites, fonts)
        self.reset()

    def reset(self):
        self.rally = None   # rebuilt on the next draw, when the size is known
        self.player_x = self.enemy_x = 0.0
        self.returns = 0
        self.score = [0, 0]
        self.goal_time = -10.0
        self.clock = 0.0    # demo time simulated so far

    def draw_scene(self, screen, rect):
        if self.rally is None or self.rally.w != rect.width:
            self.rally = _Rally(rect.width, rect.height, 330, random.Random(3))
            self.player_x = self.enemy_x = rect.width / 2
            self.clock = self.time
        while self.clock + STEP <= self.time:
            self._step(rect, STEP)
            self.clock += STEP

        r = self.rally
        ball, paddle, paddle_top = self.sprites["ball"], self.sprites["paddle"], self.sprites["paddle_top"]
        for x in range(rect.x + 20, rect.right - 20, 30):   # dashed center line
            pygame.draw.line(screen, (40, 70, 110), (x, rect.centery), (x + 16, rect.centery), 2)
        self._trail(screen, [(rect.x + x, rect.y + y) for x, y in r.trail], UI.COLORS["WHITE"],
                    ball.get_width() / 2)
        self._blit_center(screen, ball, rect.x + r.x, rect.y + r.y)
        self._blit_center(screen, paddle_top, rect.x + self.enemy_x, rect.y + 16)
        self._blit_center(screen, paddle, rect.x + self.player_x, rect.bottom - 16)

        score = self.fonts["text"].render(f"{self.score[0]}  |  {self.score[1]}", True, RED)
        screen.blit(score, score.get_rect(midtop=(rect.centerx, rect.y + 34)))
        self._flash_text(screen, t("instructions.goal"), rect.center, self.time - self.goal_time)

    def _step(self, rect, dt):
        r = self.rally
        r.move(dt, 12)
        # Paddles ease toward the ball; the top one aims off when it should miss
        miss = (self.returns + 1) % self.MISS_EVERY == 0
        enemy_target = r.x + (90 if miss else 0) if r.vy < 0 else rect.width / 2
        self.enemy_x += (enemy_target - self.enemy_x) * min(1.0, 4 * dt)
        player_target = r.x if r.vy > 0 else rect.width / 2
        self.player_x += (player_target - self.player_x) * min(1.0, 6 * dt)

        half = self.sprites["paddle"].get_width() / 2
        if r.vy > 0 and r.y >= rect.height - 26:
            r.y = rect.height - 26
            r.bounce(self.player_x, half, upward=True)
        elif r.vy < 0 and 0 < r.y <= 26 and abs(r.x - self.enemy_x) <= half + 8:
            r.y = 26
            r.bounce(self.enemy_x, half, upward=False)
            self.returns += 1
        if r.y < -10:
            self.score[0] += 1
            if self.score[0] > 9:
                self.score[0] = 0
            self.goal_time = self.time
            self.returns = 0
            r.serve(direction=1)


class EdgeShotPage(Page):
    """Scripted loop: the ball meets the edge of the paddle and shoots off
    at an angle; the top paddle lunges and doesn't make it."""

    TITLE_KEY = "instructions.edge_title"
    TEXT_KEY = "instructions.edge_text"
    LOOP = 3.6

    def draw_scene(self, screen, rect):
        phase = self.time % self.LOOP
        ball, paddle, paddle_top = self.sprites["ball"], self.sprites["paddle"], self.sprites["paddle_top"]
        half = paddle.get_width() / 2
        paddle_x = rect.x + rect.width * 0.62
        paddle_y = rect.bottom - 16
        hit = (paddle_x - half * 0.9, paddle_y - 14)            # near the left edge
        start = (rect.x + rect.width * 0.48, rect.y + 60)
        exit_point = (rect.x + 24, rect.y + rect.height * 0.35)  # bounces off the left wall...
        goal = (rect.x + rect.width * 0.40, rect.y - 20)         # ...and flies past the top paddle

        def lerp(a, b, s):
            return a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s

        enemy_x = rect.x + rect.width * 0.78
        if phase < 1.0:      # the ball comes down
            pos = lerp(start, hit, phase / 1.0)
        elif phase < 1.6:    # off the edge, at an angle
            pos = lerp(hit, exit_point, (phase - 1.0) / 0.6)
        elif phase < 2.4:    # off the wall and past the paddle
            s = (phase - 1.6) / 0.8
            pos = lerp(exit_point, goal, s)
            enemy_x -= rect.width * 0.28 * min(1.0, s * 1.3)   # the lunge
        else:
            pos = None
            enemy_x -= rect.width * 0.28

        # Where the shot goes: a dotted guide that appears on impact
        if 1.0 <= phase < 2.6:
            for a, b in ((hit, exit_point), (exit_point, goal)):
                for k in range(12):
                    x, y = lerp(a, b, k / 12)
                    pygame.draw.circle(screen, UI.COLORS["YELLOW"], (int(x), int(y)), 2)
        # The impact: an expanding ring at the paddle's edge
        if 1.0 <= phase < 1.4:
            radius = int(6 + (phase - 1.0) / 0.4 * 26)
            pygame.draw.circle(screen, UI.COLORS["YELLOW"], (int(hit[0]), int(hit[1])), radius, 2)

        self._blit_center(screen, paddle_top, enemy_x, rect.y + 16)
        self._blit_center(screen, paddle, paddle_x, paddle_y)
        if pos is not None:
            self._blit_center(screen, ball, *pos)
        self._flash_text(screen, t("instructions.goal"), rect.center, phase - 2.3)


class SurvivalPage(Page):
    """Balls bouncing under a wall; one red, handing its color around; the
    combo climbing with every return."""

    TITLE_KEY = "instructions.survival_title"
    TEXT_KEY = "instructions.survival_text"
    SWITCH_EVERY = 3.5
    WARNING = 1.2

    def __init__(self, sprites, fonts):
        super().__init__(sprites, fonts)
        self.reset()

    def reset(self):
        self.rallies = None   # rebuilt on the next draw, when the size is known
        self.paddle_x = 0.0
        self.returns = 0
        self.clock = 0.0

    def draw_scene(self, screen, rect):
        if self.rallies is None or self.rallies[0].w != rect.width:
            rng = random.Random(5)
            self.rallies = [_Rally(rect.width, rect.height, 260 + 30 * i, rng) for i in range(3)]
            for i, r in enumerate(self.rallies):
                r.x = rect.width * (0.25 + 0.25 * i)
            self.paddle_x = rect.width / 2
            self.clock = self.time
        while self.clock + STEP <= self.time:
            self._step(rect, STEP)
            self.clock += STEP

        pygame.draw.line(screen, NEON, (rect.x + 4, rect.y + 6), (rect.right - 4, rect.y + 6), 4)
        cycle = self.time % self.SWITCH_EVERY
        warning = cycle > self.SWITCH_EVERY - self.WARNING and int(self.time * 7) % 2 == 0
        current = int(self.time / self.SWITCH_EVERY) % len(self.rallies)
        upcoming = (current + 1) % len(self.rallies)
        for i, r in enumerate(self.rallies):
            red = i == current or (i == upcoming and warning)
            self._trail(screen, [(rect.x + x, rect.y + y) for x, y in r.trail],
                        RED if red else UI.COLORS["WHITE"], self.sprites["ball"].get_width() / 2)
            image = self.sprites["red_ball"] if red else self.sprites["ball"]
            self._blit_center(screen, image, rect.x + r.x, rect.y + r.y)
        self._blit_center(screen, self.sprites["paddle"], rect.x + self.paddle_x, rect.bottom - 16)

        combo = self.fonts["title"].render(f"x{1 + min(4, self.returns // 3)}", True, UI.COLORS["YELLOW"])
        screen.blit(combo, combo.get_rect(topright=(rect.right - 14, rect.y + 18)))

    def _step(self, rect, dt):
        half = self.sprites["paddle"].get_width() / 2
        falling = [r for r in self.rallies if r.vy > 0]
        target = max(falling, key=lambda r: r.y).x if falling else rect.width / 2
        self.paddle_x += (target - self.paddle_x) * min(1.0, 9 * dt)
        for r in self.rallies:
            r.move(dt, 12)
            if r.y < 18:
                r.y, r.vy = 18, abs(r.vy)
            if r.vy > 0 and r.y >= rect.height - 26:
                r.y = rect.height - 26
                # The demo paddle always makes it: aim the bounce from the ball's side
                r.bounce(r.x - max(-half, min(half, r.x - self.paddle_x)) * 0.6, half, upward=True)
                self.returns = (self.returns + 1) % 15


class ControlsPage(Page):
    """Three panels: arrow keys, mouse and hand, each moving a paddle."""

    TITLE_KEY = "instructions.controls_title"
    TEXT_KEY = "instructions.controls_text"
    CONTROLS = ("keyboard", "mouse", "camera")

    def draw_scene(self, screen, rect):
        width = rect.width / 3
        for i, control in enumerate(self.CONTROLS):
            panel = pygame.Rect(int(rect.x + i * width), rect.y, int(width), rect.height)
            if i:
                pygame.draw.line(screen, (40, 70, 110), (panel.x, panel.y + 20),
                                 (panel.x, panel.bottom - 20), 1)
            # Each panel moves on its own rhythm
            move = math.sin(self.time * 1.7 + i * 1.3)
            speed = math.cos(self.time * 1.7 + i * 1.3)
            icon_center = (panel.centerx + move * panel.width * 0.22, panel.y + panel.height * 0.38)
            getattr(self, f"_draw_{control}")(screen, panel, icon_center, move, speed)

            paddle = self.sprites["paddle"]
            paddle_x = panel.centerx + move * (panel.width / 2 - paddle.get_width() / 2 - 8)
            self._blit_center(screen, paddle, paddle_x, panel.bottom - 70)
            label = self.fonts["small"].render(t(f"control.{control}"), True, UI.COLORS["GRAY"])
            screen.blit(label, label.get_rect(center=(panel.centerx, panel.bottom - 30)))

    def _draw_keyboard(self, screen, panel, _center, _move, speed):
        y = panel.y + panel.height * 0.38
        for direction in (-1, 1):
            pressed = (speed > 0.15 and direction > 0) or (speed < -0.15 and direction < 0)
            key = pygame.Rect(0, 0, 50, 50)
            key.center = (panel.centerx + direction * 32, y + (4 if pressed else 0))
            if not pressed:   # key side, for depth
                pygame.draw.rect(screen, (30, 50, 80), key.move(0, 5), border_radius=8)
            pygame.draw.rect(screen, (60, 90, 140) if not pressed else UI.COLORS["YELLOW"],
                             key, border_radius=8)
            cx, cy = key.center
            arrow = [(cx + direction * 12, cy), (cx - direction * 8, cy - 11), (cx - direction * 8, cy + 11)]
            pygame.draw.polygon(screen, (10, 15, 30) if pressed else UI.COLORS["WHITE"], arrow)

    def _draw_mouse(self, screen, _panel, center, _move, _speed):
        body = pygame.Rect(0, 0, 44, 64)
        body.center = (int(center[0]), int(center[1]))
        pygame.draw.rect(screen, UI.COLORS["WHITE"], body, width=3, border_radius=20)
        pygame.draw.line(screen, UI.COLORS["WHITE"], (body.centerx, body.y + 4),
                         (body.centerx, body.y + 24), 3)
        pygame.draw.line(screen, UI.COLORS["WHITE"], (body.x + 4, body.y + 24),
                         (body.right - 4, body.y + 24), 2)

    def _draw_camera(self, screen, panel, center, _move, _speed):
        # Camera at the top, still; the hand moves in front of it
        cam = pygame.Rect(0, 0, 46, 26)
        cam.center = (panel.centerx, panel.y + 28)
        pygame.draw.rect(screen, UI.COLORS["GRAY"], cam, border_radius=6)
        pygame.draw.circle(screen, NEON, cam.center, 8, 3)
        hx, hy = int(center[0]), int(center[1]) + 8
        skin = (230, 190, 150)
        pygame.draw.circle(screen, skin, (hx, hy), 18)
        for k, (dx, length) in enumerate(((-12, 18), (-4, 24), (4, 25), (12, 20))):
            finger = pygame.Rect(0, 0, 7, length)
            finger.midbottom = (hx + dx, hy - 8)
            pygame.draw.rect(screen, skin, finger, border_radius=4)
        thumb = pygame.Rect(0, 0, 16, 7)
        thumb.midright = (hx - 14, hy + 2)
        pygame.draw.rect(screen, skin, thumb, border_radius=4)


class KeysPage(Page):
    """SPACE pauses, ESC goes back: two keys pressed in turn."""

    TITLE_KEY = "instructions.keys_title"
    TEXT_KEY = "instructions.keys_text"

    def draw_scene(self, screen, rect):
        keys = ((t("instructions.space"), 220, "instructions.key_pause", 0.0),
                ("ESC", 90, "instructions.key_exit", 1.0))
        for i, (name, width, caption, delay) in enumerate(keys):
            x = rect.x + rect.width * (0.33 if i == 0 else 0.75)
            y = rect.y + rect.height * 0.42
            pressed = (self.time + delay) % 2.0 < 0.35
            key = pygame.Rect(0, 0, width, 64)
            key.center = (int(x), int(y) + (5 if pressed else 0))
            if not pressed:
                pygame.draw.rect(screen, (30, 50, 80), key.move(0, 6), border_radius=10)
            pygame.draw.rect(screen, UI.COLORS["YELLOW"] if pressed else (60, 90, 140), key, border_radius=10)
            label = self.fonts["small"].render(name, True, (10, 15, 30) if pressed else UI.COLORS["WHITE"])
            screen.blit(label, label.get_rect(center=key.center))
            text = self.fonts["small"].render(t(caption), True, UI.COLORS["GRAY"])
            screen.blit(text, text.get_rect(center=(int(x), int(y) + 70)))

        # The pause icon toggles with each press of SPACE
        paused = int(self.time / 2.0) % 2 == 0
        icon = pygame.Rect(0, 0, 36, 36)
        icon.center = (int(rect.x + rect.width * 0.33), int(rect.y + rect.height * 0.15))
        if paused:
            for dx in (-8, 8):
                pygame.draw.rect(screen, UI.COLORS["WHITE"], (icon.centerx + dx - 4, icon.y + 4, 8, 28))
        else:
            pygame.draw.polygon(screen, UI.COLORS["WHITE"],
                                [(icon.x + 8, icon.y + 4), (icon.x + 8, icon.bottom - 4), (icon.right - 4, icon.centery)])


def build_pages():
    """All the pages, in order."""
    font_path = str(PATHS.FONT_PATH_ARCADE)
    fonts = {
        "title": pygame.font.Font(font_path, FONTS.LARGE),
        "text": pygame.font.Font(font_path, FONTS.SMALL),
        "small": pygame.font.Font(font_path, FONTS.SMALL),
    }
    sprites = _load_sprites()
    return [page(sprites, fonts) for page in
            (CampaignPage, EdgeShotPage, SurvivalPage, ControlsPage, KeysPage)]
