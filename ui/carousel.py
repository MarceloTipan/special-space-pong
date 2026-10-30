"""Carousel: pages that slide in and out, advancing on their own.

Navigation: LEFT/RIGHT keys, the < > arrows, clicking a dot, or dragging
the page with the mouse (or a finger, in the web version). Any of these
pauses the automatic advance for a while, so the player isn't rushed.
"""

import math

import pygame


def ease_out_cubic(t):
    """Fast start, gentle stop (t from 0 to 1)."""
    return 1 - (1 - t) ** 3


class Carousel:
    """Shows one page at a time inside a rect, with animated transitions.

    Pages are objects with update(dt) and draw(surface, rect, appear), where
    appear goes from 0 to 1 once the page has settled (for fade-ins), and
    optionally restart(), called when the page is about to be shown.
    """

    AUTO_ADVANCE = 6.0       #: seconds per page when nobody touches anything
    IDLE_RESUME = 8.0        #: after an interaction, auto-advance waits this long
    SLIDE_TIME = 0.45        #: duration of a page transition (s)
    APPEAR_TIME = 0.4        #: text fade-in once a page settles (s)
    DRAG_THRESHOLD = 0.18    #: drag this share of the width to change page
    DOT_RADIUS = 6
    DOT_GAP = 26
    ARROW_SIZE = 18

    def __init__(self, pages, rect, dots_y, colors, audio=None):
        """Create the carousel.

        Args:
            pages: Page objects (see the class docstring).
            rect: Area where pages are drawn.
            dots_y: Height of the page indicator dots.
            colors: Dict with "active", "idle" and "accent" colors.
            audio: Audio for the page-change sound (optional).
        """
        self.pages = pages
        self.rect = pygame.Rect(rect)
        self.dots_y = dots_y
        self.colors = colors
        self.audio = audio

        self.index = 0
        self.position = 0.0          # shown page as a float: 1.5 = halfway from 1 to 2
        self._from = self._to = 0.0  # transition endpoints
        self._transition = 1.0       # 0..1 progress of the current transition
        self.auto_time = 0.0         # time on the current page (auto-advance)
        self.idle_time = self.IDLE_RESUME   # time since the last interaction
        self.settled_time = 0.0      # time since the page stopped moving
        self._drag_start = None      # mouse x where a drag began
        self._drag_dx = 0.0

        cy = self.rect.centery
        self.arrow_rects = {
            -1: pygame.Rect(0, 0, 44, 60),
            +1: pygame.Rect(0, 0, 44, 60),
        }
        self.arrow_rects[-1].center = (self.rect.left - 30, cy)
        self.arrow_rects[+1].center = (self.rect.right + 30, cy)
        self.hovered_arrow = None

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def go_to(self, index, user=True):
        """Slide straight to a page (clicking its dot)."""
        self._slide_to(float(index % len(self.pages)), user)

    def step(self, direction, user=True):
        """Slide to the next (+1) or previous (-1) page. Past the last page
        it keeps sliding the same way into the first, instead of rewinding."""
        current = self._to if self._transition < 1 else round(self.position)
        self._slide_to(current + direction, user)

    def _slide_to(self, target, user):
        self._from, self._to = self.position, target
        self._transition = 0.0
        self.index = int(target) % len(self.pages)
        restart = getattr(self.pages[self.index], "restart", None)
        if restart is not None:
            restart()   # the arriving page plays its demo from the start
        self.auto_time = 0.0
        self.settled_time = 0.0
        if user:
            self.idle_time = 0.0
        if self.audio is not None:
            self.audio.play_hover()

    def handle_event(self, event):
        """Keys, arrow and dot clicks, and dragging."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                self.step(-1)
            elif event.key == pygame.K_RIGHT:
                self.step(+1)
        elif event.type == pygame.MOUSEMOTION:
            self.hovered_arrow = next(
                (d for d, r in self.arrow_rects.items() if r.collidepoint(event.pos)), None)
            if self._drag_start is not None:
                self._drag_dx = event.pos[0] - self._drag_start
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for direction, rect in self.arrow_rects.items():
                if rect.collidepoint(event.pos):
                    self.step(direction)
                    return
            for i, dot in enumerate(self._dot_rects()):
                if dot.collidepoint(event.pos):
                    self.go_to(i)
                    return
            if self.rect.collidepoint(event.pos):
                self._drag_start, self._drag_dx = event.pos[0], 0.0
                self.idle_time = 0.0
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._drag_start is not None:
                share = self._drag_dx / self.rect.width
                self._drag_start, self._drag_dx = None, 0.0
                if abs(share) >= self.DRAG_THRESHOLD:
                    self.step(-1 if share > 0 else +1)   # drag right = previous page

    # ------------------------------------------------------------------
    # Per frame
    # ------------------------------------------------------------------
    def update(self, dt):
        self.idle_time += dt
        if self._transition < 1:
            self._transition = min(1.0, self._transition + dt / self.SLIDE_TIME)
            t = ease_out_cubic(self._transition)
            self.position = self._from + (self._to - self._from) * t
            if self._transition >= 1:
                self.position = float(self.index)   # undo the forward wrap
        else:
            self.settled_time += dt
            if self._drag_start is None and self.idle_time >= self.IDLE_RESUME:
                self.auto_time += dt
                if self.auto_time >= self.AUTO_ADVANCE:
                    self.step(+1, user=False)

        for page in self._visible_pages():
            page.update(dt)

    @property
    def offset(self):
        """Shown position in pixels, including a drag in progress (for parallax)."""
        return self.position * self.rect.width - self._drag_dx

    def auto_progress(self):
        """0..1 progress toward the next automatic page change."""
        if self.idle_time < self.IDLE_RESUME:
            return 0.0
        return min(1.0, self.auto_time / self.AUTO_ADVANCE)

    def _visible_pages(self):
        shown = self.position - self._drag_dx / self.rect.width
        first = math.floor(shown)
        return {self.pages[i % len(self.pages)] for i in (first, first + 1)}

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw(self, screen):
        shown = self.position - self._drag_dx / self.rect.width
        first = math.floor(shown)
        fraction = shown - first
        appear = min(1.0, self.settled_time / self.APPEAR_TIME)

        previous_clip = screen.get_clip()
        screen.set_clip(self.rect)
        for i, page_index in enumerate((first, first + 1)):
            dx = int((i - fraction) * self.rect.width)
            if abs(dx) >= self.rect.width:
                continue
            page = self.pages[page_index % len(self.pages)]
            # The page arriving fades its text in; the one leaving keeps it
            page_appear = appear if page_index % len(self.pages) == self.index else 1.0
            page.draw(screen, self.rect.move(dx, 0), page_appear)
        screen.set_clip(previous_clip)

        self._draw_arrows(screen)
        self._draw_dots(screen, shown)

    def _dot_rects(self):
        count = len(self.pages)
        start = self.rect.centerx - (count - 1) * self.DOT_GAP / 2
        size = self.DOT_RADIUS * 3
        return [pygame.Rect(int(start + i * self.DOT_GAP - size / 2),
                            self.dots_y - size // 2, size, size) for i in range(count)]

    def _draw_dots(self, screen, shown):
        """A dot per page; the current one stretches into a pill, following
        the transition, and a thin bar under it fills up to the next page."""
        count = len(self.pages)
        start = self.rect.centerx - (count - 1) * self.DOT_GAP / 2
        for i in range(count):
            distance = abs(((shown - i + count / 2) % count) - count / 2)
            closeness = max(0.0, 1 - distance)   # 1 on the current page
            width = int(self.DOT_RADIUS * 2 + closeness * self.DOT_RADIUS * 2.5)
            x = int(start + i * self.DOT_GAP)
            color = self.colors["active"] if closeness > 0.5 else self.colors["idle"]
            dot = pygame.Rect(0, 0, width, self.DOT_RADIUS * 2)
            dot.center = (x, self.dots_y)
            pygame.draw.rect(screen, color, dot, border_radius=self.DOT_RADIUS)

        progress = self.auto_progress()
        if progress > 0:
            bar_width = (count - 1) * self.DOT_GAP + self.DOT_RADIUS * 6
            bar = pygame.Rect(0, 0, bar_width, 2)
            bar.midtop = (self.rect.centerx, self.dots_y + self.DOT_RADIUS + 10)
            pygame.draw.rect(screen, self.colors["idle"], bar)
            pygame.draw.rect(screen, self.colors["accent"],
                             (bar.x, bar.y, int(bar.width * progress), bar.height))

    def _draw_arrows(self, screen):
        for direction, rect in self.arrow_rects.items():
            color = self.colors["active"] if direction == self.hovered_arrow else self.colors["idle"]
            cx, cy = rect.center
            s = self.ARROW_SIZE
            tip = (cx + direction * s // 2, cy)
            pygame.draw.lines(screen, color, False,
                              [(cx - direction * s // 2, cy - s), tip,
                               (cx - direction * s // 2, cy + s)], 4)
