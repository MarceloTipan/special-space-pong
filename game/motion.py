"""Hand tracking for the paddle, with classic computer vision (no ML).

HandTracker turns webcam frames into the horizontal position of the hand;
MotionController runs it on a background thread so the game never waits
for the camera, and only reads the latest result.

How a frame is processed:
1. Motion: the difference with a frame from a moment ago marks what moved
   (comparing a few frames back keeps slow movements visible). The
   threshold rises with the camera's noise.
2. Short memory: motion fades out over a fraction of a second instead of
   vanishing from one frame to the next.
3. Blob choice: the moving regions are separated, and the hand is the one
   closest to where the hand was, grouped with its neighbors (a moving hand
   shows up as its two edges). Movement outside the height where the hand
   plays (learned in calibration) is ignored: a nodding head can't steal
   the paddle.
4. Hysteresis: a hand at rest needs a clear movement to start moving, so
   tremors and noise can't make a still paddle shake.
5. Position: center of the group, weighted toward the newest motion,
   smoothed by a 1€ filter (steady when slow, responsive when fast) with a
   tiny dead zone, and nudged ahead to make up for the camera's latency.
6. Calibration range: the part of the image the player's hand sweeps
   covers the whole field.
"""

import math
import sys
import threading
import time
from collections import deque

import cv2
import numpy as np

from utils.filters import OneEuroFilter


class HandTracker:
    """Finds the horizontal position of a moving hand in camera frames.

    Pure image processing, with no camera or thread: it can be fed any
    frames (tests feed synthetic ones).

    Attributes:
        raw_x: Last detected position in the image (0-1), unfiltered.
        image_x: Filtered position in the image (0-1).
        hand_x: Filtered position mapped to the field through the
            calibration range (0 left, 1 right). None until the first detection.
        blob: Last detected hand region (x, y, w, h), in 0-1 image units.
        preview: Small RGB image of what the camera sees, for the pause screen.
        calibrating: While True, the biggest movement in the image is taken
            as the hand (the player is sweeping it on purpose).
    """

    # --- Motion detection ---
    PROCESS_WIDTH = 160      #: frames are downscaled to this width (faster, less noise)
    DIFF_THRESHOLD = 12      #: min brightness change (0-255) that counts as motion...
    NOISE_SCALE = 6.0        #: ...raised to this many times the frame's typical change (noise)
    BASELINE = 3             #: frames back to compare with: slow motion still shows up
    MEMORY_TIME = 0.2        #: seconds it takes motion to fade to a third
    ACTIVE_LEVEL = 0.3       #: motion memory above this level is part of a blob
    MAX_MOTION = 0.35        #: above this share the whole image changed (light, camera bump)

    # --- Which blob is the hand ---
    MIN_BLOB = 0.004         #: smallest blob that keeps a moving hand tracked (image share)
    MIN_BLOB_START = 0.012   #: ...and the bigger motion needed to start moving from rest
    REST_SPEED = 0.1         #: below this speed (image widths/s) the hand counts as at rest
    REST_TIMEOUT = 0.15      #: with no motion for this long (s), the hand is at rest
    RIVAL_SHARE = 0.25       #: blobs this big relative to the largest compete by distance
    GROUP_X = 0.12           #: blobs this close (image share) to the hand's are part of it...
    GROUP_Y = 0.2            #: ...horizontally and vertically
    HEIGHT_BAND = 0.2        #: after calibration, motion farther than this from the hand's height is ignored
    JUMP_LIMIT = 0.25        #: a blob this far (image share) from the last detection...
    REACQUIRE_TIME = 0.6     #: ...takes over only after moving this long (s)

    # --- Smoothing ---
    MIN_CUTOFF = 1.0         #: 1€ filter: smoothing at rest (Hz; lower = steadier)
    BETA = 20.0              #: 1€ filter: how quickly smoothing drops with speed
    DEAD_ZONE = 0.005        #: changes smaller than this (image share) are ignored
    LEAD_TIME = 0.04         #: extrapolate the motion this far ahead (s), to hide latency

    DEFAULT_RANGE = (0.15, 0.85)   #: image span mapped to the field until calibrated

    def __init__(self, mirror=True, camera_range=None, hand_height=None):
        """Create a tracker.

        Args:
            mirror: Flip the image like a mirror, so moving the hand to your
                right moves the paddle right. Turn it off for cameras whose
                driver already mirrors the image.
            camera_range: (left, right) span of the image, 0-1, that the hand
                sweeps; it is mapped to the whole field. None for the default.
            hand_height: Height in the image (0 top, 1 bottom) where the hand
                plays, from calibration. None to accept motion at any height.
        """
        self.mirror = mirror
        self.range = tuple(camera_range) if camera_range else self.DEFAULT_RANGE
        self.hand_height = hand_height
        self.calibrating = False
        self.raw_x = None
        self.image_x = None
        self.hand_x = None
        self.blob = None
        self.preview = None
        self._filter = OneEuroFilter(self.MIN_CUTOFF, self.BETA)
        self._history = deque(maxlen=self.BASELINE)   # recent frames to compare against
        self._memory = None
        self._time = None
        self._last_seen = None   # time of the last detection
        self._last_y = None      # height of the last detection (0-1)
        self._far_since = None   # since when a blob far from the hand keeps moving

    def set_calibration(self, left, right, hand_height):
        """Map the image span [left, right] (0-1) to the whole field, and
        only follow motion around hand_height (0-1)."""
        self.range = (left, right)
        self.hand_height = hand_height
        self._update_hand_x()

    # ------------------------------------------------------------------
    # Per frame
    # ------------------------------------------------------------------
    def process(self, frame, now=None):
        """Update the tracked position from one camera frame (BGR)."""
        now = time.monotonic() if now is None else now
        gray = self._prepare(frame)
        # RGB copy for the pause-screen preview (converted here, off the game thread)
        self.preview = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        if not self._history:
            self._history.append(gray)
            self._time = now
            self._memory = np.zeros(gray.shape, np.float32)
            return

        dt = max(1e-3, now - self._time)
        self._time = now
        diff = cv2.absdiff(gray, self._history[0])
        self._history.append(gray)

        # Most of the image is static, so the median change is the sensor noise:
        # a noisy camera (dim room) gets a higher threshold
        threshold = max(self.DIFF_THRESHOLD, self.NOISE_SCALE * float(np.median(diff)))
        _, moving = cv2.threshold(diff, threshold, 1, cv2.THRESH_BINARY)
        if moving.mean() > self.MAX_MOTION:
            self._memory[:] = 0
            return   # the whole image changed: ignore this frame
        # Motion memory: fades exponentially, refreshed wherever something moves
        self._memory *= math.exp(-dt / self.MEMORY_TIME)
        np.maximum(self._memory, moving.astype(np.float32), out=self._memory)

        detection = self._find_hand(now)
        if detection is None:
            # Nothing moving: the paddle stays. After a moment the hand is at
            # rest: drop the speed, so the lead stops pushing the paddle on
            if (self._last_seen is not None and self._filter.speed
                    and now - self._last_seen > self.REST_TIMEOUT):
                self._filter.speed = 0.0
                self._update_hand_x()
            return
        self.raw_x = detection
        self._last_seen = now

        filtered = self._filter(detection, now)
        if self.image_x is None:
            self.image_x = filtered
        elif abs(filtered - self.image_x) > self.DEAD_ZONE:
            # Follow, but stay DEAD_ZONE behind: tiny tremors never move it
            self.image_x = filtered - math.copysign(self.DEAD_ZONE, filtered - self.image_x)
        self._update_hand_x()

    def _prepare(self, frame):
        """Downscale, mirror, grayscale and blur a camera frame."""
        h, w = frame.shape[:2]
        size = (self.PROCESS_WIDTH, max(1, round(h * self.PROCESS_WIDTH / w)))
        small = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
        if self.mirror:
            small = cv2.flip(small, 1)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        return cv2.GaussianBlur(gray, (5, 5), 0)

    def _find_hand(self, now):
        """Position (0-1) of the moving region that is the hand, or None."""
        active = (self._memory > self.ACTIVE_LEVEL).astype(np.uint8)
        count, labels, stats, centroids = cv2.connectedComponentsWithStats(active, connectivity=8)
        height, width = active.shape

        # Hysteresis: a hand at rest needs a clear movement to start moving,
        # so tremors and sensor noise can't make a still paddle shake
        at_rest = abs(self._filter.speed) < self.REST_SPEED
        min_area = (self.MIN_BLOB_START if at_rest else self.MIN_BLOB) * width * height
        blobs = [i for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] >= min_area]
        if self.hand_height is not None and not self.calibrating:
            blobs = [i for i in blobs
                     if abs(centroids[i][1] / height - self.hand_height) <= self.HEIGHT_BAND]
        if not blobs:
            return None

        best = self._pick_blob(blobs, stats, centroids, width, height, now)
        if best is None:
            return None
        return self._group_center(best, blobs, labels, stats, centroids, width, height)

    def _pick_blob(self, blobs, stats, centroids, width, height, now):
        """The blob that is the hand: while calibrating (or before the hand
        has been seen) the biggest movement; then the one closest to the hand."""
        largest = max(stats[i, cv2.CC_STAT_AREA] for i in blobs)
        rivals = [i for i in blobs if stats[i, cv2.CC_STAT_AREA] >= largest * self.RIVAL_SHARE]
        if self.calibrating or self.raw_x is None:
            return max(rivals, key=lambda i: stats[i, cv2.CC_STAT_AREA])

        def distance(i):
            cx, cy = centroids[i]
            return math.hypot(cx / width - self.raw_x, cy / height - self._last_y)

        best = min(rivals, key=distance)
        # A hand moves continuously, so motion appearing far from the last
        # detection is probably something else: it only takes over if it
        # keeps going (the hand left the image and came back elsewhere)
        if distance(best) > self.JUMP_LIMIT:
            if self._far_since is None:
                self._far_since = now
            if now - self._far_since < self.REACQUIRE_TIME:
                return None
        self._far_since = None
        return best

    def _group_center(self, best, blobs, labels, stats, centroids, width, height):
        """Center of the hand's blob and its neighbors (a hand of even color
        shows up as two blobs, its leading and trailing edges)."""
        bx, by = centroids[best]
        self._last_y = by / height
        group = [i for i in blobs
                 if abs(centroids[i][0] - bx) <= self.GROUP_X * width
                 and abs(centroids[i][1] - by) <= self.GROUP_Y * height]
        x0 = min(stats[i, cv2.CC_STAT_LEFT] for i in group)
        y0 = min(stats[i, cv2.CC_STAT_TOP] for i in group)
        x1 = max(stats[i, cv2.CC_STAT_LEFT] + stats[i, cv2.CC_STAT_WIDTH] for i in group)
        y1 = max(stats[i, cv2.CC_STAT_TOP] + stats[i, cv2.CC_STAT_HEIGHT] for i in group)
        self.blob = (x0 / width, y0 / height, (x1 - x0) / width, (y1 - y0) / height)

        # Weighted by the memory: the newest motion (where the hand is now)
        # weighs more than the fading trail behind it
        weights = np.where(np.isin(labels, group), self._memory, 0)
        column_weights = weights.sum(axis=0)
        total = column_weights.sum()
        if total <= 0:
            return None
        columns = np.arange(width, dtype=np.float32) + 0.5
        return float((column_weights * columns).sum() / total) / width

    def _update_hand_x(self):
        if self.image_x is None:
            return
        x = self.image_x + self._filter.speed * self.LEAD_TIME
        left, right = self.range
        self.hand_x = min(1.0, max(0.0, (x - left) / max(1e-6, right - left)))


class MotionController:
    """Runs a HandTracker on the webcam in a background thread.

    The game reads hand_x (and the preview attributes) whenever it wants;
    it never waits for a frame.
    """

    CAPTURE_SIZE = (640, 480)   #: requested camera resolution (only a hint to the driver)

    def __init__(self, camera_index=0, mirror=True, camera_range=None, hand_height=None):
        """Open the camera and start tracking in the background.

        Args:
            camera_index: Which camera to open.
            mirror, camera_range, hand_height: See HandTracker.
        """
        self.tracker = HandTracker(mirror, camera_range, hand_height)
        self._running = False
        self._thread = None

        # DirectShow opens much faster than the default backend on Windows
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        self.webcam = cv2.VideoCapture(camera_index, backend)
        # Hints the driver may ignore: a small queue means fresher frames (less lag)
        self.webcam.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.webcam.set(cv2.CAP_PROP_FRAME_WIDTH, self.CAPTURE_SIZE[0])
        self.webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, self.CAPTURE_SIZE[1])
        ok, frame = self.webcam.read()
        self.available = bool(ok)
        if not self.available:
            self.webcam.release()
            print("[MotionController] No camera detected")
            return

        self.tracker.process(frame)
        self._running = True
        self._thread = threading.Thread(target=self._run, name="camera", daemon=True)
        self._thread.start()

    # The game reads the tracker's results through the controller
    hand_x = property(lambda self: self.tracker.hand_x)
    image_x = property(lambda self: self.tracker.image_x)
    raw_x = property(lambda self: self.tracker.raw_x)
    blob = property(lambda self: self.tracker.blob)
    preview = property(lambda self: self.tracker.preview)
    range = property(lambda self: self.tracker.range)

    @property
    def calibrating(self):
        return self.tracker.calibrating

    @calibrating.setter
    def calibrating(self, value):
        self.tracker.calibrating = value

    def set_calibration(self, left, right, hand_height):
        self.tracker.set_calibration(left, right, hand_height)

    def _run(self):
        """Camera thread: process frames as they arrive."""
        while self._running:
            ok, frame = self.webcam.read()
            if ok:
                self.tracker.process(frame)
            else:
                time.sleep(0.01)   # avoid a busy loop if the camera hiccups

    def release(self):
        """Stop the tracking thread and release the camera (safe to call twice)."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self.available:
            self.webcam.release()
            self.available = False
