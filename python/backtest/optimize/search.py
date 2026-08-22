"""Random joint-search baseline: symbols + four allocation times."""

from __future__ import annotations

import random

from ..candidate import random_candidate
from .evaluate import objectives


def random_search(
    n_candidates: int,
    universe: list[str],
    rng: random.Random,
    min_gap: int,
    max_day: int,
    evaluate,
    progress: bool = True,
    fixed_symbols: list[str] | None = None,
    portfolio_size: int | None = None,
    evaluate_many=None,
):
    """Generate unique random candidates and evaluate them.

    ``evaluate_many`` is optional and preserves the existing result semantics while
    allowing CPU-parallel batch evaluation. Invalid candidates are replenished in
    later batches until ``n_candidates`` valid results are collected.
    """
    seen = set()
    results = []
    attempts = 0
    max_attempts = n_candidates * 200 + 1000

    while len(results) < n_candidates and attempts < max_attempts:
        need = n_candidates - len(results)
        batch = []
        target_batch = max(1, need)
        while len(batch) < target_batch and attempts < max_attempts:
            attempts += 1
            c = random_candidate(
                rng, universe, min_gap, max_day, fixed_symbols, portfolio_size
            )
            if c.key() in seen:
                continue
            seen.add(c.key())
            batch.append(c)

        if not batch:
            break

        metrics = evaluate_many(batch) if evaluate_many else [evaluate(c) for c in batch]
        for c, m in zip(batch, metrics):
            if m is None or m.get("error"):
                continue
            results.append({"candidate": c, "metrics": m, "objectives": objectives(m)})
            if len(results) >= n_candidates:
                break

        if progress and len(results) and len(results) % 50 == 0:
            print(f"  random search: {len(results)}/{n_candidates} evaluated", flush=True)

    return results
