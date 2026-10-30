"""Tests for the 1€ filter."""

import random
import statistics

import pytest

from utils.filters import OneEuroFilter

FPS = 30


def run(filt, values):
    return [filt(x, i / FPS) for i, x in enumerate(values)]


def test_first_value_passes_through():
    assert OneEuroFilter(1.0, 0.0)(0.42, 0.0) == 0.42


def test_a_constant_signal_stays_constant():
    assert run(OneEuroFilter(1.0, 5.0), [0.3] * 30)[-1] == pytest.approx(0.3)


def test_noise_at_rest_is_mostly_removed():
    rng = random.Random(1)
    noisy = [0.5 + rng.gauss(0, 0.01) for _ in range(300)]
    out = run(OneEuroFilter(min_cutoff=1.0, beta=0.0), noisy)
    assert statistics.pstdev(out[30:]) < statistics.pstdev(noisy) / 3


def test_speed_lowers_the_lag():
    # A quick sweep from 0 to 1 in a third of a second
    sweep = [min(1.0, i / 10) for i in range(30)]
    steady = run(OneEuroFilter(min_cutoff=1.0, beta=0.0), sweep)
    adaptive = run(OneEuroFilter(min_cutoff=1.0, beta=20.0), sweep)
    assert abs(1 - adaptive[12]) < abs(1 - steady[12]) / 2
