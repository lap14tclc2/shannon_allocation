"""Lightweight surrogate model to prioritise expensive evaluations.

Extra Trees / Random Forest / Gradient Boosting predict candidate performance
from a fixed-width cheap feature encoding. Variable allocation schedules use six
padded timing slots plus an explicit allocation-count feature.
"""

from __future__ import annotations

import numpy as np

from ..candidate import Candidate, MAX_ALLOCATIONS


class Surrogate:
    def __init__(self, universe: list[str], model_kind: str = "et", seed: int = 42):
        self.universe = sorted(universe)
        self.sym_index = {s: i for i, s in enumerate(self.universe)}
        self.seed = seed
        self.model = None
        from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor, GradientBoostingRegressor

        if model_kind == "rf":
            self.model = RandomForestRegressor(n_estimators=150, random_state=seed, n_jobs=-1)
        elif model_kind == "gb":
            self.model = GradientBoostingRegressor(n_estimators=150, random_state=seed)
        else:
            self.model = ExtraTreesRegressor(n_estimators=200, random_state=seed, n_jobs=-1)

    def encode(self, candidate: Candidate, max_day: int = 252) -> np.ndarray:
        onehot = np.zeros(len(self.universe), dtype=float)
        for s in candidate.symbols:
            if s in self.sym_index:
                onehot[self.sym_index[s]] = 1.0

        timing = np.zeros(MAX_ALLOCATIONS, dtype=float)
        for i, day in enumerate(candidate.allocation_days[:MAX_ALLOCATIONS]):
            timing[i] = float(day) / max(1.0, float(max_day))

        meta = np.array(
            [
                len(candidate.symbols) / 10.0,
                len(candidate.allocation_days) / float(MAX_ALLOCATIONS),
            ],
            dtype=float,
        )
        return np.concatenate([onehot, timing, meta])

    def fit(self, candidates: list[Candidate], targets: list[float]):
        X = np.vstack([self.encode(c) for c in candidates])
        y = np.asarray(targets, dtype=float)
        self.model.fit(X, y)

    def predict(self, candidates: list[Candidate]) -> np.ndarray:
        if not candidates:
            return np.array([])
        X = np.vstack([self.encode(c) for c in candidates])
        return self.model.predict(X)

    def rank(self, candidates: list[Candidate]):
        """Return candidates sorted by predicted performance (best first)."""
        if not candidates:
            return []
        preds = self.predict(candidates)
        order = np.argsort(-preds)
        return [candidates[i] for i in order]
