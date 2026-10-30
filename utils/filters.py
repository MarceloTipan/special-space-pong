"""Signal filters for noisy input (the hand position from the camera)."""

import math


class OneEuroFilter:
    """Adaptive low-pass filter for noisy, real-time positions.

    A plain low-pass filter forces a trade-off: heavy smoothing kills jitter
    but adds lag; light smoothing is responsive but shaky. The 1€ filter
    (Casiez, Roussel and Vogel, CHI 2012) adapts the smoothing to the speed:
    when the signal barely moves it smooths a lot (a hand held still stays
    still), and as it moves faster it smooths less (a quick sweep isn't
    delayed).

    Args:
        min_cutoff: Cutoff frequency (Hz) at rest. Lower = less jitter.
        beta: How fast the cutoff grows with speed. Higher = less lag.
        d_cutoff: Cutoff frequency (Hz) used to smooth the speed estimate.
    """

    def __init__(self, min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.reset()

    def reset(self):
        """Forget the history: the next value passes through unchanged."""
        self.value = None
        self.speed = 0.0
        self._time = None

    @staticmethod
    def _alpha(cutoff, dt):
        """Smoothing factor of a first-order low-pass at this cutoff and step."""
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x, now):
        """Filter a new sample.

        Args:
            x: The new noisy value.
            now: Its timestamp, in seconds.

        Returns:
            The filtered value.
        """
        if self.value is None:
            self.value, self._time = x, now
            return x
        dt = max(1e-6, now - self._time)
        self._time = now

        speed = (x - self.value) / dt
        self.speed += self._alpha(self.d_cutoff, dt) * (speed - self.speed)
        cutoff = self.min_cutoff + self.beta * abs(self.speed)
        self.value += self._alpha(cutoff, dt) * (x - self.value)
        return self.value
