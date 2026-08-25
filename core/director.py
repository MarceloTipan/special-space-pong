"""Main game loop: updates, draws and dispatches events to the active scene.

The whole game is 2D pygame. The Director owns the single Audio instance
(director.audio) and exposes director.dt (seconds since the last frame)
for frame-rate-independent physics. Continuous keyboard state is read in
each scene's on_update.
"""

import pygame
from pygame.locals import DOUBLEBUF, FULLSCREEN, SCALED

from config import GAME, PATHS
from utils import settings
from utils.audio import Audio


class Director:
    """Owns the window, the game loop and scene transitions."""

    #: Window caption per game status.
    CAPTIONS = {
        GAME.STATUS_MENU:         "Pong - Menu",
        GAME.STATUS_INSTRUCTIONS: "Pong - How to Play",
        GAME.STATUS_CREDITS:      "Pong - Credits",
        GAME.STATUS_SETTINGS:     "Pong - Settings",
        GAME.STATUS_LOADING:      "Pong - Loading",
        GAME.STATUS_GAME:         "Pong - Game",
        GAME.STATUS_HIGHSCORES:   "Pong - High Scores",
        GAME.STATUS_NAME_ENTRY:   "Pong - New Record",
    }

    #: Statuses that share the menu music.
    MENU_STATUSES = {
        GAME.STATUS_MENU, GAME.STATUS_INSTRUCTIONS,
        GAME.STATUS_CREDITS, GAME.STATUS_SETTINGS,
        GAME.STATUS_HIGHSCORES, GAME.STATUS_NAME_ENTRY,
    }

    def __init__(self):
        self.SCREEN_SIZE = GAME.SCREEN_SIZE

        icon = pygame.image.load(PATHS.IMAGE_PATH_ICON)
        pygame.display.set_icon(icon)

        self._current_flags = self._compute_flags()
        self.screen = pygame.display.set_mode(self.SCREEN_SIZE, self._current_flags)

        # Single Audio instance shared by every scene
        self.audio = Audio()

        self.scene = None
        self.quit_flag = False
        self.clock = pygame.time.Clock()

        self.status = 0        # set by each scene in its __init__
        self.dt = 0.0          # seconds elapsed in the last frame (physics)
        self.TIME = 0.0        # accumulated seconds

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def loop(self):
        """Run the game until quit is requested."""
        while not self.quit_flag:
            self.dt = self.clock.tick(GAME.FPS) / 1000.0
            self.TIME += self.dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                else:
                    self.scene.on_event(event)

            self.scene.on_update()
            self.scene.on_draw(self.screen)

            pygame.display.flip()

    # ------------------------------------------------------------------
    # Scene switching
    # ------------------------------------------------------------------
    def change_scene(self, scene):
        """Switch scene, reconfigure the window, update music and enter it."""
        self.scene = scene
        self._apply_display_config()
        self._update_music()
        scene.on_enter()

    def _compute_flags(self):
        # SCALED: the game is written at the logical GAME.SCREEN_SIZE and
        # pygame scales the window to fit any monitor (mouse included)
        flags = DOUBLEBUF | SCALED
        if settings.get("fullscreen"):
            flags |= FULLSCREEN
        return flags

    def _apply_display_config(self):
        """Update the caption and re-create the window only if the mode changed."""
        pygame.display.set_caption(self.CAPTIONS.get(self.status, "Pong"))

        flags = self._compute_flags()
        if flags != self._current_flags:
            # If fullscreen is the ONLY thing that changed, use the native
            # toggle: it flips without re-creating the window (re-creating it
            # with set_mode leaves it mis-positioned on Windows)
            only_fullscreen = (flags ^ self._current_flags) == FULLSCREEN
            self._current_flags = flags
            if only_fullscreen:
                pygame.display.toggle_fullscreen()
            else:
                self.screen = pygame.display.set_mode(self.SCREEN_SIZE, flags)

    def _update_music(self):
        """Pick music by scene group: menu music, game music, or silence."""
        if self.status in self.MENU_STATUSES:
            self.audio.play_music(PATHS.MUSIC_PATH_MENU)
        elif self.status == GAME.STATUS_GAME:
            self.audio.play_music(PATHS.MUSIC_PATH_GAME)
        else:
            self.audio.stop_music()

    def quit(self):
        """Request the game to close."""
        self.quit_flag = True