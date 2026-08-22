"""Regression tests for soft risk/reward promotion and holdout isolation."""

from __future__ import annotations

import pandas as pd

from backtest.candidate import Candidate, resolve_allocation_dates
from backtest.optimize.eligibility import assess_live_eligibility, live_risk_reward_score
from backtest.optimize.reports import leaderboards
from backtest.recommendation import build_recommendation


def test_low_return_large_drawdown_is_soft_quality_not_binary_failure():
    train = {
        "net_twr_annualized_pct": 1.62,
        "max_drawdown_pct": -27.47,
        "calmar": 0.059,
    }
    validation = {
        "p10_net_twr": 12.0,
        "median_net_twr": 22.45,
        "worst_mdd": -30.0,
        "robust_return": 18.0,
    }
    recent = {
        "net_twr_annualized_pct": 3.86,
        "max_drawdown_pct": -20.24,
        "calmar": 0.19,
    }
    ok, reasons = assess_live_eligibility(train, validation, recent)
    assert ok is True
    assert reasons == []
    quality = live_risk_reward_score(train, validation, recent)
    assert quality["overall"] < 60.0
    assert quality["train_calmar"] == 0.059
    assert quality["recent_calmar"] == 0.19


def test_healthy_risk_reward_passes_live_gate_and_scores_better():
    train = {
        "net_twr_annualized_pct": 14.0,
        "max_drawdown_pct": -20.0,
        "calmar": 0.70,
    }
    validation = {
        "p10_net_twr": 8.0,
        "median_net_twr": 15.0,
        "worst_mdd": -22.0,
        "robust_return": 12.0,
    }
    recent = {
        "net_twr_annualized_pct": 10.0,
        "max_drawdown_pct": -16.0,
        "calmar": 0.625,
    }
    ok, reasons = assess_live_eligibility(train, validation, recent)
    assert ok is True
    assert reasons == []
    assert live_risk_reward_score(train, validation, recent)["overall"] > 50.0


def test_negative_oos_tail_is_still_a_hard_gate():
    ok, reasons = assess_live_eligibility(
        {"net_twr_annualized_pct": 20.0, "calmar": 1.0},
        {"p10_net_twr": -1.0, "median_net_twr": 20.0, "worst_mdd": -10.0},
        {"net_twr_annualized_pct": 10.0, "calmar": 1.0},
    )
    assert ok is False
    assert "validation_p10_below_0%" in reasons


def _item(symbol_suffix: str, robust: float, p10: float, recent: float, train: float, holdout_valid: bool):
    return {
        "candidate": Candidate(("A", "B", "C", "D", symbol_suffix), (40, 100, 160)),
        "metrics": {
            "net_twr_annualized_pct": train,
            "sharpe": 1.0,
            "sortino": 1.2,
            "calmar": 0.7,
            "max_drawdown_pct": -20.0,
            "cdar95_pct": -15.0,
        },
        "robust": {
            "robust_return": robust,
            "p10_net_twr": p10,
            "median_net_twr": robust + 1.0,
            "worst_mdd": -20.0,
        },
        "recent_validation": {"net_twr_annualized_pct": recent},
        "live_eligible": True,
        "test": {"valid": holdout_valid, "median_net_twr": 20.0 if holdout_valid else -5.0},
    }


def test_live_winner_is_not_reranked_by_final_holdout():
    e = _item("E", robust=20.0, p10=15.0, recent=14.0, train=16.0, holdout_valid=False)
    f = _item("F", robust=12.0, p10=10.0, recent=9.0, train=11.0, holdout_valid=True)
    winners = leaderboards([e, f])
    assert winners["best_live_eligible"]["candidate"].symbols[-1] == "E"


def test_negative_final_holdout_blocks_deployment_even_after_live_gate():
    experiment = {
        "experiment_id": "risk-policy",
        "meta": {},
        "winners": {
            "best_live_eligible": {
                "symbols": ["A", "B", "C", "D", "E"],
                "allocation_days": [40, 100, 160],
                "metrics": {
                    "net_twr_annualized_pct": 12.0,
                    "sharpe": 1.0,
                    "max_drawdown_pct": -18.0,
                },
                "robust": {
                    "robust_return": 14.0,
                    "median_net_twr": 15.0,
                    "p10_net_twr": 9.0,
                    "worst_mdd": -20.0,
                },
                "recent_validation": {"net_twr_annualized_pct": 10.0, "max_drawdown_pct": -12.0},
                "test": {"valid": True, "median_net_twr": -3.0, "worst_mdd": -18.0},
                "live_eligible": True,
            }
        },
        "baseline": {
            "allocation_days": [1, 61, 122, 183],
            "robust": {"robust_return": 13.0},
            "test": {"valid": True, "median_net_twr": -2.0, "worst_mdd": -17.0},
        },
    }
    rec = build_recommendation(experiment)
    assert rec["pre_holdout_live_eligible"] is True
    assert rec["deployment_eligible"] is False
    assert rec["deployment_variant"] == "none"
    assert "final_holdout_return_not_positive" in rec["deployment_reasons"]


def test_partial_year_missing_allocation_session_is_skipped_not_clamped():
    dates = list(pd.bdate_range("2024-01-02", periods=252))
    dates += list(pd.bdate_range("2025-01-02", periods=20))
    c = Candidate(("A", "B", "C", "D", "E"), (40, 100, 200))
    resolved, mapping = resolve_allocation_dates(c, dates)

    partial = [m for m in mapping if m["year"] == 2025 and m["requested_index"] == 200][0]
    assert partial["skipped"] is True
    assert partial["resolved_date"] is None
    assert partial["clamped"] is False
    assert dates[-1] not in resolved
