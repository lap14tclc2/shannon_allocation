# Portfolio Allocation — Legacy Specification Notice

**Status: DEPRECATED FOR OPERATIONAL USE**

This document previously described the optimizer-first ERC/Shannon allocation
system. That architecture is no longer the operational product.

The canonical specification is now:

> [`BUY_AND_HOLD_SYSTEM_SPEC.md`](BUY_AND_HOLD_SYSTEM_SPEC.md)

QPort has been refactored into a **Buy & Hold Portfolio Information System**.
Operational state is derived only from an immutable portfolio ledger plus daily
market prices.

The following concepts are now research-only:

```text
annual/quarterly allocation schedules
allocation timing optimization
combination optimization
Dynamic Alpha membership rotation
NSGA-II / surrogate candidate search
live-eligible optimizer winners
volatility-driven automatic equity reduction
```

They remain available under the Research Lab (`/research`, `python/backtest/`,
`python/optimize_main.py`, `python/research_main.py`) for analysis and historical
experiments, but they cannot mutate the operational portfolio.

Operational architecture:

```text
explicit user portfolio events
        ↓
immutable ledger
        ↓
actual holdings + cash
        ↑
Vnstock / VNDIRECT daily prices
        ↓
daily snapshots
        ↓
NAV · performance · risk information
        ↓
HOLD / ADD / REVIEW
        ↓
user decision
```

Use the canonical Buy & Hold spec and `user-guide.md` for all new development.
