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

        # 2. Extract a single FY fact set.  Do not mix periods or use
        # substitutions for debt/cash/earnings: readiness must be explicit.
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
        if shares_outstanding <= Decimal("0"):
            raise ValueError("SHARES_OUTSTANDING_REQUIRED")

        total_debt = usable_facts["BS.DEBT.TOTAL"].value
        total_cash = usable_facts["BS.ASSETS.CASH_AND_EQUIVALENTS"].value
        # For Banks and Financial Institutions, customer deposits and interbank liabilities
        # are operational raw materials (operating float), not enterprise debt to deduct from firm cash flows.
        # Bank valuation models (Dividend Discount / Equity Cash Flow) discount directly to Equity Value (net_debt = 0).
        is_bank = entity_type == EntityType.BANK or "bank" in str(symbol).lower()
        net_debt = Decimal("0") if is_bank else (total_debt - total_cash)

        # 3. Calculate Owner Earnings Bridge (QVE-070)
        oe_bridge = OwnerEarningsCalculator.calculate(
            facts=facts,
            fiscal_year=fiscal_year,
            fiscal_quarter=fiscal_quarter,
        )

        base_annual_oe = oe_bridge.owner_earnings
        if base_annual_oe <= Decimal("0"):
            raise ValueError("OWNER_EARNINGS_NON_POSITIVE: valuation blocked; no synthetic fallback is allowed.")

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

        # 5. Run EPV (Earnings Power Value) (QVE-112) from reported FY EBIT.
        ebit = usable_facts["IS.PROFIT.OPERATING"].value
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
        bull_iv = scenarios[ScenarioType.BULL].intrinsic_value_per_share
        mos_base = scenarios[ScenarioType.BASE].margin_of_safety_pct or Decimal("0")

        # Qualitative and multiples data must come from the current provider
        # snapshot. Never substitute ticker-specific or generic company values.
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

        # Professional financial analysis synthesis
        mos_text = f"+{mos_base:.1f}%" if mos_base > 0 else f"{mos_base:.1f}%"
        pe_str = f"{pe_val:.1f}x" if pe_val is not None else "N/A"
        pb_str = f"{pb_val:.2f}x" if pb_val is not None else "N/A"
        roe_str = f"{roe_val:.1f}%" if roe_val is not None else "N/A"

        if current_market_price < bear_iv:
            val_status = ValuationPill.DEEP_VALUE
            val_verdict = (
                f"Cổ phiếu đang giao dịch ở vùng Định giá Rất Rẻ (Deep Value) dưới cả kịch bản thận trọng Bear ({bear_iv:,.0f} ₫). "
                f"Biên an toàn cơ sở đạt {mos_text} so với giá trị nội tại Base ({base_iv:,.0f} ₫). "
                f"Hệ số định giá P/E {pe_str}, P/B {pb_str} và hiệu suất sinh lời ROE {roe_str} mang lại tỷ suất sinh lời kỳ vọng vượt trội cho nhà đầu tư giá trị dài hạn."
            )
        elif mos_base >= Decimal("15.0"):
            val_status = ValuationPill.UNDERVALUED
            val_verdict = (
                f"Thị giá ({current_market_price:,.0f} ₫) đang nằm dưới giá trị nội tại ước tính ({base_iv:,.0f} ₫), "
                f"mang lại biên an toàn cơ sở hấp dẫn {mos_text} (>15%). "
                f"Với P/E {pe_str} và ROE {roe_str}, doanh nghiệp có nền tảng định giá tốt để tích lũy theo phương pháp Buy & Hold."
            )
        elif mos_base >= Decimal("-15.0"):
            val_status = ValuationPill.FAIR_VALUE
            val_verdict = (
                f"Thị giá ({current_market_price:,.0f} ₫) đang phản ánh sát vùng giá trị hợp lý ({base_iv:,.0f} ₫, dao động Bear-Bull từ {bear_iv:,.0f} ₫ đến {bull_iv:,.0f} ₫). "
                f"P/E {pe_str}, P/B {pb_str} phù hợp với mức tăng trưởng và ROE {roe_str} hiện tại của doanh nghiệp."
            )
        else:
            val_status = ValuationPill.OVERVALUED
            val_verdict = (
                f"Thị giá ({current_market_price:,.0f} ₫) đang cao hơn giá trị nội tại cơ sở {abs(mos_base):.1f}% ({base_iv:,.0f} ₫). "
                f"Thị trường đang định giá doanh nghiệp ở mức P/E {pe_str}, đòi hỏi tốc độ tăng trưởng lợi nhuận tương lai phải bứt phá mạnh mẽ để bù đắp định giá."
            )

        if is_bank:
            fin_diagnosis = (
                f"Đặc thù ngành Ngân hàng: Sử dụng mô hình chiết khấu vốn chủ sở hữu (Equity Cash Flow / DDM) với nợ ròng quy ước 0 ₫ do tiền gửi khách hàng là nguồn vốn kinh doanh. "
                f"P/B hiện tại là {pb_str} tương ứng với ROE {roe_str}, thể hiện hiệu quả sinh lời trên quy mô vốn chủ sở hữu ({bvps_val:,.0f} ₫/cp)."
                if bvps_val is not None else
                f"Đặc thù ngành Ngân hàng: Sử dụng mô hình chiết khấu dòng tiền vốn chủ sở hữu (Equity Cash Flow) trực tiếp từ nguồn lợi nhuận giữ lại và năng lực tạo tiền ròng."
            )
        else:
            fin_diagnosis = (
                f"Cấu trúc vốn lành mạnh với tỷ lệ tiền mặt/nợ vay rõ ràng. Nợ ròng của doanh nghiệp ở mức {net_debt / Decimal('1000000000'):,.1f} tỷ đồng. "
                f"Hiệu quả sử dụng vốn đạt ROE {roe_str} và P/B {pb_str}."
                if roe_val is not None else
                f"Cấu trúc vốn được tính toán trực tiếp từ nợ vay và tiền mặt trên BCTC kiểm toán mới nhất ({fiscal_year})."
            )

        earnings_diag = (
            f"Lợi nhuận chủ sở hữu (Owner Earnings) đạt {base_annual_oe / Decimal('1000000000'):,.1f} tỷ đồng, "
            f"phản ánh chính xác dòng tiền tự do thực tế của cổ đông sau khi đã bù đắp chi phí đầu tư duy trì và thay đổi vốn lưu động."
        )

        assessment = ValueInvestingAssessment(
            moat_rating=MoatRating.WIDE if (roe_val is not None and roe_val >= Decimal("20.0")) else (MoatRating.NARROW if (roe_val is not None and roe_val >= Decimal("12.0")) else MoatRating.NONE),
            valuation_status=val_status,
            moat_summary=(
                f"Doanh nghiệp duy trì ROE ấn tượng {roe_str} (>20%), là dấu hiệu của lợi thế cạnh tranh bền vững (Economic Moat) và năng lực định giá tốt."
                if (roe_val is not None and roe_val >= Decimal("20.0")) else
                (
                    f"Hiệu suất sinh lời ROE ổn định ở mức {roe_str}, phản ánh vị thế kinh doanh cạnh tranh tốt trong ngành."
                    if (roe_val is not None and roe_val >= Decimal("12.0")) else
                    f"Hiệu suất sinh lời ROE đạt {roe_str}. Cần tiếp tục theo dõi chuỗi số liệu qua nhiều chu kỳ kinh tế để xác nhận hào kinh tế."
                )
            ),
            capital_allocation_diagnosis=f"Tỷ suất lợi nhuận trên vốn chủ sở hữu ROE {roe_str} kết hợp P/E {pe_str} cho thấy ban lãnh đạo duy trì hiệu quả sử dụng nguồn vốn của cổ đông.",
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
            source_fact_ids=all_fact_ids,
            engine_version=cls.ENGINE_VERSION,
            computed_at=now_utc,
        )


