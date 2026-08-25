"""Icon button with hover, used for the menu's secondary actions.

Same update/draw interface as TextButton, so it can live in the same
button list. If no image is given it draws a placeholder shape, so the
menu works before the icon assets exist.
"""

import math

import pygame

from config import UI

class IconButton:
    """Square icon button with an image, or a drawn placeholder."""

    #: Placeholder shapes available when no image is provided.
    ICONS = ("gear", "info", "trophy", "question")

    def __init__(self, pos, action, size=48, image_path=None, icon="gear",
                 color=UI.COLORS["DARK_GRAY"], 
                 hover_color=UI.COLORS["WHITE"], 
                 audio=None):
        """Create an icon button.

        Args:
            pos: Center (x, y) of the button.
            action: Callback run on click.
            size: Side of the clickable area, in pixels.
            image_path: Icon image path; falls back to a placeholder if absent.
            icon: Placeholder shape: gear, info, trophy or question.
        """
        self.icon = icon if icon in self.ICONS else "gear"
        self.pos = pos
        self.action = action
        self.size = size
        self.color = color
        self.hover_color = hover_color
        self.audio = audio
        self.hovered = False
        self._was_hovered = False

        self.image = None
        if image_path:
            try:
                img = pygame.image.load(str(image_path)).convert_alpha()
                self.image = pygame.transform.smoothscale(img, (size, size))
            except (pygame.error, FileNotFoundError):
                print(f"[IconButton] Could not load {image_path}, using placeholder")

        self.rect = pygame.Rect(0, 0, size, size)
        self.rect.center = pos

    def update(self, mouse_pos, clicked):
        self.hovered = self.rect.collidepoint(mouse_pos)
        # Play the hover sound only when ENTERING the button, not every frame
        if self.hovered and not self._was_hovered and self.audio:
            self.audio.play_hover()
        self._was_hovered = self.hovered

        if self.hovered and clicked:
            self.action()

    def draw(self, screen):
        if self.image:
            img = self.image
            if self.hovered:
                grow = int(self.size * 1.12)   # slight zoom on hover
                img = pygame.transform.smoothscale(self.image, (grow, grow))
            screen.blit(img, img.get_rect(center=self.pos))
        else:
            self._draw_placeholder(screen)

    # ------------------------------------------------------------------
    # Placeholder shapes (used until real icon assets exist)
    # ------------------------------------------------------------------
    def _draw_placeholder(self, screen):
        color = self.hover_color if self.hovered else self.color
        {
            "gear": self._draw_gear,
            "info": self._draw_info,
            "trophy": self._draw_trophy,
            "question": self._draw_question,
        }[self.icon](screen, color)

    def _glyph(self, screen, color, char):
        """Draw a circle with a centered character (for info and question)."""
        cx, cy = self.pos
        radius = self.size // 2 - 4
        pygame.draw.circle(screen, color, (cx, cy), radius, 4)
        font = pygame.font.Font(None, int(self.size * 0.8))
        surface = font.render(char, True, color)
        screen.blit(surface, surface.get_rect(center=(cx, cy + 1)))

    def _draw_info(self, screen, color):
        self._glyph(screen, color, "i")

    def _draw_question(self, screen, color):
        self._glyph(screen, color, "?")

    def _draw_trophy(self, screen, color):
        cx, cy = self.pos
        s = self.size
        body = pygame.Rect(0, 0, int(s * 0.44), int(s * 0.38))
        body.midtop = (cx, cy - int(s * 0.38))
        pygame.draw.rect(screen, color, body, 4,
                         border_bottom_left_radius=10, border_bottom_right_radius=10)
        for side in (-1, 1):   # handles
            handle_x = cx + side * (body.width // 2 + 5)
            pygame.draw.circle(screen, color, (handle_x, body.centery - 3), 7, 3)
        pygame.draw.rect(screen, color, (cx - 3, body.bottom, 6, int(s * 0.16)))
        base = pygame.Rect(0, 0, int(s * 0.4), 5)
        base.midtop = (cx, body.bottom + int(s * 0.16))
        pygame.draw.rect(screen, color, base)

    def _draw_gear(self, screen, color):
        cx, cy = self.pos
        outer = self.size // 2 - 6
        for i in range(8):   # eight radial teeth
            angle = math.radians(i * 45)
            x1 = cx + math.cos(angle) * (outer - 4)
            y1 = cy + math.sin(angle) * (outer - 4)
            x2 = cx + math.cos(angle) * (outer + 5)
            y2 = cy + math.sin(angle) * (outer + 5)
            pygame.draw.line(screen, color, (x1, y1), (x2, y2), 6)
        pygame.draw.circle(screen, color, (cx, cy), outer, 6)
        pygame.draw.circle(screen, color, (cx, cy), outer // 3, 4)