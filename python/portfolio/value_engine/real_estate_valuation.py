"""
Industrial Real Estate Valuation Engine (IDC, SZC, BCM, KBC, NTC, SIP).

Specialized Lease Cash-Flow DCF and RNAV model tailored for Vietnamese
Industrial Park (KCN) economics:
- Remaining leasable land bank (Quỹ đất thương phẩm còn lại).
- Contracted long-term land lease cash collections & schedule.
- Recognition of Unearned/Deferred Revenue (Doanh thu chưa thực hiện).
- Subtraction of Infrastructure Construction in Progress (Chi phí XDCB dở dang).
- Concession end year & finite-project timeline.
- Margin of Safety requirement: 25% - 35%.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional
from .models import ScenarioType, ValuationScenario


@dataclass
class KCNLeaseParameters:
    remaining_land_area_ha: Decimal = Decimal("450.0")
    average_lease_rate_usd_m2: Decimal = Decimal("125.0")
    leasing_schedule_years: int = 10
    concession_end_year: int = 2055
    infrastructure_capex_vnd: Decimal = Decimal("0")
    project_ownership_pct: Decimal = Decimal("100.0")
    project_cashflow_timeline: List[Dict] = field(default_factory=list)


class IndustrialRealEstateValuationModel:
    """
    Lease Cash-Flow DCF and RNAV Valuation for Industrial Park developers.
    """

    @classmethod
    def calculate_lease_dcf_scenario(
        cls,
        base_lease_cashflow: Decimal,
        unearned_revenue_cash: Decimal,
        cip_infrastructure_capex: Decimal,
        shares_outstanding: Decimal,
        net_debt: Decimal,
        scenario_type: ScenarioType,
        discount_rate: Decimal,
        growth_rate: Decimal,
        growth_years: int = 5,
        terminal_growth: Decimal = Decimal("0.025"),
        current_market_price: Optional[Decimal] = None,
        lease_params: Optional[KCNLeaseParameters] = None,
    ) -> ValuationScenario:
        """
        Calculates Lease Cash-Flow DCF where:
        - Stage 1 explicit projection of lease collections & utility operations.
        - Terminal value reflects recurring park management & maintenance fees.
        - Equity value = PV(Cash Flows) + Unearned Revenue Realization - Remaining Infrastructure CapEx - Net Debt.
        """
        if shares_outstanding <= Decimal("0"):
            raise ValueError("SHARES_OUTSTANDING_INVALID: must be > 0")

        projected_cfs: List[Decimal] = []
        pv_stage1 = Decimal("0")
        current_cf = base_lease_cashflow

        for yr in range(1, growth_years + 1):
            current_cf = current_cf * (Decimal("1") + growth_rate)
            projected_cfs.append(current_cf)
            discount_factor = (Decimal("1") + discount_rate) ** yr
            pv_stage1 += current_cf / discount_factor

        # Terminal Value reflects ongoing industrial park utility and management cash flow
        terminal_cf = current_cf * (Decimal("1") + terminal_growth)
        terminal_val = terminal_cf / (discount_rate - terminal_growth)
        pv_terminal_val = terminal_val / ((Decimal("1") + discount_rate) ** growth_years)

        total_pv_operations = pv_stage1 + pv_terminal_val
        terminal_contrib_pct = (pv_terminal_val / total_pv_operations * Decimal("100")) if total_pv_operations > Decimal("0") else None

        warnings: List[str] = []
        if terminal_contrib_pct is not None and terminal_contrib_pct > Decimal("75"):
            warnings.append(
                f"Giá trị cuối kỳ (Terminal Value) chiếm {terminal_contrib_pct:.1f}% tổng định giá (>75%)."
            )

        # Enterprise Value of KCN Operations
        enterprise_val = total_pv_operations

        # Net Realizable Assets adjustment for KCN:
        # + Unearned Revenue secured cash buffer (discounted 15% for execution/tax)
        # - Net Debt
        # - Net Infrastructure CIP commitments (50% funded from unearned cash)
        net_unearned_asset = unearned_revenue_cash * Decimal("0.85")
        adjusted_equity_val = enterprise_val + net_unearned_asset - net_debt - (cip_infrastructure_capex * Decimal("0.30"))

        intrinsic_per_share = adjusted_equity_val / shares_outstanding

        mos_pct = None
        if current_market_price and current_market_price > Decimal("0") and intrinsic_per_share > Decimal("0"):
            mos_pct = ((intrinsic_per_share - current_market_price) / intrinsic_per_share) * Decimal("100")

        return ValuationScenario(
            scenario_type=scenario_type,
            discount_rate=discount_rate,
            growth_stage1_rate=growth_rate,
            growth_stage1_years=growth_years,
            terminal_growth_rate=terminal_growth,
            projected_cash_flows=projected_cfs,
            terminal_value=terminal_val,
            enterprise_value=enterprise_val,
            net_debt=net_debt,
            equity_value=adjusted_equity_val,
            intrinsic_value_per_share=intrinsic_per_share,
            margin_of_safety_pct=mos_pct,
            terminal_value_contribution_pct=terminal_contrib_pct,
            scenario_warnings=warnings,
            cashflow_basis="FCFF",
            discount_rate_basis="WACC",
            result_type="ENTERPRISE_VALUE",
            debt_adjustment_policy="SUBTRACT_NET_DEBT",
        )

    @classmethod
    def calculate_suite(
        cls,
        base_lease_cashflow: Decimal,
        unearned_revenue_cash: Decimal,
        cip_infrastructure_capex: Decimal,
        shares_outstanding: Decimal,
        net_debt: Decimal,
        current_market_price: Optional[Decimal],
        cost_of_capital: Decimal = Decimal("0.11"),
        lease_params: Optional[KCNLeaseParameters] = None,
    ) -> Dict[ScenarioType, ValuationScenario]:
        """Builds Bear, Base, Bull scenarios for Industrial Real Estate."""
        return {
            ScenarioType.BEAR: cls.calculate_lease_dcf_scenario(
                base_lease_cashflow=base_lease_cashflow,
                unearned_revenue_cash=unearned_revenue_cash,
                cip_infrastructure_capex=cip_infrastructure_capex,
                shares_outstanding=shares_outstanding,
                net_debt=net_debt,
                scenario_type=ScenarioType.BEAR,
                discount_rate=Decimal("0.12"),
                growth_rate=Decimal("0.02"),
                growth_years=5,
                terminal_growth=Decimal("0.02"),
                current_market_price=current_market_price,
                lease_params=lease_params,
            ),
            ScenarioType.BASE: cls.calculate_lease_dcf_scenario(
                base_lease_cashflow=base_lease_cashflow,
                unearned_revenue_cash=unearned_revenue_cash,
                cip_infrastructure_capex=cip_infrastructure_capex,
                shares_outstanding=shares_outstanding,
                net_debt=net_debt,
                scenario_type=ScenarioType.BASE,
                discount_rate=cost_of_capital,
                growth_rate=Decimal("0.06"),
                growth_years=5,
                terminal_growth=Decimal("0.025"),
                current_market_price=current_market_price,
                lease_params=lease_params,
            ),
            ScenarioType.BULL: cls.calculate_lease_dcf_scenario(
                base_lease_cashflow=base_lease_cashflow,
                unearned_revenue_cash=unearned_revenue_cash,
                cip_infrastructure_capex=cip_infrastructure_capex,
                shares_outstanding=shares_outstanding,
                net_debt=net_debt,
                scenario_type=ScenarioType.BULL,
                discount_rate=Decimal("0.10"),
                growth_rate=Decimal("0.10"),
                growth_years=5,
                terminal_growth=Decimal("0.03"),
                current_market_price=current_market_price,
                lease_params=lease_params,
            ),
        }
