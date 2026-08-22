"""Configuration for the Shannon/ERC combination backtest.

All quantitative parameters mirror the reference implementation
(portfolio_allocation) unless explicitly marked as a risk/alpha overlay. ERC
still determines relative risk weights; the optional alpha layer only decides
which symbols are active at a recalibration event using strictly-past prices.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class BacktestParams:
    # Data
    data_dir: str = "F:/data_finance/data"
    price_scale: int = 1000

    # Money
    initial_balance: float = 200_000_000
    annual_deposit: float = 20_000_000
    deposit_at_start_year: bool = True

    # Combination generation
    num_combinations: int = 50
    min_symbols: int = 5
    max_symbols: int = 10
    portfolio_size: int | None = None
    seed: int = 42
    symbols_file: str | None = None

    # ERC calibration
    annualization_factor: int = 252
    minimum_observations: int = 60
    lookback_days: int = 252

    # Allocation schedule
    allocation_frequency: str = "quarterly"

    # Dynamic alpha selection. When enabled, the configured market universe is
    # re-ranked at every ERC recalibration using only observations strictly before
    # the signal day. The selector chooses the active names; ERC still owns their
    # relative weights. These fixed coefficients are methodology, not optimized
    # genes, so the final holdout cannot tune them.
    dynamic_alpha_enabled: bool = False
    dynamic_alpha_portfolio_size: int = 7
    alpha_min_observations: int = 60
    alpha_short_lookback: int = 63
    alpha_medium_lookback: int = 126
    alpha_long_lookback: int = 252
    alpha_correlation_lookback: int = 126
    alpha_max_pair_correlation: float = 0.80

    # Shannon drift bands
    normal_band: float = 0.10
    soft_band: float = 0.20

    # Absolute-risk overlay. ERC stays fixed until the next allocation event;
    # exposure may be refreshed more often without re-solving ERC.
    risk_overlay_enabled: bool = False
    target_volatility: float = 0.18
    risk_fast_lookback: int = 63
    risk_slow_lookback: int = 252
    risk_refresh_days: int = 5               # weekly D1 exposure refresh; daily drift checks remain
    # Strategic floor only. 0.0 means volatility targeting may fully de-risk.
    # Missing/invalid risk data is controlled separately by risk_missing_data_exposure.
    min_equity_exposure: float = 0.0
    risk_missing_data_exposure: float = 0.0  # fail closed when no valid risk estimate exists
    max_position_weight: float | None = 0.30

    # Execution
    fractional_shares: bool = True
    rebalance_every_days: int = 1
    execution_lag: int = 1

    # Transaction costs (basis points)
    fee_buy_bps: float = 15.0
    fee_sell_bps: float = 15.0
    tax_sell_bps: float = 10.0
    slippage_bps: float = 5.0

    # Simulation window
    start_date: str | None = None
    end_date: str | None = None

    # Universe
    universe: str = "all"

    # Output
    output_dir: str = "F:/workspace/shannon_allocation/python/results"
    top_n: int = 20

    def as_dict(self) -> dict:
        return asdict(self)
