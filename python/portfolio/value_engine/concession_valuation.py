"""
Concession and Finite-Life Infrastructure Valuation Model.

Tailored for Vietnamese Regulated Energy, BOT, Gas & Water Utilities (GAS, POW, BOTs):
- Regulated tariffs and take-or-pay contracted cash flows.
- Finite concession lifetime (15 - 25 years).
- Zero terminal perpetuity (Terminal Value = 0 or residual salvage value).
- Margin of Safety requirement: 20% - 30%.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Optional
from .models import ScenarioType, ValuationScenario


class ConcessionValuationModel:
    """
    Finite-Life Concession Cash-Flow DCF.
    """

    @classmethod
    def calculate_concession_scenario(
        cls,
        base_contracted_cashflow: Decimal,
        shares_outstanding: Decimal,
        net_debt: Decimal,
        scenario_type: ScenarioType,
        discount_rate: Decimal,
        growth_rate: Decimal,
        concession_years: int = 15,
        salvage_value: Decimal = Decimal("0"),
        current_market_price: Optional[Decimal] = None,
    ) -> ValuationScenario:
        if shares_outstanding <= Decimal("0"):
            raise ValueError("SHARES_OUTSTANDING_INVALID: must be > 0")

        projected_cfs: List[Decimal] = []
        pv_cfs = Decimal("0")
        current_cf = base_contracted_cashflow

        for yr in range(1, concession_years + 1):
            current_cf = current_cf * (Decimal("1") + growth_rate)
            projected_cfs.append(current_cf)
            discount_factor = (Decimal("1") + discount_rate) ** yr
            pv_cfs += current_cf / discount_factor

        # Finite Concession Invariant: Terminal Value is 0 or salvage value only (no perpetuity)
        pv_salvage = salvage_value / ((Decimal("1") + discount_rate) ** concession_years)
        enterprise_val = pv_cfs + pv_salvage
        equity_val = enterprise_val - net_debt
        intrinsic_per_share = equity_val / shares_outstanding
        from .share_basis import calculate_canonical_mos
        mos_pct = calculate_canonical_mos(
            market_price=current_market_price,
            intrinsic_value_per_share=intrinsic_per_share,
        )

        return ValuationScenario(
            scenario_type=scenario_type,
            discount_rate=discount_rate,
            growth_stage1_rate=growth_rate,
            growth_stage1_years=concession_years,
            terminal_growth_rate=Decimal("0"),
            projected_cash_flows=projected_cfs[:5],  # expose first 5 years for summary
            terminal_value=salvage_value,
            enterprise_value=enterprise_val,
            net_debt=net_debt,
            equity_value=equity_val,
            intrinsic_value_per_share=intrinsic_per_share,
            margin_of_safety_pct=mos_pct,
            terminal_value_contribution_pct=Decimal("0"),
            scenario_warnings=[
                f"Định giá theo vòng đời hợp đồng khai thác hữu hạn ({concession_years} năm): Giá trị cuối kỳ vĩnh viễn (TV) = 0."
            ],
            cashflow_basis="FCFF",
            discount_rate_basis="WACC",
            result_type="ENTERPRISE_VALUE",
            debt_adjustment_policy="SUBTRACT_NET_DEBT",
        )

    @classmethod
    def calculate_suite(
        cls,
        base_contracted_cashflow: Decimal,
        shares_outstanding: Decimal,
        net_debt: Decimal,
        current_market_price: Optional[Decimal],
        cost_of_capital: Decimal = Decimal("0.105"),
        concession_years: int = 15,
    ) -> Dict[ScenarioType, ValuationScenario]:
        return {
            ScenarioType.BEAR: cls.calculate_concession_scenario(
                base_contracted_cashflow=base_contracted_cashflow,
                shares_outstanding=shares_outstanding,
                net_debt=net_debt,
                scenario_type=ScenarioType.BEAR,
                discount_rate=Decimal("0.115"),
                growth_rate=Decimal("0.01"),
                concession_years=concession_years,
                current_market_price=current_market_price,
            ),
            ScenarioType.BASE: cls.calculate_concession_scenario(
                base_contracted_cashflow=base_contracted_cashflow,
                shares_outstanding=shares_outstanding,
                net_debt=net_debt,
                scenario_type=ScenarioType.BASE,
                discount_rate=cost_of_capital,
                growth_rate=Decimal("0.035"),
                concession_years=concession_years,
                current_market_price=current_market_price,
            ),
            ScenarioType.BULL: cls.calculate_concession_scenario(
                base_contracted_cashflow=base_contracted_cashflow,
                shares_outstanding=shares_outstanding,
                net_debt=net_debt,
                scenario_type=ScenarioType.BULL,
                discount_rate=Decimal("0.095"),
                growth_rate=Decimal("0.055"),
                concession_years=concession_years,
                current_market_price=current_market_price,
            ),
        }
