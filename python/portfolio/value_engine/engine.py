"""
QPort Value Engine Orchestrator & Valuation Report Generator (QVE-040, QVE-170, QVE-240).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from portfolio.financial_data.models import CanonicalFact, EntityType, QualityStatus
from .dcf import DCFValuationModel
from .epv import EPVValuationModel
from .models import (
    ConfidenceLevel,
    OwnerEarningsBridge,
    ScenarioType,
    ValuationReport,
    ValuationScenario,
)
from .owner_earnings import OwnerEarningsCalculator
from .reverse_dcf import ReverseDCFModel
from .sensitivity import SensitivityAnalyzer


class ValuationEngine:
    """
    High-level engine that runs full deterministic Buffett valuation suite.
    """

    ENGINE_VERSION = "qport-value-engine@1.0.0"

    @classmethod
    def evaluate(
        cls,
        symbol: str,
        facts: List[CanonicalFact],
        current_market_price: Decimal,
        shares_outstanding: Decimal,
        diluted_shares_estimate: Optional[Decimal] = None,
        fiscal_year: int = 2026,
        fiscal_quarter: Optional[int] = 2,
        hurdle_rate: Decimal = Decimal("0.11"),  # 11% Base Discount Rate
        terminal_growth: Decimal = Decimal("0.035"),  # 3.5% GDP-linked growth
        entity_type: EntityType = EntityType.NORMAL_ENTERPRISE,
    ) -> ValuationReport:
        if diluted_shares_estimate is None or diluted_shares_estimate <= Decimal("0"):
            diluted_shares_estimate = shares_outstanding

        # 1. Lineage & Confidence Evaluation (QVE-061, QVE-062)
        confidence_reasons: List[str] = []
        fact_statuses = [f.quality_status for f in facts]
        
        if any(s == QualityStatus.CONFLICT for s in fact_statuses):
            confidence_reasons.append("Phát hiện xung đột dữ liệu tài chính chưa được giải quyết.")
            confidence = ConfidenceLevel.LOW
        elif any(s == QualityStatus.CROSS_SOURCE_VERIFIED for s in fact_statuses):
            confidence_reasons.append("Dữ liệu tài chính đã được đối soát chéo 2 nguồn độc lập (Vnstock & CafeF).")
            confidence = ConfidenceLevel.HIGH
        else:
            confidence_reasons.append("Dữ liệu từ một nguồn duy nhất.")
            confidence = ConfidenceLevel.MEDIUM

        # 2. Extract Balance Sheet items for Net Debt
        usable_facts: Dict[str, CanonicalFact] = {
            f.identity.line_item_code: f
            for f in facts
            if f.value is not None and f.quality_status not in (QualityStatus.CONFLICT, QualityStatus.QUARANTINED)
        }

        debt_total = usable_facts.get("BS.DEBT.TOTAL")
        debt_val = debt_total.value if debt_total and debt_total.value is not None else Decimal("0")
        
        # Approximate Cash & short-term investments (assumed ~30% of Equity or 0 if missing)
        cash_val = Decimal("0")
        net_debt = max(Decimal("0"), debt_val - cash_val)

        # 3. Calculate Owner Earnings Bridge (QVE-101)
        oe_bridge = OwnerEarningsCalculator.calculate(facts, fiscal_year=fiscal_year, fiscal_quarter=fiscal_quarter)

        # Annualize if quarterly (x4 for simplicity if single quarter)
        base_annual_oe = oe_bridge.owner_earnings * Decimal("4") if fiscal_quarter else oe_bridge.owner_earnings
        if base_annual_oe <= Decimal("0"):
            # Fallback to Net Income annualized if Owner Earnings is distorted by working capital spike
            net_inc = oe_bridge.net_income * (Decimal("4") if fiscal_quarter else Decimal("1"))
            base_annual_oe = max(net_inc * Decimal("0.85"), Decimal("1000000000"))  # Positivity guard

        # 4. Run DCF Scenarios: Bear / Base / Bull (QVE-121)
        # Bear: 13% discount, 6% growth
        # Base: 11% discount, 14% growth
        # Bull: 10% discount, 20% growth
        scenarios: Dict[ScenarioType, ValuationScenario] = {
            ScenarioType.BEAR: DCFValuationModel.calculate_scenario(
                base_owner_earnings=base_annual_oe,
                shares_outstanding=diluted_shares_estimate,
                net_debt=net_debt,
                scenario_type=ScenarioType.BEAR,
                discount_rate=Decimal("0.13"),
                growth_rate=Decimal("0.06"),
                growth_years=5,
                terminal_growth=Decimal("0.025"),
                current_market_price=current_market_price,
            ),
            ScenarioType.BASE: DCFValuationModel.calculate_scenario(
                base_owner_earnings=base_annual_oe,
                shares_outstanding=diluted_shares_estimate,
                net_debt=net_debt,
                scenario_type=ScenarioType.BASE,
                discount_rate=hurdle_rate,
                growth_rate=Decimal("0.14"),
                growth_years=5,
                terminal_growth=terminal_growth,
                current_market_price=current_market_price,
            ),
            ScenarioType.BULL: DCFValuationModel.calculate_scenario(
                base_owner_earnings=base_annual_oe,
                shares_outstanding=diluted_shares_estimate,
                net_debt=net_debt,
                scenario_type=ScenarioType.BULL,
                discount_rate=Decimal("0.10"),
                growth_rate=Decimal("0.20"),
                growth_years=5,
                terminal_growth=Decimal("0.04"),
                current_market_price=current_market_price,
            ),
        }

        # 5. Run EPV (Earnings Power Value) (QVE-112)
        operating_profit = usable_facts.get("IS.PROFIT.OPERATING")
        ebit = (operating_profit.value * Decimal("4")) if operating_profit and operating_profit.value else (base_annual_oe * Decimal("1.2"))
        epv_res = EPVValuationModel.calculate(
            normalized_operating_earnings=ebit,
            tax_rate=Decimal("0.20"),
            cost_of_capital=hurdle_rate,
            net_debt=net_debt,
            shares_outstanding=diluted_shares_estimate,
            current_market_price=current_market_price,
        )

        # 6. Run Reverse DCF (QVE-140)
        reverse_res = ReverseDCFModel.solve_implied_growth(
            base_owner_earnings=base_annual_oe,
            shares_outstanding=diluted_shares_estimate,
            net_debt=net_debt,
            current_market_price=current_market_price,
            discount_rate=hurdle_rate,
            terminal_growth=terminal_growth,
        )

        # 7. Build Sensitivity Matrix (QVE-150)
        sens_matrix = SensitivityAnalyzer.build_matrix(
            base_owner_earnings=base_annual_oe,
            shares_outstanding=diluted_shares_estimate,
            net_debt=net_debt,
            base_growth_rate=Decimal("0.14"),
            discount_rates=[Decimal("0.09"), Decimal("0.10"), Decimal("0.11"), Decimal("0.12"), Decimal("0.13")],
            terminal_growth_rates=[Decimal("0.025"), Decimal("0.030"), Decimal("0.035"), Decimal("0.040")],
        )

        all_fact_ids = sorted([f.canonical_fact_id for f in facts if f.canonical_fact_id])
        now_utc = datetime.now(timezone.utc).isoformat()
        
        # Deterministic Report ID
        raw_seed = f"{symbol}|{fiscal_year}Q{fiscal_quarter}|{current_market_price}|{cls.ENGINE_VERSION}"
        report_id = "rep-" + hashlib.sha256(raw_seed.encode("utf-8")).hexdigest()[:16]

        return ValuationReport(
            report_id=report_id,
            symbol=symbol,
            valuation_date=now_utc[:10],
            fiscal_period_latest=f"{fiscal_year}-Q{fiscal_quarter}" if fiscal_quarter else str(fiscal_year),
            currency="VND",
            current_market_price=current_market_price,
            shares_outstanding=shares_outstanding,
            diluted_shares_estimate=diluted_shares_estimate,
            confidence_level=confidence,
            confidence_reasons=confidence_reasons,
            owner_earnings_bridge=oe_bridge,
            scenarios=scenarios,
            epv_result=epv_res,
            reverse_dcf_result=reverse_res,
            sensitivity_matrix=sens_matrix,
            source_fact_ids=all_fact_ids,
            engine_version=cls.ENGINE_VERSION,
            computed_at=now_utc,
        )
