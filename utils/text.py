"""Text helpers shared by several screens."""


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