"""Deterministic search-budget adaptation for standard UI presets.

The expensive portfolio simulation/validation math is unchanged.  We only reduce
how many candidates are explored when a standard preset designed for the full
~90-name universe is used on a much smaller universe such as VN30 or VN50.

Advanced/custom budgets are never modified: adaptation only triggers when every
budget field exactly matches one of the shipped Fast/Balanced/Thorough presets.
The resolved values are written back to ``OptimizerConfig`` before the experiment
starts, so exported optimizer_config.json records the actual work performed.
"""

from __future__ import annotations


# Signature order:
# population, generations, random, preselect, robust_pool,
# surrogate_pool, surrogate_proposals, early_stop
_STANDARD_PRESETS = {
    "fast": (40, 18, 150, 40, 100, 3000, 25, 10),
    "balanced": (60, 30, 250, 45, 180, 5000, 40, 15),
    "thorough": (90, 45, 500, 60, 300, 10000, 80, 20),
}

# Smaller universes do not need the same number of expensive real backtests.
# Finalists still go through the identical walk-forward robustness and untouched
# holdout methodology.
_RESOLVED = {
    "vn30": {
        "fast": (24, 10, 50, 30, 35, 1000, 10, 6),
        "balanced": (30, 12, 75, 30, 50, 1500, 12, 8),
        "thorough": (40, 18, 120, 30, 80, 2500, 20, 10),
    },
    "vn50": {
        "fast": (30, 12, 80, 40, 60, 1500, 12, 7),
        "balanced": (40, 18, 120, 45, 90, 2500, 20, 10),
        "thorough": (55, 28, 220, 50, 140, 5000, 35, 14),
    },
}


def _signature(opt) -> tuple[int, ...]:
    return (
        int(opt.population_size),
        int(opt.generations),
        int(opt.n_random),
        int(opt.preselect_top or 0),
        int(opt.robust_pool_size),
        int(opt.surrogate_pool_size),
        int(opt.surrogate_proposals),
        int(opt.early_stop_generations or 0),
    )


def _preset_name(opt) -> str | None:
    sig = _signature(opt)
    for name, expected in _STANDARD_PRESETS.items():
        if sig == expected:
            return name
    return None


def adapt_optimizer_budget(params, opt) -> dict | None:
    """Mutate ``opt`` to the smaller standard budget when safe.

    Returns a small audit dictionary when adaptation occurred, otherwise ``None``.
    Custom advanced settings are preserved exactly.
    """
    universe = str(getattr(params, "universe", "all") or "all").lower()
    preset = _preset_name(opt)
    if preset is None or universe not in _RESOLVED:
        return None

    before = _signature(opt)
    resolved = _RESOLVED[universe][preset]
    (
        opt.population_size,
        opt.generations,
        opt.n_random,
        preselect,
        opt.robust_pool_size,
        opt.surrogate_pool_size,
        opt.surrogate_proposals,
        early_stop,
    ) = resolved
    opt.preselect_top = preselect if preselect > 0 else None
    opt.early_stop_generations = early_stop if early_stop > 0 else None

    return {
        "preset": preset,
        "universe": universe,
        "before": before,
        "resolved": resolved,
    }
