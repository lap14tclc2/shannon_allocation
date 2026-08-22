"""Synthetic regression tests for risk-aware / fast optimizer changes.

These tests require no external VN price-data directory.
"""

from __future__ import annotations

import random

import numpy as np
import pandas as pd

from backtest.candidate import Candidate, random_candidate, validate_candidate, schedule_for_window
from backtest.config import BacktestParams
from backtest.optimize.eligibility import assess_live_eligibility
from backtest.optimize.evaluate import config_fingerprint, evaluate_candidate
from backtest.optimize.parallel import ParallelEvaluator
from backtest.optimize.screening import screen_universe
from backtest.optimize.walkforward import make_train_val_windows, split_research_holdout, evaluate_robust
from backtest.recommendation import _improvement_verdict, build_recommendation
from backtest.risk import apply_position_cap, risk_adjusted_targets
from backtest.simulation import SimulationResult, _fill_performance, simulate_combination
from backtest.strategy import compute_recommendations


def _panel(n=520, seed=3):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-02", periods=n)
    out = {}
    for i, s in enumerate("ABCDEFGH"):
        sigma = 0.006 + i * 0.0005
        rets = 0.0002 + sigma * rng.standard_normal(n)
        out[s] = 100.0 * np.exp(np.cumsum(rets))
    return pd.DataFrame(out, index=dates)


def test_position_cap_stays_normalized_and_bounded():
    w = {"A": 0.60, "B": 0.20, "C": 0.10, "D": 0.10}
    capped = apply_position_cap(w, 0.35)
    assert abs(sum(capped.values()) - 1.0) < 1e-9
    assert max(capped.values()) <= 0.35 + 1e-9


def test_vol_target_reduces_exposure_when_risk_is_high():
    prices = _panel()
    symbols = ["A", "B", "C", "D", "E"]
    relative = {s: 0.2 for s in symbols}
    params = BacktestParams(
        risk_overlay_enabled=True,
        target_volatility=0.05,
        risk_fast_lookback=63,
        risk_slow_lookback=252,
        min_equity_exposure=0.0,
        max_position_weight=0.40,
    )
    targets, info = risk_adjusted_targets(prices, symbols, 400, relative, params)
    assert 0.0 < info["equity_exposure"] < 1.0
    assert abs(sum(targets.values()) - info["equity_exposure"]) < 1e-6
    assert abs(info["cash_target"] - (1.0 - info["equity_exposure"])) < 1e-6


def test_risk_overlay_disabled_preserves_full_equity():
    prices = _panel()
    symbols = ["A", "B", "C", "D", "E"]
    relative = {s: 0.2 for s in symbols}
    params = BacktestParams(risk_overlay_enabled=False, max_position_weight=0.40)
    targets, info = risk_adjusted_targets(prices, symbols, 400, relative, params)
    assert info["equity_exposure"] == 1.0
    assert abs(sum(targets.values()) - 1.0) < 1e-9


def test_zero_live_target_generates_sell_not_hold():
    params = BacktestParams()
    shares = {"A": 10.0, "B": 10.0}
    prices = {"A": 100.0, "B": 100.0}
    recs, _ = compute_recommendations(
        shares,
        cash=0.0,
        prices=prices,
        targets={"A": 0.0, "B": 1.0},
        params=params,
    )
    by_symbol = {r["symbol"]: r for r in recs}
    assert by_symbol["A"]["recommendation"] == "SELL"


def test_exact_portfolio_size_random_candidates():
    universe = list("ABCDEFGHIJKL")
    rng = random.Random(42)
    for _ in range(100):
        c = random_candidate(rng, universe, 40, 252, portfolio_size=7)
        assert len(c.symbols) == 7
        assert validate_candidate(c, set(universe), 252, 40, portfolio_size=7) == []


def test_screening_uses_only_train_dates():
    prices = _panel(n=400)
    train = (prices.index[0], prices.index[199])
    chosen1, rows1 = screen_universe(prices, list(prices.columns), train, top_k=5, min_observations=100)

    mutated = prices.copy()
    mutated.loc[mutated.index > train[1], "H"] *= 100.0
    chosen2, rows2 = screen_universe(mutated, list(mutated.columns), train, top_k=5, min_observations=100)
    assert chosen1 == chosen2
    assert [r["symbol"] for r in rows1] == [r["symbol"] for r in rows2]


def test_global_holdout_never_overlaps_research_windows():
    dates = list(pd.bdate_range("2018-01-02", periods=1800))
    research, holdout = split_research_holdout(dates, 252)
    windows = make_train_val_windows(research, train_days=378, val_days=252, step=120)
    assert windows
    assert research[-1] < holdout[0]
    for w in windows:
        assert w["train"][1] < holdout[0]
        assert w["val"][1] < holdout[0]


def test_robust_drawdown_gate_rejects_candidate():
    c = Candidate(("A", "B", "C", "D", "E"), (40, 100, 160, 220))
    windows = [{"val": 1}, {"val": 2}]

    def fake_eval(_c, w):
        return {
            "net_twr_annualized_pct": 12.0,
            "sharpe": 1.0,
            "max_drawdown_pct": -40.0 if w["val"] == 2 else -10.0,
            "cdar95_pct": -20.0,
        }

    assert evaluate_robust(c, fake_eval, windows, min_windows=2, max_drawdown_abs_pct=35) is None
    assert evaluate_robust(c, fake_eval, windows, min_windows=2, max_drawdown_abs_pct=45) is not None


def test_deployment_verdict_requires_final_holdout_non_degradation():
    assert _improvement_verdict(5.0, -0.1, True, -20.0, -25.0) == "keep_baseline"
    assert _improvement_verdict(5.0, 1.5, False, -20.0, -25.0) == "keep_baseline"
    assert _improvement_verdict(5.0, 1.5, True, -20.0, -25.0) == "materially_better"


def test_live_eligibility_is_post_research_gate():
    robust = {"p10_net_twr": 5.0, "robust_return": 10.0}
    recent = {"net_twr_annualized_pct": 4.0, "max_drawdown_pct": -8.0}

    ok, reasons = assess_live_eligibility(
        {"net_twr_annualized_pct": 3.0}, robust, recent
    )
    assert ok is True
    assert reasons == []

    ok, reasons = assess_live_eligibility(
        {"net_twr_annualized_pct": -0.1}, robust, recent
    )
    assert ok is False
    assert any(r.startswith("train_twr_below") for r in reasons)

    ok, reasons = assess_live_eligibility(
        {"net_twr_annualized_pct": 3.0}, robust, {"net_twr_annualized_pct": -0.1}
    )
    assert ok is False
    assert any(r.startswith("recent_validation_twr_below") for r in reasons)


def test_window_xirr_anchors_to_actual_window_start_nav():
    result = SimulationResult(symbols=("A", "B", "C", "D", "E"))
    dates = [pd.Timestamp("2025-01-01"), pd.Timestamp("2026-01-01")]
    _fill_performance(
        result,
        net_nav_series=[120.0, 130.0],
        gross_nav_series=[120.0, 130.0],
        dates=dates,
        deposit_indices=set(),
        perf_start=0,
        first_invested_idx=0,
        allocation_indices=[0],
        deposit_dates=[],
        deposit_amounts=[],
        initial_balance=100.0,
        cumulative_cost_series=[0.0, 0.0],
        cumulative_traded_value_series=[0.0, 0.0],
        cumulative_trade_count_series=[0, 0],
        actual_equity_exposure_series=[1.0, 1.0],
        metrics_from="window_start",
    )
    expected = (130.0 / 120.0 - 1.0) * 100.0
    assert abs(result.xirr - expected) < 0.05
    assert result.measurement_start_nav == 120.0
    assert result.measurement_external_contributions == 0.0
    assert result.measurement_profit == 10.0


def test_recommendation_blocks_when_no_live_eligible_candidate_exists():
    experiment = {
        "experiment_id": "x",
        "meta": {},
        "winners": {
            "best_robust": {
                "symbols": ["A", "B", "C", "D", "E"],
                "allocation_days": [1, 61, 122, 183],
                "metrics": {"net_twr_annualized_pct": -1.0},
                "robust": {"robust_return": 10.0, "median_net_twr": 10.0},
                "test": {"valid": True, "median_net_twr": 2.0, "worst_mdd": -10.0},
                "live_eligible": False,
                "eligibility_reasons": ["train_twr_below_0%"],
            }
        },
        "baseline": {
            "robust": {"robust_return": 9.0},
            "test": {"median_net_twr": 1.0, "worst_mdd": -11.0},
        },
    }
    rec = build_recommendation(experiment)
    assert rec["deployment_eligible"] is False
    assert rec["improvement_vs_baseline"]["verdict"] == "no_live_eligible_candidate"


def test_capital_contributions_and_actual_deployment_are_separate_events():
    prices = _panel(n=650)
    symbols = ["A", "B", "C", "D", "E"]
    params = BacktestParams(
        initial_balance=100_000_000,
        annual_deposit=10_000_000,
        minimum_observations=20,
        lookback_days=63,
        risk_overlay_enabled=False,
    )
    candidate = Candidate(tuple(symbols), (1, 61, 122, 183))
    alloc_dates = schedule_for_window(candidate, list(prices.index))
    result = simulate_combination(symbols, prices, params, allocation_dates=alloc_dates)
    assert result.error is None
    assert result.capital_events[0]["type"] == "INITIAL_CAPITAL"
    assert result.capital_events[0]["amount"] == 100_000_000
    assert any(e["type"] == "ANNUAL_CONTRIBUTION" for e in result.capital_events)
    assert result.deployment_events
    assert any(e["buy_cash_deployed"] > 0 for e in result.deployment_events)
    assert all(e["execution_date"] >= e["signal_date"] for e in result.deployment_events)


def test_parallel_candidate_evaluation_matches_serial_result():
    prices = _panel(n=650)
    symbols = ["A", "B", "C", "D", "E"]
    params = BacktestParams(
        annual_deposit=0,
        minimum_observations=20,
        lookback_days=63,
        risk_overlay_enabled=False,
    )
    dates = list(prices.index)
    candidate = Candidate(tuple(symbols), (1, 61, 122, 183))
    cfg = config_fingerprint(params, "parallel-test")
    serial = evaluate_candidate(candidate, prices, params, dates, cache=None, cfg=cfg, max_allocation_day=252)
    with ParallelEvaluator(prices, params, dates, cfg, 252, workers=2) as evaluator:
        parallel = evaluator.evaluate_many([candidate], None, None)[0]
    assert serial["error"] == parallel["error"]
    assert abs(serial["net_twr_annualized_pct"] - parallel["net_twr_annualized_pct"]) < 1e-9
    assert abs(serial["max_drawdown_pct"] - parallel["max_drawdown_pct"]) < 1e-9
    assert abs(serial["final_nav"] - parallel["final_nav"]) < 1e-6
