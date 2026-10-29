"""Credits screen: film-style auto-scroll with per-letter physics.

Letters react to the mouse: they drift away from the cursor, can be knocked
to the floor, spin as they fall, be kicked again, rest on the floor for a
while, and finally ease back to their place in the scroll.

Design notes:
- Each letter lives in one of two reference frames depending on its state.
  In NORMAL it follows the scroll, stored as a small offset (x, y) from its
  slot. In FALLING/GROUND/RETURNING it detaches and uses absolute screen
  coordinates (px, py). This split keeps the hitbox aligned with the drawing.
- Physics runs in on_update with the Director's dt; drawing only draws.
- The text comes from an editable credits.json, so credits change without
  touching code. Section titles can be i18n keys, so they get translated.
"""

import json
import math
import random
from pathlib import Path

import pygame

from scenes.static_screen import StaticScreen
from utils.i18n import t
from utils.text import wrap_text
from config import FONTS, PATHS, UI, GAME


class Credits(StaticScreen):
    """Credits scene with auto-scroll and physical interaction."""

    BACKGROUND_PATH = PATHS.IMAGE_PATH_CREDITS
    STATUS = GAME.STATUS_CREDITS

    #: Frame rate the per-frame factors below (DAMPING, GROUND_FRICTION) were
    #: tuned at. Physics scales by it, so the feel is the same at any FPS.
    REFERENCE_FPS = 60
    #: Largest timestep simulated in one frame (avoids jumps after a hitch).
    MAX_DT = 0.05

    # --- Layout and scroll ---
    SCROLL_SPEED = 40                               #: px/s
    LINE_SPACING = 50
    TEXT_MAX_WIDTH = 0.9                            #: longest line, fraction of the width
    BAND_TOP = int(GAME.SCREEN_HEIGHT * 0.18)       #: visible band, top
    BAND_BOTTOM = int(GAME.SCREEN_HEIGHT * 0.80)    #: visible band, bottom
    FADE_ZONE = 60                                  #: fade height at each band edge

    # --- Mouse push in the normal state ---
    MOUSE_RADIUS = 90
    MOUSE_FORCE = 35
    RETURN_FORCE = 12.0     #: spring pulling a letter back to its slot
    DAMPING = 0.80          #: velocity kept per reference frame

    # --- Fall physics ---
    GROUND_Y = int(GAME.SCREEN_HEIGHT * 0.82)   #: floor height
    GRAVITY = 900.0
    FALL_SPEED = 40.0           #: initial fall speed
    BOUNCE_FACTOR = 0.25        #: bounce on floor contact
    GROUND_FRICTION = 0.88      #: velocity kept per reference frame on the floor
    GROUND_TIME = 3.0           #: seconds a letter rests on the floor
    FALL_RADIUS = 42            #: mouse distance that knocks a letter down
    KICK_FORCE = 280.0          #: horizontal force of a mouse kick
    KICK_UP_FORCE = 220.0       #: vertical force of a kick
    FALL_ROTATION = 180.0       #: spin rate while falling (deg/s)
    KICK_ROTATION = 320.0       #: spin rate when kicked (deg/s)

    #: Decay rate of the leftover offset while a letter returns. The letter
    #: rides the scroll and only the remaining gap is eased, so there is no
    #: lag from chasing a moving target.
    RETURN_LERP = 6.0

    #: Minimum ms between chip clicks, so a fast sweep sounds like a cascade
    #: of tiles rather than one continuous buzz.
    SOUND_COOLDOWN_MS = 20
    SOUND_VOLUME_MIN = 0.35
    SOUND_VOLUME_MAX = 0.60

    # --- States ---
    STATE_NORMAL = 0
    STATE_FALLING = 1
    STATE_GROUND = 2
    STATE_RETURNING = 3

    def __init__(self, director):
        super().__init__(director)

        self.mouse_pos = (0, 0)   # cached once per frame

        self._last_sound_ms = 0
        self.chip_sounds = self._load_chip_sounds()

        self.font_title = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.LARGE)
        self.font_name = pygame.font.Font(str(PATHS.FONT_PATH_ARCADE), FONTS.MEDIUM)

        # Each line is a list of letters, or None for a spacer
        self.lines = self._build_lines(self._load_credit_lines())
        self.total_height = len(self.lines) * self.LINE_SPACING

        self.scroll_time = 0.0
        self._place_slots()
        for character in self._characters():
            character["prev_slot_y"] = character["slot_y"]

    # ------------------------------------------------------------------
    # Building the lines
    # ------------------------------------------------------------------
    def _build_lines(self, credit_lines):
        """Render each credit line letter by letter, wrapping long lines."""
        max_width = int(GAME.SCREEN_WIDTH * self.TEXT_MAX_WIDTH)
        lines = []
        for text, is_title in credit_lines:
            if not text:
                lines.append(None)
                continue
            font = self.font_title if is_title else self.font_name
            color = UI.COLORS["YELLOW"] if is_title else UI.COLORS["WHITE"]
            for row in wrap_text(text, font, max_width):
                lines.append(self._build_line(row, font, color))
        return lines

    def _build_line(self, text, font, color):
        """Render one line as individual letters, centered on the screen."""
        surfaces = [font.render(char, True, color) for char in text]
        x = (GAME.SCREEN_WIDTH - sum(s.get_width() for s in surfaces)) / 2

        characters = []
        for index, surface in enumerate(surfaces):
            width = surface.get_width()
            characters.append({
                "surface": surface,
                "state": self.STATE_NORMAL,
                # The line layout never changes, so the horizontal slot is
                # fixed; only slot_y moves with the scroll
                "home_x": x + width / 2,
                "slot_y": 0.0,
                "prev_slot_y": 0.0,
                # NORMAL: offset from the slot
                "x": 0.0, "y": 0.0,
                # FALLING / GROUND / RETURNING: absolute screen position
                "px": 0.0, "py": 0.0,
                "vx": 0.0, "vy": 0.0,
                "angle": 0.0, "angular_velocity": 0.0,
                "ground_timer": 0.0,
                # Alternate spin direction so the letters don't all turn alike
                "rotation_direction": 1.0 if index % 2 == 0 else -1.0,
            })
            x += width
        return characters

    def _characters(self):
        """Yield every letter of every line, skipping spacers."""
        for line in self.lines:
            if line is not None:
                yield from line

    # ------------------------------------------------------------------
    # Credit text loading (from an external, editable file)
    # ------------------------------------------------------------------
    def _load_credit_lines(self):
        """Load credit lines from the first valid credits.json found.

        Returns a list of (text, is_title) tuples, with ("", False) as a
        spacer. Falls back to built-in lines if no valid file is found, so
        the screen never fails.
        """
        for path in self._credits_file_candidates():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue   # missing, unreadable or malformed: try the next one

            # Accept both {"lines": [...]} and a bare list
            raw_lines = data.get("lines") if isinstance(data, dict) else data
            if isinstance(raw_lines, list) and raw_lines:
                return [self._parse_credit_entry(entry) for entry in raw_lines]

        return self._default_credit_lines()

    def _credits_file_candidates(self):
        """Yield the paths to try for credits.json, configured path first."""
        configured = getattr(PATHS, "DATA_PATH_CREDITS", None)
        if configured:
            yield Path(configured)

        scenes_dir = Path(__file__).resolve().parent
        for base in (scenes_dir.parent, scenes_dir):   # project root, then scenes/
            for folder in ("", "data", "assets"):
                yield base / folder / "credits.json"

    def _parse_credit_entry(self, entry):
        """Convert a file entry into (text, is_title).

        Accepts a bare string (literal text; "" is a spacer) or a dict:
        {"i18n": key, "title": bool}, {"text": literal, "title": bool}, or
        {"spacer": true} / {} for a spacer. 'title' defaults to false.
        """
        if isinstance(entry, str):
            return (entry, False)

        if isinstance(entry, dict) and not entry.get("spacer"):
            is_title = bool(entry.get("title", False))
            if "i18n" in entry:
                return (t(entry["i18n"]), is_title)
            if "text" in entry:
                return (str(entry["text"]), is_title)

        return ("", False)   # spacer, empty dict or anything unexpected

    def _default_credit_lines(self):
        """Fallback content when no credits file is found."""
        return [
            (t("credits.roles.development"), True),
            ("Marcelo Tipán", False),
            ("", False),
            (t("credits.roles.thanks"), True),
            (t("credits.thanks_text"), False),
        ]

    # ------------------------------------------------------------------
    # Scroll and visibility
    # ------------------------------------------------------------------
    def _place_slots(self):
        """Set each letter's slot_y from the current scroll position."""
        band_height = self.BAND_BOTTOM - self.BAND_TOP
        offset = (self.scroll_time * self.SCROLL_SPEED) % (band_height + self.total_height)

        y = self.BAND_BOTTOM - offset   # first line
        for line in self.lines:
            if line is not None:
                for character in line:
                    character["slot_y"] = y
            y += self.LINE_SPACING

    def _alpha_at(self, y):
        """Opacity (0-255) for a vertical position, fading at the band edges."""
        if y < self.BAND_TOP or y > self.BAND_BOTTOM:
            return 0
        dist = min(y - self.BAND_TOP, self.BAND_BOTTOM - y)
        if dist >= self.FADE_ZONE:
            return 255
        return int(255 * dist / self.FADE_ZONE)

    def _distance_to_mouse(self, x, y):
        return math.hypot(x - self.mouse_pos[0], y - self.mouse_pos[1])

    # ------------------------------------------------------------------
    # Chip sound
    # ------------------------------------------------------------------
    def _load_chip_sounds(self):
        """Prepare the tile ("chip") sounds.

        Preference order: a dedicated file (PATHS.SOUND_PATH_CHIP), then a
        click synthesized with numpy (works with no asset), then nothing.
        Returns a list of Sound objects, possibly empty; never raises.
        """
        if not pygame.mixer.get_init():
            return []

        path = getattr(PATHS, "SOUND_PATH_CHIP", None)
        if path:
            try:
                return [pygame.mixer.Sound(str(path))]
            except (pygame.error, OSError):
                pass   # fall back to the synthesized click

        try:
            return self._synth_chip_variants()
        except (pygame.error, ValueError):
            return []

    def _synth_chip_variants(self):
        """Generate a few tile-like clicks with numpy.

        Each variant sounds slightly different, so a sweep of letters sounds
        like many tiles rather than one repeated tone.
        """
        try:
            import numpy as np
        except ImportError:
            return []

        freq, size, channels = pygame.mixer.get_init()
        if abs(size) != 16:   # only 16-bit output is handled
            return []

        sounds = []
        for seed in (11, 23, 37):
            rng = np.random.default_rng(seed)
            duration = 0.045
            samples = int(freq * duration)
            ts = np.linspace(0.0, duration, samples, endpoint=False)

            envelope = np.exp(-ts * 90.0)                     # fast percussive decay
            noise = rng.uniform(-1.0, 1.0, samples)           # the tile "click"
            tone = np.sin(2.0 * np.pi * 2200.0 * ts) * 0.3    # metallic brightness

            wave = np.clip((noise * 0.7 + tone) * envelope, -1.0, 1.0)
            pcm = (wave * 32767.0 * 0.8).astype(np.int16)
            if channels == 2:
                pcm = np.column_stack((pcm, pcm))
            sounds.append(pygame.sndarray.make_sound(np.ascontiguousarray(pcm)))
        return sounds

    def _play_chip(self, volume_scale=1.0):
        """Play a tile click with slight volume variation, scaled by impact."""
        if not self.chip_sounds:
            return

        now = pygame.time.get_ticks()
        if now - self._last_sound_ms < self.SOUND_COOLDOWN_MS:
            return
        self._last_sound_ms = now

        sound = random.choice(self.chip_sounds)
        volume = random.uniform(self.SOUND_VOLUME_MIN, self.SOUND_VOLUME_MAX) * volume_scale
        sound.set_volume(max(0.0, min(1.0, volume)))
        sound.play()

    # ------------------------------------------------------------------
    # Per-state physics
    # ------------------------------------------------------------------
    def _update_character(self, character, dt):
        """Update one letter's physics, dispatching by state."""
        state = character["state"]

        if state == self.STATE_NORMAL:
            # Only visible letters (inside the band) can be knocked down
            if self._alpha_at(character["slot_y"]) > 0:
                current_x = character["home_x"] + character["x"]
                current_y = character["slot_y"] + character["y"]
                if 0 < self._distance_to_mouse(current_x, current_y) < self.FALL_RADIUS:
                    self._start_fall(character, current_x, current_y)
                    return
            self._update_normal_character(character, dt)

        elif state == self.STATE_FALLING:
            self._update_falling_character(character, dt)

        elif state == self.STATE_GROUND:
            if self._distance_to_mouse(character["px"], character["py"]) < self.MOUSE_RADIUS:
                self._kick_ground_character(character)
            else:
                self._update_ground_character(character, dt)

        elif state == self.STATE_RETURNING:
            self._update_returning_character(character, dt)

    def _update_normal_character(self, character, dt):
        """Spring the letter around its slot, pushed away by the mouse.

        Velocity here is in px per reference frame (the unit the constants
        were tuned in) and every per-frame factor is scaled by `frames`.
        At 60 FPS this is exactly the original motion; at other frame rates
        the letters behave the same instead of speeding up or slowing down.
        """
        frames = dt * self.REFERENCE_FPS
        dx = character["home_x"] - self.mouse_pos[0]
        dy = character["slot_y"] - self.mouse_pos[1]
        distance = math.hypot(dx, dy)

        force_x = force_y = 0.0
        if 0 < distance < self.MOUSE_RADIUS:
            force = self.MOUSE_FORCE * (1.0 - distance / self.MOUSE_RADIUS)
            force_x = dx / distance * force
            force_y = dy / distance * force

        # Mouse push plus the spring pulling the letter back to its slot
        damping = self.DAMPING ** frames
        accel_x = force_x - character["x"] * self.RETURN_FORCE
        accel_y = force_y - character["y"] * self.RETURN_FORCE
        character["vx"] = (character["vx"] + accel_x * dt) * damping
        character["vy"] = (character["vy"] + accel_y * dt) * damping
        character["x"] += character["vx"] * frames
        character["y"] += character["vy"] * frames

    def _start_fall(self, character, abs_x, abs_y):
        """Knock a letter down from an absolute position."""
        character["state"] = self.STATE_FALLING
        character["px"] = abs_x   # from here on it lives in absolute coords
        character["py"] = abs_y
        character["vy"] = self.FALL_SPEED
        character["vx"] = (-1.0 if int(abs_x) % 2 == 0 else 1.0) * 20.0
        character["angular_velocity"] = self.FALL_ROTATION * character["rotation_direction"]
        self._play_chip()

    def _update_falling_character(self, character, dt):
        """Apply gravity and spin; bounce or settle on the floor."""
        character["vy"] += self.GRAVITY * dt
        character["px"] += character["vx"] * dt
        character["py"] += character["vy"] * dt
        character["angle"] += character["angular_velocity"] * dt

        if character["py"] >= self.GROUND_Y:
            character["py"] = self.GROUND_Y
            if abs(character["vy"]) > 60:
                character["vy"] *= -self.BOUNCE_FACTOR
                self._play_chip(volume_scale=0.7)   # bounce thud
            else:
                character["vy"] = 0.0
                character["state"] = self.STATE_GROUND
                character["ground_timer"] = 0.0
                character["angular_velocity"] *= 0.2
                self._play_chip()   # settled

    def _update_ground_character(self, character, dt):
        """Slide to a stop on the floor, then start returning."""
        friction = self.GROUND_FRICTION ** (dt * self.REFERENCE_FPS)
        character["vx"] *= friction
        character["angular_velocity"] *= friction
        character["px"] += character["vx"] * dt
        character["py"] = self.GROUND_Y
        character["angle"] += character["angular_velocity"] * dt

        character["ground_timer"] += dt
        if character["ground_timer"] >= self.GROUND_TIME:
            character["state"] = self.STATE_RETURNING

    def _kick_ground_character(self, character):
        """Kick a floored letter away from the mouse, back into the air."""
        dx = character["px"] - self.mouse_pos[0]
        distance = self._distance_to_mouse(character["px"], character["py"])
        if distance > 0:
            direction_x = dx / distance
            character["vx"] += direction_x * self.KICK_FORCE
            character["vy"] = -self.KICK_UP_FORCE   # small hop
            character["angular_velocity"] = self.KICK_ROTATION * direction_x
            character["ground_timer"] = 0.0
            character["state"] = self.STATE_FALLING
            self._play_chip()

    def _update_returning_character(self, character, dt):
        """Ease a letter back into its scroll slot without jitter.

        First the letter moves exactly as much as its slot moved this frame,
        so it rides the scroll with no lag; then only the leftover offset is
        eased toward zero. Chasing a moving target would always trail behind.
        """
        slot_x, slot_y = character["home_x"], character["slot_y"]

        # Slot already outside the visible band: snap back, it's invisible
        if self._alpha_at(slot_y) == 0:
            self._reset_to_normal(character)
            return

        # 1) Ride the slot
        character["py"] += slot_y - character["prev_slot_y"]

        # 2) Ease the remaining offset (exponential, so it's frame-rate independent)
        keep = math.exp(-self.RETURN_LERP * dt)
        offset_x = (character["px"] - slot_x) * keep
        offset_y = (character["py"] - slot_y) * keep
        character["px"] = slot_x + offset_x
        character["py"] = slot_y + offset_y
        character["angle"] *= keep

        # Once gap and spin are tiny, hand off to NORMAL seamlessly; the small
        # leftover offset is absorbed by the normal-state spring
        if abs(offset_x) < 1.0 and abs(offset_y) < 1.0 and abs(character["angle"]) < 1.0:
            self._reset_to_normal(character, offset_x, offset_y)

    def _reset_to_normal(self, character, x=0.0, y=0.0):
        """Hand a letter back to the scroll flow at the given slot offset."""
        character["state"] = self.STATE_NORMAL
        character["x"], character["y"] = x, y
        character["vx"] = character["vy"] = 0.0
        character["angle"] = character["angular_velocity"] = 0.0

    # ------------------------------------------------------------------
    # Scene hooks
    # ------------------------------------------------------------------
    def on_update(self):
        dt = min(self.director.dt, self.MAX_DT)
        self.mouse_pos = pygame.mouse.get_pos()   # cache once per frame

        self.scroll_time += dt
        self._place_slots()
        for character in self._characters():
            self._update_character(character, dt)
            character["prev_slot_y"] = character["slot_y"]

    def draw_content(self, screen):
        for character in self._characters():
            self._draw_character(screen, character)

    def _draw_character(self, screen, character):
        """Draw a letter in the reference frame of its current state."""
        if character["state"] == self.STATE_NORMAL:
            draw_x = character["home_x"] + character["x"]
            draw_y = character["slot_y"] + character["y"]
            alpha = self._alpha_at(character["slot_y"])
        else:
            # Detached letters are drawn at full opacity; they pick up the
            # band's fade again once they snap back to NORMAL
            draw_x, draw_y = character["px"], character["py"]
            alpha = 255

        if alpha <= 0:
            return

        surface = character["surface"]
        surface.set_alpha(alpha)
        if abs(character["angle"]) > 0.1:
            surface = pygame.transform.rotate(surface, character["angle"])
        screen.blit(surface, surface.get_rect(center=(int(draw_x), int(draw_y))))