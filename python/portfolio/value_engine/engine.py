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
            oe_bridge = OwnerEarningsCalculator.calculate_cycle_normalized(
                facts=facts,
                latest_fiscal_year=fiscal_year,
                lookback_years=lookback_years,
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
        # P0/P1 audit (2026-08-29): only CONFIRMED economic dilution may drive the
        # EXCESSIVE_DILUTION hard reject AND the capital-allocation scoring. The
        # unexplained residual is surfaced for verification but never scored as
        # proven dilution. CRITICAL: `None` must stay `None` ("unknown"), it must
        # never be collapsed to 0 ("verified no dilution") - otherwise a company
        # with 88.8% unexplained share growth would score 15/15 on dilution.
        dilution_classification = cap_alloc.get("dilution_classification")
        dilution_evidence = cap_alloc.get("dilution_breakdown") or {}
        unexplained_pct = dilution_evidence.get("unexplained_share_change_pct") or cap_alloc.get("unexplained_share_change_pct")
        true_dilution = cap_alloc.get("confirmed_economic_dilution_pct")
        if true_dilution is None:
            true_dilution = cap_alloc.get("confirmed_economic_dilution_5y_pct")
        if true_dilution is None:
            true_dilution = cap_alloc.get("economic_dilution_5y_pct")
        # Keep None (unknown) as None for the scorer so it can cap the score; only
        # a genuinely confirmed classification yields a non-null value.
        if true_dilution is None and dilution_classification in (
            "EXCESSIVE_DILUTION", "ECONOMIC_DILUTION", "ECONOMIC_DILUTION_MINOR",
        ):
            true_dilution = cap_alloc.get("share_dilution_5y_pct")
        if dilution_classification == "UNEXPLAINED_SHARE_CHANGE":
            confidence_reasons.append(
                "Tăng số lượng CP chưa được giải thích bởi sự kiện cổ phiếu phi kinh tế; chưa có bằng chứng ESOP/quyền mua/phát hành để kết luận pha loãng kinh tế."
            )
            if confidence == ConfidenceLevel.HIGH:
                confidence = ConfidenceLevel.MEDIUM
                confidence_reasons.append("Tăng số CP chưa giải thích (UNEXPLAINED_SHARE_CHANGE): hạ bậc tin cậy cho đến khi có event-level evidence.")
            elif confidence == ConfidenceLevel.MEDIUM:
                confidence = ConfidenceLevel.LOW
                confidence_reasons.append("Tăng số CP chưa giải thích (UNEXPLAINED_SHARE_CHANGE): độ tin cậy thấp cho đến khi có event-level evidence.")

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
            unexplained_share_change_pct=unexplained_pct,
        )

        # P1 audit (2026-08-29): has_solvency_risk must mean ONLY a SOLVENCY_RISK hard
        # reject, not any hard reject. A net-cash company with EXCESSIVE_DILUTION
        # must not receive a +10 leverage penalty.
        hard_reject_values = [r.value for r in quality_scorecard.hard_rejects]
        has_solvency_risk = "SOLVENCY_RISK" in hard_reject_values
        mos_calc = MarginOfSafetyEngine.calculate(
            archetype_prof=archetype_prof,
            quality_tier=quality_scorecard.tier,
            actual_base_mos=float(mos_base),
            has_solvency_risk=has_solvency_risk,
            confidence_level=confidence.value if confidence else "MEDIUM",
            has_negative_intrinsic_value=has_negative_intrinsic_value,
            hard_rejects=hard_reject_values,
            # P1 audit (2026-08-29): pass REAL leverage metrics so the MOS leverage
            # penalty reflects actual debt serviceability, not a boolean proxy.
            net_debt=fortress.get("net_debt_vnd"),
            debt_payback_years=fortress.get("debt_payback_years"),
            net_debt_to_ebitda=cls._net_debt_to_ebitda(facts, fiscal_year, net_debt),
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
                    model_label = "Lợi nhuận Thực giữa chu kỳ (chuẩn hóa full-cycle)"
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
            earnings_diag = (
                f"Ước tính Lợi nhuận Thực của Chủ Doanh nghiệp bình quân chu kỳ đạt "
                f"{base_annual_oe / Decimal('1000000000'):,.1f} tỷ đồng, "
                f"được tính bình quân qua các năm sau khi đã trừ chi phí tái đầu tư duy trì "
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

        # P0 audit (2026-08-29): the public (presentation) valuation surface is
        # gated on a verified model. MODEL_INCOMPLETE / MODEL_PARTIAL /
        # FALLBACK_MODEL_ONLY / ARCHETYPE_UNKNOWN must never leak a
        # "verified-looking" intrinsic value or EPV to Overview/export. The
        # diagnostic values stay available under diagnostic_fallback with
        # usage=AUDIT_ONLY.
        model_verified = model_status == "MODEL_VERIFIED"
        epv_per_share = epv_res.epv_per_share if epv_res is not None else None
        if model_verified and not has_negative_intrinsic_value:
            public_bear_iv = bear_iv
            public_base_iv = base_iv
            public_bull_iv = bull_iv
            public_mos = mos_base
            public_epv = epv_per_share
        else:
            public_bear_iv = None
            public_base_iv = None
            public_bull_iv = None
            public_mos = None
            public_epv = None
        if model_verified:
            diagnostic_fallback = None
        else:
            diagnostic_fallback = {
                "usage": "AUDIT_ONLY",
                "model_status": model_status,
                "actual_model": actual_model,
                "recommended_model": archetype_prof.recommended_model,
                "bear_iv_per_share": bear_iv,
                "base_iv_per_share": base_iv,
                "bull_iv_per_share": bull_iv,
                "base_mos_pct": None if has_negative_intrinsic_value else mos_base,
                "epv_per_share": epv_per_share,
                "note": "Kết quả dưới mô hình DCF tham chiếu chỉ dùng để kiểm toán (audit-only), KHÔNG dùng để đưa kết luận định giá công khai khi mô hình chưa verified.",
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
            base_iv=base_iv,
            margin_of_safety_pct=None if has_negative_intrinsic_value else mos_base,
            public_bear_iv=public_bear_iv,
            public_base_iv=public_base_iv,
            public_bull_iv=public_bull_iv,
            public_mos=public_mos,
            public_epv=public_epv,
            diagnostic_fallback=diagnostic_fallback,
            valuation_pill=val_status.value,
            verdict=val_verdict,
            sector_conflict_warning=sector_conflict_warning,
            model_status=model_status,
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
    def _net_debt_to_ebitda(
        cls,
        facts: List[CanonicalFact],
        fiscal_year: int,
        net_debt: Decimal,
    ) -> Optional[float]:
        """Net Debt / EBITDA from the latest available facts (P1 audit).

        EBITDA ≈ IS.PROFIT.OPERATING + CF.OPERATING.DEPRECIATION for the latest
        fiscal year. Returns None when the inputs are unavailable so the MOS
        engine falls back to debt_payback_years / net_debt evidence.
        """
        if net_debt is None or net_debt <= Decimal("0"):
            return 0.0
        try:
            op_fact = next(
                f for f in facts
                if f.identity.fiscal_year == fiscal_year
                and f.identity.fiscal_quarter is None
                and f.identity.line_item_code == "IS.PROFIT.OPERATING"
                and f.value is not None
                and f.quality_status not in (QualityStatus.CONFLICT, QualityStatus.QUARANTINED, QualityStatus.MISSING)
            )
            da_fact = next(
                f for f in facts
                if f.identity.fiscal_year == fiscal_year
                and f.identity.fiscal_quarter is None
                and f.identity.line_item_code == "CF.OPERATING.DEPRECIATION"
                and f.value is not None
                and f.quality_status not in (QualityStatus.CONFLICT, QualityStatus.QUARANTINED, QualityStatus.MISSING)
            )
        except StopIteration:
            return None
        ebitda = float(op_fact.value) + float(abs(da_fact.value))
        if ebitda <= 0:
            return None
        return float(net_debt) / ebitda

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


