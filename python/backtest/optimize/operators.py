"""Symbol + allocation-frequency/timing mutation operators and crossover.

Joint mode may evolve both the stock subset and the annual ERC/risk
recalibration schedule.  The schedule genome is variable length: by default one
to six events per year.  Shannon drift checks remain daily between these events.
"""

from __future__ import annotations

import random

from ..candidate import (
    Candidate,
    MAX_ALLOCATIONS,
    MAX_SYMBOLS,
    MIN_ALLOCATIONS,
    MIN_SYMBOLS,
    random_allocation_days,
    repair_allocation_days,
)

__all__ = ["mutate", "crossover", "repair_candidate"]


def repair_candidate(
    symbols,
    allocation_days,
    universe,
    rng,
    min_gap: int,
    max_day: int,
    fixed_symbols: list[str] | None = None,
    portfolio_size: int | None = None,
    min_allocations: int = MIN_ALLOCATIONS,
    max_allocations: int = MAX_ALLOCATIONS,
) -> Candidate | None:
    """Repair symbol set + variable-length timing schedule, or return None."""
    if fixed_symbols is not None:
        syms = sorted(fixed_symbols)
    else:
        syms = sorted(set(symbols) & set(universe))
        min_n = portfolio_size if portfolio_size is not None else MIN_SYMBOLS
        max_n = portfolio_size if portfolio_size is not None else MAX_SYMBOLS
        while len(syms) < min_n:
            pool = [s for s in universe if s not in syms]
            if not pool:
                return None
            syms.append(rng.choice(pool))
        while len(syms) > max_n:
            syms.pop(rng.randrange(len(syms)))
        syms = sorted(syms)

    days = repair_allocation_days(
        allocation_days,
        min_gap,
        max_day,
        min_allocations=min_allocations,
        max_allocations=max_allocations,
    )
    if days is None:
        days = tuple(
            random_allocation_days(
                rng,
                min_gap,
                max_day,
                min_allocations=min_allocations,
                max_allocations=max_allocations,
            )
        )
    return Candidate(tuple(syms), days)


def _circular_distance(a: int, b: int, max_day: int) -> int:
    direct = abs(a - b)
    return min(direct, max_day - direct)


def mutate_allocation_days(
    days,
    rng: random.Random,
    min_gap: int,
    max_day: int,
    min_allocations: int = MIN_ALLOCATIONS,
    max_allocations: int = MAX_ALLOCATIONS,
):
    """Mutate event count and/or event positions, preserving cyclic spacing."""
    ds = list(days)

    feasible_max = min(max_allocations, max(1, max_day // max(1, min_gap)))
    min_allocations = max(1, min(min_allocations, feasible_max))

    # Frequency mutation is deliberately less common than date mutation.  It lets
    # the optimizer discover annual/semiannual/... schedules without turning the
    # search into an unconstrained high-frequency trading problem.
    if rng.random() < 0.22:
        can_add = len(ds) < feasible_max
        can_remove = len(ds) > min_allocations
        if can_add and (not can_remove or rng.random() < 0.55):
            eligible = [
                d
                for d in range(1, max_day + 1)
                if d not in ds
                and all(_circular_distance(d, x, max_day) >= min_gap for x in ds)
            ]
            if eligible:
                ds.append(rng.choice(eligible))
        elif can_remove:
            ds.pop(rng.randrange(len(ds)))

    if not ds:
        return None

    # Position mutation.  Larger moves are rare so local timing plateaus can be
    # explored while still allowing regime-scale jumps.
    n_shift = min(len(ds), rng.choice([1, 1, 1, 2, 2, 3]))
    for _ in range(n_shift):
        i = rng.randrange(len(ds))
        roll = rng.random()
        if roll < 0.6:
            delta = rng.randint(1, 5)
        elif roll < 0.9:
            delta = rng.randint(5, 20)
        else:
            delta = rng.randint(20, 60)
        ds[i] = max(1, min(max_day, ds[i] + delta * rng.choice([-1, 1])))

    return repair_allocation_days(
        ds,
        min_gap,
        max_day,
        min_allocations=min_allocations,
        max_allocations=max_allocations,
    )


def _add_symbol(syms, universe, rng):
    pool = [s for s in universe if s not in syms]
    if pool:
        syms = syms + [rng.choice(pool)]
    return syms


def _remove_symbol(syms, rng):
    if len(syms) > MIN_SYMBOLS:
        syms.pop(rng.randrange(len(syms)))
    return syms


def _replace_symbols(syms, universe, rng, k):
    for _ in range(k):
        pool = [s for s in universe if s not in syms]
        if not pool:
            break
        syms[rng.randrange(len(syms))] = rng.choice(pool)
    return syms


def mutate(
    candidate: Candidate,
    universe: list[str],
    rng: random.Random,
    min_gap: int,
    max_day: int,
    fixed_symbols: list[str] | None = None,
    portfolio_size: int | None = None,
    min_allocations: int = MIN_ALLOCATIONS,
    max_allocations: int = MAX_ALLOCATIONS,
) -> Candidate | None:
    """Apply symbol and/or allocation-schedule mutation, then repair."""
    syms = list(candidate.symbols)
    if fixed_symbols is None:
        op = rng.choice(["symbol", "symbol", "timing", "both"])
        if op in ("symbol", "both"):
            if portfolio_size is not None:
                k = 1 if rng.random() < 0.85 else min(3, max(1, portfolio_size // 3))
                syms = _replace_symbols(syms, universe, rng, k)
            else:
                roll = rng.random()
                if roll < 0.4 and len(syms) < MAX_SYMBOLS:
                    syms = _add_symbol(syms, universe, rng)
                elif roll < 0.6 and len(syms) > MIN_SYMBOLS:
                    syms = _remove_symbol(syms, rng)
                elif roll < 0.85:
                    syms = _replace_symbols(syms, universe, rng, 1)
                else:
                    syms = _replace_symbols(syms, universe, rng, rng.randint(2, min(3, len(syms))))
    else:
        op = "timing"

    days = candidate.allocation_days
    if op in ("timing", "both"):
        days = mutate_allocation_days(
            days,
            rng,
            min_gap,
            max_day,
            min_allocations=min_allocations,
            max_allocations=max_allocations,
        )
        if days is None:
            return None
    return repair_candidate(
        syms,
        days,
        universe,
        rng,
        min_gap,
        max_day,
        fixed_symbols,
        portfolio_size,
        min_allocations,
        max_allocations,
    )


def symbol_crossover(
    a: Candidate,
    b: Candidate,
    universe: list[str],
    rng: random.Random,
    portfolio_size: int | None = None,
) -> list[str]:
    """Combine symbol subsets while preserving an optional exact N."""
    if portfolio_size is not None:
        target_n = portfolio_size
    else:
        lo = min(len(a.symbols), len(b.symbols))
        hi = max(len(a.symbols), len(b.symbols))
        target_n = rng.randint(lo, hi)
    union = sorted(set(a.symbols) | set(b.symbols))
    if len(union) > target_n:
        return sorted(rng.sample(union, target_n))
    if len(union) < target_n:
        pool = [s for s in universe if s not in union]
        if len(pool) < target_n - len(union):
            return union
        return sorted(union + rng.sample(pool, target_n - len(union)))
    return union


def timing_crossover(
    a: Candidate,
    b: Candidate,
    rng: random.Random,
    min_gap: int,
    max_day: int,
    min_allocations: int = MIN_ALLOCATIONS,
    max_allocations: int = MAX_ALLOCATIONS,
):
    """Cross variable-length schedules and allow frequency inheritance."""
    lo = max(min_allocations, min(len(a.allocation_days), len(b.allocation_days)))
    hi = min(max_allocations, max(len(a.allocation_days), len(b.allocation_days)))
    target_n = rng.randint(lo, hi) if hi >= lo else min_allocations

    pool = sorted(set(a.allocation_days) | set(b.allocation_days))
    attempts = 0
    while attempts < 20 and len(pool) >= target_n:
        attempts += 1
        chosen = sorted(rng.sample(pool, target_n))
        repaired = repair_allocation_days(
            chosen,
            min_gap,
            max_day,
            min_allocations=min_allocations,
            max_allocations=max_allocations,
        )
        if repaired is not None:
            return repaired

    try:
        return tuple(
            random_allocation_days(
                rng,
                min_gap,
                max_day,
                allocation_count=target_n,
                min_allocations=min_allocations,
                max_allocations=max_allocations,
            )
        )
    except ValueError:
        return tuple(
            random_allocation_days(
                rng,
                min_gap,
                max_day,
                min_allocations=min_allocations,
                max_allocations=max_allocations,
            )
        )


def crossover(
    a: Candidate,
    b: Candidate,
    universe: list[str],
    rng: random.Random,
    min_gap: int,
    max_day: int,
    fixed_symbols: list[str] | None = None,
    portfolio_size: int | None = None,
    min_allocations: int = MIN_ALLOCATIONS,
    max_allocations: int = MAX_ALLOCATIONS,
) -> Candidate | None:
    if fixed_symbols is not None:
        syms = sorted(fixed_symbols)
    else:
        syms = symbol_crossover(a, b, universe, rng, portfolio_size)
    days = timing_crossover(
        a,
        b,
        rng,
        min_gap,
        max_day,
        min_allocations=min_allocations,
        max_allocations=max_allocations,
    )
    if days is None:
        return None
    return repair_candidate(
        syms,
        days,
        universe,
        rng,
        min_gap,
        max_day,
        fixed_symbols,
        portfolio_size,
        min_allocations,
        max_allocations,
    )
