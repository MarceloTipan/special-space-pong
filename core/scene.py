"""Base class for all scenes (menu, game, settings, ...).

A scene is a visible part of the game — a screen. The Director drives the
active scene by calling its hooks each frame. Subclasses override only the
hooks they need; all of them are optional no-ops here.
"""


class Scene:
    """Abstract game scene driven by the Director."""

    def __init__(self, director):
        self.director = director

    def on_enter(self):
        """Called when the scene becomes active, with the window ready.

        Load resources that need the display to exist here, not in __init__.
        """

    def on_update(self):
        """Per-frame logic (optional; static screens don't need it)."""

    def on_event(self, event):
        """Handle one pygame event (optional)."""

    def on_draw(self, screen):
        """Draw the scene."""