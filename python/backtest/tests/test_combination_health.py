from __future__ import annotations

import numpy as np
import pandas as pd

from backtest.combination_health import analyze_combination_health
from backtest.config import BacktestParams


def _panel(n=900, seed=17):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2022-01-03", periods=n)
    common = 0.00035 + 0.009 * rng.standard_normal(n)
    out = {}
    for i, symbol in enumerate(["A", "B", "C", "D", "E"]):
        idio = (0.0015 + i * 0.00015) * rng.standard_normal(n)
        out[symbol] = 100.0 * np.exp(np.cumsum(common + idio))

    # Diversifying alternatives with enough positive drift to pass the quality guard.
    for i, symbol in enumerate(["F", "G", "H"]):
        ret = 0.00045 + (0.007 + i * 0.0005) * rng.standard_normal(n)
        out[symbol] = 100.0 * np.exp(np.cumsum(ret))
    return pd.DataFrame(out, index=dates)


def _params():
    return BacktestParams(
        minimum_observations=60,
        lookback_days=252,
        annualization_factor=252,
    )


def test_health_never_uses_reserved_final_holdout():
    prices = _panel()
    symbols = ["A", "B", "C", "D", "E"]
    original = analyze_combination_health(
        prices,
        symbols,
        params=_params(),
        available_symbols=list(prices.columns),
        holdout_days=252,
        include_suggestions=False,
    )

    mutated = prices.copy()
    # Extreme changes exist only inside the globally reserved holdout.
    tail = mutated.index[-252:]
    mutated.loc[tail, "A"] *= np.linspace(1.0, 20.0, len(tail))
    mutated.loc[tail, "B"] *= np.linspace(1.0, 0.05, len(tail))
    changed = analyze_combination_health(
        mutated,
        symbols,
        params=_params(),
        available_symbols=list(mutated.columns),
        holdout_days=252,
        include_suggestions=False,
    )

    assert original["status"] == changed["status"]
    assert original["score"] == changed["score"]
    assert original["correlation"] == changed["correlation"]
    assert original["diversification"] == changed["diversification"]
    assert original["erc"] == changed["erc"]
    assert original["reserved_holdout"]["used_for_health_or_suggestions"] is False


def test_missing_recent_data_blocks_optimizer_health_gate():
    prices = _panel()
    # Remove most research-period recent data for E, but leave the final holdout intact.
    research_end = len(prices) - 252
    prices.iloc[research_end - 220:research_end, prices.columns.get_loc("E")] = np.nan
    result = analyze_combination_health(
        prices,
        ["A", "B", "C", "D", "E"],
        params=_params(),
        available_symbols=list(prices.columns),
        holdout_days=252,
        include_suggestions=False,
    )
    assert result["status"] == "invalid"
    assert any("coverage" in reason.lower() or "observations" in reason.lower() for reason in result["reasons"])


def test_high_correlation_combination_can_suggest_diversifying_replacement():
    prices = _panel()
    result = analyze_combination_health(
        prices,
        ["A", "B", "C", "D", "E"],
        params=_params(),
        available_symbols=list(prices.columns),
        holdout_days=252,
        include_suggestions=True,
        suggestion_limit=5,
    )
    assert result["status"] in ("warning", "healthy")
    assert result["correlation"]["average"] is not None
    assert result["suggestions"]
    assert any(s["add"] in {"F", "G", "H"} for s in result["suggestions"])
    for suggestion in result["suggestions"]:
        corr_better = suggestion["after"]["average_correlation"] < suggestion["before"]["average_correlation"]
        div_better = suggestion["after"]["diversification_ratio"] > suggestion["before"]["diversification_ratio"]
        cluster_better = suggestion["after"]["largest_cluster_size"] < suggestion["before"]["largest_cluster_size"]
        assert corr_better or div_better or cluster_better
        assert suggestion["reasons"]
        assert len(suggestion["symbols"]) == 5
