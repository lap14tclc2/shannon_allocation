"""Centralized Configurable Threshold Policy for Munger Financial Statement Analysis Engine (Task 136).

All numerical thresholds used for growth, profitability, earnings quality, balance sheet,
capital allocation, and forensic rules are documented and archetype-aware.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class MungerThresholdPolicy:
    """Threshold configuration for Munger financial statement analysis."""

    # History Depth Classification
    MIN_YEARS_INSUFFICIENT: int = 3
    MIN_YEARS_LIMITED: int = 5
    MIN_YEARS_USABLE: int = 7
    MIN_YEARS_STRONG: int = 10

    # Earnings & Cash Quality (Normal Enterprise)
    NORMAL_CFO_PAT_PASS_RATIO: float = 0.80  # 5Y average CFO / PAT >= 0.8x
    NORMAL_CFO_PAT_WATCH_RATIO: float = 0.50  # 5Y average CFO / PAT >= 0.5x
    PROFIT_CASH_DIVERGENCE_CAGR_GAP: float = 0.15  # PAT CAGR - CFO CAGR > 15%
    PERSISTENT_NEGATIVE_CFO_YEARS: int = 3  # CFO negative 3+ years out of 5

    # Receivables Forensics
    RECEIVABLES_VS_REVENUE_CAGR_GAP: float = 0.10  # Receivables CAGR - Revenue CAGR > 10%
    RECEIVABLES_REVENUE_RATIO_HIGH: float = 0.40   # Receivables / Revenue > 40%
    RECEIVABLES_REVENUE_RATIO_RISING_PERSISTENT_YEARS: int = 3

    # Inventory Forensics (Normal Enterprise)
    INVENTORY_VS_REVENUE_CAGR_GAP: float = 0.10     # Inventory CAGR - Revenue CAGR > 10%
    INVENTORY_REVENUE_RATIO_HIGH: float = 0.35      # Inventory / Revenue > 35%

    # Debt & Balance Sheet Strength
    DEBT_EQUITY_PASS: float = 0.80                  # Total Debt / Equity <= 0.8x for normal enterprise
    DEBT_EQUITY_WATCH: float = 1.50                 # Total Debt / Equity <= 1.5x
    DEBT_GROWTH_VS_REVENUE_CAGR_GAP: float = 0.15   # Debt CAGR - Revenue CAGR > 15%
    INTEREST_COVERAGE_PASS: float = 4.0             # EBIT / Interest Expense >= 4.0x
    INTEREST_COVERAGE_WATCH: float = 2.0            # EBIT / Interest Expense >= 2.0x

    # Capital Efficiency & Retained Earnings
    ROIC_PASS: float = 0.12                         # 5Y Median ROIC >= 12%
    ROIC_WATCH: float = 0.08                        # 5Y Median ROIC >= 8%
    ROE_PASS: float = 0.15                          # 5Y Median ROE >= 15%
    ROE_WATCH: float = 0.10                         # 5Y Median ROE >= 10%
    RETAINED_EARNINGS_VALUE_CREATION_RATIO: float = 1.0  # $1 retained -> $1+ incremental market cap / earnings value

    # Dilution & Per-Share Compounder
    DILUTION_CAGR_WATCH: float = 0.03               # Share count CAGR > 3% per year
    DILUTION_CAGR_DESTRUCTIVE: float = 0.07         # Share count CAGR > 7% per year
    PER_SHARE_DILUTION_PAT_GAP: float = 0.05        # Net Income CAGR - EPS CAGR > 5%

    # Bank-Specific Thresholds
    BANK_ROE_PASS: float = 0.14                     # 5Y Median ROE >= 14%
    BANK_ROE_WATCH: float = 0.09                    # 5Y Median ROE >= 9%
    BANK_NPL_PROXY_WATCH: float = 0.03              # Provision / Total Loans or Loan Risk Proxy > 3%
    BANK_EQUITY_ASSETS_MIN: float = 0.06            # Equity / Total Assets >= 6%

    # Securities-Specific Thresholds
    SECURITIES_ROE_PASS: float = 0.12               # 5Y Median ROE >= 12%
    SECURITIES_ROE_WATCH: float = 0.07              # 5Y Median ROE >= 7%
    SECURITIES_FVTPL_DEPENDENCE_HIGH: float = 0.50  # Trading/FVTPL gains > 50% of Operating Income
    SECURITIES_LEVERAGE_PASS: float = 3.5           # Total Assets / Equity <= 3.5x
    SECURITIES_LEVERAGE_WATCH: float = 5.0          # Total Assets / Equity <= 5.0x


DEFAULT_MUNGER_THRESHOLD_POLICY = MungerThresholdPolicy()
