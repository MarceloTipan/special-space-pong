"""Tests for the carousel's navigation (no drawing involved)."""

import pygame
import pytest

from ui.carousel import Carousel, ease_out_cubic

COLORS = {"active": (255, 255, 0), "idle": (90, 90, 90), "accent": (0, 200, 255)}


class FakePage:
    def __init__(self):
        self.restarts = 0

    def update(self, dt):
        pass

    def restart(self):
        self.restarts += 1


@pytest.fixture
def carousel():
    pages = [FakePage() for _ in range(5)]
    return Carousel(pages, pygame.Rect(100, 100, 600, 400), dots_y=550, colors=COLORS)


def run(carousel, seconds, dt=1 / 60):
    for _ in range(int(seconds / dt)):
        carousel.update(dt)


def key(code):
    return pygame.event.Event(pygame.KEYDOWN, key=code)


def test_easing_starts_fast_and_ends_at_one():
    assert ease_out_cubic(0) == 0
    assert ease_out_cubic(1) == 1
    assert ease_out_cubic(0.5) > 0.5


def test_it_advances_on_its_own(carousel):
    run(carousel, Carousel.AUTO_ADVANCE - 0.5)
    assert carousel.index == 0
    run(carousel, 1)
    assert carousel.index == 1


def test_after_the_last_page_it_slides_on_to_the_first(carousel):
    carousel.go_to(4)
    run(carousel, 1)
    carousel.handle_event(key(pygame.K_RIGHT))
    run(carousel, Carousel.SLIDE_TIME / 2)
    assert carousel.index == 0
    assert carousel.position > 4   # moving forward, not rewinding through every page
    run(carousel, 1)
    assert carousel.position == 0


def test_touching_it_pauses_the_automatic_advance(carousel):
    carousel.handle_event(key(pygame.K_RIGHT))
    run(carousel, Carousel.IDLE_RESUME - 1)
    assert carousel.index == 1
    assert carousel.auto_progress() == 0


def test_a_long_drag_changes_page_and_a_short_one_does_not(carousel):
    def drag(dx):
        start = carousel.rect.center
        carousel.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=start))
        end = (start[0] + dx, start[1])
        carousel.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=end, rel=(dx, 0), buttons=(1, 0, 0)))
        carousel.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=end))

    drag(-30)
    assert carousel.index == 0
    drag(-200)   # dragging left shows the next page
    assert carousel.index == 1
    run(carousel, 1)
    drag(200)
    assert carousel.index == 0


def test_the_arriving_page_restarts_its_demo(carousel):
    carousel.go_to(2)
    assert carousel.pages[2].restarts == 1
