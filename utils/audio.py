"""Game audio: sound effects and background music.

A single Audio instance is created by the Director and shared by every
scene through ``director.audio``. Sound effects live in a dict, so adding
a new one is a single line in EFFECTS; music uses the dedicated
``pygame.mixer.music`` channel so effects never interrupt it.
"""

import pygame

from config import PATHS
from utils import settings


class Audio:
    """Central audio controller (one shared instance, owned by the Director)."""

    #: Effect name -> file path. Add a new effect by adding one entry here.
    EFFECTS = {
        "click":        PATHS.SOUND_PATH_CLIC,
        "hover":        PATHS.SOUND_PATH_HOVER,
        "hit":          PATHS.SOUND_PATH_HIT,           # player paddle / walls
        "hit_enemy":    PATHS.SOUND_PATH_HIT_ENEMY,     # enemy paddle
        "hit_obstacle": PATHS.SOUND_PATH_HIT_OBSTACLE,  # asteroids
        "error":        PATHS.SOUND_PATH_ERROR,         # missed ball
    }

    def __init__(self):
        self.sounds = {
            name: pygame.mixer.Sound(str(path))
            for name, path in self.EFFECTS.items()
        }
        # Path of the track currently playing, to avoid restarting it
        self.current_music = None

        self.volume = 1.0
        self.set_volume(settings.get("volume"))

    def set_volume(self, volume):
        """Set the volume (0.0-1.0) for music and every effect at once."""
        self.volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.volume)
        for sound in self.sounds.values():
            sound.set_volume(self.volume)

    # ------------------------------------------------------------------
    # Sound effects
    # ------------------------------------------------------------------
    def play(self, name):
        """Play an effect by its EFFECTS key."""
        self.sounds[name].play()

    # Named shortcuts used by buttons and scenes
    def play_click(self):
        self.play("click")

    def play_hover(self):
        self.play("hover")

    def play_hit(self):
        self.play("hit")

    def play_error(self):
        self.play("error")

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