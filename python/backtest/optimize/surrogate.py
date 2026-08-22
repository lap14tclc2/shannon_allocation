"""Lightweight surrogate model to prioritise expensive evaluations.

Extra Trees / Random Forest / Gradient Boosting (sklearn) predict candidate
performance from a cheap feature encoding. Surrogate predictions are NEVER used
as final results — finalists always receive real backtests.
"""

from __future__ import annotations

import numpy as np

from ..candidate import Candidate


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
        onehot = np.zeros(len(self.universe))
        for s in candidate.symbols:
            if s in self.sym_index:
                onehot[self.sym_index[s]] = 1.0
        timing = np.array(candidate.allocation_days, dtype=float) / max_day
        n = np.array([len(candidate.symbols) / 10.0])
        return np.concatenate([onehot, timing, n])

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