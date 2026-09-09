"""Crash and Job-Loss Stress Engine for Personal Capital Durability."""

from __future__ import annotations

from portfolio.personal_finance.models import (
    PersonalBalanceSheetInput,
    StressTestScenarioResult,
)


def run_crash_job_loss_stress_engine(
    input_data: PersonalBalanceSheetInput,
    portfolio_equity_value: float,
    portfolio_cash: float,
    largest_position_value: float = 0.0,
) -> list[StressTestScenarioResult]:
    """Run deterministic stress tests to detect FORCED EQUITY SALE risk under severe economic shocks.

    Scenarios:
    1. MARKET_CRASH: Equity -40%
    2. JOB_LOSS: Income = 0 for 12 months
    3. COMBINED: Income = 0, Equity -40%, Largest position permanent impairment -50%
    4. FAMILY_SHOCK: One-time emergency expense = 6 months essential spending
    """
    essential_burn = max(0.0, float(input_data.monthly_essential_spending))
    safe_assets = max(0.0, float(input_data.safe_liquid_assets))
    cash = max(0.0, float(portfolio_cash))
    equity = max(0.0, float(portfolio_equity_value))
    near_term_liabilities = max(0.0, float(input_data.near_term_liabilities))
    margin_debt = max(0.0, float(input_data.margin_debt))

    results: list[StressTestScenarioResult] = []

    # Scenario 1: MARKET_CRASH (-40% equity)
    crash_equity = equity * 0.60
    crash_nav = safe_assets + cash + crash_equity - near_term_liabilities - margin_debt
    crash_margin_call = margin_debt > 0 and (crash_equity < margin_debt * 1.3)
    crash_survival_months = (safe_assets / essential_burn) if essential_burn > 0 else 999.0
    crash_forced_sale = crash_margin_call or (safe_assets < 0)

    results.append(
        StressTestScenarioResult(
            scenario_name="MARKET_CRASH",
            stressed_nav=crash_nav,
            remaining_safe_assets=safe_assets,
            survival_months=round(crash_survival_months, 1),
            forced_equity_sale_required=crash_forced_sale,
            near_term_liability_covered=safe_assets >= near_term_liabilities,
            margin_call_possible=crash_margin_call,
            summary="Thị trường giảm 40%. " + ("CẢNH BÁO: Có thể giải chấp Margin!" if crash_margin_call else "Không bắt buộc bán cổ phiếu."),
        )
    )

    # Scenario 2: JOB_LOSS (Income = 0 for 12 months)
    # Burn essential spending for 12 months from safe_assets
    annual_burn = essential_burn * 12.0
    rem_safe_job_loss = safe_assets - annual_burn
    job_loss_survival_months = (safe_assets / essential_burn) if essential_burn > 0 else 999.0
    job_loss_forced_sale = rem_safe_job_loss < 0
    job_loss_nav = (max(0.0, rem_safe_job_loss) + cash + equity) - near_term_liabilities - margin_debt

    results.append(
        StressTestScenarioResult(
            scenario_name="JOB_LOSS",
            stressed_nav=job_loss_nav,
            remaining_safe_assets=rem_safe_job_loss,
            survival_months=round(job_loss_survival_months, 1),
            forced_equity_sale_required=job_loss_forced_sale,
            near_term_liability_covered=rem_safe_job_loss >= near_term_liabilities,
            margin_call_possible=margin_debt > 0,
            summary="Mất thu nhập 12 tháng. " + ("CẢNH BÁO: Thiếu hụt quỹ dự phòng, bắt buộc bán cổ phiếu để sinh sống!" if job_loss_forced_sale else "Dự phòng an toàn, không cần bán cổ phiếu."),
        )
    )

    # Scenario 3: COMBINED (Income = 0 + Equity -40% + Largest thesis -50%)
    impairment = max(0.0, float(largest_position_value)) * 0.50
    combined_equity = max(0.0, crash_equity - impairment)
    rem_safe_combined = safe_assets - annual_burn
    combined_survival_months = (safe_assets / essential_burn) if essential_burn > 0 else 999.0
    combined_margin_call = margin_debt > 0 and (combined_equity < margin_debt * 1.5)
    combined_forced_sale = rem_safe_combined < 0 or combined_margin_call
    combined_nav = (max(0.0, rem_safe_combined) + cash + combined_equity) - near_term_liabilities - margin_debt

    results.append(
        StressTestScenarioResult(
            scenario_name="COMBINED",
            stressed_nav=combined_nav,
            remaining_safe_assets=rem_safe_combined,
            survival_months=round(combined_survival_months, 1),
            forced_equity_sale_required=combined_forced_sale,
            near_term_liability_covered=rem_safe_combined >= near_term_liabilities,
            margin_call_possible=combined_margin_call,
            summary="Khủng hoảng kép (Mất việc + Thị trường sập 40% + Vị thế lớn suy giảm 50%). " + ("BẮT BUỘC BÁN BỚT TÀI SẢN BẢO VỆ SINH TỒN!" if combined_forced_sale else "Khung tài sản đủ sức chịu đựng."),
        )
    )

    # Scenario 4: FAMILY_SHOCK (Emergency expense = 6 months essential spending)
    shock_expense = essential_burn * 6.0
    rem_safe_shock = safe_assets - shock_expense
    shock_survival_months = (max(0.0, rem_safe_shock) / essential_burn) if essential_burn > 0 else 999.0
    shock_forced_sale = rem_safe_shock < 0
    shock_nav = (max(0.0, rem_safe_shock) + cash + equity) - near_term_liabilities - margin_debt

    results.append(
        StressTestScenarioResult(
            scenario_name="FAMILY_SHOCK",
            stressed_nav=shock_nav,
            remaining_safe_assets=rem_safe_shock,
            survival_months=round(shock_survival_months, 1),
            forced_equity_sale_required=shock_forced_sale,
            near_term_liability_covered=rem_safe_shock >= near_term_liabilities,
            margin_call_possible=margin_debt > 0,
            summary="Biến cố gia đình phát sinh chi phí đột xuất 6 tháng. " + ("Thiếu hụt tiền mặt dự phòng!" if shock_forced_sale else "Đủ quỹ dự phòng khẩn cấp."),
        )
    )

    return results
