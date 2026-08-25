"""Draggable horizontal slider, used for volume (and other 0.0-1.0 values).

Unlike the buttons, it takes raw pygame events via handle_event(), because
dragging needs to tell press, move and release apart.
"""

import pygame


class Slider:
    """Horizontal track with a draggable handle; value in [0.0, 1.0]."""

    TRACK_HEIGHT = 6
    HANDLE_RADIUS = 12

    def __init__(self, pos, width, value, label, font_config,
                 track_color, fill_color, handle_color, text_color,
                 on_change=None, on_release=None):
        """Create a slider.

        Args:
            pos: Center (x, y) of the whole widget.
            width: Track width in pixels.
            value: Initial value (0.0 to 1.0).
            label: Caption drawn above the track.
            font_config: (font_path, size) tuple.
            on_change: Callback(value) fired while dragging.
            on_release: Callback(value) fired when the handle is released.
        """
        self.x, self.y = pos
        self.width = width
        self.value = max(0.0, min(1.0, value))
        self.dragging = False

        self.track_color = track_color
        self.fill_color = fill_color
        self.handle_color = handle_color
        self.text_color = text_color
        self.on_change = on_change
        self.on_release = on_release

        font = pygame.font.Font(*font_config)
        self.label_surface = font.render(label, True, text_color)
        self.pct_font = font
        self._pct_cache_value = None
        self._pct_surface = None

        # Center the whole group (track + percentage) on self.x by reserving
        # room for the widest percentage ("100%")
        self.pct_gap = 25
        self.pct_reserve = font.size("100%")[0]
        total = self.width + self.pct_gap + self.pct_reserve
        self._left = self.x - total // 2

    @property
    def track_left(self):
        return self._left

    @property
    def handle_x(self):
        return self.track_left + int(self.value * self.width)

    def _value_from_mouse(self, mouse_x):
        rel = (mouse_x - self.track_left) / self.width
        return max(0.0, min(1.0, rel))

    def handle_event(self, event):
        """Process one raw pygame event (press, drag or release)."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            on_handle = (abs(mx - self.handle_x) <= self.HANDLE_RADIUS * 2
                         and abs(my - self.y) <= self.HANDLE_RADIUS * 2)
            on_track = (self.track_left <= mx <= self.track_left + self.width
                        and abs(my - self.y) <= self.HANDLE_RADIUS)
            if on_handle or on_track:
                self.dragging = True
                self._set_value(self._value_from_mouse(mx))

        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_value(self._value_from_mouse(event.pos[0]))

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False
                if self.on_release:
                    self.on_release(self.value)

    def _set_value(self, value):
        if value != self.value:
            self.value = value
            if self.on_change:
                self.on_change(value)

    def draw(self, screen):
        # Label centered on the widget center (not the track, which sits
        # left of center because of the percentage's reserved space)
        label_rect = self.label_surface.get_rect(midbottom=(self.x, self.y - 18))
        screen.blit(self.label_surface, label_rect)

        track_rect = pygame.Rect(
            self.track_left, self.y - self.TRACK_HEIGHT // 2,
            self.width, self.TRACK_HEIGHT)
        pygame.draw.rect(screen, self.track_color, track_rect, border_radius=3)

        fill_rect = pygame.Rect(
            self.track_left, self.y - self.TRACK_HEIGHT // 2,
            self.handle_x - self.track_left, self.TRACK_HEIGHT)
        pygame.draw.rect(screen, self.fill_color, fill_rect, border_radius=3)

        radius = self.HANDLE_RADIUS + (3 if self.dragging else 0)   # grows while dragging
        pygame.draw.circle(screen, self.handle_color, (self.handle_x, self.y), radius)

        # Percentage on the right, re-rendered only when it changes
        pct = int(self.value * 100)
        if pct != self._pct_cache_value:
            self._pct_cache_value = pct
            self._pct_surface = self.pct_font.render(f"{pct}%", True, self.text_color)
        pct_rect = self._pct_surface.get_rect(
            midleft=(self.track_left + self.width + self.pct_gap, self.y))
        screen.blit(self._pct_surface, pct_rect)