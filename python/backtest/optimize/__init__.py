"""Risk-aware portfolio + allocation-time optimizer."""

from ..candidate import Candidate
from .run import run_optimizer, OptimizerConfig
from .nsga2 import nsga2
from .search import random_search
from .walkforward import (
    make_windows,
    make_train_val_windows,
    split_research_holdout,
    evaluate_robust,
    halving,
)

__all__ = [
    "Candidate",
    "run_optimizer",
    "OptimizerConfig",
    "nsga2",
    "random_search",
    "make_windows",
    "make_train_val_windows",
    "split_research_holdout",
    "evaluate_robust",
    "halving",
]
