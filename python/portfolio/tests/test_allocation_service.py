"""Allocation service golden scenarios.

These tests exercise the full orchestration (eligibility -> fit simulation ->
opportunity cost -> advisory report) with a deterministic fake risk engine so
they never require a live finance DB or network access.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from portfolio.allocation.eligibility import signal_from_screener_item
from portfolio.allocation.service import AllocationService

BASE_VOL = 0.20


class FakeRiskEngine:
    """Deterministic stand-in for the canonical portfolio_risk engine.

    Implements the same covariance math shape: weights normalized to equity,
    correlation matrix, portfolio volatility, risk contribution, correlation
    metrics, diversification ratio, concentration, and an UNAVAILABLE status for
    symbols with missing history.
    """

    def __init__(self, corr=None, base_vol=BASE_VOL, missing=(), rc_override=None):
        self.corr = corr or {}
        self.base_vol = float(base_vol)
        self.missing = set(missing)
        self.rc_override = dict(rc_override or {})

    def _corr(self, a: str, b: str) -> float:
        if a == b:
            return 1.0
        return float(self.corr.get(a, {}).get(b, self.corr.get(b, {}).get(a, 0.35)))

    def __call__(self, position_rows, histories):
        rows = [r for r in position_rows if r.get("market_value") is not None]
        if not rows:
            return {"status": "NO_POSITIONS"}
        symbols = [str(r["symbol"]).upper() for r in rows]
        weights = np.array([max(0.0, float(r.get("weight") or 0.0)) for r in rows], dtype=float)
        total = float(weights.sum())
        if total <= 0:
            return {"status": "UNAVAILABLE"}
        equity_weights = weights / total
        n = len(symbols)
        corr_matrix = np.full((n, n), 0.35)
        for i in range(n):
            for j in range(n):
                corr_matrix[i, j] = self._corr(symbols[i], symbols[j])
        corr_matrix = (corr_matrix + corr_matrix.T) / 2.0
        variance = float(equity_weights @ corr_matrix @ equity_weights)
        vol = self.base_vol * math.sqrt(max(variance, 1e-12))
        indiv = np.full(n, self.base_vol)
        weighted_indiv = float(equity_weights @ indiv)
        div = (weighted_indiv / vol) if vol > 1e-12 else None
        marginal = corr_matrix @ equity_weights
        rc_arr = ((equity_weights * marginal) / variance) if variance > 1e-12 else equity_weights
        rc = {s: float(v) for s, v in zip(symbols, rc_arr)}
        if self.rc_override:
            merged = {s: float(self.rc_override.get(s, rc.get(s, 0.0))) for s in symbols}
            ssum = sum(merged.values())
            if ssum > 0:
                rc = {k: v / ssum for k, v in merged.items()}
        equal_risk = 1.0 / n
        hhi = float((equity_weights ** 2).sum())
        effective = (1.0 / hhi) if hhi > 0 else 0.0
        sym_metrics = {}
        for s in symbols:
            peers = [self._corr(s, o) for o in symbols if o != s]
            avg_c = float(np.mean(peers)) if peers else None
            max_c = float(np.max(peers)) if peers else None
            sym_metrics[s] = {
                "average_correlation_to_others": avg_c,
                "max_correlation_to_others": max_c,
                "risk_contribution": rc[s],
            }
        avg_values = [m["average_correlation_to_others"] for m in sym_metrics.values()]
        avg_values = [v for v in avg_values if v is not None]
        portfolio_avg_corr = float(np.mean(avg_values)) if avg_values else None
        missing = [s for s in symbols if s in self.missing]
        status = "UNAVAILABLE" if missing else "VALID"
        return {
            "status": status,
            "volatility_252": vol,
            "volatility_63": vol,
            "average_correlation": portfolio_avg_corr,
            "max_correlation": float(np.max([
                m["max_correlation_to_others"] for m in sym_metrics.values()
                if m["max_correlation_to_others"] is not None
            ])) if n >= 2 else None,
            "diversification_ratio": div,
            "equity_hhi": hhi,
            "effective_positions": effective,
            "max_equity_weight": float(np.max(equity_weights)),
            "risk_contributions": rc,
            "equal_risk_contribution": equal_risk,
            "largest_risk_symbol": max(rc, key=rc.get),
            "largest_risk_contribution": max(rc.values()),
            "symbol_metrics": sym_metrics,
            "quality": {
                "coverage_weight": 0.0 if missing else 1.0,
                "missing_symbols": missing,
            },
        }


def make_service(corr=None, missing=(), rc_override=None):
    return AllocationService(risk_fn=FakeRiskEngine(corr=corr, missing=missing, rc_override=rc_override))


def build_rows(spec, nav=100.0):
    rows = []
    for symbol, weight in spec:
        rows.append({"symbol": symbol, "market_value": weight * nav, "weight": weight})
    return rows


def signal(**kwargs):
    defaults = {
        "symbol": "X",
        "quality_tier": "HIGH_QUALITY",
        "quality_score": 85,
        "hard_rejects": [],
        "valuation_status": "ATTRACTIVE",
        "actual_mos_pct": 32.0,
        "required_mos_pct": 25.0,
        "valuation_confidence": "MEDIUM",
    }
    defaults.update(kwargs)
    return defaults


def screener_item(**kwargs):
    base = {
        "symbol": "VNM",
        "company_name": "Vinamilk",
        "industry": "Sữa",
        "avg_turnover_20d_billion": 40.0,
        "current_price": 70000,
    }
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# Scenario 1: Excellent business + attractive valuation + good fit -> BUY_MORE
# ---------------------------------------------------------------------------
def test_scenario1_excellent_attractive_good_fit_buys():
    svc = make_service(corr={"FPT": {"VNM": 0.20}})
    rows = build_rows([("FPT", 0.60)])
    valuation_map = {
        "FPT": signal(symbol="FPT", quality_tier="HIGH_QUALITY", actual_mos_pct=30.0, required_mos_pct=25.0),
        "VNM": signal(symbol="VNM", quality_tier="EXCEPTIONAL", quality_score=92, actual_mos_pct=42.0, required_mos_pct=25.0),
    }
    candidates = [screener_item(
        symbol="VNM",
        tier="EXCEPTIONAL",
        total_score=92,
        valuation_status="HIGH_CONVICTION_VALUE",
        margin_of_safety=42.0,
        required_mos=25.0,
    )]
    report = svc.evaluate(
        position_rows=rows, cash=40.0, portfolio_id=1, as_of="2026-09-06",
        valuation_map=valuation_map, candidate_items=candidates,
    )
    assert report.no_action_required is False
    candidate_actions = [o.symbol for o in report.opportunities]
    assert "VNM" in candidate_actions
    decision = next(d for d in report.holdings if d.symbol == "FPT")
    assert decision.action == "HOLD"
    # The candidate itself must be BUY_MORE via the decision pipeline.
    from portfolio.allocation.opportunity import decide_candidate
    opp = report.opportunities[0]
    cand_decision = decide_candidate(opp, cash_weight=report.cash_current, rotation_funded=False)
    assert cand_decision.action == "BUY_MORE"
    assert cand_decision.target_mid is not None and 0.12 <= cand_decision.target_mid <= 0.18
    assert report.posture == "HOLD_SELECTIVE_BUY"


# ---------------------------------------------------------------------------
# Scenario 2: Excellent business + fair valuation + high risk contribution -> HOLD
# ---------------------------------------------------------------------------
def test_scenario2_excellent_fair_high_rc_holds():
    # Two holdings, FPT naturally contributes ~56% of risk (> equal-risk 50%)
    # but below the "excessive" breach threshold.
    svc = make_service(corr={"FPT": {"ACB": 0.60}})
    rows = build_rows([("FPT", 0.55), ("ACB", 0.45)])
    valuation_map = {
        "FPT": signal(symbol="FPT", quality_tier="EXCEPTIONAL", quality_score=90, valuation_status="FAIRLY_VALUED", actual_mos_pct=10.0, required_mos_pct=25.0),
        "ACB": signal(symbol="ACB", quality_tier="HIGH_QUALITY", quality_score=82, valuation_status="ATTRACTIVE", actual_mos_pct=30.0, required_mos_pct=25.0),
    }
    report = svc.evaluate(
        position_rows=rows, cash=0.0, portfolio_id=1, as_of="2026-09-06",
        valuation_map=valuation_map, candidate_items=[],
    )
    fpt = next(d for d in report.holdings if d.symbol == "FPT")
    assert fpt.action == "HOLD"
    assert "NO_SUPERIOR_REPLACEMENT" in fpt.reason_codes
    assert report.no_action_required is True
    assert "BUY_MORE" not in {d.action for d in report.holdings}


# ---------------------------------------------------------------------------
# Scenario 3: Weak business + large MOS -> must NOT BUY
# ---------------------------------------------------------------------------
def test_scenario3_weak_business_large_mos_never_buys():
    svc = make_service()
    rows = build_rows([("FPT", 0.60)])
    valuation_map = {
        "FPT": signal(symbol="FPT", quality_tier="HIGH_QUALITY", actual_mos_pct=30.0, required_mos_pct=25.0),
    }
    candidates = [screener_item(
        symbol="WEAK",
        tier="LOW_QUALITY",
        total_score=38,
        valuation_status="HIGH_CONVICTION_VALUE",
        margin_of_safety=70.0,
        required_mos=25.0,
    )]
    report = svc.evaluate(
        position_rows=rows, cash=40.0, portfolio_id=1, as_of="2026-09-06",
        valuation_map=valuation_map, candidate_items=candidates,
    )
    # The weak candidate is not shortlisted as an opportunity at all.
    assert all(o.symbol != "WEAK" for o in report.opportunities)
    assert report.no_action_required is True
    assert report.posture == "KEEP_CASH"


# ---------------------------------------------------------------------------
# Scenario 4: High momentum + accounting hard reject -> INELIGIBLE
# ---------------------------------------------------------------------------
def test_scenario4_hard_reject_never_investable():
    from portfolio.allocation.eligibility import eligibility_from_signal

    sig = signal(
        quality_tier="HIGH_QUALITY", quality_score=85,
        hard_rejects=["ACCOUNTING_UNRELIABLE"],
        valuation_status="HIGH_CONVICTION_VALUE", actual_mos_pct=60.0, required_mos_pct=25.0,
    )
    eligibility = eligibility_from_signal(sig)
    assert eligibility.status == "INELIGIBLE"
    assert "HARD_REJECT" in eligibility.reason_codes


# ---------------------------------------------------------------------------
# Scenario 5: Weak holding + superior low-correlation candidate -> REDUCE/ROTATE
# ---------------------------------------------------------------------------
def test_scenario5_weak_holding_superior_candidate_rotates():
    svc = make_service(corr={"XYZ": {"VNM": 0.20}})
    rows = build_rows([("XYZ", 0.50), ("CASH", 0.0)])
    rows = [r for r in rows if r["symbol"] != "CASH"]
    valuation_map = {
        "XYZ": signal(symbol="XYZ", quality_tier="WATCH", quality_score=62, valuation_status="FAIRLY_VALUED", actual_mos_pct=10.0, required_mos_pct=25.0),
        "VNM": signal(symbol="VNM", quality_tier="EXCEPTIONAL", quality_score=92, actual_mos_pct=42.0, required_mos_pct=25.0),
    }
    candidates = [screener_item(
        symbol="VNM",
        tier="EXCEPTIONAL",
        total_score=92,
        valuation_status="HIGH_CONVICTION_VALUE",
        margin_of_safety=42.0,
        required_mos=25.0,
    )]
    report = svc.evaluate(
        position_rows=rows, cash=0.0, portfolio_id=1, as_of="2026-09-06",
        valuation_map=valuation_map, candidate_items=candidates,
    )
    xyz = next(d for d in report.holdings if d.symbol == "XYZ")
    assert xyz.action == "REDUCE"
    assert "SUPERIOR_REPLACEMENT_AVAILABLE" in xyz.reason_codes
    from portfolio.allocation.opportunity import decide_candidate
    opp = report.opportunities[0]
    cand_decision = decide_candidate(opp, cash_weight=report.cash_current, rotation_funded=True)
    assert cand_decision.action == "BUY_MORE"


# ---------------------------------------------------------------------------
# Scenario 6: Weak holding + no superior alternative -> HOLD / KEEP_CASH
# ---------------------------------------------------------------------------
def test_scenario6_weak_holding_no_superior_holds():
    svc = make_service()
    rows = build_rows([("XYZ", 0.60)])
    valuation_map = {
        "XYZ": signal(symbol="XYZ", quality_tier="WATCH", quality_score=62, valuation_status="FAIRLY_VALUED", actual_mos_pct=10.0, required_mos_pct=25.0),
    }
    report = svc.evaluate(
        position_rows=rows, cash=0.0, portfolio_id=1, as_of="2026-09-06",
        valuation_map=valuation_map, candidate_items=[],
    )
    xyz = next(d for d in report.holdings if d.symbol == "XYZ")
    assert xyz.action == "HOLD"
    assert report.no_action_required is True
    assert report.posture == "KEEP_CASH"


# ---------------------------------------------------------------------------
# Scenario 7: Correlated bank candidate in bank-heavy portfolio -> capped/WATCH
# ---------------------------------------------------------------------------
def test_scenario7_correlated_bank_candidate_is_capped_and_watched():
    svc = make_service(corr={
        "ACB": {"MBB": 0.75, "VPB": 0.85},
        "MBB": {"VPB": 0.85},
    })
    rows = build_rows([("ACB", 0.50), ("MBB", 0.50)])
    valuation_map = {
        "ACB": signal(symbol="ACB", quality_tier="HIGH_QUALITY", actual_mos_pct=30.0, required_mos_pct=25.0),
        "MBB": signal(symbol="MBB", quality_tier="HIGH_QUALITY", actual_mos_pct=30.0, required_mos_pct=25.0),
        "VPB": signal(symbol="VPB", quality_tier="INVESTABLE", quality_score=75, actual_mos_pct=35.0, required_mos_pct=25.0),
    }
    candidates = [screener_item(
        symbol="VPB",
        tier="INVESTABLE",
        total_score=75,
        valuation_status="ATTRACTIVE",
        margin_of_safety=35.0,
        required_mos=25.0,
    )]
    report = svc.evaluate(
        position_rows=rows, cash=30.0, portfolio_id=1, as_of="2026-09-06",
        valuation_map=valuation_map, candidate_items=candidates,
    )
    assert report.opportunities, "VPB must appear as a candidate opportunity"
    vpb = report.opportunities[0]
    assert vpb.portfolio_fit.fit == "WEAK"
    assert vpb.sizing.target_max <= 0.05
    from portfolio.allocation.opportunity import decide_candidate
    decision = decide_candidate(vpb, cash_weight=report.cash_current, rotation_funded=False)
    assert decision.action == "WATCH"


# ---------------------------------------------------------------------------
# Scenario 8: No eligible candidates -> KEEP_CASH
# ---------------------------------------------------------------------------
def test_scenario8_no_eligible_candidates_keeps_cash():
    svc = make_service()
    rows = build_rows([("FPT", 0.60)])
    valuation_map = {
        "FPT": signal(symbol="FPT", quality_tier="HIGH_QUALITY", actual_mos_pct=30.0, required_mos_pct=25.0),
    }
    report = svc.evaluate(
        position_rows=rows, cash=40.0, portfolio_id=1, as_of="2026-09-06",
        valuation_map=valuation_map, candidate_items=[],
    )
    assert report.opportunities == ()
    assert report.no_action_required is True
    assert report.posture == "KEEP_CASH"


# ---------------------------------------------------------------------------
# Scenario 9: Missing risk history -> UNAVAILABLE, never zero risk
# ---------------------------------------------------------------------------
def test_scenario9_missing_risk_history_is_unavailable_not_zero():
    svc = make_service(missing={"FPT", "VNM"})
    rows = build_rows([("FPT", 0.60)])
    valuation_map = {
        "FPT": signal(symbol="FPT", quality_tier="HIGH_QUALITY", actual_mos_pct=30.0, required_mos_pct=25.0),
        "VNM": signal(symbol="VNM", quality_tier="EXCEPTIONAL", quality_score=92, actual_mos_pct=42.0, required_mos_pct=25.0),
    }
    candidates = [screener_item(
        symbol="VNM",
        tier="EXCEPTIONAL",
        total_score=92,
        valuation_status="HIGH_CONVICTION_VALUE",
        margin_of_safety=42.0,
        required_mos=25.0,
    )]
    report = svc.evaluate(
        position_rows=rows, cash=40.0, portfolio_id=1, as_of="2026-09-06",
        valuation_map=valuation_map, candidate_items=candidates,
    )
    assert report.risk_summary.get("status") == "UNAVAILABLE"
    assert report.data_quality["risk_status"] == "UNAVAILABLE"
    vnm = report.opportunities[0]
    assert vnm.portfolio_fit.fit == "UNAVAILABLE"
    assert vnm.portfolio_fit.risk_available is False
    assert vnm.portfolio_fit.portfolio_vol_after is None
    from portfolio.allocation.opportunity import decide_candidate
    decision = decide_candidate(vnm, cash_weight=report.cash_current, rotation_funded=False)
    assert decision.action == "WATCH"
    assert "DATA_INSUFFICIENT" in decision.reason_codes


# ---------------------------------------------------------------------------
# Hysteresis: small valuation differences never rotate.
# ---------------------------------------------------------------------------
def test_hysteresis_small_valuation_difference_never_rotates():
    from portfolio.allocation.models import CandidateOpportunity, EligibilityResult, PortfolioFitResult
    from portfolio.allocation.opportunity import VALUATION_SAFETY_REPLACEMENT_DELTA, rotation_gates

    holding = EligibilityResult(symbol="XYZ", status="INVESTABLE", quality_tier="WATCH", quality_score=62, valuation_safety=-5.0)
    candidate = CandidateOpportunity(
        symbol="VNM", source="SCREENER",
        eligibility=EligibilityResult(symbol="VNM", status="INVESTABLE", quality_tier="HIGH_QUALITY", quality_score=85, valuation_safety=-2.0),
        portfolio_fit=PortfolioFitResult(symbol="VNM", current_weight=0.0, proposed_weight=0.1, risk_available=True, fit="GOOD"),
    )
    # Delta (3 pp) below the 10 pp governance buffer -> no rotation.
    passed, _ = rotation_gates(holding, holding_fit="MODERATE", candidate=candidate)
    assert passed is False
    assert VALUATION_SAFETY_REPLACEMENT_DELTA == 10.0


# ---------------------------------------------------------------------------
# Determinism: same inputs -> identical outputs.
# ---------------------------------------------------------------------------
def test_determinism_same_inputs_same_output():
    kwargs = dict(
        position_rows=build_rows([("FPT", 0.60)]),
        cash=40.0,
        portfolio_id=1,
        as_of="2026-09-06",
        valuation_map={
            "FPT": signal(symbol="FPT", quality_tier="HIGH_QUALITY", actual_mos_pct=30.0, required_mos_pct=25.0),
            "VNM": signal(symbol="VNM", quality_tier="EXCEPTIONAL", quality_score=92, actual_mos_pct=42.0, required_mos_pct=25.0),
        },
        candidate_items=[screener_item(
            symbol="VNM", tier="EXCEPTIONAL", total_score=92,
            valuation_status="HIGH_CONVICTION_VALUE", margin_of_safety=42.0, required_mos=25.0,
        )],
    )
    a = make_service(corr={"FPT": {"VNM": 0.20}}).evaluate(**kwargs).to_dict()
    b = make_service(corr={"FPT": {"VNM": 0.20}}).evaluate(**kwargs).to_dict()
    assert a == b


# ---------------------------------------------------------------------------
# Simulate mode never mutates inputs and reports persisted=False.
# ---------------------------------------------------------------------------
def test_simulate_returns_risk_before_after_without_mutation():
    svc = make_service(corr={"FPT": {"VNM": 0.20}})
    rows = build_rows([("FPT", 0.60)])
    valuation_map = {
        "FPT": signal(symbol="FPT", quality_tier="HIGH_QUALITY", actual_mos_pct=30.0, required_mos_pct=25.0),
    }
    rows_before = [dict(r) for r in rows]
    report = svc.simulate(
        changes=[{"symbol": "VNM", "target_weight": 0.10}],
        position_rows=rows,
        cash=40.0,
        portfolio_id=1,
        as_of="2026-09-06",
        valuation_map=valuation_map,
        candidate_items=[],
    )
    assert rows == rows_before, "simulate must not mutate input rows"
    assert report.simulation["persisted"] is False
    assert report.simulation["risk_before"] is not None
    assert report.simulation["risk_after"] is not None
    # Simulated buy appears in the after holdings (advisory only).
    symbols = {d.symbol for d in report.holdings}
    assert "VNM" in symbols


def test_simulate_infeasible_buy_is_skipped_not_fabricated():
    svc = make_service(corr={"FPT": {"VNM": 0.20}})
    rows = build_rows([("FPT", 0.95)])
    valuation_map = {"FPT": signal(symbol="FPT", quality_tier="HIGH_QUALITY", actual_mos_pct=30.0, required_mos_pct=25.0)}
    report = svc.simulate(
        changes=[{"symbol": "VNM", "target_weight": 0.50}],
        position_rows=rows,
        cash=0.05,
        portfolio_id=1,
        as_of="2026-09-06",
        valuation_map=valuation_map,
        candidate_items=[],
    )
    symbols = {d.symbol for d in report.holdings}
    assert "VNM" not in symbols, "infeasible buy must be skipped"
    assert report.simulation["persisted"] is False


# ---------------------------------------------------------------------------
# Real canonical risk engine integration (not the fake)
# ---------------------------------------------------------------------------
def _synthetic_histories(symbols, corr_map, days=260, seed=7):
    import pandas as pd

    rng = np.random.default_rng(seed)
    n = len(symbols)
    corr = np.eye(n)
    for i in range(n):
        for j in range(n):
            if i != j:
                corr[i, j] = float(corr_map.get(symbols[i], {}).get(symbols[j], corr_map.get(symbols[j], {}).get(symbols[i], 0.3)))
    corr = (corr + corr.T) / 2.0
    chol = np.linalg.cholesky(corr + np.eye(n) * 1e-9)
    z = rng.normal(0.0, 1.0, (days, n))
    daily = (z @ chol.T) * 0.015
    prices = 20000.0 * np.exp(np.cumsum(daily, axis=0))
    dates = pd.bdate_range(end="2026-09-04", periods=days)
    histories = {}
    for i, symbol in enumerate(symbols):
        histories[symbol] = [
            {"trading_date": str(d.date()), "close": float(prices[t, i])}
            for t, d in enumerate(dates)
        ]
    return histories


def test_real_canonical_risk_engine_drives_fit_simulation():
    from portfolio.allocation.service import AllocationService as RealService

    service = RealService()
    symbols = ["FPT", "VNM"]
    histories = _synthetic_histories(symbols, {"FPT": {"VNM": 0.15}})
    rows = build_rows([("FPT", 0.60)])
    valuation_map = {
        "FPT": signal(symbol="FPT", quality_tier="HIGH_QUALITY", actual_mos_pct=30.0, required_mos_pct=25.0),
        "VNM": signal(symbol="VNM", quality_tier="EXCEPTIONAL", quality_score=92, actual_mos_pct=42.0, required_mos_pct=25.0),
    }
    candidates = [screener_item(
        symbol="VNM", tier="EXCEPTIONAL", total_score=92,
        valuation_status="HIGH_CONVICTION_VALUE", margin_of_safety=42.0, required_mos=25.0,
    )]
    report = service.evaluate(
        position_rows=rows,
        histories=histories,
        cash=40.0,
        portfolio_id=1,
        as_of="2026-09-06",
        valuation_map=valuation_map,
        candidate_items=candidates,
    )
    # The canonical engine produced real risk numbers.
    assert report.risk_summary["status"] == "VALID"
    assert report.risk_summary["volatility_252"] is not None
    vnm = report.opportunities[0]
    assert vnm.portfolio_fit.fit in ("GOOD", "MODERATE", "WEAK")
    assert vnm.portfolio_fit.portfolio_vol_after is not None
    # Deterministic across calls.
    again = service.evaluate(
        position_rows=rows, histories=histories, cash=40.0, portfolio_id=1,
        as_of="2026-09-06", valuation_map=valuation_map, candidate_items=candidates,
    ).to_dict()
    assert again == report.to_dict()