"""T12 — Forward benchmark-relative outcomes.

Future labels are computed ONLY after factor snapshots are frozen. They never
feed factor computation (no same-period leakage). Horizons are exact trading
sessions: 21 / 63 / 126 / 252.

Convention (documented):
    forward_stock_return_H   = P_stock(t+H) / P_stock(t) - 1
        where t is the stock's own session at/after the snapshot date and t+H
        is the H-th subsequent session in the SAME stock series.
    forward_vnindex_return_H = P_index(date(t+H)) / P_index(date(t)) - 1
        using the last available index close on or before each date
        (trading-date alignment / missing-day policy).
    forward_excess_return_H  = stock_return_H - vnindex_return_H

Unresolved horizons (insufficient future sessions) stay None. Outcomes are
never forward-filled.
"""
from __future__ import annotations

from typing import Callable

import pandas as pd

HORIZONS = (21, 63, 126, 252)
DEFAULT_HORIZONS = HORIZONS


def _position_return(close_series: pd.Series, as_of_date, horizon_sessions: int) -> float | None:
    """Return over ``horizon_sessions`` trading sessions in the series itself.

    Base is the LAST close on or before ``as_of_date`` (PIT-safe: the price known
    at the snapshot time). ``t+h`` is the ``horizon_sessions``-th subsequent
    session in the same series.
    """
    s = pd.to_numeric(pd.Series(close_series), errors="coerce").dropna().sort_index()
    if s.empty:
        return None
    idx = s.index
    base_idx = idx.asof(pd.Timestamp(as_of_date))
    if pd.isna(base_idx):
        return None  # as_of precedes all data
    base_pos = idx.get_loc(base_idx)
    base = float(s.iloc[base_pos])
    end_pos = base_pos + int(horizon_sessions)
    if end_pos >= len(s):
        return None  # unresolved horizon
    end_value = float(s.iloc[end_pos])
    if base <= 0:
        return None
    return end_value / base - 1.0


def _benchmark_between(benchmark_close: pd.Series, start_date, end_date) -> float | None:
    """Index return between two dates using last-available-before closes."""
    s = pd.to_numeric(pd.Series(benchmark_close), errors="coerce").dropna().sort_index()
    start_idx = s.index.asof(pd.Timestamp(start_date))
    end_idx = s.index.asof(pd.Timestamp(end_date))
    if pd.isna(start_idx) or pd.isna(end_idx):
        return None
    start_v = float(s.loc[start_idx])
    end_v = float(s.loc[end_idx])
    if start_v <= 0:
        return None
    return end_v / start_v - 1.0


def forward_stock_return(
    price_frame: pd.DataFrame,
    as_of_date: str,
    horizon_sessions: int,
) -> float | None:
    if price_frame is None or price_frame.empty or "close" not in price_frame.columns:
        return None
    return _position_return(price_frame["close"], as_of_date, horizon_sessions)


def forward_benchmark_return(
    benchmark_frame: pd.DataFrame,
    price_frame: pd.DataFrame,
    as_of_date: str,
    horizon_sessions: int,
) -> float | None:
    """Index return aligned to the stock's base and end session dates."""
    if price_frame is None or price_frame.empty or "close" not in price_frame.columns:
        return None
    if benchmark_frame is None or benchmark_frame.empty or "close" not in benchmark_frame.columns:
        return None
    s = pd.to_numeric(pd.Series(price_frame["close"]), errors="coerce").dropna().sort_index()
    idx = s.index
    pos = idx.searchsorted(pd.Timestamp(as_of_date), side="left")
    if pos >= len(idx):
        return None
    end_pos = pos + int(horizon_sessions)
    if end_pos >= len(idx):
        return None
    base_date = idx[pos]
    end_date = idx[end_pos]
    return _benchmark_between(benchmark_frame["close"], base_date, end_date)


def forward_excess_return(
    price_frame: pd.DataFrame,
    benchmark_frame: pd.DataFrame,
    as_of_date: str,
    horizon_sessions: int,
) -> tuple[float | None, float | None, float | None]:
    """Return (stock_return, benchmark_return, excess_return) for a horizon.

    If either leg is missing, the excess is missing (never assumed zero).
    """
    stock = forward_stock_return(price_frame, as_of_date, horizon_sessions)
    benchmark = forward_benchmark_return(benchmark_frame, price_frame, as_of_date, horizon_sessions)
    if stock is None or benchmark is None:
        return stock, benchmark, None
    return stock, benchmark, stock - benchmark


def build_outcomes(
    price_provider: Callable[[str], pd.DataFrame],
    benchmark_frame: pd.DataFrame,
    snapshots: list[dict],
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
) -> list[dict]:
    """Attach forward outcomes to every factor snapshot row.

    ``price_provider(symbol)`` returns the full price frame for a symbol (may
    include future dates; only dates >= snapshot_date are used for labels).
    """
    rows: list[dict] = []
    for snap in snapshots:
        symbol = str(snap["symbol"]).upper()
        snapshot_date = snap["snapshot_date"]
        price_frame = price_provider(symbol)
        out = dict(snap)
        for h in horizons:
            stock, bench, excess = forward_excess_return(
                price_frame, benchmark_frame, snapshot_date, h,
            )
            out[f"forward_stock_return_{h}"] = stock
            out[f"forward_vnindex_return_{h}"] = bench
            out[f"forward_excess_return_{h}"] = excess
        rows.append(out)
    return rows