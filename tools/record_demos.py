"""Record the instructions demos as GIFs, e.g. for the README.

Draws each page's animation off-screen, frame by frame, with the real
sprites, and saves one looping GIF per page (only the animation; the README
gives the captions). Run it from the project root:

    python tools/record_demos.py
    python tools/record_demos.py --out docs/demos --width 420 --fps 15

Needs Pillow (in requirements-dev.txt).
"""

import argparse
import os
import sys
from pathlib import Path

# Headless: no window and no audio device needed
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402
from PIL import Image  # noqa: E402

SCENE_SIZE = (560, 420)   #: drawing size of each demo, before scaling down


def record(page, fps, width, colors):
    """Frames of one loop of a page's demo, as palette images."""
    surface = pygame.Surface(SCENE_SIZE)
    rect = surface.get_rect()
    height = round(width * SCENE_SIZE[1] / SCENE_SIZE[0])
    page.restart()
    frames = []
    for _ in range(round(page.LOOP_SECONDS * fps)):
        surface.fill((5, 10, 25))
        page.draw_scene(surface, rect)
        pygame.draw.rect(surface, (80, 200, 255), rect, width=3, border_radius=8)
        image = Image.frombytes("RGB", SCENE_SIZE, pygame.image.tostring(surface, "RGB"))
        image = image.resize((width, height), Image.LANCZOS)
        frames.append(image.quantize(colors=colors, method=Image.Quantize.MEDIANCUT))
        page.update(1 / fps)
    return frames


def main():
    parser = argparse.ArgumentParser(description="Record the instructions demos as GIFs.")
    parser.add_argument("--out", default="docs/demos", help="output folder")
    parser.add_argument("--width", type=int, default=420, help="GIF width in pixels")
    parser.add_argument("--fps", type=int, default=15)
    parser.add_argument("--colors", type=int, default=48, help="palette size (smaller = lighter files)")
    parser.add_argument("--lang", default="en", help="language of the labels drawn in the demos")
    args = parser.parse_args()

    from config import GAME
    from utils import i18n
    pygame.init()
    pygame.display.set_mode(GAME.SCREEN_SIZE)   # needed to load sprites with alpha
    i18n.set_language(args.lang)
    from scenes.instruction_slides import build_pages

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    for page in build_pages():
        frames = record(page, args.fps, args.width, args.colors)
        path = out / f"{page.NAME}.gif"
        frames[0].save(path, save_all=True, append_images=frames[1:],
                       duration=round(1000 / args.fps), loop=0, optimize=True)
        print(f"{path.relative_to(ROOT)}  ({len(frames)} frames, {path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
