"""Allocation service — orchestrates eligibility, candidates, fit simulation,
opportunity cost, and the final advisory report.

Portfolio-risk simulation reuses the canonical ``portfolio.risk.portfolio_risk``
engine. We never copy covariance/correlation/ERC/VaR math.

Advisory only: no ledger mutation, no auto-execution.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable

from ..risk import portfolio_risk as canonical_portfolio_risk
from .candidate_service import shortlist_candidates
from .eligibility import eligibility_from_signal, signal_from_screener_item
from .models import (
    CandidateOpportunity,
    PortfolioFitResult,
    PortfolioAllocationReport,
)
from .opportunity import (
    decide_candidate,
    decide_holding,
    rotation_gates,
)
from .reason_codes import DATA_INSUFFICIENT
from .sizing import conviction_mid, conviction_tier_for, sizing_for

DEFAULT_HARD_CAP = 0.20
DEFAULT_MAX_CANDIDATES = 5
DEFAULT_MIN_LIQUIDITY = 10.0

RISK_KEY_FIELDS = (
    "volatility_252", "volatility_63", "average_correlation", "max_correlation",
    "diversification_ratio", "equity_hhi", "effective_positions",
    "largest_position_symbol", "max_equity_weight", "risk_contribution_hhi",
    "largest_risk_symbol", "largest_risk_contribution",
    "equal_risk_contribution", "risk_concentration_ratio",
    "daily_var_95", "daily_cvar_95", "downside_volatility",
    "positive_day_ratio", "return_observations", "status",
)


def _number(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed == parsed else None


class AllocationService:
    """Deterministic advisory allocation engine.

    All inputs are injected (position rows, histories, valuation signals,
    screener items) so the service is testable without a live database and
    stays DB-first in production.
    """

    def __init__(
        self,
        *,
        risk_fn: Callable = canonical_portfolio_risk,
        hard_cap: float = DEFAULT_HARD_CAP,
        max_candidates: int = DEFAULT_MAX_CANDIDATES,
        min_liquidity: float = DEFAULT_MIN_LIQUIDITY,
    ) -> None:
        self._risk = risk_fn
        self._hard_cap = float(hard_cap)
        self._max_candidates = int(max_candidates)
        self._min_liquidity = float(min_liquidity)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _signal_for(self, symbol: str, valuation_map: dict | None) -> dict:
        symbol = str(symbol).upper()
        if valuation_map:
            signal = valuation_map.get(symbol)
            if signal:
                merged = dict(signal)
                merged.setdefault("symbol", symbol)
                return merged
        return {"symbol": symbol}

    def _baseline_risk(self, rows: list[dict], histories: dict) -> dict:
        if not rows:
            return {}
        # The canonical engine requires histories to match the position symbols.
        position_symbols = {str(r.get("symbol") or "").upper() for r in rows}
        scoped = {
            str(s).upper(): h
            for s, h in (histories or {}).items()
            if str(s).upper() in position_symbols
        }
        return self._risk(rows, scoped)

    @staticmethod
    def _risk_summary(risk: dict) -> dict[str, Any]:
        if not risk:
            return {"status": "NO_POSITIONS"}
        return {key: risk.get(key) for key in RISK_KEY_FIELDS if key in risk}

    @staticmethod
    def _current_fit(
        symbol: str,
        weight: float,
        risk: dict,
        hard_cap: float,
    ) -> str:
        if not risk or risk.get("status") in ("NO_POSITIONS", "UNAVAILABLE"):
            return "UNAVAILABLE"
        rc = (risk.get("risk_contributions") or {}).get(symbol)
        if rc is None:
            return "UNAVAILABLE"
        equal_risk = risk.get("equal_risk_contribution")
        avg_corr = (risk.get("symbol_metrics") or {}).get(symbol, {}).get("average_correlation_to_others")
        weight = max(0.0, float(weight))
        if equal_risk and rc > max(0.45, 1.50 * float(equal_risk)):
            return "WEAK"
        if avg_corr is not None and float(avg_corr) >= 0.70:
            return "WEAK"
        if equal_risk and rc <= 1.20 * float(equal_risk) and (avg_corr is None or float(avg_corr) <= 0.50):
            return "GOOD"
        return "MODERATE"

    def _clone_apply_weight(self, rows: list[dict], nav: float, symbol: str, target_weight: float) -> list[dict] | None:
        """Clone rows and set a position's weight to ``target_weight`` (NAV-based).

        Returns None when infeasible (cash shortfall). Total NAV is preserved by
        moving the delta to/from cash (cash is not part of the risk rows).
        """
        target_weight = max(0.0, float(target_weight))
        clone = [dict(r) for r in rows]
        target_value = target_weight * nav
        current = next((r for r in clone if str(r.get("symbol") or "").upper() == str(symbol).upper()), None)
        if current is None:
            clone.append({"symbol": str(symbol).upper(), "market_value": target_value, "weight": target_weight})
        else:
            current["market_value"] = target_value
        for row in clone:
            row["weight"] = (float(row.get("market_value") or 0.0) / nav) if nav > 0 else 0.0
        return clone

    def _fit_for_proposed(
        self,
        base_rows: list[dict],
        histories: dict,
        before_risk: dict,
        nav: float,
        symbol: str,
        proposed_weight: float,
    ) -> PortfolioFitResult:
        """Simulate adding/setting a position at ``proposed_weight`` and compare.

        Uses the canonical risk engine only.
        """
        current_weight = max(0.0, next(
            (float(r.get("weight") or 0.0) for r in base_rows if str(r.get("symbol") or "").upper() == str(symbol).upper()),
            0.0,
        ))
        proposed = max(0.0, float(proposed_weight))
        cloned = self._clone_apply_weight(base_rows, nav, symbol, proposed)
        after_risk: dict = {}
        if cloned:
            after_risk = self._risk(cloned, histories)

        before_vol = _number(before_risk.get("volatility_252"))
        after_vol = _number(after_risk.get("volatility_252"))
        before_div = _number(before_risk.get("diversification_ratio"))
        after_div = _number(after_risk.get("diversification_ratio"))
        before_rc = (before_risk.get("risk_contributions") or {}).get(symbol)
        after_rc = (after_risk.get("risk_contributions") or {}).get(symbol)
        after_metric = (after_risk.get("symbol_metrics") or {}).get(symbol, {})
        avg_corr = _number(after_metric.get("average_correlation_to_others"))
        max_corr = _number(after_metric.get("max_correlation_to_others"))

        risk_available = bool(after_risk) and after_risk.get("status") not in ("NO_POSITIONS", "UNAVAILABLE") and after_vol is not None
        if not risk_available:
            return PortfolioFitResult(
                symbol=str(symbol).upper(),
                current_weight=current_weight,
                proposed_weight=proposed,
                portfolio_vol_before=before_vol,
                portfolio_vol_after=None,
                risk_contribution_before=before_rc,
                risk_contribution_after=None,
                diversification_ratio_before=before_div,
                diversification_ratio_after=None,
                average_correlation_to_portfolio=None,
                max_correlation_to_portfolio=None,
                hhi_after=_number(after_risk.get("equity_hhi")),
                effective_positions_after=_number(after_risk.get("effective_positions")),
                risk_available=False,
                fit="UNAVAILABLE",
            )

        equal_risk_after = after_risk.get("equal_risk_contribution")
        vol_change = ((after_vol - before_vol) / before_vol) if (before_vol and before_vol > 0) else None
        fit = "MODERATE"
        if after_rc is not None and equal_risk_after and after_rc > max(0.45, 1.50 * float(equal_risk_after)):
            fit = "WEAK"
        elif avg_corr is not None and avg_corr >= 0.70:
            fit = "WEAK"
        elif vol_change is not None and vol_change >= 0.10:
            fit = "WEAK"
        elif (
            (vol_change is None or vol_change <= 0.02)
            and (avg_corr is None or avg_corr <= 0.50)
            and (before_div is None or after_div is None or after_div >= before_div * 0.95)
        ):
            fit = "GOOD"

        return PortfolioFitResult(
            symbol=str(symbol).upper(),
            current_weight=current_weight,
            proposed_weight=proposed,
            portfolio_vol_before=before_vol,
            portfolio_vol_after=after_vol,
            risk_contribution_before=before_rc,
            risk_contribution_after=after_rc,
            diversification_ratio_before=before_div,
            diversification_ratio_after=after_div,
            average_correlation_to_portfolio=avg_corr,
            max_correlation_to_portfolio=max_corr,
            hhi_after=_number(after_risk.get("equity_hhi")),
            effective_positions_after=_number(after_risk.get("effective_positions")),
            risk_available=True,
            fit=fit,
        )

    # ------------------------------------------------------------------
    # evaluation
    # ------------------------------------------------------------------
    def evaluate(
        self,
        *,
        position_rows: list[dict],
        histories: dict[str, list[dict]] | None = None,
        cash: float = 0.0,
        portfolio_id: int | None = None,
        as_of: str | None = None,
        valuation_map: dict | None = None,
        candidate_items: list[dict] | None = None,
        changes: list[dict] | None = None,
    ) -> PortfolioAllocationReport:
        rows = [dict(r) for r in position_rows or []]
        histories = histories or {}
        cash = max(0.0, float(cash))
        nav = cash + sum(float(r.get("market_value") or 0.0) for r in rows)

        # Optional hypothetical changes (simulate mode) — rows are cloned.
        simulated_cash = cash
        if changes:
            rows, simulated_cash, _ = self._apply_changes(rows, nav, cash, changes)

        baseline = self._baseline_risk(rows, histories)
        holdings = sorted(rows, key=lambda r: float(r.get("weight") or 0.0), reverse=True)
        holding_symbols = {str(r.get("symbol") or "").upper() for r in holdings}

        holding_decisions = []
        holding_context: list[dict] = []
        for row in holdings:
            symbol = str(row.get("symbol") or "").upper()
            signal = self._signal_for(symbol, valuation_map)
            eligibility = eligibility_from_signal(signal)
            weight = max(0.0, float(row.get("weight") or 0.0))
            current_fit = self._current_fit(symbol, weight, baseline, self._hard_cap)
            sizing = sizing_for(signal, fit=current_fit, hard_cap=self._hard_cap)
            rc = (baseline.get("risk_contributions") or {}).get(symbol)
            decision = decide_holding(
                eligibility,
                current_weight=weight,
                risk_contribution=rc,
                equal_risk=baseline.get("equal_risk_contribution"),
                target_min=sizing.target_min,
                target_mid=sizing.target_mid,
                target_max=sizing.target_max,
                hard_cap=self._hard_cap,
                current_fit=current_fit,
            )
            holding_decisions.append(decision)
            holding_context.append({
                "symbol": symbol,
                "eligibility": eligibility,
                "current_fit": current_fit,
            })

        # Candidate discovery + portfolio-fit simulation.
        shortlist, candidate_diagnostics = shortlist_candidates(
            candidate_items or [],
            exclude_symbols=holding_symbols,
            max_candidates=self._max_candidates,
            min_liquidity=self._min_liquidity,
        )

        opportunities: list[CandidateOpportunity] = []
        for candidate in shortlist:
            signal = self._signal_for(candidate.symbol, valuation_map)
            if not signal.get("quality_tier") or signal.get("symbol") != candidate.symbol:
                item_signal = {
                    "symbol": candidate.symbol,
                    "quality_tier": candidate.eligibility.quality_tier,
                    "quality_score": candidate.eligibility.quality_score,
                    "hard_rejects": list(candidate.eligibility.hard_rejects),
                    "valuation_status": candidate.eligibility.valuation_status,
                    "actual_mos_pct": candidate.eligibility.actual_mos_pct,
                    "required_mos_pct": candidate.eligibility.required_mos_pct,
                    "valuation_confidence": candidate.eligibility.valuation_confidence,
                }
                signal = item_signal
            provisional_tier = conviction_tier_for(signal)
            provisional_mid = conviction_mid(provisional_tier)
            fit = self._fit_for_proposed(rows, histories, baseline, nav, candidate.symbol, provisional_mid)
            sizing = sizing_for(signal, fit=fit.fit, hard_cap=self._hard_cap)
            if abs(sizing.target_mid - provisional_mid) > 1e-6:
                fit = self._fit_for_proposed(rows, histories, baseline, nav, candidate.symbol, sizing.target_mid)
            candidate = replace(
                candidate,
                portfolio_fit=fit,
                sizing=sizing,
                reason_codes=tuple(dict.fromkeys(list(candidate.reason_codes) + list(sizing.reason_codes))),
            )
            opportunities.append(candidate)

        # Rotation coordination — explicit gates only (no composite score).
        for idx, decision in enumerate(holding_decisions):
            if decision.action != "HOLD":
                continue
            context = holding_context[idx]
            for candidate in opportunities:
                passed, gate_reasons = rotation_gates(
                    context["eligibility"],
                    holding_fit=context["current_fit"],
                    candidate=candidate,
                )
                if not passed:
                    continue
                reasons = list(dict.fromkeys(list(decision.reason_codes) + list(gate_reasons)))
                holding_decisions[idx] = replace(
                    decision,
                    action="REDUCE",
                    target_min=0.0,
                    target_mid=0.0,
                    target_max=0.0,
                    reason_codes=tuple(reasons),
                )
                break

        # Candidate decisions.
        cash_weight = (simulated_cash / nav) if nav > 0 else 0.0
        rotation_funded_symbols = {
            decision.symbol for decision in holding_decisions if decision.action == "REDUCE"
            and "SUPERIOR_REPLACEMENT_AVAILABLE" in decision.reason_codes
        }
        candidate_decisions = {
            candidate.symbol: decide_candidate(
                candidate,
                cash_weight=cash_weight,
                rotation_funded=candidate.symbol in rotation_funded_symbols,
            )
            for candidate in opportunities
        }
        # Attach the final advisory decision to each opportunity for the UI.
        opportunities = tuple(
            replace(candidate, decision=candidate_decisions.get(candidate.symbol))
            for candidate in opportunities
        )

        # Portfolio verdict.
        holdings_actions = [d.action for d in holding_decisions]
        candidate_actions = [d.action for d in candidate_decisions.values()]
        any_reduce = "REDUCE" in holdings_actions or "SELL" in holdings_actions
        any_buy = "BUY_MORE" in candidate_actions
        if any_reduce:
            posture = "ROTATE_OR_REVIEW"
        elif any_buy:
            posture = "HOLD_SELECTIVE_BUY"
        else:
            posture = "KEEP_CASH"
        no_action_required = not any_reduce and not any_buy

        planned_buy_mid = sum(
            float(candidate_decisions[s].target_mid or 0.0)
            for s in candidate_decisions
            if candidate_decisions[s].action == "BUY_MORE"
        )
        if any_reduce:
            freed = sum(
                max(0.0, float(d.current_weight) - float(d.target_mid or 0.0))
                for d in holding_decisions if d.action == "REDUCE"
            )
        else:
            freed = 0.0
        spendable = min(max(0.0, cash_weight + freed), planned_buy_mid)
        cash_low = max(0.0, round(cash_weight - spendable, 4))
        cash_suggested_range = (cash_low, round(cash_weight, 4))

        # Data quality summary.
        missing_valuation = sorted(
            s for s in holding_symbols
            if not (valuation_map or {}).get(s)
        )
        hard_reject_count = sum(1 for d in holding_decisions if d.action == "SELL")
        risk_coverage = ((baseline.get("quality") or {}).get("coverage_weight")) if baseline else None
        data_quality = {
            "valuation_coverage": {
                "holdings_with_signal": len(holding_symbols) - len(missing_valuation),
                "holdings_total": len(holding_symbols),
                "missing_valuation_symbols": missing_valuation,
            },
            "hard_reject_holdings": hard_reject_count,
            "risk_coverage": risk_coverage,
            "risk_status": baseline.get("status"),
            "candidate_diagnostics": candidate_diagnostics,
        }

        all_reasons = []
        for d in holding_decisions:
            all_reasons.extend(d.reason_codes)
        for d in candidate_decisions.values():
            all_reasons.extend(d.reason_codes)
        reason_codes = tuple(dict.fromkeys(all_reasons))

        if missing_valuation or risk_coverage is None or (risk_coverage is not None and risk_coverage < 0.90):
            confidence = "LOW"
        elif any(d.confidence == "LOW" for d in holding_decisions) or any(d.confidence == "LOW" for d in candidate_decisions.values()):
            confidence = "MEDIUM"
        else:
            confidence = "HIGH"

        report = PortfolioAllocationReport(
            portfolio_id=portfolio_id,
            as_of=as_of,
            verdict="NO_ACTION_REQUIRED" if no_action_required else "SELECTIVE_ACTION",
            posture=posture,
            cash_current=round(cash_weight, 4),
            cash_suggested_range=cash_suggested_range,
            no_action_required=no_action_required,
            holdings=tuple(holding_decisions),
            opportunities=tuple(opportunities),
            risk_summary=self._risk_summary(baseline),
            data_quality=data_quality,
            reason_codes=reason_codes,
            confidence=confidence,
        )
        if changes:
            report = replace(
                report,
                simulation={
                    "changes": [dict(c) for c in changes],
                    "risk_before": self._risk_summary(baseline),
                },
            )
        return report

    def simulate(
        self,
        *,
        changes: list[dict],
        position_rows: list[dict],
        histories: dict[str, list[dict]] | None = None,
        cash: float = 0.0,
        portfolio_id: int | None = None,
        as_of: str | None = None,
        valuation_map: dict | None = None,
        candidate_items: list[dict] | None = None,
    ) -> PortfolioAllocationReport:
        """Evaluate a hypothetical portfolio change set. Never persists anything."""
        before_risk = self._baseline_risk(list(position_rows or []), histories or {})
        report = self.evaluate(
            position_rows=position_rows,
            histories=histories,
            cash=cash,
            portfolio_id=portfolio_id,
            as_of=as_of,
            valuation_map=valuation_map,
            candidate_items=candidate_items,
            changes=changes,
        )
        report = replace(
            report,
            simulation={
                "changes": [dict(c) for c in changes],
                "risk_before": self._risk_summary(before_risk),
                "risk_after": report.risk_summary,
                "persisted": False,
            },
        )
        return report

    # ------------------------------------------------------------------
    # hypothetical change application
    # ------------------------------------------------------------------
    @staticmethod
    def _apply_changes(
        rows: list[dict],
        nav: float,
        cash: float,
        changes: list[dict],
    ) -> tuple[list[dict], float, bool]:
        """Apply hypothetical weight changes to cloned rows.

        Returns (rows, adjusted_cash, infeasible). Adjustments move value to/from
        cash so NAV is preserved; this is a pure in-memory simulation.
        """
        clone = [dict(r) for r in rows]
        working_cash = float(cash)
        infeasible = False
        for change in changes or []:
            symbol = str(change.get("symbol") or "").upper()
            target_weight = max(0.0, float(change.get("target_weight") or 0.0))
            if not symbol or nav <= 0:
                infeasible = True
                continue
            target_value = target_weight * nav
            current = next((r for r in clone if str(r.get("symbol") or "").upper() == symbol), None)
            if current is None:
                # Buying a new position must be funded by available cash; an
                # infeasible change is skipped and reported, never silently
                # creating negative cash or phantom equity.
                if target_value > working_cash + 1e-9:
                    infeasible = True
                    continue
                working_cash -= target_value
                clone.append({"symbol": symbol, "market_value": target_value, "weight": target_weight})
            else:
                old_value = float(current.get("market_value") or 0.0)
                if working_cash + old_value - target_value < -1e-9:
                    infeasible = True
                    continue
                working_cash += old_value - target_value
                current["market_value"] = target_value
        for row in clone:
            row["weight"] = (float(row.get("market_value") or 0.0) / nav) if nav > 0 else 0.0
        working_cash = max(0.0, working_cash)
        return clone, working_cash, infeasible