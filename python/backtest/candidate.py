"""Candidate representation + validation + trading-day allocation mapping.

A candidate is a joint choice of stock subset and annual allocation/recalibration
schedule.  The optimizer may search both the number of annual allocation events
and their trading-session positions.  Shannon drift checks still run daily; an
allocation event means ERC/risk targets are recalibrated, not that trading is
otherwise disabled between those events.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

MIN_SYMBOLS = 5
MAX_SYMBOLS = 10

# Kept only for backwards compatibility with old imports/reports.  New candidate
# validation does NOT require exactly four events.
NUM_ALLOCATIONS = 4
MIN_ALLOCATIONS = 1
MAX_ALLOCATIONS = 6

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


def _feasible_max_allocations(max_day: int, min_gap: int) -> int:
    """Maximum cyclically separated events that fit in one trading year."""
    if max_day < 1:
        return 0
    if min_gap <= 0:
        return MAX_ALLOCATIONS
    # One event is always feasible; for >=2 events every circular gap must obey
    # min_gap, so n * min_gap <= max_day.
    return max(1, max_day // min_gap)


def validate_candidate(
    candidate: Candidate,
    universe: set[str],
    max_allocation_day: int = DEFAULT_MAX_ALLOCATION_DAY,
    min_gap: int = DEFAULT_MIN_GAP,
    portfolio_size: int | None = None,
    min_allocations: int = MIN_ALLOCATIONS,
    max_allocations: int = MAX_ALLOCATIONS,
) -> list[str]:
    """Return a list of constraint violations (empty = valid)."""
    errors: list[str] = []
    syms = candidate.symbols
    if portfolio_size is not None:
        if not (MIN_SYMBOLS <= portfolio_size <= MAX_SYMBOLS):
            errors.append(f"portfolio_size {portfolio_size} outside {MIN_SYMBOLS}..{MAX_SYMBOLS}")
        if len(syms) != portfolio_size:
            errors.append(f"expected exactly {portfolio_size} symbols, got {len(syms)}")
    elif not (MIN_SYMBOLS <= len(syms) <= MAX_SYMBOLS):
        errors.append(f"symbol count {len(syms)} outside {MIN_SYMBOLS}..{MAX_SYMBOLS}")
    if len(set(syms)) != len(syms):
        errors.append("duplicate symbols")
    bad = [s for s in syms if s not in universe]
    if bad:
        errors.append(f"symbols not in universe: {bad}")

    min_allocations = max(1, int(min_allocations))
    max_allocations = max(min_allocations, int(max_allocations))
    feasible_max = min(max_allocations, _feasible_max_allocations(max_allocation_day, min_gap))

    days = candidate.allocation_days
    if not (min_allocations <= len(days) <= feasible_max):
        errors.append(
            f"allocation count {len(days)} outside feasible {min_allocations}..{feasible_max}"
        )
    if any(not isinstance(d, int) or d < 1 for d in days):
        errors.append("allocation days must be integers >= 1")
    if any(d > max_allocation_day for d in days):
        errors.append(f"allocation days exceed max {max_allocation_day}")
    if list(days) != sorted(days):
        errors.append("allocation days not ordered")
    if len(set(days)) != len(days):
        errors.append("duplicate allocation days")
    if len(days) >= 2 and any(b - a < min_gap for a, b in zip(days, days[1:])):
        errors.append(f"minimum gap {min_gap} between allocation days violated")
    if len(days) >= 2 and max_allocation_day + days[0] - days[-1] < min_gap:
        errors.append(
            f"cyclic minimum gap {min_gap} violated (year-end to next year's T1: "
            f"{max_allocation_day}+{days[0]}-{days[-1]} = "
            f"{max_allocation_day + days[0] - days[-1]} < {min_gap})"
        )
    return errors


def assert_valid_candidate(
    candidate,
    universe,
    max_allocation_day=252,
    min_gap=40,
    portfolio_size: int | None = None,
    min_allocations: int = MIN_ALLOCATIONS,
    max_allocations: int = MAX_ALLOCATIONS,
) -> None:
    errors = validate_candidate(
        candidate,
        universe,
        max_allocation_day,
        min_gap,
        portfolio_size,
        min_allocations,
        max_allocations,
    )
    if errors:
        raise ValueError(f"Invalid candidate {candidate}: " + "; ".join(errors))


def resolve_allocation_dates(
    candidate: Candidate,
    all_dates,
    max_allocation_day: int = DEFAULT_MAX_ALLOCATION_DAY,
) -> tuple[list, list[dict]]:
    """Map allocation-day positions to actual market dates per calendar year.

    Partial calendar years at the beginning/end of a dataset may not contain a
    requested trading-session index. Such an event is skipped instead of being
    clamped to the year's last available date. Clamping created artificial
    allocations near research/holdout boundaries and could distort timing tests.
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
            if idx >= len(days):
                mapping.append(
                    {
                        "year": int(year),
                        "requested_index": int(ti),
                        "resolved_date": None,
                        "clamped": False,
                        "skipped": True,
                        "reason": "partial_year_missing_session",
                    }
                )
                continue
            resolved = days[idx]
            dates_out.append(resolved)
            mapping.append(
                {
                    "year": int(year),
                    "requested_index": int(ti),
                    "resolved_date": str(resolved.date()),
                    "clamped": False,
                    "skipped": False,
                }
            )
    dates_out.sort()
    return dates_out, mapping


def schedule_for_window(candidate: Candidate, all_dates) -> list:
    dates, _ = resolve_allocation_dates(candidate, all_dates)
    return dates


def random_allocation_days(
    rng: random.Random,
    min_gap: int,
    max_day: int,
    allocation_count: int | None = None,
    min_allocations: int = MIN_ALLOCATIONS,
    max_allocations: int = MAX_ALLOCATIONS,
) -> list[int]:
    """Generate a valid cyclic annual allocation schedule.

    The event count itself is part of the genome when ``allocation_count`` is
    omitted.  For n>=2 the circular gaps are constructed directly so rejection
    sampling is unnecessary even near the feasibility boundary (e.g. 6 events
    with a 40-session gap in a ~242-session year).
    """
    if max_day < 1:
        raise ValueError("max_day must be >= 1")

    min_allocations = max(1, int(min_allocations))
    max_allocations = max(min_allocations, int(max_allocations))
    feasible_max = min(max_allocations, _feasible_max_allocations(max_day, min_gap))
    if feasible_max < min_allocations:
        raise ValueError(
            f"no allocation schedule fits: feasible max {feasible_max} < requested min {min_allocations}"
        )

    if allocation_count is None:
        n = rng.randint(min_allocations, feasible_max)
    else:
        n = int(allocation_count)
        if not (min_allocations <= n <= feasible_max):
            raise ValueError(
                f"allocation_count {n} outside feasible {min_allocations}..{feasible_max}"
            )

    if n == 1:
        return [rng.randint(1, max_day)]

    slack = max_day - n * min_gap
    extras = [0] * n
    for _ in range(slack):
        extras[rng.randrange(n)] += 1
    gaps = [min_gap + x for x in extras]

    start = rng.randint(1, max_day)
    positions = [start]
    current = start
    for gap in gaps[:-1]:
        current = ((current - 1 + gap) % max_day) + 1
        positions.append(current)
    return sorted(positions)


def random_candidate(
    rng: random.Random,
    universe: list[str],
    min_gap: int,
    max_day: int,
    fixed_symbols: list[str] | None = None,
    portfolio_size: int | None = None,
    min_allocations: int = MIN_ALLOCATIONS,
    max_allocations: int = MAX_ALLOCATIONS,
) -> Candidate:
    """Random candidate; symbols and allocation frequency/timing may be searched."""
    if fixed_symbols is not None:
        symbols = tuple(sorted(fixed_symbols))
    else:
        if portfolio_size is not None:
            if not (MIN_SYMBOLS <= portfolio_size <= min(MAX_SYMBOLS, len(universe))):
                raise ValueError(
                    f"portfolio_size must be {MIN_SYMBOLS}..{min(MAX_SYMBOLS, len(universe))}, got {portfolio_size}"
                )
            n = portfolio_size
        else:
            n = rng.randint(MIN_SYMBOLS, min(MAX_SYMBOLS, len(universe)))
        symbols = tuple(sorted(rng.sample(universe, n)))
    days = tuple(
        random_allocation_days(
            rng,
            min_gap,
            max_day,
            min_allocations=min_allocations,
            max_allocations=max_allocations,
        )
    )
    return Candidate(symbols, days)


def repair_allocation_days(
    days,
    min_gap: int,
    max_day: int,
    min_allocations: int = MIN_ALLOCATIONS,
    max_allocations: int = MAX_ALLOCATIONS,
) -> tuple[int, ...] | None:
    """Sort + enforce minimum/cyclic gap for a variable-length schedule."""
    raw = [max(1, min(max_day, int(d))) for d in days]
    if len(set(raw)) != len(raw):
        return None
    ds = sorted(raw)
    n = len(ds)
    feasible_max = min(max_allocations, _feasible_max_allocations(max_day, min_gap))
    if not (max(1, min_allocations) <= n <= feasible_max):
        return None
    if n == 1:
        return (ds[0],)

    out: list[int] = []
    prev = None
    for d in ds:
        if prev is not None and d < prev + min_gap:
            d = prev + min_gap
        if d > max_day:
            return None
        out.append(d)
        prev = d

    if any(b - a < min_gap for a, b in zip(out, out[1:])):
        return None

    shortfall = min_gap - (max_day + out[0] - out[-1])
    if shortfall > 0:
        # Try moving the first point forward without breaking its next gap.
        new_first = out[0] + shortfall
        if new_first + min_gap <= out[1]:
            out[0] = new_first
        else:
            # Otherwise pull the final point backward.
            new_last = out[-1] - shortfall
            if new_last - out[-2] < min_gap:
                return None
            out[-1] = new_last

    if max_day + out[0] - out[-1] < min_gap:
        return None
    return tuple(out)