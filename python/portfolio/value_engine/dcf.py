"""
Owner Earnings Discounted Cash Flow (DCF) Model (QVE-111, QVE-121, QVE-130).

Two-Stage Growth Model:
  Stage 1 (Years 1 to N): Explicit growth of Owner Earnings discounted at WACC / Hurdle Rate.
  Terminal Value (Gordon Growth): OwnerEarnings_{N+1} / (DiscountRate - TerminalGrowth).
  Enterprise Value = PV(Stage 1) + PV(Terminal Value).
  Equity Value = Enterprise Value - Net Debt (Total Debt - Cash & Short-term Investments).
  Intrinsic Value Per Share = Equity Value / Shares Outstanding.
"""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional
from .models import ScenarioType, ValuationScenario


class DCFValuationModel:
    @staticmethod
    def calculate_scenario(
        base_owner_earnings: Decimal,
        shares_outstanding: Decimal,
        net_debt: Decimal,
        scenario_type: ScenarioType,
        discount_rate: Decimal,  # e.g., Decimal("0.11") for 11%
        growth_rate: Decimal,  # e.g., Decimal("0.12") for 12%
        growth_years: int = 5,
        terminal_growth: Decimal = Decimal("0.035"),  # 3.5%
        current_market_price: Optional[Decimal] = None,
    ) -> ValuationScenario:
        if discount_rate <= terminal_growth:
            raise ValueError(f"Discount rate ({discount_rate}) must be strictly greater than terminal growth ({terminal_growth})")
        if shares_outstanding <= Decimal("0"):
            raise ValueError("Shares outstanding must be positive")

        projected_cfs: List[Decimal] = []
        pv_stage1 = Decimal("0")
        current_oe = base_owner_earnings

        # Stage 1: Explicit projection
        for yr in range(1, growth_years + 1):
            current_oe = current_oe * (Decimal("1") + growth_rate)
            projected_cfs.append(current_oe)
            discount_factor = (Decimal("1") + discount_rate) ** yr
            pv_stage1 += current_oe / discount_factor

        # Terminal Value
        terminal_oe = current_oe * (Decimal("1") + terminal_growth)
        terminal_val = terminal_oe / (discount_rate - terminal_growth)
        pv_terminal_val = terminal_val / ((Decimal("1") + discount_rate) ** growth_years)

        # Enterprise & Equity Value
        enterprise_val = pv_stage1 + pv_terminal_val
        equity_val = enterprise_val - net_debt
        intrinsic_per_share = equity_val / shares_outstanding

        # Margin of Safety % = (Intrinsic Value - Market Price) / Intrinsic Value * 100%
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
            equity_value=equity_val,
            intrinsic_value_per_share=intrinsic_per_share,
            margin_of_safety_pct=mos_pct,
        )
