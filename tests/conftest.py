"""Shared test setup, loaded by pytest before any test module.

Uses SDL's dummy drivers so the tests run without a window or audio device
(needed on CI servers and machines without a display).
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
