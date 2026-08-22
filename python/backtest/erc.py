"""Equal Risk Contribution weight solver.

Direct Python port of src/services/erc.service.ts from the reference
portfolio_allocation implementation so results stay comparable:

- daily log returns
- sample covariance (N-1) annualized by annualization_factor
- cyclic-coordinate / multiplier style ERC solver, max 1000 iterations
- convergence tolerance 1e-7, final validation 1e-5
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .config import BacktestParams


class ERCError(Exception):
    pass


@dataclass
class ERCResult:
    weights: np.ndarray
    risk_contributions: np.ndarray
    portfolio_risk: float
    portfolio_variance: float
    erc_error: float
    observations: int


def log_returns_from_window(window: np.ndarray) -> np.ndarray:
    """window: (obs, n_symbols) aligned close prices -> log returns (obs-1, n_symbols)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.log(window[1:] / window[:-1])
    if out.shape[0] < 1:
        raise ERCError("Not enough aligned observations to compute returns.")
    return out


def annualized_covariance(returns: np.ndarray, annualization_factor: int) -> np.ndarray:
    if returns.shape[0] < 2:
        raise ERCError("Covariance requires at least 2 observations.")
    matrix = np.cov(returns, rowvar=False, ddof=1)
    matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)
    return matrix * annualization_factor


def solve_erc(returns: np.ndarray, params: BacktestParams) -> ERCResult:
    """Solve ERC weights from aligned log returns, returning full diagnostics."""
    n = returns.shape[1]
    if n < 1:
        raise ERCError("ERC requires at least one symbol.")
    matrix = annualized_covariance(returns, params.annualization_factor)

    # Symmetry validation mirroring the reference implementation.
    tolerance = 1e-10
    for i in range(n):
        for j in range(i + 1, n):
            if abs(matrix[i, j] - matrix[j, i]) > tolerance:
                raise ERCError(f"Covariance matrix not symmetric: cov[{i}][{j}] vs cov[{j}][{i}].")

    target = 1.0 / n
    weights = np.full(n, target)
    max_iterations = 1000

    def metrics(w: np.ndarray):
        marginal = matrix @ w
        variance = float(w @ marginal)
        risk = math.sqrt(max(variance, 0.0))
        if risk == 0:
            crc = np.zeros(n)
        else:
            crc = (w * marginal) / risk
        return marginal, variance, risk, crc, (crc / risk if risk else np.zeros(n))

    for _ in range(max_iterations):
        marginal, variance, risk, crc, rc = metrics(weights)
        if risk > 0 and np.max(np.abs(rc - target)) < 1e-7:
            break
        if risk <= 0 or np.any(rc <= 0):
            raise ERCError("ERC solver failed.")
        divisor = (weights * marginal) / risk
        if np.any(np.abs(divisor) < 1e-300):
            raise ERCError("ERC solver failed.")
        weights = weights * np.power((variance * target) / divisor, 0.25)
        weights = weights / weights.sum()

    _, variance, risk, crc, rc = metrics(weights)
    erc_error = float(np.max(np.abs(rc - target))) if risk > 0 else float("inf")
    if erc_error >= 1e-5:
        raise ERCError("ERC validation failed.")
    return ERCResult(
        weights=weights.astype(float),
        risk_contributions=rc.astype(float),
        portfolio_risk=risk,
        portfolio_variance=variance,
        erc_error=erc_error,
        observations=returns.shape[0] + 1,  # aligned price observations (matches reference TS system)
    )


def solve_erc_weights(returns: np.ndarray, params: BacktestParams) -> np.ndarray:
    """Convenience wrapper returning only the weights vector."""
    return solve_erc(returns, params).weights