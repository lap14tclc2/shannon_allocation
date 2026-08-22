"""Multi-process candidate evaluation for expensive optimizer stages.

The optimizer server runs on Windows as well as Linux, so this module keeps all
worker entry points at module scope (required by multiprocessing spawn). Price
data and immutable config are sent to each worker once via the initializer; each
candidate job then sends only a small Candidate/window payload.

If process creation fails, callers can fall back to the existing serial path.
"""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor

from .evaluate import evaluate_candidate
from .walkforward import evaluate_robust

_CTX = {}


def _init_worker(prices, params, dates, cfg: str, max_day: int):
    global _CTX
    _CTX = {
        "prices": prices,
        "params": params,
        "dates": dates,
        "cfg": cfg,
        "max_day": max_day,
    }


def _candidate_job(job):
    candidate, start, end = job
    return evaluate_candidate(
        candidate,
        _CTX["prices"],
        _CTX["params"],
        _CTX["dates"],
        (start, end),
        cache=None,
        cfg=_CTX["cfg"],
        max_allocation_day=_CTX["max_day"],
    )


def _robust_job(job):
    candidate, windows, lamb, require_full_coverage, max_drawdown_abs_pct = job

    def eval_fn(cc, w):
        start, end = w
        return evaluate_candidate(
            cc,
            _CTX["prices"],
            _CTX["params"],
            _CTX["dates"],
            (start, end),
            cache=None,
            cfg=_CTX["cfg"],
            max_allocation_day=_CTX["max_day"],
        )

    window_dicts = [{"val": w} for w in windows]

    def wrapped(cc, w):
        return eval_fn(cc, w["val"])

    return evaluate_robust(
        candidate,
        wrapped,
        window_dicts,
        lamb=lamb,
        min_windows=len(window_dicts) if require_full_coverage else None,
        max_drawdown_abs_pct=max_drawdown_abs_pct,
    )


def auto_worker_count(requested: int = 0) -> int:
    """Resolve a conservative process count suitable for desktop use."""
    if requested and requested > 0:
        return max(1, int(requested))
    cpu = os.cpu_count() or 2
    # Leave at least one logical CPU for the UI/server and cap RAM duplication.
    return max(1, min(6, cpu - 1))


class ParallelEvaluator:
    def __init__(self, prices, params, dates, cfg: str, max_day: int, workers: int = 0):
        self.workers = auto_worker_count(workers)
        self._pool = None
        self._serial_args = (prices, params, dates, cfg, max_day)
        if self.workers > 1:
            self._pool = ProcessPoolExecutor(
                max_workers=self.workers,
                initializer=_init_worker,
                initargs=self._serial_args,
            )
        else:
            _init_worker(*self._serial_args)

    @property
    def enabled(self) -> bool:
        return self._pool is not None

    def close(self):
        if self._pool is not None:
            self._pool.shutdown(wait=True, cancel_futures=False)
            self._pool = None

    def evaluate_many(self, candidates, start: str, end: str):
        candidates = list(candidates)
        if not candidates:
            return []
        if self._pool is None:
            _init_worker(*self._serial_args)
            return [_candidate_job((c, start, end)) for c in candidates]
        return list(self._pool.map(_candidate_job, [(c, start, end) for c in candidates], chunksize=1))

    def robust_many(
        self,
        candidates,
        windows,
        lamb: float,
        require_full_coverage: bool,
        max_drawdown_abs_pct: float | None,
    ):
        candidates = list(candidates)
        jobs = [
            (c, windows, lamb, require_full_coverage, max_drawdown_abs_pct)
            for c in candidates
        ]
        if self._pool is None:
            _init_worker(*self._serial_args)
            return [_robust_job(j) for j in jobs]
        return list(self._pool.map(_robust_job, jobs, chunksize=1))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
