"""Entry point: python main.py (desktop) or pygbag . (browser)."""

import asyncio

import pygame

from core import director
from scenes import menu
from utils import settings
from utils.i18n import set_language


async def main():
    """Load the settings, open the window and run the game from the menu."""
    settings.load()
    set_language(settings.get("language"))

    pygame.init()
    app = director.Director()
    app.change_scene(menu.Menu(app))
    await app.loop()
    pygame.quit()

# pygbag needs this exact call at the end of main.py, with nothing after it
asyncio.run(main())
