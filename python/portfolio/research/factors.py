"""T11 — Research factor computations (independent, PIT-safe).

Each factor is computed independently. There are NO weighted combinations and NO
composite scores in this milestone. Momentum/Reversal use historical OHLCV up to
the snapshot date only; Value and Quality use PIT-safe fundamentals.

Lookback conventions (exact trading sessions, documented):
    momentum_3m   = 63 sessions
    momentum_6m   = 126 sessions
    momentum_12m  = 252 sessions
    momentum_12_1 = P(t-21)/P(t-273) - 1  (12M momentum skipping the recent 1M)
    reversal_1m   = -(P(t)/P(t-21) - 1)   (1M return, reversed sign)
    liquidity     = 20D average daily traded value

NaN policy: insufficient history / missing values produce None (never zero).
"""
from __future__ import annotations

import pandas as pd

# Exact trading-session lookbacks.
MOMENTUM_3M = 63
MOMENTUM_6M = 126
MOMENTUM_12M = 252
REVERSAL_1M = 21
MOMENTUM_12_1_SKIP = 21
LIQUIDITY_WINDOW = 20
MIN_LIQUIDITY_OBS = 20


def _as_close(series) -> pd.Series:
    return pd.to_numeric(pd.Series(series), errors="coerce").dropna()


def momentum(close: pd.Series, lookback_sessions: int) -> float | None:
    """``P(t)/P(t-lookback) - 1`` over exact trading sessions.

    Requires at least ``lookback_sessions + 1`` observations. Missing -> None.
    """
    s = _as_close(close)
    if len(s) <= lookback_sessions:
        return None
    current = float(s.iloc[-1])
    past = float(s.iloc[-1 - lookback_sessions])
    if current <= 0 or past <= 0:
        return None
    return current / past - 1.0


def reversal_1m(close: pd.Series, lookback_sessions: int = REVERSAL_1M) -> float | None:
    """1M return with reversed sign: ``-(P(t)/P(t-21) - 1)``."""
    raw = momentum(close, lookback_sessions)
    return -raw if raw is not None else None


def momentum_12_1(
    close: pd.Series,
    lookback_12: int = MOMENTUM_12M,
    skip: int = MOMENTUM_12_1_SKIP,
) -> float | None:
    """12-1 momentum: ``P(t-skip)/P(t-skip-lookback_12) - 1``.

    Skips the most recent ``skip`` sessions so the short-term reversal month is
    not double-counted. Requires ``lookback_12 + skip + 1`` observations.
    """
    s = _as_close(close)
    if len(s) < lookback_12 + skip + 1:
        return None
    current = float(s.iloc[-1 - skip])
    past = float(s.iloc[-1 - skip - lookback_12])
    if current <= 0 or past <= 0:
        return None
    return current / past - 1.0


def liquidity(turnover: pd.Series, window: int = LIQUIDITY_WINDOW) -> float | None:
    """Mean daily traded value over the trailing ``window`` sessions (VND)."""
    s = pd.to_numeric(pd.Series(turnover), errors="coerce").dropna().tail(window)
    if len(s) < MIN_LIQUIDITY_OBS:
        return None
    return float(s.mean())


def price_factors_from_frame(frame: pd.DataFrame) -> dict:
    """Compute all OHLCV-based factors from a price frame sliced to <= snapshot.

    ``frame`` must have a datetime index and a ``close`` column (plus ``volume``
    for liquidity). Callers MUST pre-filter to ``<= snapshot_date``.
    """
    close = frame["close"]
    out = {
        "momentum_3m": momentum(close, MOMENTUM_3M),
        "momentum_6m": momentum(close, MOMENTUM_6M),
        "momentum_12m": momentum(close, MOMENTUM_12M),
        "reversal_1m": reversal_1m(close, REVERSAL_1M),
        "momentum_12_1": momentum_12_1(close),
    }
    if "volume" in frame.columns and "close" in frame.columns:
        turnover = frame["close"] * frame["volume"]
        out["liquidity"] = liquidity(turnover)
    else:
        out["liquidity"] = None
    return out


def value_factor(actual_mos_pct: float | None, required_mos_pct: float | None) -> float | None:
    """Value factor = valuation safety in percentage points.

    ``valuation_safety = actual_mos - required_mos``. Missing -> None. This is a
    PIT valuation measure and is NEVER mapped to alpha.
    """
    if actual_mos_pct is None or required_mos_pct is None:
        return None
    return float(actual_mos_pct) - float(required_mos_pct)