"""T13 — Factor validation: rank IC, quantiles, walk-forward, verdict.

Each factor is validated independently. Metrics are deterministic. Verdicts use
conservative explicit rules — a factor is NEVER called VALIDATED merely because
mean IC > 0.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from .walk_forward import (
    ResearchConfig,
    is_sealed,
    partition_periods,
    walk_forward_windows as _walk_forward_windows,
)

FACTOR_VERDICTS = ("VALIDATED", "WEAK", "UNSTABLE", "REJECTED", "INSUFFICIENT_DATA")

# Conservative governance thresholds (documented policy, not empirical optimum).
MIN_CROSS_SECTION = 3          # symbols required per date for a rank IC
MIN_OBSERVATIONS = 30          # minimum pooled observations for any verdict
MIN_IC_POSITIVE_RATIO = 0.55   # required for WEAK/VALIDATED candidate
OOS_IC_FLOOR = 0.0             # sealed-OOS mean IC must be > this for VALIDATED


# ---------------------------------------------------------------------------
# Rank IC
# ---------------------------------------------------------------------------
def date_rank_ic(factor_series: pd.Series, excess_series: pd.Series) -> float | None:
    """Spearman rank IC for a single cross-section (one date)."""
    frame = pd.concat([factor_series, excess_series], axis=1).dropna()
    frame.columns = ["factor", "excess"]
    if len(frame) < MIN_CROSS_SECTION:
        return None
    if frame["excess"].nunique() < 2 or frame["factor"].nunique() < 2:
        return None
    factor_rank = frame["factor"].rank(method="average")
    excess_rank = frame["excess"].rank(method="average")
    return float(np.corrcoef(factor_rank, excess_rank)[0, 1])


def rank_ic_series(snapshot_rows: Iterable[dict], excess_key: str) -> pd.Series:
    """Per-date rank IC series across the full sample (excludes sealed by caller)."""
    rows = list(snapshot_rows)
    if not rows:
        return pd.Series(dtype=float)
    factor = pd.Series({(r["snapshot_date"], r["symbol"]): r.get("value_factor") for r in rows}, dtype=float)
    excess = pd.Series({(r["snapshot_date"], r["symbol"]): r.get(excess_key) for r in rows}, dtype=float)
    factor.index = pd.MultiIndex.from_tuples(factor.index, names=["date", "symbol"])
    excess.index = pd.MultiIndex.from_tuples(excess.index, names=["date", "symbol"])
    frame = pd.DataFrame({"factor": factor, "excess": excess}).dropna()
    ics: dict[str, float] = {}
    for date_value, group in frame.groupby(level="date"):
        ic = date_rank_ic(group["factor"], group["excess"])
        if ic is not None:
            ics[str(date_value)] = ic
    return pd.Series(ics, dtype=float).sort_index()


def ic_summary(ic_series: pd.Series) -> dict:
    if ic_series.empty:
        return {
            "count": 0, "mean_ic": None, "median_ic": None, "ic_std": None,
            "positive_ic_ratio": None,
        }
    values = ic_series.dropna().astype(float)
    if values.empty:
        return {
            "count": 0, "mean_ic": None, "median_ic": None, "ic_std": None,
            "positive_ic_ratio": None,
        }
    return {
        "count": int(len(values)),
        "mean_ic": float(values.mean()),
        "median_ic": float(values.median()),
        "ic_std": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
        "positive_ic_ratio": float((values > 0).mean()),
    }


# ---------------------------------------------------------------------------
# Quantile analysis
# ---------------------------------------------------------------------------
def quantile_analysis(snapshot_rows: Iterable[dict], excess_key: str, n_quantiles: int = 5) -> dict:
    """Cross-sectional quantile assignment per date, then pooled averages.

    Returns per-quantile mean excess return, top-minus-bottom spread, and
    turnover (fraction of symbols changing quantile vs previous date).
    """
    rows = list(snapshot_rows)
    frame = pd.DataFrame([
        {"date": r["snapshot_date"], "symbol": r["symbol"],
         "factor": r.get("value_factor"), "excess": r.get(excess_key)}
        for r in rows
    ], columns=["date", "symbol", "factor", "excess"]).dropna(subset=["factor", "excess"])
    if frame.empty:
        return {"quantiles": {}, "spread": None, "turnover": None, "count": 0}

    quantiles: dict[str, list] = {}
    prev_assignment: dict[str, int] = {}
    changes = 0
    total = 0
    for date_value, group in frame.groupby("date"):
        if len(group) < n_quantiles:
            continue
        q = pd.qcut(group["factor"].rank(method="first"), n_quantiles, labels=False, duplicates="drop") + 1
        group = group.assign(q=q)
        for _, row in group.iterrows():
            qv = int(row["q"])
            quantiles.setdefault(f"Q{qv}", []).append(float(row["excess"]))
            if row["symbol"] in prev_assignment:
                total += 1
                if prev_assignment[row["symbol"]] != qv:
                    changes += 1
            prev_assignment[row["symbol"]] = qv

    result = {}
    for key in sorted(quantiles):
        result[key] = float(np.mean(quantiles[key])) if quantiles[key] else None
    keys = sorted(quantiles)
    spread = None
    if keys:
        top = result.get(keys[-1])
        bottom = result.get(keys[0])
        if top is not None and bottom is not None:
            spread = float(top - bottom)
    return {
        "quantiles": result,
        "spread": spread,
        "turnover": float(changes / total) if total else None,
        "count": int(len(frame)),
    }


# ---------------------------------------------------------------------------
# Transaction costs
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResearchCostModel:
    """Simple, configurable research cost model (assumptions, not live-realistic).

    - commission_rate: per-side commission (fraction of traded value), default 25 bps.
    - sell_tax_rate: sell tax on proceeds (VN 0.1% default), applied to sold side.
    - slippage_bps: per-side slippage assumption, default 10 bps.
    """
    commission_rate: float = 0.0025
    sell_tax_rate: float = 0.001
    slippage_rate: float = 0.001

    def round_trip_cost(self) -> float:
        """Total one-way-equivalent cost for a full buy+sell round trip."""
        return 2 * self.commission_rate + self.sell_tax_rate + 2 * self.slippage_rate

    def one_way_cost(self) -> float:
        return self.commission_rate + self.slippage_rate

    def after_cost_spread(self, gross_spread: float | None) -> float | None:
        if gross_spread is None:
            return None
        # A round trip (buy at quantile bottom, sell at quantile top) pays the
        # round-trip cost on the traded value.
        return float(gross_spread) - self.round_trip_cost()

    def to_dict(self) -> dict:
        return {
            "commission_rate": self.commission_rate,
            "sell_tax_rate": self.sell_tax_rate,
            "slippage_rate": self.slippage_rate,
            "assumptions": "Configurable research cost model. Not live-realistic; "
                           "execution/slippage is simplified.",
        }


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------
def factor_verdict(
    *,
    ic: dict,
    oos_mean_ic: float | None,
    quantile_spread_after_cost: float | None,
    min_observations: int = MIN_OBSERVATIONS,
    oos_ic_floor: float = OOS_IC_FLOOR,
) -> str:
    """Conservative explicit verdict rules (documented governance policy).

    - insufficient sample            -> INSUFFICIENT_DATA
    - mean IC <= 0 or no positive edge -> REJECTED
    - positive in-sample but no OOS support -> UNSTABLE
    - consistent positive IC + after-cost spread + OOS floor -> VALIDATED
    - otherwise                      -> WEAK
    """
    count = int(ic.get("count") or 0)
    if count < min_observations:
        return "INSUFFICIENT_DATA"
    mean_ic = ic.get("mean_ic")
    positive_ratio = ic.get("positive_ic_ratio")
    if mean_ic is None or mean_ic <= 0:
        return "REJECTED"
    if positive_ratio is None or positive_ratio < MIN_IC_POSITIVE_RATIO:
        return "WEAK"
    if quantile_spread_after_cost is None or quantile_spread_after_cost <= 0:
        return "WEAK"
    if oos_mean_ic is None or oos_mean_ic <= oos_ic_floor:
        return "UNSTABLE"
    return "VALIDATED"


def validate_factor(
    snapshot_rows: Iterable[dict],
    *,
    excess_key: str = "forward_excess_return_63",
    config: ResearchConfig | None = None,
    cost_model: ResearchCostModel | None = None,
    n_quantiles: int = 5,
) -> dict:
    """Run the full per-factor validation and produce a deterministic report dict."""
    rows = list(snapshot_rows)
    cost_model = cost_model or ResearchCostModel()

    # Split sealed OOS out of the tuning path.
    tuning_rows = rows
    sealed_rows: list[dict] = []
    if config is not None and (config.sealed_oos_start or config.sealed_oos_end):
        partitioned = partition_periods(config, [r["snapshot_date"] for r in rows])
        sealed_dates = set(partitioned["sealed"])
        tuning_rows = [r for r in rows if r["snapshot_date"] not in sealed_dates]
        sealed_rows = [r for r in rows if r["snapshot_date"] in sealed_dates]

    in_sample_ic = rank_ic_series(tuning_rows, excess_key)
    ic = ic_summary(in_sample_ic)

    quant = quantile_analysis(tuning_rows, excess_key, n_quantiles=n_quantiles)
    gross_spread = quant.get("spread")
    after_cost_spread = cost_model.after_cost_spread(gross_spread)

    oos_mean_ic = None
    if sealed_rows:
        oos_ic = rank_ic_series(sealed_rows, excess_key)
        oos_summary = ic_summary(oos_ic)
        oos_mean_ic = oos_summary.get("mean_ic")

    windows = _walk_forward_windows(config) if config else []
    verdict = factor_verdict(
        ic=ic,
        oos_mean_ic=oos_mean_ic,
        quantile_spread_after_cost=after_cost_spread,
    )

    return {
        "factor": "value_factor",
        "horizon_sessions": int(excess_key.split("_")[-1]),
        "excess_key": excess_key,
        "observations": int(len(tuning_rows)),
        "sealed_observations": int(len(sealed_rows)),
        "rank_ic": ic,
        "quantiles": quant,
        "gross_spread": gross_spread,
        "after_cost_spread": after_cost_spread,
        "cost_model": cost_model.to_dict(),
        "sealed_oos_mean_ic": oos_mean_ic,
        "walk_forward_windows": windows,
        "verdict": verdict,
        "limitations": [
            "Historical universe membership is not reconstructible from current data; "
            "survivorship-bias-free results are NOT claimed.",
            "Inferred publication dates use governance lags (45d quarter / 90d annual); "
            "these are assumptions, not verified filing dates.",
            "Cost model is configurable research simplification, not live-realistic.",
        ],
    }