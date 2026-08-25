"""
Sensitivity Analysis Matrix (QVE-150).

Generates 2D table of Intrinsic Value Per Share varying Discount Rate vs Terminal Growth.
"""
from __future__ import annotations

from decimal import Decimal
from typing import List
from .dcf import DCFValuationModel
from .models import ScenarioType, SensitivityMatrix


class SensitivityAnalyzer:
    @staticmethod
    def build_matrix(
        base_owner_earnings: Decimal,
        shares_outstanding: Decimal,
        net_debt: Decimal,
        base_growth_rate: Decimal,
        discount_rates: List[Decimal],
        terminal_growth_rates: List[Decimal],
        growth_years: int = 5,
    ) -> SensitivityMatrix:
        grid: List[List[Decimal]] = []
        for g_term in terminal_growth_rates:
            row: List[Decimal] = []
            for r_disc in discount_rates:
                if r_disc <= g_term:
                    row.append(Decimal("0"))  # Invalid Gordon growth condition
                    continue
                scen = DCFValuationModel.calculate_scenario(
                    base_owner_earnings=base_owner_earnings,
                    shares_outstanding=shares_outstanding,
                    net_debt=net_debt,
                    scenario_type=ScenarioType.BASE,
                    discount_rate=r_disc,
                    growth_rate=base_growth_rate,
                    growth_years=growth_years,
                    terminal_growth=g_term,
                )
                row.append(round(scen.intrinsic_value_per_share, 0))
            grid.append(row)

        return SensitivityMatrix(
            discount_rates=discount_rates,
            terminal_growth_rates=terminal_growth_rates,
            grid_values_per_share=grid,
        )
