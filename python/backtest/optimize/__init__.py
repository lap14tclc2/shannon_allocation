"""Risk-aware portfolio + allocation-time optimizer."""

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
    """Run optimizer after resolving standard preset budgets for small universes."""
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
