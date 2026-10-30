"""Text helpers shared by several screens."""

from functools import lru_cache

import pygame


def wrap_text(text, font, max_width):
    """Split text into lines that fit within max_width pixels.

    Words are never broken: a single word wider than max_width gets a line
    of its own.

    Args:
        text: Text to wrap.
        font: pygame Font used to measure the text.
        max_width: Maximum line width, in pixels.

    Returns:
        A list of lines (empty if the text is empty).
    """
    lines, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if font.size(candidate)[0] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


@lru_cache(maxsize=None)
def _font(path, size):
    return pygame.font.Font(path, size)


def render_fit(font_path, size, text, color, max_width):
    """Render text at the largest size, up to size, that fits max_width.

    The size steps down in multiples of 8 so pixel fonts (like Press Start
    2P, drawn on an 8 px grid) stay crisp instead of being scaled blurry.

    Args:
        font_path: Path of the font file.
        size: Preferred size.
        text: Text to render.
        color: Text color.
        max_width: Maximum width, in pixels.

    Returns:
        The rendered Surface.
    """
    font_path = str(font_path)
    while True:
        font = _font(font_path, size)
        if font.size(text)[0] <= max_width or size <= 8:
            return font.render(text, True, color)
        size = (size - 1) // 8 * 8
