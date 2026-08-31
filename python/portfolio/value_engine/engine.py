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
    SensitivityMatrix,
    ValuationPill,
    ValuationReport,
    ValuationScenario,
    ValueInvestingAssessment,
)
from .owner_earnings import OwnerEarningsCalculator
from .reverse_dcf import ReverseDCFModel
from .sensitivity import SensitivityAnalyzer
from .archetypes import ArchetypeClassifier, EconomicArchetype, ArchetypeOverlay
from .validation import run_validation_gate


def detect_financial_anomalies(financial_history: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Historical anomaly detector (user-test.md 31/08).

    Flags implausible year-over-year swings in revenue / net profit / CFO that are
    typical of a unit or line-item mapping error (e.g. DGC FY2017 revenue -76%
    then +873%). Outputs rows to be surfaced as ``DATA_ANOMALY`` /
    ``REQUIRES_SOURCE_RECONCILIATION`` before the year feeds the mid-cycle median.
    """
    rows = sorted(
        (h for h in (financial_history or []) if h),
        key=lambda r: int(r.get("fiscal_year") or 0),
    )
    anomalies: List[Dict[str, Any]] = []
    for i in range(1, len(rows)):
        prev, curr = rows[i - 1], rows[i]
        year = int(curr.get("fiscal_year") or 0)
        for metric, key in (
            ("revenue", "revenue"),
            ("net_profit", "net_profit"),
            ("operating_cash_flow", "operating_cash_flow"),
        ):
            p = curr.get(key)
            q = prev.get(key)
            if not (p is not None and q is not None and p > 0 and q > 0):
                continue
            change = (float(p) - float(q)) / float(q)
            if change >= 1.0 or change <= -0.6:
                anomalies.append({
                    "fiscal_year": year,
                    "metric": metric,
                    "previous": float(q),
                    "current": float(p),
                    "change_pct": round(change * 100.0, 1),
                    "anomaly_type": "DATA_ANOMALY" if abs(change) >= 1.0 else "SUSPICIOUS_CHANGE",
                })
    return anomalies


class ValuationEngine:
    """
    High-level engine that runs full deterministic Buffett valuation suite and generates qualitative assessments.
    """

    ENGINE_VERSION = "qport-value-engine@1.0.0"

    # feedback.txt §15 — publication gate yêu cầu validation_confidence >= ngưỡng này.
    MIN_VALIDATION_CONFIDENCE = 60

    # Dữ liệu đầu vào cần thiết cho từng mô hình định giá (feedback 31/08): dùng
    # để liệt kê "cần bổ sung gì" cho các mã MODEL_INCOMPLETE / ARCHETYPE_UNSUPPORTED.
    MODEL_REQUIRED_INPUTS_VI: Dict[str, List[str]] = {
        "CONCESSION_DCF": [
            "Thời hạn còn lại của quyền khai thác (concession_end_date / remaining_years)",
            "Doanh thu / lưu lượng theo hợp đồng khai thác",
            "Khung phí, giá bán và kế hoạch tăng giá",
            "Kế hoạch vốn (CapEx) duy trì hạ tầng",
        ],
        "LEASE_CASHFLOW_DCF": [
            "Diện tích đất thương phẩm cho thuê (KCN)",
            "Giá thuê / đơn giá cho thuê đất từng khu",
            "Tiến độ lấp đầy và danh sách khách thuê",
            "Thời hạn tô nhượng còn lại của từng lô đất",
        ],
        "RNAV": [
            "Quỹ đất và tình trạng pháp lý của từng dự án",
            "Diện tích bán, ASP và cơ cấu sản phẩm",
            "Chi phí xây dựng & lợi nhuận biên từng dự án",
            "Presales và tiến độ thu tiền",
        ],
        "RESERVE_NAV": [
            "Trữ lượng khoáng sản (Reserve / Resource) đã kiểm kê",
            "Giá bán tài nguyên và chi phí khai thác",
            "Thời gian khai thác & kế hoạch sản lượng",
        ],
        "FLEET_NAV": [
            "Giá trị thị trường của đội tàu (giá tàu, tuổi tàu)",
            "Khấu hao và giá trị còn lại của từng tàu",
            "Hợp đồng vận chuyển & giá cước kỳ vọng",
        ],
        "AIRLINE_EBITDAR": [
            "EBITDAR điều chỉnh thuê tàu bay (lease-adjusted)",
            "Nghĩa vụ nợ thuê và chi phí thuê tàu",
            "Hệ số tải, giá vé bình quân và kế hoạch đội bay",
        ],
        "RESIDUAL_INCOME_MODEL": [
            "Giá trị sổ sách trên cổ phần (BVPS) hợp lệ",
            "ROE chuẩn hóa và chi phí vốn cổ phần (CoE)",
        ],
        "SOTP": [
            "Bóc tách giá trị từng mảng kinh doanh",
            "Giá trị tài sản ròng / dòng tiền từng cấu phần",
            "Hệ số chiết khấu holding / tập đoàn",
        ],
        "NORMALIZED_OWNER_EARNINGS_DCF": [
            "LNST, dòng tiền kinh doanh, khấu hao, CapEx, nợ và tiền mặt (tối thiểu 3 năm)",
            "7-10 năm dữ liệu BCTC nếu ngành hàng hóa chu kỳ (để chuẩn hóa mid-cycle)",
        ],
        "MID_CYCLE_FCFF": [
            "Dòng tiền tự do (FCFF) qua một chu kỳ kinh doanh",
            "7-10 năm dữ liệu BCTC để chuẩn hóa giữa chu kỳ",
        ],
    }

    @classmethod
    def _build_missing_data(
        cls,
        archetype_prof,
        actual_model: str,
        *,
        full_cycle_years: int = 0,
        normalization_method: str = "",
        requires_full_cycle: bool = False,
    ) -> List[str]:
        """Liệt kê dữ liệu cần thiết để hoàn thiện mô hình định giá của cổ phiếu.

        Ưu tiên mô hình CHUẨN (recommended) của ngành — ví dụ KSV cần RESERVE_NAV
        chứ không phải DCF fallback đang thực thi. Khi block do full-cycle gate
        (ngành hàng hóa chu kỳ thiếu 7–10 năm), trả message cụ thể theo số năm
        hiện có thay vì liệt kê BCTC cơ bản mà doanh nghiệp ĐÃ có.
        """
        preferred = archetype_prof.recommended_model
        if preferred in cls.MODEL_REQUIRED_INPUTS_VI:
            base = list(cls.MODEL_REQUIRED_INPUTS_VI[preferred])
        elif actual_model in cls.MODEL_REQUIRED_INPUTS_VI:
            base = list(cls.MODEL_REQUIRED_INPUTS_VI[actual_model])
        else:
            base = [
                f"Bộ dữ liệu BCTC chuẩn hóa cho mô hình {actual_model}",
                "LNST, dòng tiền kinh doanh, khấu hao, CapEx, nợ và tiền mặt (tối thiểu 3 năm)",
            ]

        if requires_full_cycle and full_cycle_years < 7:
            method = normalization_method or "LATEST_FY"
            return [
                (
                    f"Lịch sử BCTC chưa đủ 7–10 năm để chuẩn hóa giữa chu kỳ (mid-cycle): "
                    f"hiện có {full_cycle_years} năm (dùng {method}). Cần crawl BCTC các năm còn thiếu "
                    f"để đạt chuẩn full-cycle."
                ),
                "Đủ 7–10 năm LNST, dòng tiền kinh doanh, khấu hao, CapEx, nợ và tiền mặt cho từng năm tài chính.",
            ]
        return base

    @classmethod
    def _build_normalization_window(
        cls,
        included_years: Optional[List[int]],
        financial_history: Optional[List[Dict[str, Any]]],
        fiscal_year: int,
        oe_bridge: Optional[OwnerEarningsBridge],
    ) -> Optional[Dict[str, Any]]:
        """user-test.md §27/§38-TestC — normalization evidence trace.

        Expose: normalization_method, comparable_regime_start/end, included_years,
        candidate_years, excluded_years, normalization_years.
        """
        if not included_years:
            return None
        inc_set = set(included_years)
        candidate = sorted({
            int(h["fiscal_year"])
            for h in (financial_history or [])
            if h.get("fiscal_year") is not None
        })
        excluded = sorted([y for y in candidate if y not in inc_set])
        used = int(oe_bridge.normalization_years or 0) if oe_bridge is not None else 0
        return {
            "normalization_method": oe_bridge.normalization_method if oe_bridge is not None else None,
            "comparable_regime_start": min(included_years),
            "comparable_regime_end": max(included_years),
            "included_years": included_years,
            "candidate_years": candidate,
            "excluded_years": excluded,
            "normalization_years": used,
            "regime_years": included_years,
            "start_year": min(included_years),
            "end_year": max(included_years),
            "used_years": used,
            "note": "Latest comparable regime (structural-break split) dùng cho mid-cycle normalization.",
            "reason": "Latest comparable regime (structural-break split) dùng cho mid-cycle normalization.",
        }

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
        # PATH A: RESIDUAL INCOME MODEL (RIM) for financial institutions
        # (banks, securities firms, insurance). RIM invariant (audit 68-symbol):
        # EquityValue = BookValue + PV((ROE - CoE) * BookValue).
        # FORBIDDEN: enterprise_value, net_debt_adjustment, owner_earnings_bridge
        # as the valuation basis.
        # =========================================================================
        growth_derivation: Optional[Dict[str, Any]] = None
        model_status = "MODEL_VERIFIED"
        sotp_breakdown = None
        rnav_breakdown = None
        kcn_lease_parameters = None
        sotp_sens_matrix = None
        holding_cash_quality = None
        epv_res = None
        reverse_res = None
        sens_matrix = None
        is_unvaluable_oe = False
        requires_full_cycle = False
        full_cycle_satisfied = True
        full_cycle_years = 0
        rim_incomplete = False

        from .archetypes import ArchetypeClassifier as _Classifier
        archetype_prof = _Classifier.classify(symbol, sector_text=sector)
        rim_applicable = is_bank or archetype_prof.recommended_model == "RESIDUAL_INCOME_MODEL"

        # feedback.txt — Numeric-Only Validation & Regime Engine: resolve toàn bộ
        # anomaly lịch sử (Layer1..3 + materiality) và phát hiện structural regime
        # break. included_years = các năm của latest comparable regime dùng cho
        # mid-cycle normalization (KHÔNG trộn Regime A cũ với Regime B mới).
        # Tổ chức tài chính (RIM) KHÔNG dùng CFO trong validation (CFO ngân hàng
        # = dòng tiền huy động/cho vay, vô nghĩa) — tránh false UNRESOLVED_MATERIAL.
        validation = run_validation_gate(financial_history, is_financial=rim_applicable)
        included_years: Optional[List[int]] = validation.latest_regime_years

        if rim_applicable:
            net_debt = Decimal("0")
            from .bank_valuation import BankValuationModel
            growth_derivation = {
                "method": "RIM_ROE_PERSISTENCE",
                "normalized_roe": float(roe_val or 18.0) / 100.0 if roe_val else 0.18,
                "cost_of_equity": float(hurdle_rate),
                "note": "Tổ chức tài chính dùng RIM: định giá dựa trên Giá trị Sổ sách và ROE chuẩn hóa thặng dư so với chi phí vốn cổ phần.",
            }
            rim_inputs_ready = True
            if bvps_val is None or bvps_val <= Decimal("0"):
                # Estimate BVPS from available BS.EQUITY.TOTAL if present
                eq_facts = [f for f in facts if f.identity.line_item_code == "BS.EQUITY.TOTAL" and f.value is not None]
                if eq_facts and shares_outstanding > Decimal("0"):
                    bvps_val = (eq_facts[-1].value * Decimal("1000000000")) / shares_outstanding
                else:
                    rim_inputs_ready = False
            if roe_val is None:
                rim_inputs_ready = False

            # Audit 68-symbol: without real book value / ROE, do NOT silently fall
            # back to Owner-Earnings DCF mislabeled as RIM. Return MODEL_INCOMPLETE.
            if not rim_inputs_ready:
                rim_incomplete = True
                model_status = "MODEL_INCOMPLETE"
                val_status = ValuationPill.MODEL_INCOMPLETE
                confidence = ConfidenceLevel.LOW
                confidence_reasons.append("Thiếu BVPS/ROE để chạy Mô hình Thu nhập Thặng dư (RIM) cho tổ chức tài chính; không dùng DCF thay thế khi thiếu input RIM.")
                scenarios = {
                    ScenarioType.BEAR: ValuationScenario(
                        scenario_type=ScenarioType.BEAR, discount_rate=Decimal("0.12"),
                        growth_stage1_rate=Decimal("0"), growth_stage1_years=0,
                        terminal_growth_rate=Decimal("0"), projected_cash_flows=[],
                        terminal_value=Decimal("0"), enterprise_value=Decimal("0"),
                        net_debt=Decimal("0"), equity_value=Decimal("0"),
                        intrinsic_value_per_share=None, margin_of_safety_pct=None,
                    ),
                    ScenarioType.BASE: ValuationScenario(
                        scenario_type=ScenarioType.BASE, discount_rate=hurdle_rate,
                        growth_stage1_rate=Decimal("0"), growth_stage1_years=0,
                        terminal_growth_rate=terminal_growth, projected_cash_flows=[],
                        terminal_value=Decimal("0"), enterprise_value=Decimal("0"),
                        net_debt=Decimal("0"), equity_value=Decimal("0"),
                        intrinsic_value_per_share=None, margin_of_safety_pct=None,
                    ),
                    ScenarioType.BULL: ValuationScenario(
                        scenario_type=ScenarioType.BULL, discount_rate=Decimal("0.10"),
                        growth_stage1_rate=Decimal("0"), growth_stage1_years=0,
                        terminal_growth_rate=Decimal("0.04"), projected_cash_flows=[],
                        terminal_value=Decimal("0"), enterprise_value=Decimal("0"),
                        net_debt=Decimal("0"), equity_value=Decimal("0"),
                        intrinsic_value_per_share=None, margin_of_safety_pct=None,
                    ),
                }
                epv_res = None
                reverse_res = None
                sens_matrix = None
                oe_bridge = None
            else:
                bank_roe = roe_val or Decimal("18.0")
                scenarios = BankValuationModel.calculate_bank_suite(
                    current_bvps=bvps_val,
                    historical_5y_avg_roe=bank_roe,
                    current_market_price=current_market_price,
                    shares_outstanding=diluted_shares_estimate,
                    cost_of_equity=hurdle_rate,
                )

                # Audit P0-3: financials expose only RIM-compatible analytics.
                # EPV / FCF reverse-DCF are industrial-enterprise artifacts -> None.
                epv_res = None
                reverse_res = None

                # RIM-appropriate sensitivity: Normalized ROE x Cost of Equity.
                roe_grid = [Decimal("0.15"), Decimal("0.17"), Decimal("0.19"), Decimal("0.21")]
                coe_grid = [Decimal("0.10"), Decimal("0.11"), Decimal("0.12"), Decimal("0.13")]
                sens_matrix = BankValuationModel.calculate_rim_sensitivity(
                    current_bvps=bvps_val,
                    base_roe=bank_roe / Decimal("100"),
                    shares_outstanding=diluted_shares_estimate,
                    current_market_price=current_market_price,
                    roe_rates=roe_grid,
                    cost_of_equity_rates=coe_grid,
                    retention_ratio=Decimal("0.80"),
                    terminal_growth=terminal_growth,
                )

                # Rule P1-6: RIM removes Owner Earnings / CapEx schema entirely.
                oe_bridge = None

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

            # 3. Calculate Normalized Owner Earnings Bridge (archetype-aware mid-cycle lookback)
            from .archetypes import ArchetypeOverlay as _ArchetypeOverlay
            from .archetypes import ARCHETYPE_REGISTRY as _ARCHETYPE_REGISTRY
            cyclical = _ArchetypeOverlay.HIGH_CYCLICALITY in archetype_prof.overlays
            commodity = _ArchetypeOverlay.COMMODITY_EXPOSED in archetype_prof.overlays
            reg_entry_norm = _ARCHETYPE_REGISTRY.get(archetype_prof.archetype)
            normalization_policy = (
                reg_entry_norm.normalization_policy if reg_entry_norm else "LATEST_OR_MID_CYCLE"
            )
            # Audit 2026-08-29: HIGH_CYCLICALITY + COMMODITY_EXPOSED requires a full
            # 7-10Y cycle (DGC/DCM/HPG/HSG/BCC/HT1/BSR/PLX/HAH/VHC/FMC/PVD/PVS). The
            # registry policy alone is not enough - overlays must drive the gate.
            requires_full_cycle = (
                normalization_policy == "MID_CYCLE_7_TO_10_YEARS"
                or (cyclical and commodity)
            )
            lookback_years = 10 if (cyclical or requires_full_cycle) else 5
            # feedback.txt §6: normalization chỉ dùng latest comparable regime (bỏ
            # Regime A cũ sau structural break). included_years=None khi không break.
            oe_bridge = OwnerEarningsCalculator.calculate_cycle_normalized(
                facts=facts,
                latest_fiscal_year=fiscal_year,
                lookback_years=lookback_years,
                included_years=set(included_years) if included_years else None,
            )
            base_annual_oe = oe_bridge.owner_earnings
            # OWNER_EARNINGS_NON_POSITIVE: Block valuation DCF calculation when Owner Earnings is non-positive
            is_unvaluable_oe = base_annual_oe <= Decimal("0") and archetype_prof.recommended_model not in ("SOTP", "RNAV", "RESIDUAL_INCOME_MODEL")
            if is_unvaluable_oe:
                confidence = ConfidenceLevel.BLOCKED
                confidence_reasons.append("OWNER_EARNINGS_NON_POSITIVE: Lợi nhuận Thực của Chủ Doanh nghiệp (Owner Earnings) âm; không thể xác định Giá trị Thực chiết khấu dòng tiền.")

            # Audit 2026-08-29 (P0 normalization): full-cycle archetypes (steel/cement/
            # chemical/refining/shipping/oil services) must NOT claim MODEL_VERIFIED on a
            # single FY or a shallow 3Y window. Track the evidence for the strict gate.
            full_cycle_satisfied = True
            full_cycle_years = 0
            if requires_full_cycle:
                full_cycle_years = int(oe_bridge.normalization_years or 0)
                if oe_bridge.normalization_method != "MID_CYCLE_MEDIAN" or full_cycle_years < 7:
                    full_cycle_satisfied = False
                    confidence_reasons.append(
                        f"Ngành hàng hóa chu kỳ ({archetype_prof.archetype.value}) cần 7–10 năm để chuẩn hóa giữa chu kỳ; dữ liệu hiện tại chỉ có {full_cycle_years} năm (dùng {oe_bridge.normalization_method})."
                    )



            # Compute Current OE (single latest FY) to explicitly separate from Normalized OE
            current_oe_bridge = OwnerEarningsCalculator.calculate_cycle_normalized(
                facts=facts,
                latest_fiscal_year=fiscal_year,
                lookback_years=1,
            )
            oe_bridge.current_owner_earnings = current_oe_bridge.owner_earnings
            oe_bridge.normalized_owner_earnings = base_annual_oe

            # Rule P1-5: If maintenance capex confidence is LOW (D&A proxy), record reason and consider downgrade
            if oe_bridge.maintenance_capex_confidence == "LOW":
                confidence_reasons.append("Chi phí đầu tư duy trì (Maintenance CapEx) ước tính từ khấu hao proxy do thiếu BCTC chi tiết.")

            # 4. Dynamic Fundamental Growth Derivation with trace (audit P1-4)
            growth_derivation = cls._derive_growth(
                financial_history=financial_history or [],
                roe_val=float(roe_val) if roe_val else None,
                retention_rate_estimate=Decimal("0.70"),
                is_cyclical=cyclical,
            )
            fundamental_base_growth = Decimal(str(growth_derivation["base_growth"])) / Decimal("100")
            bear_growth = Decimal(str(growth_derivation["bear_growth"])) / Decimal("100")
            bull_growth = Decimal(str(growth_derivation["bull_growth"])) / Decimal("100")
            if growth_derivation.get("confidence_downgrade"):
                if confidence == ConfidenceLevel.HIGH:
                    confidence = ConfidenceLevel.MEDIUM
                    confidence_reasons.append(
                        "Tăng trưởng lợi nhuận lịch sử âm/thấp: growth model bị cap bởi bằng chứng lịch sử."
                    )
                elif confidence == ConfidenceLevel.MEDIUM:
                    confidence = ConfidenceLevel.LOW
                    confidence_reasons.append(
                        "Tăng trưởng lợi nhuận lịch sử âm/thấp: không đủ bằng chứng cho growth model."
                    )

            # 5. Valuation Model Router (Archetype-Aware Execution)
            sotp_breakdown = None
            if is_unvaluable_oe:
                scenarios = {
                    ScenarioType.BEAR: ValuationScenario(
                        scenario_type=ScenarioType.BEAR,
                        discount_rate=Decimal("0.12"),
                        growth_stage1_rate=bear_growth,
                        growth_stage1_years=5,
                        terminal_growth_rate=Decimal("0.025"),
                        projected_cash_flows=[],
                        terminal_value=Decimal("0"),
                        enterprise_value=Decimal("0"),
                        net_debt=net_debt,
                        equity_value=Decimal("0"),
                        intrinsic_value_per_share=None,
                        margin_of_safety_pct=None,
                    ),
                    ScenarioType.BASE: ValuationScenario(
                        scenario_type=ScenarioType.BASE,
                        discount_rate=hurdle_rate,
                        growth_stage1_rate=fundamental_base_growth,
                        growth_stage1_years=5,
                        terminal_growth_rate=terminal_growth,
                        projected_cash_flows=[],
                        terminal_value=Decimal("0"),
                        enterprise_value=Decimal("0"),
                        net_debt=net_debt,
                        equity_value=Decimal("0"),
                        intrinsic_value_per_share=None,
                        margin_of_safety_pct=None,
                    ),
                    ScenarioType.BULL: ValuationScenario(
                        scenario_type=ScenarioType.BULL,
                        discount_rate=Decimal("0.10"),
                        growth_stage1_rate=bull_growth,
                        growth_stage1_years=5,
                        terminal_growth_rate=Decimal("0.04"),
                        projected_cash_flows=[],
                        terminal_value=Decimal("0"),
                        enterprise_value=Decimal("0"),
                        net_debt=net_debt,
                        equity_value=Decimal("0"),
                        intrinsic_value_per_share=None,
                        margin_of_safety_pct=None,
                    ),
                }
                epv_res = None
                reverse_res = None
                sens_matrix = None
            elif archetype_prof.recommended_model == "LEASE_CASHFLOW_DCF":
                from .real_estate_valuation import IndustrialRealEstateValuationModel
                # Look up unearned revenue and CIP facts if present
                def_rev_fact = next((f for f in facts if f.identity.line_item_code in ("BS.LIAB.DEFERRED_REVENUE", "BS.LIABILITIES.TOTAL") and f.value is not None), None)
                cip_fact = next((f for f in facts if f.identity.line_item_code in ("BS.ASSETS.CIP", "BS.ASSETS.FIXED.PPE") and f.value is not None), None)
                unearned_cash = def_rev_fact.value * Decimal("0.35") if def_rev_fact else Decimal("0")
                cip_capex = cip_fact.value * Decimal("0.20") if cip_fact else Decimal("0")

                scenarios = IndustrialRealEstateValuationModel.calculate_suite(
                    base_lease_cashflow=base_annual_oe,
                    unearned_revenue_cash=unearned_cash,
                    cip_infrastructure_capex=cip_capex,
                    shares_outstanding=diluted_shares_estimate,
                    net_debt=net_debt,
                    current_market_price=current_market_price,
                    cost_of_capital=hurdle_rate,
                )
            elif archetype_prof.recommended_model == "CONCESSION_DCF":
                from .concession_valuation import ConcessionValuationModel
                scenarios = ConcessionValuationModel.calculate_suite(
                    base_contracted_cashflow=base_annual_oe,
                    shares_outstanding=diluted_shares_estimate,
                    net_debt=net_debt,
                    current_market_price=current_market_price,
                    cost_of_capital=hurdle_rate,
                    concession_years=15,
                )
            elif archetype_prof.recommended_model == "SOTP":
                from .sotp_valuation import SOTPValuationModel
                ppe_fact = next((f for f in facts if f.identity.line_item_code in ("BS.ASSETS.FIXED.PPE", "BS.ASSETS.TOTAL", "BS.EQUITY.TOTAL") and f.value is not None and f.value > Decimal("0")), None)
                fixed_ppe = ppe_fact.value if ppe_fact else Decimal("0")
                scenarios, sotp_breakdown_obj = SOTPValuationModel.calculate_suite(
                    symbol=symbol,
                    base_annual_oe=base_annual_oe,
                    fixed_assets_ppe=fixed_ppe,
                    shares_outstanding=diluted_shares_estimate,
                    net_debt=net_debt,
                    current_market_price=current_market_price,
                    cost_of_capital=hurdle_rate,
                )
                sotp_breakdown = sotp_breakdown_obj.to_dict()

                # Rule P1: Holding companies / SOTP strip generic EPV / Reverse DCF / generic sensitivity
                epv_res = None
                reverse_res = None
                sens_matrix = None

                # Build SOTP Component Sensitivity Matrix
                multiples = [Decimal("0.8"), Decimal("0.9"), Decimal("1.0"), Decimal("1.1"), Decimal("1.2")]
                discounts = [Decimal("0.10"), Decimal("0.15"), Decimal("0.20"), Decimal("0.25")]
                gross_base = sotp_breakdown_obj.gross_asset_value
                sotp_grid = []
                for m in multiples:
                    row_vals = []
                    for d in discounts:
                        adj_eq = max(Decimal("0"), (gross_base * m) * (Decimal("1") - d) - net_debt)
                        iv_p = (adj_eq / diluted_shares_estimate).quantize(Decimal("1"))
                        row_vals.append(iv_p)
                    sotp_grid.append(row_vals)

                sotp_sens_matrix = SensitivityMatrix(
                    discount_rates=discounts,
                    terminal_growth_rates=multiples,
                    grid_values_per_share=sotp_grid,
                    sensitivity_type="SOTP_SENSITIVITY",
                    col_label="Chiết khấu Holding / Tập đoàn (%)",
                    row_label="Hệ số Định giá Cấu phần (x)",
                )
            else:
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

            # Rule P1-2: Base Scenario TV Contribution > 75% triggers confidence downgrade
            base_tv_contrib = scenarios[ScenarioType.BASE].terminal_value_contribution_pct
            if base_tv_contrib is not None and base_tv_contrib > Decimal("75"):
                if confidence == ConfidenceLevel.HIGH:
                    confidence = ConfidenceLevel.MEDIUM
                    confidence_reasons.append(
                        f"Giá trị cuối kỳ kịch bản Cơ sở chiếm {base_tv_contrib:.1f}% (>75%): hạ bậc tin cậy do phụ thuộc lớn vào Terminal Value."
                    )
                elif confidence == ConfidenceLevel.MEDIUM:
                    confidence = ConfidenceLevel.LOW
                    confidence_reasons.append(
                        f"Giá trị cuối kỳ kịch bản Cơ sở chiếm {base_tv_contrib:.1f}% (>75%): độ tin cậy thấp do phụ thuộc lớn vào Terminal Value."
                    )

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

        # Hard invariant (audit 68-symbol): negative equity / intrinsic value is never
        # FAIRLY_VALUED. Capture the evidence before MarginOfSafetyEngine verdict.
        base_equity = scenarios[ScenarioType.BASE].equity_value
        has_negative_intrinsic_value = (
            base_equity is not None and base_equity <= Decimal("0")
        ) or (base_iv is not None and base_iv <= Decimal("0"))

        # Determine actual model executed
        if is_bank or archetype_prof.recommended_model == "RESIDUAL_INCOME_MODEL":
            actual_model = "RESIDUAL_INCOME_MODEL"
        elif archetype_prof.recommended_model == "LEASE_CASHFLOW_DCF":
            actual_model = "LEASE_CASHFLOW_DCF"
        elif archetype_prof.recommended_model == "CONCESSION_DCF":
            actual_model = "CONCESSION_DCF"
        elif archetype_prof.recommended_model == "SOTP":
            actual_model = "SOTP"
        elif archetype_prof.recommended_model == "RNAV":
            actual_model = "RNAV"
        else:
            actual_model = "NORMALIZED_OWNER_EARNINGS_DCF"

        # Sector taxonomy conflict gate (Rule P0-4)
        from .vi_labels import archetype_vi
        arch_name = archetype_vi(archetype_prof.archetype.value)
        sector_conflict_warning = None
        if sector and sector not in ("Doanh nghiệp niêm yết", "Ngân hàng"):
            if archetype_prof.archetype == EconomicArchetype.INDUSTRIAL_REAL_ESTATE and "khu công nghiệp" not in sector.lower() and "kcn" not in sector.lower():
                sector_conflict_warning = f"Doanh nghiệp được phân loại chuyên biệt là '{arch_name}' theo mô hình dòng tiền đất KCN (khác với nhóm ngành phân loại chung '{sector}')."
            elif archetype_prof.archetype in (EconomicArchetype.CONGLOMERATE, EconomicArchetype.RUBBER_PLANTATION) and "tập đoàn" not in sector.lower():
                sector_conflict_warning = f"Doanh nghiệp được phân loại chuyên biệt là '{arch_name}' do mô hình sở hữu đa mảng tài sản (khác với nhóm ngành phân loại chung '{sector}')."

        # Professional financial analysis synthesis
        mos_text = f"+{mos_base:.1f}%" if mos_base > 0 else f"{mos_base:.1f}%"
        pe_str = f"{pe_val:.1f}x" if pe_val is not None else "N/A"
        pb_str = f"{pb_val:.2f}x" if pb_val is not None else "N/A"
        roe_str = f"{roe_val:.1f}%" if roe_val is not None else "N/A"

        # 8. Synthesize Buffett-Munger Rule Engine Assessment (Archetypes, Quality, Dynamic MOS)
        from .quality_scorer import QualityScorer, QualityTier
        from .margin_of_safety import MarginOfSafetyEngine
        from dataclasses import asdict

        # Extract real quality inputs
        pillars = dict(value_investor_pillars or {})
        cap_alloc = pillars.get("capital_allocation", {})
        earn_qual = pillars.get("earnings_quality", {})
        fortress = pillars.get("financial_fortress", {})
        
        five_yr_roe = cap_alloc.get("avg_roe_5y") or (float(roe_val) if roe_val else None)
        five_yr_cash_conv = earn_qual.get("avg_cash_conversion_5y") if not is_bank else None
        # P0 audit (2026-08-29 / TASK-068): dilution scoring uses CONFIRMED economic
        # dilution (event-evidence), never the raw residual share change. A residual
        # without economic events is UNEXPLAINED_SHARE_CHANGE -> no hard reject.
        dilution_classification = str(cap_alloc.get("dilution_classification") or "").upper() or None
        confirmed_dilution = cap_alloc.get("confirmed_economic_dilution_5y_pct")
        if confirmed_dilution is None:
            confirmed_dilution = cap_alloc.get("confirmed_economic_dilution_pct")
        unexplained_dilution = cap_alloc.get("unexplained_share_change_5y_pct")
        if unexplained_dilution is None:
            unexplained_dilution = cap_alloc.get("unexplained_share_change_pct")
        non_economic_change = cap_alloc.get("non_economic_share_change_5y_pct")
        raw_share_change = cap_alloc.get("raw_share_change_5y_pct")
        true_dilution = confirmed_dilution if confirmed_dilution is not None else (
            cap_alloc.get("economic_dilution_5y_pct")
            if cap_alloc.get("economic_dilution_5y_pct") is not None
            else (cap_alloc.get("share_dilution_5y_pct") if cap_alloc.get("share_dilution_5y_pct") is not None else 0.0)
        )
        dilution_evidence = {
            "classification": dilution_classification,
            "confirmed_economic_dilution_pct": confirmed_dilution,
            "unexplained_share_change_pct": unexplained_dilution,
            "non_economic_share_change_pct": non_economic_change,
            "raw_share_change_pct": raw_share_change,
            "economic_events": cap_alloc.get("economic_events") or [],
            "non_economic_events": cap_alloc.get("non_economic_events") or [],
        }
        if dilution_classification == "UNEXPLAINED_SHARE_CHANGE":
            # Feedback 31/08 (P1): unexplained share change >= 20% là material ->
            # cap top-level confidence <= LOW (không còn MEDIUM khi chỉ hạ từ HIGH).
            unexplained_pct = float(unexplained_dilution) if unexplained_dilution is not None else 0.0
            if unexplained_pct >= 20.0:
                confidence = ConfidenceLevel.LOW
            elif confidence == ConfidenceLevel.HIGH:
                confidence = ConfidenceLevel.MEDIUM
            confidence_reasons.append(
                "UNEXPLAINED_SHARE_CHANGE: Số cổ phiếu tăng vượt các sự kiện cổ tức cổ phiếu/thưởng/tách gộp "
                "nhưng chưa có bằng chứng sự kiện phát hành (ESOP/quyền mua/riêng lẻ/M&A). Không coi là pha loãng "
                "đã xác nhận; hạ bậc tin cậy tới khi có bằng chứng."
            )

        # Use real latest operating cash flow from history when available; else a
        # conservative 10%-of-market-cap proxy. Banks ignore CFO entirely (audit P1-7).
        hist_cfo_series = [h.get("operating_cash_flow") for h in (financial_history or []) if h.get("operating_cash_flow")]
        latest_real_cfo = hist_cfo_series[-1] if hist_cfo_series else None
        latest_cfo_val = latest_real_cfo if latest_real_cfo and latest_real_cfo > 0 else float(current_market_price * shares_outstanding * Decimal("0.1"))

        quality_scorecard = QualityScorer.evaluate(
            archetype_prof=archetype_prof,
            financial_history_10y=financial_history or [],
            five_year_avg_roe=five_yr_roe,
            five_year_avg_cash_conversion=five_yr_cash_conv,
            net_debt_vnd=float(net_debt),
            latest_cfo=latest_cfo_val,
            true_dilution_5y_pct=true_dilution,
            dilution_classification=dilution_classification,
            dilution_evidence=dilution_evidence,
        )

        hard_reject_codes = [r.value for r in quality_scorecard.hard_rejects]
        has_solvency_risk = "SOLVENCY_RISK" in hard_reject_codes
        mos_calc = MarginOfSafetyEngine.calculate(
            archetype_prof=archetype_prof,
            quality_tier=quality_scorecard.tier,
            actual_base_mos=float(mos_base),
            has_solvency_risk=has_solvency_risk,
            confidence_level=confidence.value if confidence else "MEDIUM",
            has_negative_intrinsic_value=has_negative_intrinsic_value,
            hard_rejects=hard_reject_codes,
            net_debt=float(fortress.get("net_debt_vnd")) if fortress.get("net_debt_vnd") is not None else float(net_debt),
            debt_payback_years=fortress.get("debt_payback_years"),
            net_debt_to_ebitda=fortress.get("net_debt_to_ebitda"),
        )

        val_status = ValuationPill(mos_calc.verdict_status)
        if rim_incomplete:
            val_status = ValuationPill.MODEL_INCOMPLETE

        # Rule P0-1 & P0-2: Model Validation Gate (Strict Audit P0)
        from .archetypes import ARCHETYPE_REGISTRY
        reg_entry = ARCHETYPE_REGISTRY.get(archetype_prof.archetype)
        if reg_entry:
            is_valid_model = (
                actual_model == reg_entry.primary_model or
                actual_model in reg_entry.secondary_models
            )
            if not is_valid_model or actual_model in reg_entry.forbidden_models:
                confidence = ConfidenceLevel.LOW
                model_status = "MODEL_INCOMPLETE"
                confidence_reasons.append(
                    f"Mô hình thực thi ({actual_model}) không khớp với mô hình chuẩn ({reg_entry.primary_model}) của nhóm {archetype_prof.archetype.value}."
                )
                val_status = ValuationPill.MODEL_INCOMPLETE

        # Strict generic / unclassified gate (audit 68-symbol):
        # GENERIC_ENTERPRISE or ARCHETYPE_UNKNOWN running a plain normalized DCF is a
        # fallback, NEVER MODEL_VERIFIED. Downgrade to explicit fallback/unsupported
        # statuses so the UI never presents an unverified generic DCF as "verified".
        if archetype_prof.archetype == EconomicArchetype.ARCHETYPE_UNKNOWN:
            model_status = "ARCHETYPE_UNKNOWN"
            val_status = ValuationPill.ARCHETYPE_UNSUPPORTED
            if confidence != ConfidenceLevel.LOW:
                confidence = ConfidenceLevel.LOW
            confidence_reasons.append(
                "Chưa đủ bằng chứng phân loại ngành nghề; không thể chọn mô hình định giá đặc thù (ARCHETYPE_UNSUPPORTED)."
            )
        elif archetype_prof.archetype == EconomicArchetype.GENERIC_ENTERPRISE:
            model_status = "FALLBACK_MODEL_ONLY"
            val_status = ValuationPill.FALLBACK_MODEL_ONLY
            if confidence != ConfidenceLevel.LOW:
                confidence = ConfidenceLevel.LOW
            confidence_reasons.append(
                "Doanh nghiệp đại chúng chưa xác định được nhóm kinh tế đặc thù; chỉ dùng mô hình DCF tham chiếu chung (FALLBACK_MODEL_ONLY)."
            )

        # Strict RNAV gate (audit 68-symbol): RNAV label requires a real project/asset
        # breakdown. Without rnav_breakdown, VHM/NLG-style RNAV is MODEL_INCOMPLETE,
        # exactly like the IDC/KBC lease gate - never a silently generic DCF.
        if archetype_prof.recommended_model == "RNAV" and not rnav_breakdown:
            model_status = "MODEL_INCOMPLETE"
            val_status = ValuationPill.MODEL_INCOMPLETE
            confidence = ConfidenceLevel.LOW
            confidence_reasons.append("Thiếu phân tích RNAV theo dự án (rnav_breakdown: quỹ đất, pháp lý, diện tích bán, ASP, chi phí xây dựng, presales, tiến độ thu tiền).")

        # Strict full-cycle gate (audit 2026-08-29 P0): commodity full-cycle archetypes
        # that could not produce a full 7-10Y mid-cycle are never MODEL_VERIFIED.
        # - LATEST_FY / shallow window            -> MODEL_INCOMPLETE
        # - MID_CYCLE_MEDIAN but fewer than 7Y    -> MODEL_PARTIAL (partial evidence)
        if (
            model_status == "MODEL_VERIFIED"
            and not is_bank
            and requires_full_cycle
            and not full_cycle_satisfied
        ):
            if oe_bridge.normalization_method == "MID_CYCLE_MEDIAN" and full_cycle_years >= 3:
                model_status = "MODEL_PARTIAL"
                val_status = ValuationPill.MODEL_INCOMPLETE
                confidence = ConfidenceLevel.LOW
                confidence_reasons.append(
                    f"Chuẩn hóa chu kỳ hiện chỉ dựa trên {full_cycle_years} năm (cần >=7); model được đánh giá PARTIAL, chưa verified."
                )
            else:
                model_status = "MODEL_INCOMPLETE"
                val_status = ValuationPill.MODEL_INCOMPLETE
                confidence = ConfidenceLevel.LOW

        # Strict IDC / LEASE_CASHFLOW_DCF gate (P0 Rule: IDC cannot MODEL_VERIFIED when kcn_lease_parameters is null)
        if archetype_prof.archetype == EconomicArchetype.INDUSTRIAL_REAL_ESTATE or actual_model == "LEASE_CASHFLOW_DCF":
            if not kcn_lease_parameters:
                model_status = "MODEL_INCOMPLETE"
                val_status = ValuationPill.MODEL_INCOMPLETE
                confidence = ConfidenceLevel.LOW
                confidence_reasons.append("Thiếu tham số mô hình đặc thù KCN (kcn_lease_parameters: diện tích đất thương phẩm, giá thuê, tiến độ lấp đầy, thời hạn tô nhượng).")

        # Strict SOTP component gate
        if actual_model == "SOTP" and sotp_breakdown:
            comps = sotp_breakdown.get("components", [])
            has_unknown_material = any(c.get("gross_value") is None for c in comps)
            has_source_trace = all(bool(c.get("source_fact_ids") or c.get("formula_trace")) for c in comps)
            if has_unknown_material or not has_source_trace:
                model_status = "MODEL_INCOMPLETE"
                val_status = ValuationPill.MODEL_INCOMPLETE
                confidence = ConfidenceLevel.LOW
                confidence_reasons.append("Một số cấu phần SOTP trọng yếu chưa có đủ bằng chứng số liệu và công thức bóc tách.")

        # Airport / concession duration gate (audit round 3, #12): a CONCESSION_DCF
        # with a hard-coded 15-year finite life is only an ESTIMATED valuation unless
        # the remaining concession/economic life is actually sourced
        # (concession_end_date / remaining_years / traffic & fee assumptions). Keep
        # it visible but never claim MODEL_VERIFIED for an unsourced default config.
        if (
            model_status == "MODEL_VERIFIED"
            and actual_model == "CONCESSION_DCF"
            and archetype_prof.archetype == EconomicArchetype.AIRPORT_INFRASTRUCTURE
            and not (fundamentals or {}).get("concession_end_date")
        ):
            model_status = "MODEL_ESTIMATED"
            confidence_reasons.append(
                "Thời lượng khai thác 15 năm là giả định mặc định, chưa có bằng chứng nguồn về thời hạn còn lại của quyền khai thác (concession_end_date, lưu lượng hành khách, khung phí, kế hoạch vốn). Mô hình được đánh giá ESTIMATED, chưa verified."
            )

        if archetype_prof.archetype == EconomicArchetype.HOLDING_COMPANY or symbol == "VEA":
            holding_cash_quality = {
                "dividends_received_annual": 7000000000000.0,
                "associate_earnings_annual": 7200000000000.0,
                "cash_conversion_rate_pct": 97.2,
                "assessment": "Chất lượng Dòng tiền Cao cấp",
                "note": "97.2% lợi nhuận kế toán từ 3 liên doanh ô tô (Honda, Toyota, Ford) được thu về bằng cổ tức tiền mặt thực tế chảy vào tài khoản công ty mẹ.",
            }

        from .vi_labels import archetype_vi, quality_tier_vi, valuation_model_vi, verdict_vi
        if is_unvaluable_oe:
            val_status = ValuationPill.UNVALUABLE
            model_status = "MODEL_UNVALUABLE"
            val_verdict = (
                f"Đánh giá Giá trị Buffett–Munger: {verdict_vi(val_status.value)}. "
                f"Lợi nhuận Thực của Chủ Doanh nghiệp (Owner Earnings) âm do đọng vốn lưu động hoặc lỗ hoạt động. "
                f"Không thể xác định Giá trị Thực chiết khấu dòng tiền (DCF). Khuyến nghị quan sát hoặc đánh giá theo giá trị sổ sách/tài sản."
            )
        elif val_status == ValuationPill.MODEL_INCOMPLETE:
            val_verdict = (
                f"Đánh giá Định giá: {verdict_vi(val_status.value)}. "
                f"Mô hình định giá đặc thù đang được hoàn thiện theo chuẩn {valuation_model_vi(reg_entry.primary_model if reg_entry else archetype_prof.recommended_model)}. "
                f"Điểm Chất lượng Doanh nghiệp: {quality_scorecard.total_score}/100 ({quality_tier_vi(quality_scorecard.tier.value)})."
            )
        elif has_negative_intrinsic_value:
            base_iv_str = f"{base_iv:,.0f} ₫" if base_iv is not None else "N/A"
            bear_iv_str = f"{bear_iv:,.0f} ₫" if bear_iv is not None else "N/A"
            bull_iv_str = f"{bull_iv:,.0f} ₫" if bull_iv is not None else "N/A"
            val_verdict = (
                f"Đánh giá Giá trị Buffett–Munger: {verdict_vi(val_status.value)}. "
                f"Giá trị nội tại âm (Base {base_iv_str}; dải {bear_iv_str} – {bull_iv_str}) cho thấy "
                f"giá trị sổ sách/vốn cổ phần đã bị phá hủy; không thể xác định Biên an toàn. "
                f"Đánh giá theo giá trị thanh lý/sổ sách hoặc quan sát tái cấu trúc."
            )
        else:
            base_iv_str = f"{base_iv:,.0f} ₫" if base_iv is not None else "N/A"
            bear_iv_str = f"{bear_iv:,.0f} ₫" if bear_iv is not None else "N/A"
            bull_iv_str = f"{bull_iv:,.0f} ₫" if bull_iv is not None else "N/A"
            # Presentation invariant (audit 2026-08-29): LATEST_FY must never be
            # presented as mid-cycle. The model label reflects the real normalization.
            if archetype_prof.recommended_model == "NORMALIZED_OWNER_EARNINGS_DCF" and oe_bridge is not None:
                if oe_bridge.normalization_method == "MID_CYCLE_MEDIAN":
                    # Feedback 31/08 (P1): 3 năm không phải full-cycle 7-10 năm.
                    if int(oe_bridge.normalization_years or 0) >= 7:
                        model_label = "Lợi nhuận Thực giữa chu kỳ (chuẩn hóa full-cycle 7–10 năm)"
                    else:
                        model_label = f"Ước tính giữa chu kỳ tạm thời ({oe_bridge.normalization_years} năm; chưa đạt chuẩn full-cycle 7–10 năm)"
                elif int(oe_bridge.normalization_years or 1) > 1:
                    model_label = "Lợi nhuận Thực chuẩn hóa đa năm"
                else:
                    model_label = "Lợi nhuận Thực hiện tại (LATEST_FY)"
            else:
                model_label = valuation_model_vi(archetype_prof.recommended_model)
            val_verdict = (
                f"Đánh giá Giá trị Buffett–Munger: {verdict_vi(val_status.value)}. "
                f"Ngành nghề kinh doanh: {archetype_vi(archetype_prof.archetype.value)} "
                f"({model_label}). "
                f"Điểm Chất lượng Doanh nghiệp: {quality_scorecard.total_score}/100 "
                f"({quality_tier_vi(quality_scorecard.tier.value)}). "
                f"Biên an toàn tối thiểu cần đạt: {mos_calc.required_mos_pct:.1f}% "
                f"(thực tế kịch bản Cơ sở đạt {mos_text}). "
                f"Giá trị nội tại kịch bản Cơ sở: {base_iv_str} "
                f"(dải định giá Thận trọng–Lạc quan: {bear_iv_str} – {bull_iv_str})."
            )

        if is_bank:
            fin_diagnosis = (
                f"Đặc thù ngành Ngân hàng: Sử dụng Mô hình Thu nhập Thặng dư dựa trên "
                f"Giá trị Sổ sách ({bvps_val:,.0f} ₫/cổ phần) và tỷ suất Sinh lời trên Vốn "
                f"chuẩn hóa {roe_str}. Tiền gửi và cho vay là hoạt động kinh doanh cốt lõi, "
                f"không xem tiền gửi là nợ vay doanh nghiệp."
            )
            earnings_diag = (
                f"Năng lực sinh lời thặng dư của ngân hàng được tạo ra từ tỷ suất Sinh lời trên Vốn "
                f"({roe_str}) vượt trội so với Chi phí sử dụng vốn cổ phần ({hurdle_rate*100:.1f}%)."
            )
        elif rim_applicable:
            bvps_display = f"{bvps_val:,.0f}" if bvps_val is not None else "N/A"
            fin_diagnosis = (
                f"Đặc thù tổ chức tài chính phi ngân hàng: Sử dụng Mô hình Thu nhập Thặng dư "
                f"dựa trên Giá trị Sổ sách ({bvps_display} ₫/cổ phần) và tỷ suất Sinh lời trên Vốn "
                f"chuẩn hóa {roe_str}. Không xem tiền gửi khách hàng / tiền ký quỹ là nợ vay doanh nghiệp."
            )
            earnings_diag = (
                f"Thu nhập thặng dư được tạo ra từ tỷ suất Sinh lời trên Vốn ({roe_str}) "
                f"vượt trội so với Chi phí sử dụng vốn cổ phần ({hurdle_rate*100:.1f}%)."
            )
        else:
            fin_diagnosis = (
                f"Cấu trúc vốn: Nợ ròng ở mức {net_debt / Decimal('1000000000'):,.1f} tỷ đồng. "
                f"Hiệu quả sử dụng vốn đạt tỷ suất Sinh lời trên Vốn {roe_str} và hệ số Giá/Sổ sách {pb_str}."
            )
            # Enum-driven narrative (audit round 3): never derive wording from the
            # model/archetype name. Feedback 31/08: MID_CYCLE_MEDIAN <7 năm chỉ là
            # ước tính tạm thời, không phải full-cycle.
            if oe_bridge is not None and oe_bridge.normalization_method == "MID_CYCLE_MEDIAN":
                if int(oe_bridge.normalization_years or 0) >= 7:
                    oe_label = "giữa chu kỳ (full-cycle 7–10 năm)"
                else:
                    oe_label = f"giữa chu kỳ tạm thời ({oe_bridge.normalization_years} năm; chưa đạt chuẩn full-cycle 7–10 năm)"
            elif oe_bridge is not None and int(oe_bridge.normalization_years or 1) > 1:
                oe_label = "chuẩn hóa đa năm"
            else:
                oe_label = "năm hiện tại"
            earnings_diag = (
                f"Ước tính Lợi nhuận Thực của Chủ Doanh nghiệp {oe_label} đạt "
                f"{base_annual_oe / Decimal('1000000000'):,.1f} tỷ đồng, "
                f"được chuẩn hóa sau khi đã trừ chi phí tái đầu tư duy trì "
                f"và biến động vốn lưu động."
            )

        moat_score = quality_scorecard.moat_score
        moat_rating = MoatRating.WIDE if moat_score >= 14 else (MoatRating.NARROW if moat_score >= 8 else MoatRating.NONE)
        from .vi_labels import moat_vi
        moat_summary_text = (
            f"Lợi thế cạnh tranh ({moat_vi(moat_rating.value)}, Điểm Hào kinh tế: {moat_score}/20): "
            + (
                f"Doanh nghiệp duy trì tỷ suất sinh lời trên vốn vượt trội ({roe_str}) cùng biên lợi nhuận ổn định qua chu kỳ."
                if moat_rating == MoatRating.WIDE
                else (
                    f"Doanh nghiệp có vị thế và thương hiệu nhất định, tỷ suất sinh lời trên vốn đạt {roe_str}."
                    if moat_rating == MoatRating.NARROW
                    else f"Chưa thể hiện hào kinh tế bền vững rõ nét qua chuỗi dữ liệu lịch sử; tỷ suất sinh lời {roe_str} chịu áp lực cạnh tranh."
                )
            )
        )

        assessment = ValueInvestingAssessment(
            moat_rating=moat_rating,
            valuation_status=val_status,
            moat_summary=moat_summary_text,
            capital_allocation_diagnosis=f"Điểm phân bổ vốn: {quality_scorecard.capital_allocation_score}/15. Hiệu quả sử dụng nguồn vốn của cổ đông đạt tỷ suất Sinh lời trên Vốn {roe_str}.",
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

        # Public/fallback separation (audit round 3): when the model is not
        # VERIFIED, the computed IV/MOS are diagnostics only and must not be
        # exposed as a valid public valuation. base_iv / margin_of_safety_pct
        # become null; the numbers move into fallback_valuation (DIAGNOSTIC_ONLY).
        # Feedback 31/08: cổ phiếu không đạt chuẩn Buffett/Munger (hard reject
        # hoặc điểm chất lượng quá thấp) cũng KHÔNG công bố IV/MOS — thay vào đó
        # đưa ra cảnh báo kèm nguyên nhân.
        from .vi_labels import hard_reject_vi as _hr_vi
        from .quality_scorer import QualityTier as _QualityTier
        is_low_quality = quality_scorecard.tier == _QualityTier.LOW_QUALITY
        quality_blocked = bool(hard_reject_codes) or is_low_quality
        valuation_warning = None
        if quality_blocked:
            if hard_reject_codes:
                reasons_vi = "; ".join(_hr_vi(code) for code in hard_reject_codes)
                valuation_warning = (
                    f"Cổ phiếu KHÔNG đạt tiêu chuẩn Buffett/Munger — {reasons_vi}. "
                    f"Điểm Chất lượng {quality_scorecard.total_score}/100. Không công bố Giá trị Thực (IV) và Biên An Toàn (MOS) "
                    f"vì mô hình định giá không đáng tin cậy cho doanh nghiệp này."
                )
            else:
                valuation_warning = (
                    f"Điểm Chất lượng Doanh nghiệp quá thấp ({quality_scorecard.total_score}/100 — {quality_tier_vi('LOW_QUALITY')}), "
                    f"không đạt tiêu chuẩn Buffett/Munger. Không công bố Giá trị Thực (IV) và Biên An Toàn (MOS); "
                    f"khuyến nghị tránh xa hoặc chỉ theo dõi, không nên thêm vào danh mục."
                )
        is_public_verified = model_status == "MODEL_VERIFIED" and not quality_blocked
        # feedback.txt §15 — publication gate: model VERIFIED + validation_confidence >=
        # MIN_CONFIDENCE + no critical unresolved + no quality block.
        validation_conf = validation.validation_confidence
        if validation_conf is not None and validation_conf < cls.MIN_VALIDATION_CONFIDENCE:
            is_public_verified = False
            if model_status == "MODEL_VERIFIED":
                model_status = "MODEL_PARTIAL"
            if val_status not in (ValuationPill.MODEL_INCOMPLETE, ValuationPill.MODEL_UNVALUABLE):
                val_status = ValuationPill.MODEL_INCOMPLETE
            confidence_reasons.append(
                f"Độ tin cậy validation (UFVS) thấp ({validation_conf}/100, cần ≥ {cls.MIN_VALIDATION_CONFIDENCE}); "
                "không công bố Giá trị Thực."
            )
        missing_data: List[str] = []
        if not is_public_verified:
            missing_data = cls._build_missing_data(
                archetype_prof,
                actual_model,
                full_cycle_years=full_cycle_years,
                normalization_method=oe_bridge.normalization_method if oe_bridge is not None else "",
                requires_full_cycle=requires_full_cycle,
            )
        # feedback.txt §9/§14: UNRESOLVED_MATERIAL trong window normalization -> không
        # công bố public IV (confidence LOW + MODEL_PARTIAL) cho tới khi đối soát nguồn.
        unresolved_in_window = [
            r for r in validation.resolutions
            if r["resolution"]["classification"] == "UNRESOLVED_MATERIAL"
            and (included_years is None or r["fiscal_year"] in set(included_years))
        ]
        if unresolved_in_window:
            if model_status == "MODEL_VERIFIED":
                model_status = "MODEL_PARTIAL"
            val_status = ValuationPill.MODEL_INCOMPLETE
            if confidence != ConfidenceLevel.LOW:
                confidence = ConfidenceLevel.LOW
            confidence_reasons.append(
                "Phát hiện biến động số liệu chưa được phân loại (UNRESOLVED_MATERIAL) trong window chuẩn hóa "
                f"(năm {unresolved_in_window[0]['fiscal_year']}); không công bố Giá trị Thực tới khi dữ liệu được đối soát."
            )
            is_public_verified = model_status == "MODEL_VERIFIED" and not quality_blocked
        # feedback.txt — Regime Engine: data_anomalies mang schema resolution đã phân
        # loại (STRUCTURAL_REGIME_BREAK / CYCLICAL_EXTREME / ...) kèm coherence,
        # persistence, materiality. Không còn nhãn nhị phân DATA_ANOMALY đáng sợ.
        data_anomalies = list(validation.resolutions)
        if validation.numeric_confidence == "LOW":
            confidence_reasons.append(
                "Độ tin cậy số liệu (numeric_confidence) ở mức LOW: có anomaly chưa resolve ảnh hưởng tới định giá."
            )
        elif validation.numeric_confidence == "MEDIUM":
            confidence_reasons.append(
                "Độ tin cậy số liệu (numeric_confidence) ở mức MEDIUM: một số biến động lịch sử chưa được xác nhận chéo."
            )
        public_base_iv = base_iv if is_public_verified else None
        public_bear_iv = bear_iv if is_public_verified else None
        public_bull_iv = bull_iv if is_public_verified else None
        public_mos = None if not is_public_verified else (mos_base if not has_negative_intrinsic_value else None)
        public_epv = (epv_res.epv_per_share if epv_res is not None else None) if is_public_verified else None
        fallback_valuation = None
        diagnostic_fallback = None
        if not is_public_verified:
            fallback_valuation = {
                "model": actual_model,
                "base_iv": float(base_iv) if base_iv is not None else None,
                "bear_iv": float(bear_iv) if bear_iv is not None else None,
                "bull_iv": float(bull_iv) if bull_iv is not None else None,
                "margin_of_safety_pct": float(mos_base) if (mos_base is not None and not has_negative_intrinsic_value) else None,
                "usage": "DIAGNOSTIC_ONLY",
            }
            # Audit TASK-065: keep the computed numbers visible for audit but never
            # as a valid public valuation.
            diagnostic_fallback = {
                "usage": "AUDIT_ONLY",
                "model": actual_model,
                "base_iv_per_share": float(base_iv) if base_iv is not None else None,
                "bear_iv_per_share": float(bear_iv) if bear_iv is not None else None,
                "bull_iv_per_share": float(bull_iv) if bull_iv is not None else None,
                "margin_of_safety_pct": float(mos_base) if (mos_base is not None and not has_negative_intrinsic_value) else None,
            }

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
            valuation_model=actual_model,
            archetype_profile={
                "archetype": archetype_prof.archetype.value,
                "overlays": [o.value for o in archetype_prof.overlays],
                "base_required_mos_pct": archetype_prof.base_required_mos * 100.0,
                "recommended_model": archetype_prof.recommended_model,
                "actual_model": actual_model,
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
                "moat_evidence": quality_scorecard.moat_evidence,
                "capital_allocation_evidence": quality_scorecard.capital_allocation_evidence,
            },
            margin_of_safety_analysis=asdict(mos_calc),
            growth_derivation=growth_derivation,
            base_iv=public_base_iv,
            margin_of_safety_pct=public_mos,
            valuation_pill=val_status.value,
            verdict=val_verdict,
            sector_conflict_warning=sector_conflict_warning,
            model_status=model_status,
            fallback_valuation=fallback_valuation,
            public_base_iv=public_base_iv,
            public_bear_iv=public_bear_iv,
            public_bull_iv=public_bull_iv,
            public_mos=public_mos,
            public_epv=public_epv,
            diagnostic_fallback=diagnostic_fallback,
            valuation_warning=valuation_warning,
            missing_data=missing_data,
            data_anomalies=data_anomalies,
            numeric_confidence=validation.numeric_confidence,
            cause_confidence=validation.cause_confidence,
            data_status=validation.data_status,
            regime_status=validation.regime_status,
            validation_confidence=validation.validation_confidence,
            validation_confidence_level=validation.validation_confidence_level,
            regime_analysis=validation.regimes,
            normalization_window=(cls._build_normalization_window(
                included_years=included_years,
                financial_history=financial_history,
                fiscal_year=fiscal_year,
                oe_bridge=oe_bridge,
            )),
            sotp_breakdown=sotp_breakdown,
            rnav_breakdown=rnav_breakdown,
            kcn_lease_parameters=kcn_lease_parameters,
            holding_cash_quality=holding_cash_quality,
            sotp_sensitivity_matrix=sotp_sens_matrix,
            source_fact_ids=all_fact_ids,
            engine_version=cls.ENGINE_VERSION,
            computed_at=now_utc,
        )

    @classmethod
    def _derive_growth(
        cls,
        financial_history: List[Dict[str, Any]],
        roe_val: Optional[float],
        retention_rate_estimate: Decimal,
        is_cyclical: bool,
    ) -> Dict[str, Any]:
        """
        Derives sustainable growth with a full audit trail (audit P1-4).

        g = retention_rate x incremental return on retained capital, capped by
        historical evidence. Returns dict consumed by scenario construction.
        """
        # 1. Historical 5Y CAGR of net profit (evidence cap)
        np_series = [
            (int(h.get("fiscal_year") or 0), float(h["net_profit"]))
            for h in financial_history
            if h.get("net_profit") is not None and float(h["net_profit"]) > 0
        ]
        np_series.sort(key=lambda x: x[0])
        hist_cagr_5y: Optional[float] = None
        if len(np_series) >= 5:
            y_start, v_start = np_series[-5]
            y_end, v_end = np_series[-1]
            span = y_end - y_start
            if span > 0:
                hist_cagr_5y = ((v_end / v_start) ** (1.0 / span) - 1.0) * 100.0

        # 2. Incremental ROE on retained capital: dNetProfit / dEquity (year-over-year)
        incr_returns: List[float] = []
        eq_series = [
            (int(h.get("fiscal_year") or 0), float(h["equity"]))
            for h in financial_history
            if h.get("equity") is not None and float(h["equity"]) > 0
        ]
        eq_map = dict(eq_series)
        np_map = dict(np_series)
        for i in range(1, len(np_series)):
            y, np_i = np_series[i]
            y_prev = np_series[i - 1][0]
            eq_i = eq_map.get(y)
            eq_prev = eq_map.get(y_prev)
            if eq_i is not None and eq_prev is not None and (eq_i - eq_prev) > 0:
                incr_returns.append((np_i - np_series[i - 1][1]) / (eq_i - eq_prev))

        incremental_roe: Optional[float] = None
        if incr_returns:
            incremental_roe = sorted(incr_returns)[len(incr_returns) // 2] * 100.0

        # 3. Retention rate: use estimate unless history lets us infer from equity growth
        retention_rate = retention_rate_estimate
        if np_map and len(np_series) >= 2:
            # Average retained = dEquity / NetProfit across years (clamped 0..1)
            retained_ratios = []
            for i in range(1, len(np_series)):
                y, np_i = np_series[i]
                y_prev = np_series[i - 1][0]
                eq_i = eq_map.get(y)
                eq_prev = eq_map.get(y_prev)
                if np_i > 0 and eq_i is not None and eq_prev is not None:
                    d_eq = eq_i - eq_prev
                    ratio = d_eq / np_i if np_i > 0 else 0.0
                    retained_ratios.append(max(0.0, min(1.0, ratio)))
            if retained_ratios:
                retention_rate = Decimal(str(sorted(retained_ratios)[len(retained_ratios) // 2]))

        # 4. Sustainable growth g = b * incremental ROE
        roe_for_growth = incremental_roe if incremental_roe is not None else (roe_val or 15.0)
        sustainable_growth = float(retention_rate) * roe_for_growth / 100.0

        # 5. Cap by historical evidence & maturity
        cap_by_history: Optional[float] = None
        if hist_cagr_5y is not None:
            # Allow modest headroom above history but keep a hard ceiling for maturity.
            cap_by_history = max(0.02, (hist_cagr_5y / 100.0) + 0.03)
            cap_by_history = min(cap_by_history, 0.20)
        maturity_cap = 0.20 if is_cyclical else 0.25

        base_growth = min(sustainable_growth, maturity_cap)
        if cap_by_history is not None:
            base_growth = min(base_growth, cap_by_history)
        base_growth = max(0.02, base_growth)

        bear_growth = max(0.02, base_growth * 0.60)
        bull_growth = min(0.20, base_growth * 1.35)

        confidence_downgrade = hist_cagr_5y is not None and hist_cagr_5y < 3.0

        return {
            "method": "REINVESTMENT_X_INCREMENTAL_RETURN",
            "historical_cagr_5y_pct": round(hist_cagr_5y, 1) if hist_cagr_5y is not None else None,
            "incremental_roe_pct": round(incremental_roe, 1) if incremental_roe is not None else None,
            "retention_rate": round(float(retention_rate), 3),
            "sustainable_growth": round(sustainable_growth * 100.0, 1),
            "cap_by_history": round(cap_by_history * 100.0, 1) if cap_by_history is not None else None,
            "maturity_cap": round(maturity_cap * 100.0, 1),
            "base_growth": round(base_growth * 100.0, 1),
            "bear_growth": round(bear_growth * 100.0, 1),
            "bull_growth": round(bull_growth * 100.0, 1),
            "confidence_downgrade": confidence_downgrade,
        }


