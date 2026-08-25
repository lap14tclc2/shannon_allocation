"""
Earnings Power Value (EPV) Model (QVE-112).

Bruce Greenwald Zero-Growth Valuation:
  Normalized Operating Earnings (EBIT) * (1 - Tax Rate) = Adjusted NOPAT
  EPV Enterprise Value = Adjusted NOPAT / Cost of Capital (WACC)
  EPV Equity Value = EPV Enterprise Value - Net Debt (Total Debt - Excess Cash)
  EPV Per Share = EPV Equity Value / Shares Outstanding
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
from .models import EPVResult


class EPVValuationModel:
    @staticmethod
    def calculate(
        normalized_operating_earnings: Decimal,
        tax_rate: Decimal,
        cost_of_capital: Decimal,
        net_debt: Decimal,
        shares_outstanding: Decimal,
        reproduction_cost_assets: Optional[Decimal] = None,
        current_market_price: Optional[Decimal] = None,
    ) -> EPVResult:
        if cost_of_capital <= Decimal("0"):
            raise ValueError("Cost of capital must be positive")
        if shares_outstanding <= Decimal("0"):
            raise ValueError("Shares outstanding must be positive")

        nopat = normalized_operating_earnings * (Decimal("1") - tax_rate)
        epv_enterprise = nopat / cost_of_capital
        epv_equity = epv_enterprise - net_debt
        epv_per_share = epv_equity / shares_outstanding

        mos_pct = None
        if current_market_price and current_market_price > Decimal("0") and epv_per_share > Decimal("0"):
            mos_pct = ((epv_per_share - current_market_price) / epv_per_share) * Decimal("100")

        return EPVResult(
            normalized_operating_earnings=normalized_operating_earnings,
            tax_rate=tax_rate,
            nopat=nopat,
            cost_of_capital=cost_of_capital,
            reproduction_cost_assets=reproduction_cost_assets,
            epv_enterprise_value=epv_enterprise,
            net_debt=net_debt,
            epv_equity_value=epv_equity,
            epv_per_share=epv_per_share,
            margin_of_safety_pct=mos_pct,
        )
