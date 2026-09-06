"""T13 — Factor validation tests (IC, quantiles, walk-forward, sealed OOS)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from portfolio.research.validation import (
    ResearchCostModel,
    date_rank_ic,
    factor_verdict,
    ic_summary,
    quantile_analysis,
    rank_ic_series,
    validate_factor,
)
from portfolio.research.walk_forward import (
    ResearchConfig,
    is_sealed,
    partition_periods,
    walk_forward_windows,
)


def _rows(factor_by_date_symbol: dict, excess_by_date_symbol: dict) -> list[dict]:
    rows = []
    for date_value, symbols in factor_by_date_symbol.items():
        for symbol, value in symbols.items():
            rows.append({
                "snapshot_date": date_value,
                "symbol": symbol,
                "value_factor": value,
                "forward_excess_return_63": excess_by_date_symbol.get(date_value, {}).get(symbol),
            })
    return rows


def _cross_section(dates: list[str], positive: bool = True) -> list[dict]:
    """40 dates x 10 symbols. Factor and excess positively (or inversely) related."""
    factor = {f"S{i}": i for i in range(1, 11)}
    rows = []
    for date_value in dates:
        excess = {f"S{i}": (i if positive else 11 - i) for i in range(1, 11)}
        for i in range(1, 11):
            rows.append({
                "snapshot_date": date_value,
                "symbol": f"S{i}",
                "value_factor": factor[f"S{i}"],
                "forward_excess_return_63": excess[f"S{i}"],
            })
    return rows


def _dates(n: int, start="2023-01-02") -> list[str]:
    return [str(d.date()) for d in pd.bdate_range(start, periods=n)]


def test_rank_ic_is_spearman():
    frame = pd.DataFrame({"factor": [1, 2, 3, 4, 5], "excess": [5, 4, 3, 2, 1]})
    assert date_rank_ic(frame["factor"], frame["excess"]) == pytest.approx(-1.0)
    frame2 = pd.DataFrame({"factor": [1, 2, 3, 4, 5], "excess": [1, 2, 3, 4, 5]})
    assert date_rank_ic(frame2["factor"], frame2["excess"]) == pytest.approx(1.0)


def test_rank_ic_requires_minimum_cross_section():
    frame = pd.DataFrame({"factor": [1, 2], "excess": [1, 2]})
    assert date_rank_ic(frame["factor"], frame["excess"]) is None


def test_ic_summary():
    summary = ic_summary(pd.Series([0.1, 0.2, 0.05, -0.1, 0.3]))
    assert summary["count"] == 5
    assert summary["positive_ic_ratio"] == pytest.approx(0.8)
    assert summary["mean_ic"] == pytest.approx(0.11)
    assert summary["median_ic"] == pytest.approx(0.1)


def test_quantile_assignment_and_spread():
    factor = {f"S{i}": i for i in range(1, 11)}
    excess = {f"S{i}": i for i in range(1, 11)}
    rows = _rows({"2023-01-02": factor}, {"2023-01-02": excess})
    result = quantile_analysis(rows, "forward_excess_return_63", n_quantiles=5)
    # Q5 should have the highest excess return, Q1 the lowest.
    assert result["quantiles"]["Q5"] > result["quantiles"]["Q1"]
    assert result["spread"] > 0


def test_top_minus_bottom_spread_positive_for_positive_factor():
    factor = {f"S{i}": i for i in range(1, 11)}
    excess = {f"S{i}": i for i in range(1, 11)}
    rows = _rows({"2023-01-02": factor, "2023-01-03": factor}, {"2023-01-02": excess, "2023-01-03": excess})
    result = quantile_analysis(rows, "forward_excess_return_63", n_quantiles=5)
    assert result["spread"] is not None and result["spread"] > 0
    # Deterministic.
    again = quantile_analysis(rows, "forward_excess_return_63", n_quantiles=5)
    assert again == result


def test_chronological_walk_forward_no_random_split():
    config = ResearchConfig(research_start="2016-01-01", train_years=5, validation_years=1)
    windows = walk_forward_windows(config)
    assert windows
    first = windows[0]
    # Train strictly precedes validation.
    assert first["train_start"] == "2016-01-01"
    assert first["train_end"] < first["valid_start"]
    for w in windows:
        assert w["train_start"] <= w["train_end"] < w["valid_start"] <= w["valid_end"]
    # Windows are strictly chronological (no random split).
    for a, b in zip(windows, windows[1:]):
        assert a["valid_end"] < b["valid_start"]


def test_sealed_oos_excluded_from_tuning():
    config = ResearchConfig(
        research_start="2016-01-01", train_years=5, validation_years=1,
        sealed_oos_start="2024-01-01", sealed_oos_end="2025-12-31",
    )
    dates = ["2018-06-01", "2019-06-01", "2024-03-01", "2025-03-01"]
    partitioned = partition_periods(config, dates)
    assert "2024-03-01" in partitioned["sealed"]
    assert "2025-03-01" in partitioned["sealed"]
    assert "2018-06-01" in partitioned["in_sample"]
    assert is_sealed(config, "2024-06-01") is True
    assert is_sealed(config, "2023-06-01") is False


def test_tuning_on_sealed_oos_is_guarded():
    from portfolio.research.walk_forward import assert_not_sealed

    config = ResearchConfig(
        research_start="2016-01-01", sealed_oos_start="2024-01-01", sealed_oos_end="2025-12-31",
    )
    with pytest.raises(ValueError):
        assert_not_sealed(config, "2024-06-01")
    # In-sample date passes.
    assert_not_sealed(config, "2023-06-01")


def test_validate_factor_verdict_rules():
    # Positive factor-edge in-sample, but sealed-OOS mean IC <= 0 -> UNSTABLE.
    in_sample = _cross_section(_dates(40, "2023-01-02"), positive=True)
    sealed = _cross_section(_dates(12, "2024-01-02"), positive=False)
    config = ResearchConfig(
        research_start="2016-01-01", sealed_oos_start="2024-01-01", sealed_oos_end="2025-12-31",
    )
    result = validate_factor(in_sample + sealed, config=config, n_quantiles=5)
    assert result["verdict"] == "UNSTABLE"
    assert result["sealed_oos_mean_ic"] is not None and result["sealed_oos_mean_ic"] <= 0
    assert result["observations"] == len(in_sample)
    assert result["sealed_observations"] == len(sealed)


def test_validate_factor_insufficient_data():
    result = validate_factor([], config=ResearchConfig(research_start="2016-01-01"))
    assert result["verdict"] == "INSUFFICIENT_DATA"


def test_validate_factor_rejected_when_no_edge():
    result = validate_factor(
        _cross_section(_dates(40, "2023-01-02"), positive=False),
        config=ResearchConfig(research_start="2016-01-01"),
    )
    assert result["verdict"] == "REJECTED"


def test_validate_factor_validated_with_stable_oos():
    in_sample = _cross_section(_dates(40, "2023-01-02"), positive=True)
    sealed = _cross_section(_dates(12, "2024-01-02"), positive=True)
    config = ResearchConfig(
        research_start="2016-01-01", sealed_oos_start="2024-01-01", sealed_oos_end="2025-12-31",
    )
    result = validate_factor(in_sample + sealed, config=config, n_quantiles=5)
    assert result["verdict"] == "VALIDATED"
    assert result["sealed_oos_mean_ic"] is not None and result["sealed_oos_mean_ic"] > 0


def test_cost_adjusted_output():
    cost = ResearchCostModel(commission_rate=0.0025, sell_tax_rate=0.001, slippage_rate=0.001)
    assert cost.round_trip_cost() == pytest.approx(0.0025 * 2 + 0.001 + 0.001 * 2)
    assert cost.after_cost_spread(0.10) == pytest.approx(0.10 - cost.round_trip_cost())
    assert cost.after_cost_spread(None) is None
    assert "not live-realistic" in cost.to_dict()["assumptions"].lower()


def test_validate_factor_is_deterministic():
    rows = _rows(
        {"2023-01-02": {f"S{i}": i for i in range(1, 11)}},
        {"2023-01-02": {f"S{i}": i for i in range(1, 11)}},
    )
    a = validate_factor(rows, config=ResearchConfig(research_start="2016-01-01"))
    b = validate_factor(rows, config=ResearchConfig(research_start="2016-01-01"))
    assert a == b


def test_factor_verdict_direct_rules():
    assert factor_verdict(ic={"count": 10}, oos_mean_ic=None, quantile_spread_after_cost=0.01) == "INSUFFICIENT_DATA"
    assert factor_verdict(
        ic={"count": 50, "mean_ic": -0.01, "positive_ic_ratio": 0.4},
        oos_mean_ic=0.01, quantile_spread_after_cost=0.01,
    ) == "REJECTED"
    assert factor_verdict(
        ic={"count": 50, "mean_ic": 0.05, "positive_ic_ratio": 0.9},
        oos_mean_ic=0.0, quantile_spread_after_cost=0.03,
    ) == "UNSTABLE"
    assert factor_verdict(
        ic={"count": 50, "mean_ic": 0.05, "positive_ic_ratio": 0.9},
        oos_mean_ic=0.03, quantile_spread_after_cost=0.03,
    ) == "VALIDATED"


def test_rank_ic_series_deterministic():
    rows = _rows(
        {"2023-01-02": {f"S{i}": i for i in range(1, 11)}},
        {"2023-01-02": {f"S{i}": i for i in range(1, 11)}},
    )
    ic = rank_ic_series(rows, "forward_excess_return_63")
    assert not ic.empty
    assert ic.iloc[0] == pytest.approx(1.0)