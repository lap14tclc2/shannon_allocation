from __future__ import annotations

import random

import numpy as np

from backtest.candidate import Candidate, random_allocation_days, validate_candidate
from backtest.optimize.surrogate import Surrogate


UNIVERSE = ["A", "B", "C", "D", "E", "F", "G", "H"]
SYMBOLS = ("A", "B", "C", "D", "E")


def test_all_allocation_counts_1_to_6_are_generatable_and_valid():
    rng = random.Random(123)
    for n in range(1, 7):
        for _ in range(20):
            days = random_allocation_days(rng, 40, 252, allocation_count=n)
            c = Candidate(SYMBOLS, tuple(days))
            assert len(days) == n
            assert validate_candidate(c, set(UNIVERSE), 252, 40) == []


def test_surrogate_encoding_has_fixed_width_for_variable_schedules():
    surrogate = Surrogate(UNIVERSE, seed=7)
    one = Candidate(SYMBOLS, (120,))
    three = Candidate(SYMBOLS, (30, 115, 200))
    six = Candidate(SYMBOLS, (1, 41, 81, 121, 161, 201))

    encoded = [surrogate.encode(c) for c in (one, three, six)]
    assert encoded[0].shape == encoded[1].shape == encoded[2].shape
    # one-hot universe + six timing slots + symbol-count + allocation-count
    assert encoded[0].shape[0] == len(UNIVERSE) + 8


def test_surrogate_can_fit_mixed_allocation_counts():
    rng = random.Random(99)
    candidates = []
    targets = []
    for i in range(30):
        n = 1 + (i % 6)
        days = random_allocation_days(rng, 40, 252, allocation_count=n)
        candidates.append(Candidate(SYMBOLS, tuple(days)))
        targets.append(float(n) + sum(days) / 1000.0)

    surrogate = Surrogate(UNIVERSE, seed=3)
    surrogate.fit(candidates, targets)
    pred = surrogate.predict(candidates[:5])
    assert pred.shape == (5,)
    assert np.all(np.isfinite(pred))
