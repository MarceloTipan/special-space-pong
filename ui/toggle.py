"""Toggle switch (a pill with a sliding knob) for boolean settings.

The pill's color shows the state and the knob slides across when toggled.
Same update/draw interface as the other ui components.
"""

import pygame

from config import UI

class Toggle:
    """Pill-shaped on/off switch with an animated knob."""

    def __init__(self, pos, get_state, action, audio=None,
                 width=72, height=34, on_text=None, off_text=None,
                 font_path=None,
                 on_color=UI.COLORS["YELLOW"], 
                 off_color=UI.COLORS["GRAY"],
                 knob_color=UI.COLORS["WHITE"]):
        """Create a toggle.

        Args:
            pos: Center (x, y) of the switch.
            get_state: Callable returning the current state (True = on).
            action: Callback run on click; must flip the state get_state reads.
            on_text / off_text: Optional label shown inside the pill.
            font_path: Font for the inner label (None uses pygame's default).
        """
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = pos
        self.get_state = get_state
        self.action = action
        self.audio = audio
        self.on_color = on_color
        self.off_color = off_color
        self.knob_color = knob_color

        self.hovered = False
        self._was_hovered = False

        # Animated knob position (0.0 = left, 1.0 = right)
        self.knob_t = 1.0 if get_state() else 0.0

        # Inner labels, pre-rendered in a tone derived from the pill color
        # so they read like a watermark
        font_size = max(9, int(height * 0.38))
        font = (pygame.font.Font(str(font_path), font_size) if font_path
                else pygame.font.Font(None, font_size + 6))
        dark_on = tuple(c // 2 for c in on_color)
        dark_off = tuple(min(255, c + 70) for c in off_color)
        self.on_surface = font.render(on_text, True, dark_on) if on_text else None
        self.off_surface = font.render(off_text, True, dark_off) if off_text else None

        # Widen the pill if the text doesn't fit next to the knob
        widest = max((s.get_width() for s in (self.on_surface, self.off_surface)
                      if s is not None), default=0)
        needed = height + widest + 18
        if needed > self.rect.width:
            self.rect.width = needed
            self.rect.center = pos

    def update(self, mouse_pos, clicked):
        self.hovered = self.rect.collidepoint(mouse_pos)
        if self.hovered and not self._was_hovered and self.audio:
            self.audio.play_hover()
        self._was_hovered = self.hovered
        if self.hovered and clicked:
            if self.audio:
                self.audio.play_click()
            self.action()

    def draw(self, screen):
        state = self.get_state()

        # Ease the knob toward its side (exponential interpolation)
        target = 1.0 if state else 0.0
        self.knob_t += (target - self.knob_t) * 0.25
        if abs(self.knob_t - target) < 0.01:
            self.knob_t = target

        pill_color = self.on_color if state else self.off_color
        radius = self.rect.height // 2
        pygame.draw.rect(screen, pill_color, self.rect, border_radius=radius)
        if self.hovered:
            pygame.draw.rect(screen, self.knob_color, self.rect,
                             width=2, border_radius=radius)

        margin = 4
        knob_radius = radius - margin
        left_x = self.rect.left + margin + knob_radius
        right_x = self.rect.right - margin - knob_radius
        knob_x = left_x + (right_x - left_x) * self.knob_t

        # Inner label centered in the gap the knob leaves free
        text = self.on_surface if state else self.off_surface
        if text is not None:
            gap_left = self.rect.left + margin
            gap_right = knob_x - knob_radius
            if not state:   # knob on the left -> gap on the right
                gap_left = knob_x + knob_radius
                gap_right = self.rect.right - margin
            center_x = (gap_left + gap_right) / 2
            screen.blit(text, text.get_rect(
                center=(int(center_x), self.rect.centery)))

        pygame.draw.circle(screen, self.knob_color,
                           (int(knob_x), self.rect.centery), knob_radius)