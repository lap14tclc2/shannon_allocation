"""Random joint-search baseline: random symbols + random four allocation times."""

from __future__ import annotations

import random

from ..candidate import Candidate, random_candidate
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
):
    """Generate unique random candidates, evaluate each, store all results.

    `evaluate(candidate) -> metrics dict`. Returns list of dicts:
    {candidate, metrics, objectives}. With `fixed_symbols`, only timing varies.
    """
    seen = set()
    results = []
    attempts = 0
    while len(results) < n_candidates and attempts < n_candidates * 200 + 1000:
        attempts += 1
        c = random_candidate(rng, universe, min_gap, max_day, fixed_symbols)
        if c.key() in seen:
            continue
        seen.add(c.key())
        m = evaluate(c)
        if m is None or m.get("error"):
            continue
        results.append({"candidate": c, "metrics": m, "objectives": objectives(m)})
        if progress and len(results) % 200 == 0:
            print(f"  random search: {len(results)}/{n_candidates} evaluated", flush=True)
    return results