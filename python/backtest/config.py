"""Configuration for the Shannon/ERC combination backtest.

All quantitative parameters mirror the reference implementation
(portfolio_allocation) unless explicitly marked as a risk overlay.  The risk
overlay is orthogonal to ERC: ERC determines relative weights; the overlay can
scale total equity exposure and leave the remainder in cash.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class BacktestParams:
    # Data
    data_dir: str = "F:/data_finance/data"
    # CSV price column values are thousands of VND (ACB 22.4 => 22,400 VND).
    price_scale: int = 1000

    # Money
    initial_balance: float = 200_000_000      # 200M VND starting cash
    annual_deposit: float = 20_000_000        # 20M VND deposited each calendar year
    deposit_at_start_year: bool = True        # deposit on each Jan 1 boundary during the run

    # Combination generation
    num_combinations: int = 50
    min_symbols: int = 5
    max_symbols: int = 10
    # When set, generation uses exactly this many symbols instead of min..max.
    portfolio_size: int | None = None
    seed: int = 42
    symbols_file: str | None = None           # optional explicit ticker list (newline separated)

    # ERC calibration (walk-forward, look-ahead free)
    annualization_factor: int = 252
    minimum_observations: int = 60
    lookback_days: int = 252                  # trailing trading days used to estimate covariance

    # Allocation schedule
    #   "quarterly" -> first trading day of each quarter (Jan/Apr/Jul/Oct)
    #   "annual"    -> first trading day of each calendar year
    allocation_frequency: str = "quarterly"

    # Shannon drift bands (relative to each asset's current live target weight)
    normal_band: float = 0.10                 # +/- 10%  -> NORMAL (no trade)
    soft_band: float = 0.20                   # +/- 20%  -> SOFT / HARD outer envelope

    # Absolute-risk overlay.  With risk_overlay_enabled=False the engine remains
    # a 100%-equity ERC/Shannon portfolio (except residual execution cash).
    risk_overlay_enabled: bool = False
    target_volatility: float = 0.18           # annualized portfolio vol target (18%)
    risk_fast_lookback: int = 63              # faster crisis-sensitive estimate
    risk_slow_lookback: int = 252             # slow/stable estimate
    min_equity_exposure: float = 0.25         # no leverage; lower bound while risk estimate exists
    risk_missing_data_exposure: float = 0.0   # fail closed when risk cannot be estimated
    max_position_weight: float | None = 0.30  # cap relative ERC weight before exposure scaling

    # Execution
    fractional_shares: bool = True            # False = whole shares (floor buys, floor sells)
    rebalance_every_days: int = 1             # band check frequency (1 = daily)
    execution_lag: int = 1                    # 0 = execute at signal close; 1 = execute at next close (no look-ahead)

    # Transaction costs (basis points of executed trade notional; 1 bps = 0.01%)
    fee_buy_bps: float = 15.0                 # broker commission on buys
    fee_sell_bps: float = 15.0                # broker commission on sells
    tax_sell_bps: float = 10.0                # sell-side tax (e.g. Vietnamese 0.1%)
    slippage_bps: float = 5.0                 # adverse execution slippage on both sides

    # Simulation window (optional overrides; default = full data range)
    start_date: str | None = None             # YYYY-MM-DD
    end_date: str | None = None               # YYYY-MM-DD

    # Universe filter: all | vn30 | vn50 | vn100 (vn100 == every symbol in data_dir)
    universe: str = "all"

    # Output
    output_dir: str = "F:/workspace/shannon_allocation/python/results"
    top_n: int = 20

    def as_dict(self) -> dict:
        return asdict(self)
