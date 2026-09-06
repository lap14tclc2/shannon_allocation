"""T10 — VNIndex benchmark abstraction.

Reuses the existing market-data provider architecture (``portfolio.market_data``)
and adds index-specific semantics:

- VNINDEX is an index POINTS series, NOT a VND price. The benchmark must NOT
  apply the VND scaling that stock prices use (index values are used as-is).
- The provider symbol mapping is verified at runtime (``verify``) and never
  assumed from naming conventions.
- Return math is deterministic: ``R(t,h) = P(t+h) / P(t) - 1`` over trading
  sessions. Corporate-action policy is irrelevant to an index and documented.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from ..market_data import AutoMarketData, MarketDataProvider

VNINDEX = "VNINDEX"
VALID_BENCHMARKS = (VNINDEX,)


@dataclass
class BenchmarkError(RuntimeError):
    message: str = ""


def normalize_benchmark(df: pd.DataFrame, symbol: str = VNINDEX) -> pd.DataFrame:
    """Normalize a provider index frame to benchmark points (no VND scaling).

    Expected columns: close (+ optional open/high/low/volume/source). The index
    is an integer/float points series; values are used as-is.
    """
    if df is None or df.empty:
        raise BenchmarkError("benchmark provider returned no data")
    out = df.copy()
    if "close" not in out.columns:
        raise BenchmarkError("benchmark frame has no close column")
    out["close"] = pd.to_numeric(out["close"], errors="coerce")
    out = out.dropna(subset=["close"])
    if out.empty:
        raise BenchmarkError("benchmark close series is empty after cleaning")
    out = out[~out.index.duplicated(keep="last")].sort_index()
    out["benchmark"] = str(symbol).upper()
    if "source" in out.columns:
        out["source"] = out["source"].fillna("unknown").astype(str)
    else:
        out["source"] = "unknown"
    return out


def validate_benchmark_points(series: pd.Series, symbol: str = VNINDEX) -> None:
    """Reject clearly-invalid index series (non-positive, NaN, zero range)."""
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        raise BenchmarkError(f"benchmark {symbol} has no usable close values")
    if (values <= 0).any():
        raise BenchmarkError(f"benchmark {symbol} contains non-positive close values")
    if values.nunique() <= 1:
        raise BenchmarkError(f"benchmark {symbol} has no price variation (flat series)")


class VNIndexBenchmark:
    """Canonical VNIndex benchmark service.

    ``history`` returns a normalized daily points frame for ``symbol`` in
    ``[start, end]``. Provider order follows ``AutoMarketData``.
    """

    def __init__(
        self,
        market: MarketDataProvider | None = None,
        symbol: str = VNINDEX,
    ) -> None:
        self._market = market or AutoMarketData()
        self.symbol = str(symbol).upper()

    def history(self, start: str, end: str) -> pd.DataFrame:
        if self.symbol not in VALID_BENCHMARKS:
            raise BenchmarkError(f"unsupported benchmark symbol: {self.symbol}")
        df = self._market.daily_history(self.symbol, start, end)
        normalized = normalize_benchmark(df, self.symbol)
        validate_benchmark_points(normalized["close"], self.symbol)
        return normalized[["benchmark", "close", "source"]].copy()

    def verify(self, start: str | None = None, end: str | None = None) -> dict:
        """Empirically verify the provider mapping, not assume naming semantics."""
        start = start or "2020-01-01"
        end = end or date.today().isoformat()
        try:
            df = self.history(start, end)
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "symbol": self.symbol,
                "error": str(exc),
                "source": None,
                "points": 0,
                "first_date": None,
                "last_date": None,
            }
        return {
            "ok": True,
            "symbol": self.symbol,
            "source": str(df["source"].iloc[0]) if not df.empty else None,
            "points": int(len(df)),
            "first_date": str(df.index.min().date()) if not df.empty else None,
            "last_date": str(df.index.max().date()) if not df.empty else None,
            "last_close": float(df["close"].iloc[-1]) if not df.empty else None,
        }


# ---------------------------------------------------------------------------
# Deterministic benchmark return math
# ---------------------------------------------------------------------------
def forward_benchmark_return(
    close_series: pd.Series,
    as_of_date,
    horizon_sessions: int,
    *,
    fill: str = "last",
) -> float | None:
    """Benchmark return over ``horizon_sessions`` trading sessions.

    ``R = P(t+h)/P(t) - 1`` where the base ``P(t)`` is the LAST close on or
    before ``as_of_date`` (price known at the analysis time — PIT-safe) and
    ``t+h`` is the ``horizon_sessions``-th subsequent session in the series.

    Missing days: the base uses last-available-before (``fill="last"``).
    Returns None when ``as_of_date`` precedes all data or the horizon is
    unresolved (beyond the series).
    """
    series = pd.to_numeric(close_series, errors="coerce").dropna().sort_index()
    if series.empty:
        return None
    base_idx = series.index.asof(pd.Timestamp(as_of_date))
    if pd.isna(base_idx):
        return None
    base_pos = series.index.get_loc(base_idx)
    base = float(series.iloc[base_pos])
    if base <= 0:
        return None
    end_pos = base_pos + int(horizon_sessions)
    if end_pos >= len(series):
        return None
    end_value = float(series.iloc[end_pos])
    if end_value <= 0:
        return None
    return end_value / base - 1.0


def benchmark_return_exact(
    close_series: pd.Series,
    start_date,
    end_date,
) -> float | None:
    """Return between two exact dates using last-available-before closes."""
    series = pd.to_numeric(close_series, errors="coerce").dropna().sort_index()
    start_idx = series.index.asof(pd.Timestamp(start_date))
    end_idx = series.index.asof(pd.Timestamp(end_date))
    if pd.isna(start_idx) or pd.isna(end_idx):
        return None
    start_v = float(series.loc[start_idx])
    end_v = float(series.loc[end_idx])
    if start_v <= 0:
        return None
    return end_v / start_v - 1.0