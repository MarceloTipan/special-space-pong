"""Game audio: sound effects and background music.

A single Audio instance is created by the Director and shared by every
scene through ``director.audio``. Sound effects live in a dict, so adding
one is a single line in EFFECTS; music uses the dedicated
``pygame.mixer.music`` channel so effects never interrupt it.
"""

import random

import pygame

from config import PATHS
from utils import settings


class Audio:
    """Central audio controller (one shared instance, owned by the Director)."""

    #: Effect name -> file path, or a list of paths for variants: a list
    #: plays a random one each time, so repeated hits don't sound identical.
    EFFECTS = {
        "click":        PATHS.SOUND_PATH_CLIC,
        "hover":        PATHS.SOUND_PATH_HOVER,
        "hit_player":   [PATHS.SOUND_PATH_HIT_PLAYER],
        "hit_wall":     PATHS.SOUND_PATH_HIT_WALL,
        "hit_enemy":    [PATHS.SOUND_PATH_HIT_ENEMY_1, PATHS.SOUND_PATH_HIT_ENEMY_2,
                         PATHS.SOUND_PATH_HIT_ENEMY_3, PATHS.SOUND_PATH_HIT_ENEMY_4],
        "hit_obstacle": PATHS.SOUND_PATH_HIT_OBSTACLE,
        "error":        PATHS.SOUND_PATH_ERROR,
        "goal":         PATHS.SOUND_PATH_GOAL,
    }

    def __init__(self):
        self.sounds = {name: self._load(value) for name, value in self.EFFECTS.items()}
        # Path of the track currently playing, to avoid restarting it
        self.current_music = None

        self.volume = 1.0
        self.set_volume(settings.get("volume"))

    @staticmethod
    def _load(value):
        """Load a single path, or a list of paths as a group of variants."""
        if isinstance(value, (list, tuple)):
            return [pygame.mixer.Sound(str(path)) for path in value]
        return pygame.mixer.Sound(str(value))

    def _iter_sounds(self):
        """Yield every loaded Sound, whether single or part of a variant group."""
        for value in self.sounds.values():
            if isinstance(value, list):
                yield from value
            else:
                yield value

    def set_volume(self, volume):
        """Set the volume (0.0-1.0) for music and every effect at once."""
        self.volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.volume)
        for sound in self._iter_sounds():
            sound.set_volume(self.volume)

    # ------------------------------------------------------------------
    # Sound effects
    # ------------------------------------------------------------------
    def play(self, name):
        """Play an effect by its EFFECTS key (a random variant for groups)."""
        sound = self.sounds[name]
        if isinstance(sound, list):
            sound = random.choice(sound)
        sound.play()

    # Named shortcuts used by buttons and scenes
    def play_click(self):
        self.play("click")

    def play_hover(self):
        self.play("hover")

    def play_hit(self):
        """Ball hitting a wall."""
        self.play("hit_wall")

    def play_error(self):
        self.play("error")

    def play_goal(self):
        self.play("goal")

    # ------------------------------------------------------------------
    # Background music (exclusive mixer.music channel)
    # ------------------------------------------------------------------
    def play_music(self, path, fade_ms=1000):
        """Loop background music with a fade-in.

        Does nothing if that track is already playing, so navigating
        between menu screens doesn't restart it. Use .ogg for gapless loops.
        """
        if self.current_music == str(path):
            return
        self.current_music = str(path)
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.set_volume(self.volume)
        pygame.mixer.music.play(loops=-1, fade_ms=fade_ms)

    def stop_music(self, fade_ms=1000):
        """Stop the background music with a fade-out."""
        self.current_music = None
        pygame.mixer.music.fadeout(fade_ms)