"""Service for calculating personal balance sheet metrics and available deployable capital."""

from __future__ import annotations

from portfolio.personal_finance.models import (
    CapitalDurabilityMetrics,
    PersonalBalanceSheetInput,
)


def calculate_capital_durability(
    input_data: PersonalBalanceSheetInput,
    portfolio_equity_value: float,
    deployable_portfolio_cash: float,
) -> CapitalDurabilityMetrics:
    """Calculate Net Worth, Survival Reserve, Opportunity Cash, and Available Long-Term Capital.

    Mandatory Invariant:
    Available Long-Term Capital = Deployable Cash + New Contributions + Reinvestable Dividends
                                  - Survival Reserve Target - Near-Term Liabilities
    Survival Reserve MUST NOT equal Buy Capital.
    Available Long-Term Capital MUST NOT be negative.
    """
    essential_burn = max(0.0, float(input_data.monthly_essential_spending))
    safe_assets = max(0.0, float(input_data.safe_liquid_assets))
    portfolio_cash = max(0.0, float(deployable_portfolio_cash))
    portfolio_equity = max(0.0, float(portfolio_equity_value))
    total_liabilities = max(
        0.0,
        float(input_data.near_term_liabilities)
        + float(input_data.consumer_debt)
        + float(input_data.personal_debt)
        + float(input_data.margin_debt),
    )

    # 1. Net Worth calculations
    net_worth = (safe_assets + portfolio_cash + portfolio_equity) - total_liabilities
    investable_net_worth = (portfolio_cash + portfolio_equity) - float(input_data.margin_debt)

    # 2. Survival Reserve calculations
    target_months = max(1.0, float(input_data.target_survival_months))
    reserve_target_amount = essential_burn * target_months

    if essential_burn > 0:
        survival_months = safe_assets / essential_burn
    else:
        survival_months = 999.0 if safe_assets > 0 else 0.0

    if essential_burn == 0 and safe_assets == 0:
        survival_reserve_status = "UNKNOWN"
    elif survival_months >= target_months:
        survival_reserve_status = "SAFE"
    elif survival_months >= target_months * 0.5:
        survival_reserve_status = "ATTENTION"
    else:
        survival_reserve_status = "UNSAFE"

    # 3. Near-Term Liabilities status
    near_term_due = max(0.0, float(input_data.near_term_liabilities))
    total_liquid = safe_assets + portfolio_cash
    if near_term_due == 0:
        near_term_status = "COVERED"
    elif total_liquid >= (reserve_target_amount + near_term_due):
        near_term_status = "COVERED"
    else:
        near_term_status = "UNCOVERED"


    # 4. Available Long-Term Capital calculation (Strict Invariant)
    # Total available liquid assets (safe liquid + portfolio cash) minus reserve target and debt/liabilities
    total_liquid = safe_assets + portfolio_cash
    required_reservations = reserve_target_amount + near_term_due + float(input_data.margin_debt)

    raw_deployable = total_liquid - required_reservations
    available_long_term_capital = max(0.0, raw_deployable)

    # Opportunity Cash = portfolio cash portion available after reservations
    opportunity_cash = max(0.0, portfolio_cash - max(0.0, reserve_target_amount - safe_assets))

    # Overall Status
    if survival_reserve_status == "UNSAFE" or near_term_status == "UNCOVERED":
        overall_status = "UNSAFE"
    elif survival_reserve_status == "ATTENTION":
        overall_status = "ATTENTION"
    else:
        overall_status = "SAFE"

    return CapitalDurabilityMetrics(
        net_worth=net_worth,
        investable_net_worth=investable_net_worth,
        survival_months=round(survival_months, 1),
        reserve_target_amount=reserve_target_amount,
        survival_reserve_status=survival_reserve_status,
        opportunity_cash=opportunity_cash,
        available_long_term_capital=available_long_term_capital,
        near_term_liability_status=near_term_status,
        status=overall_status,
    )
