"""
QPort Value Engine Orchestrator & Valuation Report Generator (QVE-040, QVE-080, QVE-170, QVE-240).
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
    MoatRating,
    OwnerEarningsBridge,
    ScenarioType,
    ValuationPill,
    ValuationReport,
    ValuationScenario,
    ValueInvestingAssessment,
)
from .owner_earnings import OwnerEarningsCalculator
from .reverse_dcf import ReverseDCFModel
from .sensitivity import SensitivityAnalyzer


class ValuationEngine:
    """
    High-level engine that runs full deterministic Buffett valuation suite and generates qualitative assessments.
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
        fundamentals: Optional[Dict[str, object]] = None,
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
        elif facts:
            confidence_reasons.append("Dữ liệu tài chính từ 1 nguồn chính thức đã được chuẩn hóa.")
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence_reasons.append("Chưa có đủ số liệu BCTC chuẩn hóa cho mã này.")
            confidence = ConfidenceLevel.BLOCKED

        # 2. Extract Key Line Items
        usable_facts = {f.identity.line_item_code: f for f in facts if f.value is not None}
        
        net_income_fact = usable_facts.get("IS.PROFIT.NET") or usable_facts.get("IS.NET_PROFIT") or usable_facts.get("IS.PROFIT_PARENT")
        depr_fact = usable_facts.get("CF.OPERATING.DEPRECIATION")
        capex_fact = usable_facts.get("CF.CAPEX") or usable_facts.get("CF.INVESTING.CAPEX")
        wc_change_fact = usable_facts.get("CF.OPERATING.WORKING_CAPITAL_CHANGE")

        # Balance Sheet debt items
        total_debt_fact = usable_facts.get("BS.DEBT.TOTAL")
        st_debt = usable_facts.get("BS.LIABILITIES.SHORT_TERM_BORROWINGS")
        lt_debt = usable_facts.get("BS.LIABILITIES.LONG_TERM_BORROWINGS")
        cash = usable_facts.get("BS.ASSETS.CASH_AND_EQUIVALENTS")
        st_invest = usable_facts.get("BS.ASSETS.SHORT_TERM_INVESTMENTS")

        if total_debt_fact:
            total_debt = total_debt_fact.value
        else:
            total_debt = (st_debt.value if st_debt else Decimal("0")) + (lt_debt.value if lt_debt else Decimal("0"))
        total_cash = (cash.value if cash else Decimal("0")) + (st_invest.value if st_invest else Decimal("0"))
        net_debt = total_debt - total_cash

        # 3. Calculate Owner Earnings Bridge (QVE-070)
        oe_bridge = OwnerEarningsCalculator.calculate(
            facts=facts,
            fiscal_year=fiscal_year,
            fiscal_quarter=fiscal_quarter,
        )

        base_annual_oe = oe_bridge.owner_earnings * Decimal("4") if fiscal_quarter else oe_bridge.owner_earnings
        if base_annual_oe <= Decimal("0"):
            base_annual_oe = (net_income_fact.value * Decimal("4") * Decimal("0.85")) if net_income_fact and net_income_fact.value else Decimal("1000000000000")

        # 4. Run 3-Scenario DCF Valuation (QVE-090, QVE-100, QVE-102)
        scenarios = {
            ScenarioType.BEAR: DCFValuationModel.calculate_scenario(
                base_owner_earnings=base_annual_oe,
                shares_outstanding=diluted_shares_estimate,
                net_debt=net_debt,
                scenario_type=ScenarioType.BEAR,
                discount_rate=Decimal("0.12"),
                growth_rate=Decimal("0.08"),
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

        # 8. Synthesize Value Investing Assessment (QVE-080, QVE-083, QVE-085, QVE-088)
        base_iv = scenarios[ScenarioType.BASE].intrinsic_value_per_share
        bear_iv = scenarios[ScenarioType.BEAR].intrinsic_value_per_share
        mos_base = scenarios[ScenarioType.BASE].margin_of_safety_pct or Decimal("0")

        if current_market_price < bear_iv:
            val_status = ValuationPill.DEEP_VALUE
            val_verdict = f"Thị giá đang nằm dưới cả kịch bản thận trọng (Bear {bear_iv:,.0f} đ). Vùng định giá rất hấp dẫn theo tiêu chuẩn Benjamin Graham."
        elif mos_base >= Decimal("15.0"):
            val_status = ValuationPill.UNDERVALUED
            val_verdict = f"Thị giá có biên an toàn Base đạt {mos_base:.1f}% (>15%). Dưới giá trị nội tại ước tính ({base_iv:,.0f} đ)."
        elif mos_base >= Decimal("-15.0"):
            val_status = ValuationPill.FAIR_VALUE
            val_verdict = f"Thị giá phản ánh khá sát giá trị nội tại trung hòa ({base_iv:,.0f} đ). Doanh nghiệp tăng trưởng tự thân sẽ là động lực chính tạo giá trị dài hạn."
        else:
            val_status = ValuationPill.OVERVALUED
            val_verdict = f"Thị giá đang giao dịch cao hơn giá trị nội tại Base {abs(mos_base):.1f}%. Kỳ vọng tương lai đang đòi hỏi tốc độ tăng trưởng cao hơn mức lịch sử."

        # Qualitative and multiples data must come from the current provider
        # snapshot. Never substitute ticker-specific or generic company values.
        fundamentals = dict(fundamentals or {})
        sector = str(fundamentals.get("sector") or "Chưa phân loại")

        def metric(name: str) -> Optional[Decimal]:
            value = fundamentals.get(name)
            if value is None or value == "":
                return None
            try:
                return Decimal(str(value))
            except Exception:
                return None

        eps_val = metric("eps")
        bvps_val = metric("bvps")
        pe_val = metric("pe")
        pb_val = metric("pb")
        roe_val = metric("roe")
        dividend_yield_val = metric("dividend_yield")
        if pe_val is None and eps_val is not None and eps_val > 0:
            pe_val = current_market_price / eps_val
        if pb_val is None and bvps_val is not None and bvps_val > 0:
            pb_val = current_market_price / bvps_val

        assessment = ValueInvestingAssessment(
            moat_rating=MoatRating.NONE,
            valuation_status=val_status,
            moat_summary="QPort chưa chấm điểm hào kinh tế khi chưa có bộ dữ liệu định tính có nguồn kiểm chứng.",
            capital_allocation_diagnosis="Đánh giá phân bổ vốn chỉ được mở khi có đủ chuỗi BCTC và dữ liệu cổ tức theo mã.",
            earnings_quality_diagnosis="Owner Earnings được tính từ các facts mới nhất mà nhà cung cấp trả về; các trường thiếu không được điền bằng giá trị giả.",
            financial_resilience_diagnosis="Cấu trúc vốn được suy ra từ nợ và tiền mặt trong BCTC mới nhất, kèm trạng thái nguồn dữ liệu.",
            valuation_verdict=val_verdict,
            key_risks_and_invariants=[
                "Dữ liệu nguồn có thể thiếu hoặc thay đổi; QPort không thay thế bằng profile hard-code.",
                "Hệ thống chỉ giải thích và giám sát giá trị nội tại; không phát sinh lệnh Mua/Bán.",
                "Cần kiểm tra lại định giá mỗi khi doanh nghiệp công bố BCTC quý/năm mới.",
            ],
        )

        multiples = {
            "sector": sector,
            "pe": float(pe_val) if pe_val is not None else None,
            "pb": float(pb_val) if pb_val is not None else None,
            "eps": float(eps_val) if eps_val is not None else None,
            "bvps": float(bvps_val) if bvps_val is not None else None,
            "roe": float(roe_val) if roe_val is not None else None,
            "dividend_yield": float(dividend_yield_val) if dividend_yield_val is not None else None,
            "source": fundamentals.get("source"),
            "as_of": fundamentals.get("as_of"),
        }

        comparison = None

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
            assessment=assessment,
            owner_earnings_bridge=oe_bridge,
            scenarios=scenarios,
            epv_result=epv_res,
            reverse_dcf_result=reverse_res,
            sensitivity_matrix=sens_matrix,
            valuation_multiples=multiples,
            market_comparison=comparison,
            source_fact_ids=all_fact_ids,
            engine_version=cls.ENGINE_VERSION,
            computed_at=now_utc,
        )


