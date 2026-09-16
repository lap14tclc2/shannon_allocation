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

    # Receivables Forensics (Evidence-Based Multi-Signal Thresholds)
    RECEIVABLES_VS_REVENUE_CAGR_GAP: float = 0.10          # Legacy alias (10Y gap threshold)
    RECEIVABLES_GROWTH_GAP_3Y_WATCH: float = 0.05          # Recent 3Y gap > 5% triggers preliminary watch
    RECEIVABLES_GROWTH_GAP_3Y_HIGH: float = 0.12           # Recent 3Y gap > 12% indicates strong acceleration
    RECEIVABLES_GROWTH_GAP_10Y_HISTORICAL: float = 0.10    # 10Y gap > 10% (historical signal only, not a sole trigger)
    RECEIVABLES_MATERIALITY_LOW: float = 0.15              # Receivables / Revenue < 15% is low materiality
    RECEIVABLES_MATERIALITY_HIGH: float = 0.35             # Receivables / Revenue > 35% is high materiality
    RECEIVABLES_ASSETS_RATIO_HIGH: float = 0.25            # Receivables / Total Assets > 25% is high asset concentration
    RECEIVABLES_DSO_HIGH_DAYS: float = 90.0                # DSO > 90 days indicates slow collection cycle
    RECEIVABLES_DSO_INCREASE_WATCH_DAYS: float = 15.0      # DSO 3Y increase > 15 days indicates lengthening cycle
    RECEIVABLES_LOW_BASE_RATIO_THRESHOLD: float = 0.05     # Base-year Receivables / Revenue < 5% indicates low-base effect
    RECEIVABLES_CFO_PAT_CONCERN: float = 0.60              # 3Y CFO / PAT < 0.6x indicates weak cash conversion
    RECEIVABLES_REVENUE_RATIO_HIGH: float = 0.40           # Legacy alias (Receivables / Revenue > 40%)
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

    # Required Margin of Safety (MOS) Policy Thresholds
    BASE_REQUIRED_MOS_COMPOUNDER: float = 15.0      # Base Required MOS for high-quality durable compounder
    BASE_REQUIRED_MOS_POTENTIAL_COMPOUNDER: float = 20.0 # Base Required MOS for potential compounder
    BASE_REQUIRED_MOS_AVERAGE: float = 25.0         # Base Required MOS for average enterprise
    BASE_REQUIRED_MOS_WEAK: float = 35.0            # Base Required MOS for weak enterprise (if buyable)
    MOS_ADDON_VALUE_TRAP_WATCH: float = 5.0          # +5% MOS penalty for WATCH value trap
    MOS_ADDON_LIMITED_HISTORY: float = 5.0          # +5% MOS penalty for limited history (5-7Y)
    MOS_ADDON_BALANCE_SHEET_WATCH: float = 5.0      # +5% MOS penalty for balance sheet watch
    MOS_ADDON_LOW_CONFIDENCE: float = 5.0           # +5% MOS penalty for low valuation confidence


DEFAULT_MUNGER_THRESHOLD_POLICY = MungerThresholdPolicy()

