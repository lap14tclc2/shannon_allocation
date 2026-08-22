"""Candidate representation + validation + trading-day allocation mapping.

A candidate is a JOINT choice of stock subset and four annual allocation times:

    Candidate(symbols, allocation_days)

`allocation_days` are trading-day positions (1..max_allocation_day) mapped to
actual market dates separately for every calendar year, so the optimizer searches
symbols and allocation timing together, never independently.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import pandas as pd

MIN_SYMBOLS = 5
MAX_SYMBOLS = 10
NUM_ALLOCATIONS = 4
DEFAULT_MAX_ALLOCATION_DAY = 252
DEFAULT_MIN_GAP = 40


@dataclass(frozen=True)
class Candidate:
    symbols: tuple[str, ...]
    allocation_days: tuple[int, ...]

    def key(self) -> str:
        return f"{'|'.join(self.symbols)}::{','.join(str(d) for d in self.allocation_days)}"

    def __str__(self) -> str:
        return f"[{','.join(self.symbols)} | {list(self.allocation_days)}]"


# --------------------------------------------------------------------------- validation
def validate_candidate(
    candidate: Candidate,
    universe: set[str],
    max_allocation_day: int = DEFAULT_MAX_ALLOCATION_DAY,
    min_gap: int = DEFAULT_MIN_GAP,
) -> list[str]:
    """Return a list of constraint violations (empty = valid)."""
    errors: list[str] = []
    syms = candidate.symbols
    if not (MIN_SYMBOLS <= len(syms) <= MAX_SYMBOLS):
        errors.append(f"symbol count {len(syms)} outside {MIN_SYMBOLS}..{MAX_SYMBOLS}")
    if len(set(syms)) != len(syms):
        errors.append("duplicate symbols")
    bad = [s for s in syms if s not in universe]
    if bad:
        errors.append(f"symbols not in universe: {bad}")

    days = candidate.allocation_days
    if len(days) != NUM_ALLOCATIONS:
        errors.append(f"expected exactly {NUM_ALLOCATIONS} allocation times, got {len(days)}")
    if any(not isinstance(d, int) or d < 1 for d in days):
        errors.append("allocation days must be integers >= 1")
    if any(d > max_allocation_day for d in days):
        errors.append(f"allocation days exceed max {max_allocation_day}")
    if list(days) != sorted(days):
        errors.append("allocation days not ordered")
    if len(days) >= 2 and any(b - a < min_gap for a, b in zip(days, days[1:])):
        errors.append(f"minimum gap {min_gap} between allocation days violated")
    # Cyclic constraint: allocation repeats every year, so the gap from the last
    # allocation of year Y to the first allocation of year Y+1 must also be >= min_gap.
    #   G_4 = YEAR_LENGTH + T1 - T4   (YEAR_LENGTH == max_allocation_day)
    if len(days) >= 2 and max_allocation_day + days[0] - days[-1] < min_gap:
        errors.append(
            f"cyclic minimum gap {min_gap} violated (year-end to next year's T1: "
            f"{max_allocation_day}+{days[0]}-{days[-1]} = {max_allocation_day + days[0] - days[-1]} < {min_gap})"
        )
    return errors


def assert_valid_candidate(candidate, universe, max_allocation_day=252, min_gap=40) -> None:
    errors = validate_candidate(candidate, universe, max_allocation_day, min_gap)
    if errors:
        raise ValueError(f"Invalid candidate {candidate}: " + "; ".join(errors))


# --------------------------------------------------------------------------- trading-day mapping
def resolve_allocation_dates(
    candidate: Candidate,
    all_dates,
    max_allocation_day: int = DEFAULT_MAX_ALLOCATION_DAY,
) -> tuple[list, list[dict]]:
    """Map candidate allocation_days to actual market dates per calendar year.

    Returns (sorted dates, mapping) where mapping records each requested
    trading-day index and the resolved market date (clamped to the last trading
    day of a year when the year has fewer trading days than requested).
    """
    by_year: dict[int, list] = {}
    for d in all_dates:
        by_year.setdefault(d.year, []).append(d)

    dates_out: list = []
    mapping: list[dict] = []
    for year in sorted(by_year):
        days = by_year[year]
        for ti in candidate.allocation_days:
            idx = ti - 1
            resolved = days[idx] if idx < len(days) else days[-1]
            dates_out.append(resolved)
            mapping.append(
                {
                    "year": int(year),
                    "requested_index": int(ti),
                    "resolved_date": str(resolved.date()),
                    "clamped": idx >= len(days),
                }
            )
    dates_out.sort()
    return dates_out, mapping


def schedule_for_window(candidate: Candidate, all_dates) -> list:
    """Allocation dates restricted to the calendar years present in `all_dates`."""
    dates, _ = resolve_allocation_dates(candidate, all_dates)
    return dates


# --------------------------------------------------------------------------- generators / repair
def random_allocation_days(rng: random.Random, min_gap: int, max_day: int) -> list[int]:
    """Four valid, ordered allocation days with minimum gap, including the cyclic gap.

    Models the year as a ring of length `max_day` split into five gaps:
      g1 = T1 - 1                     (before the first allocation)
      g2 = T2 - T1, g3 = T3 - T2, g4 = T4 - T3
      g5 = max_day - T4               (after the last allocation)
    The cyclic gap (T4 -> next year's T1) equals g5 + g1 + 1, so the constraint
    g1 + g5 >= min_gap - 1 keeps every annual cycle valid.
    """
    if max_day < 4 * min_gap:
        raise ValueError(f"max_day {max_day} < 4*min_gap {4*min_gap}: no valid schedule exists")
    g = [0, min_gap, min_gap, min_gap, min_gap - 1]  # g1, g2, g3, g4, g5
    remaining = (max_day - 1) - (4 * min_gap - 1)
    # distribute `remaining` days uniformly across the five gaps (stars-and-bars)
    cuts = sorted(rng.sample(range(remaining + 4), 4))
    add = [cuts[0]]
    for i in range(1, 4):
        add.append(cuts[i] - cuts[i - 1] - 1)
    add.append(remaining + 3 - cuts[-1])
    g = [a + b for a, b in zip(g, add)]

    t1 = g[0] + 1
    days = [t1]
    for gap in g[1:4]:
        days.append(days[-1] + gap)
    return days


def random_candidate(
    rng: random.Random,
    universe: list[str],
    min_gap: int,
    max_day: int,
    fixed_symbols: list[str] | None = None,
) -> Candidate:
    """Random candidate. When `fixed_symbols` is given, only timing is randomised."""
    if fixed_symbols is not None:
        symbols = tuple(sorted(fixed_symbols))
    else:
        n = rng.randint(MIN_SYMBOLS, min(MAX_SYMBOLS, len(universe)))
        symbols = tuple(sorted(rng.sample(universe, n)))
    days = tuple(random_allocation_days(rng, min_gap, max_day))
    return Candidate(symbols, days)


def repair_allocation_days(days, min_gap: int, max_day: int) -> tuple[int, ...] | None:
    """Sort + enforce minimum gap (including cyclic). Returns valid days or None."""
    ds = sorted(set(int(d) for d in days))
    out: list[int] = []
    prev = 0
    for d in ds:
        if d < prev + min_gap:
            d = prev + min_gap
        if d > max_day:
            return None
        out.append(d)
        prev = d
    if len(out) != NUM_ALLOCATIONS or len(set(out)) != len(out):
        return None
    if any(b - a < min_gap for a, b in zip(out, out[1:])):
        return None
    # Cyclic gap: YEAR_LENGTH + T1 - T4 >= min_gap.
    shortfall = min_gap - (max_day + out[0] - out[-1])
    if shortfall > 0:
        # try lifting the first allocation; if that collides, sink the last one.
        new_first = out[0] + shortfall
        if new_first + min_gap <= out[1]:
            out[0] = new_first
        else:
            new_last = out[-1] - shortfall
            if new_last - out[-2] < min_gap:
                return None
            out[-1] = new_last
    return tuple(out)