"""Risk-aware dynamic-alpha/static portfolio optimizer."""

from ..candidate import Candidate
from .run import run_optimizer as _run_optimizer, OptimizerConfig
from .budget import adapt_optimizer_budget
from .nsga2 import nsga2
from .search import random_search
from .walkforward import (
    make_windows,
    make_train_val_windows,
    split_research_holdout,
    evaluate_robust,
    halving,
)


def run_optimizer(params, opt, progress=True):
    """Run the product optimizer.

    Product ``joint`` mode now means dynamic alpha membership: the machine ranks
    the configured market universe at each recalibration, then ERC allocates the
    selected names. This removes the static-combination bottleneck while keeping
    ``timing`` mode available for a user-owned fixed combination.
    """
    if opt.mode == "joint":
        from .alpha_run import run_alpha_optimizer

        params.dynamic_alpha_enabled = True
        params.dynamic_alpha_portfolio_size = int(opt.portfolio_size or 7)
        return run_alpha_optimizer(params, opt, progress=progress)

    resolved = adapt_optimizer_budget(params, opt)
    if resolved:
        before = resolved["before"]
        after = resolved["resolved"]
        print(
            "Adaptive search budget: "
            f"{resolved['preset']} on {resolved['universe'].upper()} "
            f"random {before[2]}->{after[2]}, pop {before[0]}->{after[0]}, "
            f"gen {before[1]}->{after[1]}, validation {before[4]}->{after[4]}",
            flush=True,
        )
    return _run_optimizer(params, opt, progress=progress)


__all__ = [
    "Candidate",
    "run_optimizer",
    "OptimizerConfig",
    "adapt_optimizer_budget",
    "nsga2",
    "random_search",
    "make_windows",
    "make_train_val_windows",
    "split_research_holdout",
    "evaluate_robust",
    "halving",
]
