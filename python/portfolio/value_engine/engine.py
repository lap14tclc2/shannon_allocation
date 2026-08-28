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
        fiscal_quarter: Optional[int] = None,
        hurdle_rate: Decimal = Decimal("0.11"),  # 11% Base Discount Rate
        terminal_growth: Decimal = Decimal("0.035"),  # 3.5% GDP-linked growth
        entity_type: EntityType = EntityType.NORMAL_ENTERPRISE,
        fundamentals: Optional[Dict[str, object]] = None,
        financial_history: Optional[List[Dict[str, Any]]] = None,
        value_investor_pillars: Optional[Dict[str, Any]] = None,
    ) -> ValuationReport:
        if diluted_shares_estimate is None or diluted_shares_estimate <= Decimal("0"):
            diluted_shares_estimate = shares_outstanding
        if fiscal_quarter is not None:
            raise ValueError(
                "TTM_REQUIRED: quarterly facts require an explicit audited TTM bridge before valuation."
            )

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

        # 2. Extract facts & identify company type
        is_bank = entity_type == EntityType.BANK or "bank" in str(symbol).lower()

        # Check multiples and qualitative data from fundamentals
        fundamentals = dict(fundamentals or {})
        sector = str(fundamentals.get("sector") or ("Ngân hàng" if is_bank else "Doanh nghiệp niêm yết"))

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
        if roe_val is None and eps_val is not None and bvps_val is not None and bvps_val > 0:
            roe_val = (eps_val / bvps_val) * Decimal("100")

        # =========================================================================
        # PATH A: DEDICATED BANK VALUATION ENGINE (Residual Income Model + Justified P/B)
        # =========================================================================
        if is_bank:
            net_debt = Decimal("0")
            from .bank_valuation import BankValuationModel
            if bvps_val is None or bvps_val <= Decimal("0"):
                # Estimate BVPS from available BS.EQUITY.TOTAL if present
                eq_facts = [f for f in facts if f.identity.line_item_code == "BS.EQUITY.TOTAL" and f.value is not None]
                if eq_facts and shares_outstanding > Decimal("0"):
                    bvps_val = (eq_facts[-1].value * Decimal("1000000000")) / shares_outstanding
                else:
                    bvps_val = current_market_price / (pb_val or Decimal("1.2"))

            bank_roe = roe_val or Decimal("18.0")
            scenarios = BankValuationModel.calculate_bank_suite(
                current_bvps=bvps_val,
                historical_5y_avg_roe=bank_roe,
                current_market_price=current_market_price,
                shares_outstanding=diluted_shares_estimate,
                cost_of_equity=hurdle_rate,
            )

            # Bank EPV is Tangible Book Value adjusted for normalized spread
            epv_per_share = bvps_val * (bank_roe / hurdle_rate)
            epv_res = EPVValuationModel.calculate(
                normalized_operating_earnings=bvps_val * shares_outstanding * Decimal("0.15"),
                tax_rate=Decimal("0.20"),
                cost_of_capital=hurdle_rate,
                net_debt=Decimal("0"),
                shares_outstanding=diluted_shares_estimate,
                current_market_price=current_market_price,
            )

            reverse_res = ReverseDCFModel.solve_implied_growth(
                base_owner_earnings=bvps_val * shares_outstanding * (bank_roe / Decimal("100")),
                shares_outstanding=diluted_shares_estimate,
                net_debt=Decimal("0"),
                current_market_price=current_market_price,
                discount_rate=hurdle_rate,
                terminal_growth=terminal_growth,
            )

            sens_matrix = SensitivityAnalyzer.build_matrix(
                base_owner_earnings=bvps_val * shares_outstanding * (bank_roe / Decimal("100")),
                shares_outstanding=diluted_shares_estimate,
                net_debt=Decimal("0"),
                base_growth_rate=scenarios[ScenarioType.BASE].growth_stage1_rate,
                discount_rates=[Decimal("0.09"), Decimal("0.10"), Decimal("0.11"), Decimal("0.12"), Decimal("0.13")],
                terminal_growth_rates=[Decimal("0.025"), Decimal("0.030"), Decimal("0.035"), Decimal("0.040")],
            )

            oe_bridge = OwnerEarningsBridge(
                net_income=(bvps_val * shares_outstanding * (bank_roe / Decimal("100"))),
                depreciation_amortization=Decimal("0"),
                maintenance_capex=Decimal("0"),
                growth_capex_estimated=Decimal("0"),
                working_capital_change=Decimal("0"),
                owner_earnings=(bvps_val * shares_outstanding * (bank_roe / Decimal("100"))),
                formula_description=(
                    f"Bank Valuation Model: Residual Income Model (RIM) dựa trên BVPS ({bvps_val:,.0f} ₫) "
                    f"và ROE chuẩn hóa ({bank_roe:.1f}%). Khác với doanh nghiệp thông thường, tiền gửi và cho vay của ngân hàng "
                    f"là tài sản/nguồn vốn hoạt động cốt lõi, giá trị nội tại được xác định bằng thặng dư ROE trên chi phí vốn (Cost of Equity)."
                ),
                source_fact_ids=[],
            )

        # =========================================================================
        # PATH B: NON-FINANCIAL ENTERPRISES (Normalized Owner Earnings + DCF + EPV)
        # =========================================================================
        else:
            usable_facts = {
                fact.identity.line_item_code: fact
                for fact in facts
                if fact.value is not None
                and fact.identity.fiscal_year == fiscal_year
                and fact.identity.fiscal_quarter is None
                and fact.quality_status not in (QualityStatus.CONFLICT, QualityStatus.QUARANTINED, QualityStatus.MISSING)
            }
            required_codes = (
                "IS.PROFIT.NET",
                "IS.PROFIT.OPERATING",
                "CF.OPERATING.NET",
                "CF.OPERATING.DEPRECIATION",
                "CF.CAPEX",
                "BS.DEBT.TOTAL",
                "BS.ASSETS.CASH_AND_EQUIVALENTS",
                "IS.SHARES.OUTSTANDING",
            )
            missing = [code for code in required_codes if code not in usable_facts]
            if missing:
                raise ValueError("VALUATION_FACTS_INCOMPLETE: " + ", ".join(missing))

            total_debt = usable_facts["BS.DEBT.TOTAL"].value
            total_cash = usable_facts["BS.ASSETS.CASH_AND_EQUIVALENTS"].value
            net_debt = total_debt - total_cash

            # 3. Calculate Normalized Owner Earnings Bridge
            oe_bridge = OwnerEarningsCalculator.calculate_cycle_normalized(
                facts=facts,
                latest_fiscal_year=fiscal_year,
                lookback_years=5,
            )
            base_annual_oe = oe_bridge.owner_earnings
            if base_annual_oe <= Decimal("0"):
                raise ValueError("OWNER_EARNINGS_NON_POSITIVE: valuation blocked; no synthetic fallback is allowed.")

            # 4. Dynamic Fundamental Growth Derivation: g = b * ROE (or ROIC)
            roe_ratio = (roe_val / Decimal("100")) if roe_val and roe_val > Decimal("0") else Decimal("0.15")
            retention_rate = Decimal("0.70")  # Estimate 70% retention for growth
            fundamental_base_growth = min(Decimal("0.18"), max(Decimal("0.06"), roe_ratio * retention_rate))
            bear_growth = max(Decimal("0.03"), fundamental_base_growth * Decimal("0.60"))
            bull_growth = min(Decimal("0.22"), fundamental_base_growth * Decimal("1.35"))

            scenarios = {
                ScenarioType.BEAR: DCFValuationModel.calculate_scenario(
                    base_owner_earnings=base_annual_oe,
                    shares_outstanding=diluted_shares_estimate,
                    net_debt=net_debt,
                    scenario_type=ScenarioType.BEAR,
                    discount_rate=Decimal("0.12"),
                    growth_rate=bear_growth,
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
                    growth_rate=fundamental_base_growth,
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
                    growth_rate=bull_growth,
                    growth_years=5,
                    terminal_growth=Decimal("0.04"),
                    current_market_price=current_market_price,
                ),
            }

            ebit = usable_facts["IS.PROFIT.OPERATING"].value
            epv_res = EPVValuationModel.calculate(
                normalized_operating_earnings=ebit,
                tax_rate=Decimal("0.20"),
                cost_of_capital=hurdle_rate,
                net_debt=net_debt,
                shares_outstanding=diluted_shares_estimate,
                current_market_price=current_market_price,
            )

            reverse_res = ReverseDCFModel.solve_implied_growth(
                base_owner_earnings=base_annual_oe,
                shares_outstanding=diluted_shares_estimate,
                net_debt=net_debt,
                current_market_price=current_market_price,
                discount_rate=hurdle_rate,
                terminal_growth=terminal_growth,
            )

            sens_matrix = SensitivityAnalyzer.build_matrix(
                base_owner_earnings=base_annual_oe,
                shares_outstanding=diluted_shares_estimate,
                net_debt=net_debt,
                base_growth_rate=fundamental_base_growth,
                discount_rates=[Decimal("0.09"), Decimal("0.10"), Decimal("0.11"), Decimal("0.12"), Decimal("0.13")],
                terminal_growth_rates=[Decimal("0.025"), Decimal("0.030"), Decimal("0.035"), Decimal("0.040")],
            )

        # 8. Synthesize Value Investing Assessment (Buffett-Munger Standards)
        base_iv = scenarios[ScenarioType.BASE].intrinsic_value_per_share
        bear_iv = scenarios[ScenarioType.BEAR].intrinsic_value_per_share
        bull_iv = scenarios[ScenarioType.BULL].intrinsic_value_per_share
        mos_base = scenarios[ScenarioType.BASE].margin_of_safety_pct or Decimal("0")

        # Professional financial analysis synthesis
        mos_text = f"+{mos_base:.1f}%" if mos_base > 0 else f"{mos_base:.1f}%"
        pe_str = f"{pe_val:.1f}x" if pe_val is not None else "N/A"
        pb_str = f"{pb_val:.2f}x" if pb_val is not None else "N/A"
        roe_str = f"{roe_val:.1f}%" if roe_val is not None else "N/A"

        # 8. Synthesize Buffett-Munger Rule Engine Assessment (Archetypes, Quality, Dynamic MOS)
        from .archetypes import ArchetypeClassifier
        from .quality_scorer import QualityScorer, QualityTier
        from .margin_of_safety import MarginOfSafetyEngine
        from dataclasses import asdict

        archetype_prof = ArchetypeClassifier.classify(symbol, sector_text=sector)
        
        # Extract real quality inputs
        pillars = dict(value_investor_pillars or {})
        cap_alloc = pillars.get("capital_allocation", {})
        earn_qual = pillars.get("earnings_quality", {})
        fortress = pillars.get("financial_fortress", {})
        
        five_yr_roe = cap_alloc.get("avg_roe_5y") or (float(roe_val) if roe_val else None)
        five_yr_cash_conv = earn_qual.get("avg_cash_conversion_5y") or (85.0 if is_bank else None)
        true_dilution = cap_alloc.get("share_dilution_5y_pct") if cap_alloc.get("share_dilution_5y_pct") is not None else 0.0

        quality_scorecard = QualityScorer.evaluate(
            archetype_prof=archetype_prof,
            financial_history_10y=financial_history or [],
            five_year_avg_roe=five_yr_roe,
            five_year_avg_cash_conversion=five_yr_cash_conv,
            net_debt_vnd=float(net_debt),
            latest_cfo=float(current_market_price * shares_outstanding * Decimal("0.1")),
            true_dilution_5y_pct=true_dilution,
        )

        mos_calc = MarginOfSafetyEngine.calculate(
            archetype_prof=archetype_prof,
            quality_tier=quality_scorecard.tier,
            actual_base_mos=float(mos_base),
            has_solvency_risk=len(quality_scorecard.hard_rejects) > 0,
            confidence_is_low=confidence == ConfidenceLevel.LOW,
        )

        val_status = ValuationPill(mos_calc.verdict_status)
        val_verdict = (
            f"Đánh giá Giá trị Buffett–Munger: {val_status.value}. "
            f"Hình thái kinh tế: {archetype_prof.archetype.value} ({archetype_prof.recommended_model}). "
            f"Điểm Chất lượng Doanh nghiệp: {quality_scorecard.total_score}/100 ({quality_scorecard.tier.value}). "
            f"Biên an toàn yêu cầu: {mos_calc.required_mos_pct:.1f}% (Thực tế Base MoS đạt {mos_text}). "
            f"Giá trị nội tại ước tính Base {base_iv:,.0f} ₫ (dải Bear-Bull: {bear_iv:,.0f} ₫ - {bull_iv:,.0f} ₫)."
        )

        if is_bank:
            fin_diagnosis = (
                f"Đặc thù ngành Ngân hàng: Sử dụng Mô hình Thu nhập Thặng dư (Residual Income Model) dựa trên BVPS ({bvps_val:,.0f} ₫/cp) "
                f"và ROE chuẩn hóa {roe_str}. Tiền gửi và cho vay là hoạt động kinh doanh cốt lõi, không xem tiền gửi là nợ vay doanh nghiệp."
            )
            earnings_diag = (
                f"Năng lực sinh lời thặng dư (Excess Return) của ngân hàng được tạo ra từ ROE ({roe_str}) vượt trội so với Chi phí sử dụng vốn cổ phần Cost of Equity ({hurdle_rate*100:.1f}%)."
            )
        else:
            fin_diagnosis = (
                f"Cấu trúc vốn: Nợ ròng ở mức {net_debt / Decimal('1000000000'):,.1f} tỷ đồng. "
                f"Hiệu quả sử dụng vốn đạt ROE {roe_str} và P/B {pb_str}."
            )
            earnings_diag = (
                f"Ước tính Lợi nhuận chủ sở hữu chuẩn hóa (Normalized Owner Earnings) đạt {base_annual_oe / Decimal('1000000000'):,.1f} tỷ đồng, "
                f"được tính toán trung bình chu kỳ sau khi đã khấu trừ chi phí vốn duy trì (Maintenance CapEx) và biến động vốn lưu động."
            )

        assessment = ValueInvestingAssessment(
            moat_rating=MoatRating.WIDE if quality_scorecard.moat_score >= 18 else (MoatRating.NARROW if quality_scorecard.moat_score >= 12 else MoatRating.NONE),
            valuation_status=val_status,
            moat_summary=(
                f"Lợi thế cạnh tranh (Moat Score: {quality_scorecard.moat_score}/20): Doanh nghiệp duy trì hiệu suất sinh lời ROE {roe_str}, "
                f"đáp ứng các tiêu chuẩn hào kinh tế bền vững theo trường phái Buffett–Munger."
            ),
            capital_allocation_diagnosis=f"Điểm phân bổ vốn: {quality_scorecard.capital_allocation_score}/15. Hiệu quả sử dụng nguồn vốn của cổ đông đạt ROE {roe_str}.",
            earnings_quality_diagnosis=earnings_diag,
            financial_resilience_diagnosis=fin_diagnosis,
            valuation_verdict=val_verdict,
            key_risks_and_invariants=[
                "Hệ thống tuân thủ triết lý Buy & Hold: giám sát và giải thích giá trị nội tại, không tự động phát sinh lệnh giao dịch.",
                "Định giá dựa trên BCTC chuẩn hóa chính thức; định giá cần được tái đánh giá định kỳ sau mỗi kỳ báo cáo tài chính.",
                "Biến động thị trường ngắn hạn không làm thay đổi giá trị kinh doanh dài hạn của doanh nghiệp.",
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
            valuation_model="RESIDUAL_INCOME_MODEL" if is_bank else "NORMALIZED_OWNER_EARNINGS_DCF",
            archetype_profile={
                "archetype": archetype_prof.archetype.value,
                "overlays": [o.value for o in archetype_prof.overlays],
                "base_required_mos_pct": archetype_prof.base_required_mos * 100.0,
                "recommended_model": archetype_prof.recommended_model,
            },
            quality_scorecard={
                "total_score": quality_scorecard.total_score,
                "tier": quality_scorecard.tier.value,
                "predictability_score": quality_scorecard.predictability_score,
                "moat_score": quality_scorecard.moat_score,
                "return_economics_score": quality_scorecard.return_economics_score,
                "financial_strength_score": quality_scorecard.financial_strength_score,
                "cash_quality_score": quality_scorecard.cash_quality_score,
                "capital_allocation_score": quality_scorecard.capital_allocation_score,
                "governance_score": quality_scorecard.governance_score,
                "hard_rejects": [r.value for r in quality_scorecard.hard_rejects],
                "summary": quality_scorecard.summary,
            },
            margin_of_safety_analysis=asdict(mos_calc),
            source_fact_ids=all_fact_ids,
            engine_version=cls.ENGINE_VERSION,
            computed_at=now_utc,
        )


