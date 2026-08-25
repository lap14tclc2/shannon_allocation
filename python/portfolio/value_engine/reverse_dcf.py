"""
Reverse DCF / Implied Market Expectations Model (QVE-140).

Solves for the Stage 1 growth rate g such that DCF Intrinsic Value == Current Market Price.
Uses binary search for deterministic, fast root-finding.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
from .dcf import DCFValuationModel
from .models import ReverseDCFResult, ScenarioType


class ReverseDCFModel:
    @staticmethod
    def solve_implied_growth(
        base_owner_earnings: Decimal,
        shares_outstanding: Decimal,
        net_debt: Decimal,
        current_market_price: Decimal,
        discount_rate: Decimal = Decimal("0.11"),
        terminal_growth: Decimal = Decimal("0.035"),
        growth_years: int = 5,
        tolerance: Decimal = Decimal("100"),  # VND tolerance
        max_iterations: int = 60,
    ) -> ReverseDCFResult:
        if current_market_price <= Decimal("0"):
            raise ValueError("Current market price must be positive for Reverse DCF")

        # Binary search for growth rate between -50% and +150%
        low = Decimal("-0.50")
        high = Decimal("1.50")
        implied_g = Decimal("0.0")

        for _ in range(max_iterations):
            mid = (low + high) / Decimal("2")
            scenario = DCFValuationModel.calculate_scenario(
                base_owner_earnings=base_owner_earnings,
                shares_outstanding=shares_outstanding,
                net_debt=net_debt,
                scenario_type=ScenarioType.BASE,
                discount_rate=discount_rate,
                growth_rate=mid,
                growth_years=growth_years,
                terminal_growth=terminal_growth,
                current_market_price=current_market_price,
            )
            diff = scenario.intrinsic_value_per_share - current_market_price

            if abs(diff) <= tolerance:
                implied_g = mid
                break
            elif diff < Decimal("0"):
                low = mid
            else:
                high = mid
            implied_g = mid

        g_pct = implied_g * Decimal("100")
        if g_pct > Decimal("25"):
            verdict = f"Thị trường đang định giá mức tăng trưởng rất cao ({g_pct:.1f}%/năm trong {growth_years} năm tới)"
        elif g_pct > Decimal("10"):
            verdict = f"Thị trường đang định giá mức tăng trưởng vừa phải ({g_pct:.1f}%/năm trong {growth_years} năm tới)"
        elif g_pct >= Decimal("0"):
            verdict = f"Thị trường đang định giá mức tăng trưởng thận trọng ({g_pct:.1f}%/năm trong {growth_years} năm tới)"
        else:
            verdict = f"Thị trường đang bi quan, ngụ ý suy giảm lợi nhuận ({g_pct:.1f}%/năm)"

        return ReverseDCFResult(
            current_market_price=current_market_price,
            implied_stage1_growth_rate=implied_g,
            discount_rate_used=discount_rate,
            terminal_growth_used=terminal_growth,
            verdict=verdict,
        )
