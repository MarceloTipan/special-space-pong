"""Tests for the hand tracker, fed with synthetic camera frames."""

import numpy as np
import cv2
import pytest

from game.motion import HandTracker

W, H, FPS = 320, 240, 30


class Scene:
    """A fake webcam: textured background, sensor noise and moving blobs."""

    def __init__(self, seed=1):
        self.rng = np.random.default_rng(seed)
        texture = self.rng.integers(50, 120, (H, W, 3), dtype=np.uint8)
        self.background = cv2.GaussianBlur(texture, (15, 15), 0)

    def frame(self, hand_x, extra=None, brightness=0):
        image = self.background.astype(np.int16) + brightness
        img = np.clip(image, 0, 255).astype(np.uint8)
        cv2.ellipse(img, (int(hand_x), 160), (20, 26), 0, 0, 360, (130, 170, 220), -1)
        if extra is not None:   # a smaller distractor, e.g. a head nodding
            cv2.circle(img, (int(extra), 60), 14, (130, 170, 220), -1)
        noise = self.rng.normal(0, 3, img.shape)
        return np.clip(img + noise, 0, 255).astype(np.uint8)


def feed(tracker, scene, path, start=0, **kwargs):
    """Feed one frame per camera x in path; returns the hand_x after each."""
    out = []
    for i, x in enumerate(path):
        tracker.process(scene.frame(x, **kwargs), now=(start + i) / FPS)
        out.append(tracker.hand_x)
    return out


def sweep(a, b, frames):
    return [a + (b - a) * i / (frames - 1) for i in range(frames)]


def test_the_paddle_moves_like_a_mirror():
    # The hand moves to the camera's left: in a mirror, that is the player's right
    tracker, scene = HandTracker(mirror=True, camera_range=(0.0, 1.0)), Scene()
    out = feed(tracker, scene, [240] * 5 + sweep(240, 80, 15) + [80] * 15)
    moving = [x for x in out if x is not None]
    assert moving[-1] > moving[0]
    assert moving[-1] == pytest.approx(1 - 80 / W, abs=0.04)


def test_without_mirror_it_follows_the_image():
    tracker, scene = HandTracker(mirror=False, camera_range=(0.0, 1.0)), Scene()
    out = feed(tracker, scene, [240] * 5 + sweep(240, 80, 15) + [80] * 15)
    moving = [x for x in out if x is not None]
    assert moving[-1] < moving[0]
    assert moving[-1] == pytest.approx(80 / W, abs=0.04)


def test_a_resting_hand_keeps_the_paddle_still():
    tracker, scene = HandTracker(), Scene()
    feed(tracker, scene, [240] * 5 + sweep(240, 160, 10))
    settled = feed(tracker, scene, [160] * 45, start=15)[15:]
    assert max(settled) - min(settled) < 0.01


def test_the_paddle_stops_where_the_hand_stops():
    tracker, scene = HandTracker(camera_range=(0.0, 1.0)), Scene()
    feed(tracker, scene, [240] * 5 + sweep(240, 120, 12) + [120] * 30)
    assert tracker.hand_x == pytest.approx(1 - 120 / W, abs=0.03)


def test_a_brief_movement_elsewhere_does_not_steal_the_paddle():
    tracker, scene = HandTracker(camera_range=(0.0, 1.0)), Scene()
    feed(tracker, scene, [240] * 5 + sweep(240, 200, 6))
    nod = [60 + 15 * np.sin(i / 3) for i in range(12)]   # a "head" moving far away
    for i, head in enumerate(nod):
        tracker.process(scene.frame(200, extra=head), now=(11 + i) / FPS)
    assert tracker.hand_x == pytest.approx(1 - 200 / W, abs=0.05)


def test_a_change_of_light_is_ignored():
    tracker, scene = HandTracker(), Scene()
    feed(tracker, scene, [240] * 5 + sweep(240, 160, 10) + [160] * 20)
    before = tracker.hand_x
    for i in range(5):
        tracker.process(scene.frame(160, brightness=60), now=(35 + i) / FPS)
    assert tracker.hand_x == before


def test_calibration_maps_the_swept_span_to_the_whole_field():
    tracker = HandTracker()
    tracker.image_x = 0.5
    tracker.set_calibration(0.25, 0.75, hand_height=0.6)
    assert tracker.hand_x == pytest.approx(0.5)
    tracker.set_calibration(0.5, 1.0, hand_height=0.6)
    assert tracker.hand_x == 0.0


def test_after_calibration_motion_away_from_the_hand_is_ignored():
    # Calibrated at the hand's height: a head moving above it doesn't count,
    # however long it moves
    tracker = HandTracker(camera_range=(0.0, 1.0), hand_height=160 / H)
    scene = Scene()
    feed(tracker, scene, [240] * 5 + sweep(240, 200, 6))
    for i in range(90):
        tracker.process(scene.frame(200, extra=60 + 25 * np.sin(i / 3)), now=(11 + i) / FPS)
    assert tracker.hand_x == pytest.approx(1 - 200 / W, abs=0.05)


def test_while_calibrating_the_biggest_movement_is_the_hand():
    tracker, scene = HandTracker(camera_range=(0.0, 1.0)), Scene()
    # Something small was being tracked...
    for i in range(10):
        tracker.process(scene.frame(240, extra=60 + 15 * np.sin(i / 2)), now=i / FPS)
    # ...but the sweeping hand is picked up as soon as calibration starts
    tracker.calibrating = True
    feed(tracker, scene, sweep(240, 120, 10) + [120] * 10, start=10)
    assert tracker.hand_x == pytest.approx(1 - 120 / W, abs=0.05)
