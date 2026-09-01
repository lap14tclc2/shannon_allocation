"""
Bank Valuation Models (QVE-300): Residual Income Model (RIM), Justified P/B & Dividend Discount Model.

For Commercial Banks and Financial Institutions, customer deposits and interbank liabilities are
operational raw materials, not enterprise debt. Cash flow from operations reflects loan growth and
deposit volatility, not distributable cash flow. 

Standard Value Investing Banking Model:
1. Residual Income Model (RIM):
   V_0 = BVPS_0 + sum_{t=1..5} [ (ROE_t - r_e) * BVPS_{t-1} / (1 + r_e)^t ] + Terminal Residual Income
2. Justified P/B Check:
   Target P/B = (ROE - g) / (r_e - g)
   Intrinsic Value = Target P/B * BVPS_0
"""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Optional
from .models import ScenarioType, SensitivityMatrix, ValuationScenario


class BankValuationModel:
    """
    Dedicated Banking Valuation Engine implementing the Residual Income Model (RIM).
    """

    @classmethod
    def calculate_rim_sensitivity(
        cls,
        current_bvps: Decimal,
        base_roe: Decimal,  # e.g. Decimal("0.19") for 19%
        shares_outstanding: Decimal,
        current_market_price: Decimal,
        roe_rates: List[Decimal],
        cost_of_equity_rates: List[Decimal],
        retention_ratio: Decimal = Decimal("0.80"),
        terminal_growth: Decimal = Decimal("0.035"),
        growth_years: int = 5,
    ) -> SensitivityMatrix:
        """
        Bank-appropriate sensitivity: RIM intrinsic value across Normalized ROE (rows)
        and Cost of Equity (cols). NOT a generic Gordon DCF matrix (audit P0-3).
        """
        grid: List[List[Decimal]] = []
        for roe in roe_rates:
            row: List[Decimal] = []
            for coe in cost_of_equity_rates:
                if coe <= terminal_growth:
                    row.append(Decimal("0"))
                    continue
                scen = cls.calculate_rim_scenario(
                    current_bvps=current_bvps,
                    base_roe=roe,
                    cost_of_equity=coe,
                    retention_ratio=retention_ratio,
                    terminal_growth=terminal_growth,
                    shares_outstanding=shares_outstanding,
                    current_market_price=current_market_price,
                    scenario_type=ScenarioType.BASE,
                    growth_years=growth_years,
                )
                row.append(round(scen.intrinsic_value_per_share, 0))
            grid.append(row)

        return SensitivityMatrix(
            discount_rates=roe_rates,
            terminal_growth_rates=cost_of_equity_rates,
            grid_values_per_share=grid,
            sensitivity_type="RIM_ROE_COE",
            col_label="Tỷ suất Sinh lời trên Vốn (ROE)",
            row_label="Chi phí vốn cổ phần (CoE)",
        )

    @classmethod
    def calculate_rim_scenario(
        cls,
        current_bvps: Decimal,
        base_roe: Decimal,  # e.g. 0.18 for 18%
        cost_of_equity: Decimal,  # r_e e.g. 0.11 for 11%
        retention_ratio: Decimal,  # b e.g. 0.80 for 80% (20% payout)
        terminal_growth: Decimal,  # g e.g. 0.035 for 3.5%
        shares_outstanding: Decimal,
        current_market_price: Decimal,
        scenario_type: ScenarioType,
        growth_years: int = 5,
        target_terminal_roe: Optional[Decimal] = None,
    ) -> ValuationScenario:
        """
        Calculates Bank Intrinsic Value per share using 5-year explicit Residual Income + Terminal Value.
        """
        if current_bvps <= Decimal("0"):
            raise ValueError("BVPS_POSITIVE_REQUIRED: Bank valuation requires positive book value per share.")

        if target_terminal_roe is None:
            # Steady-state banking ROE reverts closer to COE + 2.5% (~14%)
            target_terminal_roe = min(Decimal("0.15"), max(cost_of_equity + Decimal("0.02"), base_roe * Decimal("0.75")))

        projected_excess_returns: List[Decimal] = []
        bvps_t = current_bvps
        pv_residual_income = Decimal("0")

        # Explicit stage 1 (5 years)
        for t in range(1, growth_years + 1):
            # Linearly fade ROE towards terminal ROE over 5 years if cyclical
            roe_t = base_roe + (target_terminal_roe - base_roe) * (Decimal(str(t - 1)) / Decimal(str(growth_years)))
            excess_return_t = (roe_t - cost_of_equity) * bvps_t  # Residual Income per share in VND
            projected_excess_returns.append(excess_return_t)

            discount_factor = (Decimal("1") + cost_of_equity) ** t
            pv_residual_income += excess_return_t / discount_factor

            # Book value compounds at retained earnings rate: BVPS_t = BVPS_{t-1} * (1 + b * ROE_t)
            bvps_t = bvps_t * (Decimal("1") + retention_ratio * roe_t)

        # Terminal Residual Income (Gordon Growth on Excess Return)
        # RI_{5+1} = (ROE_term - r_e) * BVPS_5
        terminal_ri = (target_terminal_roe - cost_of_equity) * bvps_t
        if cost_of_equity > terminal_growth and terminal_ri > Decimal("0"):
            terminal_val = terminal_ri / (cost_of_equity - terminal_growth)
            pv_terminal = terminal_val / ((Decimal("1") + cost_of_equity) ** growth_years)
        else:
            pv_terminal = Decimal("0")
            terminal_val = Decimal("0")

        intrinsic_value_per_share = current_bvps + pv_residual_income + pv_terminal
        # Ensure floor at 0.8x Tangible Book Value for solvent banks
        intrinsic_value_per_share = max(current_bvps * Decimal("0.80"), intrinsic_value_per_share)

        equity_val = intrinsic_value_per_share * shares_outstanding
        margin_of_safety = None
        if intrinsic_value_per_share > Decimal("0"):
            margin_of_safety = (
                (intrinsic_value_per_share - current_market_price) / intrinsic_value_per_share
            ) * Decimal("100")

        return ValuationScenario(
            scenario_type=scenario_type,
            discount_rate=cost_of_equity,
            growth_stage1_rate=base_roe * retention_ratio,
            growth_stage1_years=growth_years,
            terminal_growth_rate=terminal_growth,
            projected_cash_flows=projected_excess_returns,
            terminal_value=terminal_val,
            # RIM produces EQUITY value directly (book value + PV excess ROE).
            # Equity-specific naming: the discounted stream is presented as
            # present_value / equity_value; enterprise_value is kept equal only
            # for schema backward compatibility (audit round 3, #1/#8).
            enterprise_value=equity_val,
            net_debt=Decimal("0"),
            equity_value=equity_val,
            intrinsic_value_per_share=intrinsic_value_per_share,
            margin_of_safety_pct=margin_of_safety,
            cashflow_basis="RESIDUAL_INCOME",
            discount_rate_basis="COST_OF_EQUITY",
            result_type="EQUITY_VALUE",
            present_value=equity_val,
            residual_income_pv=pv_residual_income,
            terminal_residual_income_pv=pv_terminal,
            debt_adjustment_policy="NO_NET_DEBT_ADJUSTMENT",
        )

    @classmethod
    def calculate_bank_suite(
        cls,
        current_bvps: Decimal,
        historical_5y_avg_roe: Decimal,  # e.g. Decimal("19.3") for 19.3%
        current_market_price: Decimal,
        shares_outstanding: Decimal,
        cost_of_equity: Decimal = Decimal("0.115"),  # 11.5% COE
        dividend_payout_ratio: Decimal = Decimal("0.20"),  # 20% cash dividend, 80% retained
    ) -> Dict[ScenarioType, ValuationScenario]:
        """
        Builds 3 bank valuation scenarios (Bear, Base, Bull) based on long-term ROE persistence.
        """
        roe_dec = historical_5y_avg_roe / Decimal("100") if historical_5y_avg_roe > Decimal("1") else historical_5y_avg_roe
        retention = Decimal("1") - dividend_payout_ratio

        # Bear Scenario: ROE compresses to 14%, higher Cost of Equity (13%), lower terminal growth
        bear_roe = max(Decimal("0.12"), roe_dec * Decimal("0.75"))
        bear_scen = cls.calculate_rim_scenario(
            current_bvps=current_bvps,
            base_roe=bear_roe,
            cost_of_equity=Decimal("0.13"),
            retention_ratio=retention,
            terminal_growth=Decimal("0.025"),
            shares_outstanding=shares_outstanding,
            current_market_price=current_market_price,
            scenario_type=ScenarioType.BEAR,
            target_terminal_roe=Decimal("0.13"),
        )

        # Base Scenario: Normalized 5Y ROE, 11.5% Cost of Equity, 3.5% Terminal growth
        base_scen = cls.calculate_rim_scenario(
            current_bvps=current_bvps,
            base_roe=roe_dec,
            cost_of_equity=cost_of_equity,
            retention_ratio=retention,
            terminal_growth=Decimal("0.035"),
            shares_outstanding=shares_outstanding,
            current_market_price=current_market_price,
            scenario_type=ScenarioType.BASE,
            target_terminal_roe=min(Decimal("0.145"), max(Decimal("0.13"), roe_dec * Decimal("0.75"))),
        )

        # Bull Scenario: ROE expands / stays high (+10%), 10.5% Cost of Equity, 4.0% Terminal growth
        bull_roe = min(Decimal("0.24"), roe_dec * Decimal("1.10"))
        bull_scen = cls.calculate_rim_scenario(
            current_bvps=current_bvps,
            base_roe=bull_roe,
            cost_of_equity=Decimal("0.105"),
            retention_ratio=retention,
            terminal_growth=Decimal("0.040"),
            shares_outstanding=shares_outstanding,
            current_market_price=current_market_price,
            scenario_type=ScenarioType.BULL,
            target_terminal_roe=min(Decimal("0.165"), max(Decimal("0.14"), roe_dec * Decimal("0.85"))),
        )

        return {
            ScenarioType.BEAR: bear_scen,
            ScenarioType.BASE: base_scen,
            ScenarioType.BULL: bull_scen,
        }
