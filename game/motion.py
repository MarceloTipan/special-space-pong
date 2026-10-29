"""Hand tracking for the paddle, with classic computer vision (no ML).

A background thread reads the webcam, finds where in the image things are
moving (the difference between consecutive frames) and publishes the
horizontal position of that movement, from 0 (left) to 1 (right). The game
reads the latest value and never waits for the camera.

Tracking the hand's position, instead of the direction it moves in, is what
makes it playable: the paddle goes where the hand is, so small corrections
stay small and it can never drift or move against the hand.
"""

import sys
import threading
import time

import cv2


class MotionController:
    """Tracks the horizontal position of the moving hand in the webcam image."""

    PROCESS_WIDTH = 160     #: frames are downscaled to this width (faster, less noise)
    DIFF_THRESHOLD = 25     #: brightness change (0-255) that counts as motion
    MIN_MOTION = 0.003      #: min share of moving pixels to count as a hand
    MAX_MOTION = 0.35       #: above this the whole image changed (light, camera bump)
    REACH = 0.7             #: central share of the camera width mapped to the whole field
    SMOOTHING = 0.6         #: how far each detection moves the tracked position (0-1)

    def __init__(self, camera_index=0, mirror=True):
        """Open the camera and start tracking in the background.

        Args:
            camera_index: Which camera to open.
            mirror: Flip the image like a mirror, so moving the hand to your
                right moves the paddle right. Turn it off for cameras whose
                driver already mirrors the image.
        """
        self.mirror = mirror
        self.hand_x = None    # 0-1 across the field; None until the first detection
        self.raw_x = None     # last detection in image coordinates (0-1), for the preview
        self.preview = None   # latest small RGB frame (H x W x 3), for the pause screen
        self._prev_gray = None
        self._running = False
        self._thread = None

        # DirectShow opens much faster than the default backend on Windows
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        self.webcam = cv2.VideoCapture(camera_index, backend)
        ok, frame = self.webcam.read()
        self.available = bool(ok)
        if not self.available:
            self.webcam.release()
            print("[MotionController] No camera detected")
            return

        self._prev_gray = self._prepare(frame)
        self._running = True
        self._thread = threading.Thread(target=self._run, name="camera", daemon=True)
        self._thread.start()

    def _run(self):
        """Camera thread: process frames as they arrive."""
        while self._running:
            ok, frame = self.webcam.read()
            if ok:
                self._process(frame)
            else:
                time.sleep(0.01)   # avoid a busy loop if the camera hiccups

    def _prepare(self, frame):
        """Downscale, mirror, grayscale and blur a camera frame."""
        h, w = frame.shape[:2]
        size = (self.PROCESS_WIDTH, max(1, round(h * self.PROCESS_WIDTH / w)))
        small = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
        if self.mirror:
            small = cv2.flip(small, 1)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        return cv2.GaussianBlur(gray, (5, 5), 0)

    def _process(self, frame):
        """Update the tracked hand position from one camera frame."""
        gray = self._prepare(frame)
        diff = cv2.absdiff(gray, self._prev_gray)
        self._prev_gray = gray
        # RGB copy for the pause-screen preview (converted here, off the game thread)
        self.preview = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)

        _, mask = cv2.threshold(diff, self.DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)
        mask = cv2.dilate(mask, None, iterations=2)
        moments = cv2.moments(mask, binaryImage=True)
        moving = moments["m00"] / mask.size
        if not self.MIN_MOTION <= moving <= self.MAX_MOTION:
            return   # nothing moving, or the whole image changed: keep the last position

        # Center of the moving region, 0 (left) to 1 (right)
        x = moments["m10"] / moments["m00"] / mask.shape[1]
        self.raw_x = x

        # Map the central REACH of the image to the whole field, so the player
        # doesn't have to stretch to the very edge of the camera view
        margin = (1 - self.REACH) / 2
        target = min(1.0, max(0.0, (x - margin) / self.REACH))
        if self.hand_x is None:
            self.hand_x = target
        else:
            self.hand_x += (target - self.hand_x) * self.SMOOTHING

    def release(self):
        """Stop the tracking thread and release the camera (safe to call twice)."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self.available:
            self.webcam.release()
            self.available = False