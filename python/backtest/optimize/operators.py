"""Symbol + timing mutation operators and crossover, with repair.

When ``portfolio_size`` is provided, joint-mode genomes keep exactly that number
of symbols.  Mutations therefore replace names instead of randomly adding or
removing them, which shrinks the search space and matches the user's requested
portfolio size.
"""

from __future__ import annotations

import random

from ..candidate import (
    Candidate,
    MAX_SYMBOLS,
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
) -> Candidate | None:
    """Repair symbol set + timing to satisfy all constraints, or return None."""
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

    days = repair_allocation_days(allocation_days, min_gap, max_day)
    if days is None:
        days = tuple(random_allocation_days(rng, min_gap, max_day))
    return Candidate(tuple(syms), days)


def mutate_allocation_days(days, rng: random.Random, min_gap: int, max_day: int, large_chance=0.15):
    """Shift 1..3 allocation days; returns repaired days or None."""
    ds = list(days)
    n_shift = rng.choice([1, 1, 1, 2, 2, 3])
    for _ in range(n_shift):
        i = rng.randrange(len(ds))
        roll = rng.random()
        if roll < 0.6:
            delta = rng.randint(1, 5)
        elif roll < 0.9:
            delta = rng.randint(5, 20)
        else:
            delta = rng.randint(20, 60)
        delta *= rng.choice([-1, 1])
        ds[i] = max(1, min(max_day, ds[i] + delta))
    return repair_allocation_days(ds, min_gap, max_day)


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
) -> Candidate | None:
    """Apply a symbol and/or timing mutation, then repair."""
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
        days = mutate_allocation_days(days, rng, min_gap, max_day)
        if days is None:
            return None
    return repair_candidate(
        syms, days, universe, rng, min_gap, max_day, fixed_symbols, portfolio_size
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


def timing_crossover(a: Candidate, b: Candidate, rng: random.Random, min_gap: int, max_day: int):
    child = [a.allocation_days[i] if rng.random() < 0.5 else b.allocation_days[i] for i in range(4)]
    return repair_allocation_days(child, min_gap, max_day)


def crossover(
    a: Candidate,
    b: Candidate,
    universe: list[str],
    rng: random.Random,
    min_gap: int,
    max_day: int,
    fixed_symbols: list[str] | None = None,
    portfolio_size: int | None = None,
) -> Candidate | None:
    if fixed_symbols is not None:
        syms = sorted(fixed_symbols)
    else:
        syms = symbol_crossover(a, b, universe, rng, portfolio_size)
    days = timing_crossover(a, b, rng, min_gap, max_day)
    if days is None:
        return None
    return repair_candidate(
        syms, days, universe, rng, min_gap, max_day, fixed_symbols, portfolio_size
    )
