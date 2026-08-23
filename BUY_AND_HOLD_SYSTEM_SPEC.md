# QPort — Buy & Hold Portfolio Information System Specification

**Status:** Canonical operational specification  
**Version:** 1.0  
**Date:** 2026-08-23

This document is the authoritative contract for the operational product. The
legacy optimizer/backtest system is retained as a **Research Lab** and is not an
operational portfolio controller.

---

## 1. Product purpose

QPort is a long-horizon information system for a user-owned Vietnamese equity
portfolio.

The user decides what they own and records real portfolio events. QPort provides:

- immutable portfolio accounting;
- daily market-data synchronization;
- NAV and P/L;
- TWR and XIRR;
- drawdown and volatility;
- concentration and risk contribution;
- optional ERC reference information;
- HOLD / ADD / REVIEW information;
- an isolated research area for backtests and experiments.

QPort does **not** optimize annual allocation dates, rotate stocks automatically,
or create trades from a model output.

---

## 2. Non-negotiable invariants

```text
INV-P01  Price movement never changes shares.
INV-P02  Model output never changes shares or cash.
INV-P03  Risk output never changes shares or cash.
INV-P04  Time/year-end/schedules never change shares or cash.
INV-P05  Only explicit immutable ledger events change holdings/cash.
INV-P06  SELL may not exceed owned shares.
INV-P07  BUY/withdraw/fee may not create negative cash.
INV-P08  Research cannot write to the operational ledger.
INV-P09  Missing/stale market data is reported, never hidden.
INV-P10  Only fully fresh daily data may produce an OFFICIAL snapshot.
INV-P11  Contribution suggestions are BUY-only information and never execution.
INV-P12  ERC is a risk reference, never a mandatory allocation instruction.
```

These invariants take priority over convenience or historical optimizer behavior.

---

## 3. Operational architecture

```text
                         USER
                          │
                    explicit events
                          │
                          ▼
                ┌──────────────────┐
                │ IMMUTABLE LEDGER │
                └────────┬─────────┘
                         │
                         ▼
                  CURRENT STATE
                 holdings + cash
                         ▲
                         │
                DAILY MARKET DATA
                ┌────────┴────────┐
                │                 │
             Vnstock         VNDIRECT
                │                 │
                └────────┬────────┘
                         ▼
                   NORMALIZATION
                         │
                         ▼
                DAILY PRICE STORE
                         │
                         ▼
               PORTFOLIO SNAPSHOT
             ┌───────────┼───────────┐
             ▼           ▼           ▼
            NAV      PERFORMANCE    RISK
             │           │           │
             └───────────┼───────────┘
                         ▼
                 HOLD / ADD / REVIEW
                         │
                         ▼
                        USER
```

Operational Python package:

```text
python/portfolio/
  domain.py        event/state contracts
  storage.py       SQLite ledger, prices, snapshots
  accounting.py    deterministic event replay
  market_data.py   provider boundary
  analytics.py     TWR/XIRR/drawdown helpers
  risk.py          informational portfolio risk
  service.py       application orchestration
  scheduler.py     EOD data/snapshot scheduler
  cli.py           local operations
```

No module in `portfolio/` imports `backtest.optimize` or uses optimizer output to
mutate state.

---

## 4. Ledger model

The ledger is append-only at the application boundary.

Supported event types:

### `POSITION_IMPORT`
Migration/opening-position event. Adds shares and cost basis without pretending
that a historical cash trade occurred inside QPort.

Required:
- symbol;
- quantity > 0;
- average/import cost > 0.

It is intended primarily for initial migration. For clean XIRR history, use the
actual acquisition date when known.

### `BUY`
A real executed purchase. Reduces cash by:

```text
quantity × price + fee + tax
```

and increases shares/cost basis.

### `SELL`
A real executed sale. Quantity cannot exceed holdings. Realized P/L uses average
cost accounting.

### Cash events
- `CASH_DEPOSIT`
- `CASH_WITHDRAW`
- `CASH_DIVIDEND`
- `FEE`

Cash dividends are portfolio return, not external investor contributions.

### Share/corporate-action events
- `STOCK_DIVIDEND`
- `SPLIT`

They update shares explicitly. Adjusted historical prices must never be used as a
substitute for changing the actual share ledger.

Corrections are represented by explicit compensating events. The application has
no ledger-event update/delete API.

---

## 5. Market-data boundary

Operational code depends on this conceptual contract:

```python
class MarketDataProvider:
    def daily_history(symbol, start, end): ...
    def health(): ...
```

Current provider chain:

```text
optional Vnstock
    ↓ failure / unavailable
VNDIRECT public dchart
    ↓ failure
stored last-known price + explicit STALE/MISSING state
```

The implementation pattern is adapted from the `dnse_bot` project.

### VNDIRECT
Daily OHLCV comes from the public dchart endpoint and is normalized into:

```text
trading_date
open
high
low
close
volume
source
fetched_at
is_final
data_quality
```

### Vnstock
Vnstock is an optional dependency and is imported lazily. The base product must
remain usable when Vnstock is unavailable.

### Price persistence
Market prices are stored locally in SQLite. Repeated sync is idempotent by
`(symbol, trading_date)`.

### Data-quality rule
For a multi-stock portfolio, a daily snapshot is OFFICIAL only when every active
holding has the same latest trading date and the current sync has no provider
errors.

Otherwise QPort may show an estimated/stale snapshot, clearly labeled as such.

---

## 6. Daily monitoring lifecycle

Default scheduler time:

```text
15:30 Asia/Ho_Chi_Minh
```

On a weekday:

```text
fetch/update market history for current holdings
→ normalize/store prices
→ validate common latest trading date
→ replay immutable ledger
→ mark positions to market
→ compute portfolio risk information
→ calculate external flow since prior snapshot
→ create/update daily snapshot
→ classify OFFICIAL vs STALE/MISSING
```

The scheduler has no transaction-writing operation.

Manual equivalent:

```bash
python -m portfolio.cli sync
```

The scheduler is safe to run repeatedly because price rows and date snapshots are
idempotent.

---

## 7. Portfolio snapshot

A daily snapshot records at least:

```text
snapshot_date
cash
equity_value
nav
external_flow
daily_pnl
daily_return
twr_index
total_pnl
current_drawdown
max_drawdown
volatility_63
volatility_252
hhi
max_position_weight
data_quality
official
```

Each position snapshot records:

```text
symbol
shares
average_cost
price
market_value
weight
unrealized_pnl
unrealized_return
risk_contribution
erc_reference_weight
status
```

Historical portfolio snapshots preserve the valuation used on that date even if
a data provider later revises historical bars.

---

## 8. Performance accounting

### NAV

```text
NAV = cash + Σ(shares × latest valuation price)
```

### Daily P/L
External cash/asset contributions are removed from the daily performance return:

```text
daily_pnl = NAV_t - NAV_t-1 - external_flow_t

daily_return = daily_pnl / NAV_t-1
```

### TWR
Daily returns are chain-linked into a TWR wealth index. Deposits and withdrawals
do not create fake investment return.

### XIRR
XIRR uses dated investor cash flows plus terminal NAV. It represents investor
experience and is distinct from TWR.

### Dividends
Cash dividends remain inside NAV and count as investment return unless the user
records a withdrawal event.

---

## 9. Risk is information, not execution

The operational system computes:

- 63-session volatility;
- 252-session volatility;
- HHI concentration;
- maximum position weight;
- covariance-based portfolio risk;
- risk contribution by holding;
- optional ERC reference weights.

Risk output can make the UI say `REVIEW`, but cannot generate `SELL`.

```text
risk rises
→ dashboard warning
→ user reviews
→ portfolio unchanged
```

Pairwise covariance with minimum-history checks is used so one short-history
holding does not erase all portfolio diagnostics. Missing coverage is reported.

---

## 10. Strategic reference weights

Reference weights are optional and persistent until the user changes them.

They are **not annual targets** and do not expire/recalculate at year-end.

When present:

```text
current < 80% of reference  → ADD
current > 120% of reference → REVIEW
otherwise                   → HOLD
```

These labels are informational.

If no reference weights exist, contribution-directed suggestions use equal-weight
deficits only as a simple informational baseline.

---

## 11. Contribution-directed BUY-only suggestions

When cash exists, QPort may calculate how cash could reduce underweight drift.

```text
available cash
→ compute positive target deficits
→ allocate only toward deficits
→ return ADD suggestions
```

No SELL is generated and no BUY event is persisted automatically.

The user must record an actual broker execution as a separate `BUY` event.

---

## 12. Web product

Primary routes:

```text
/              Portfolio Dashboard
/transactions  Immutable ledger entry/history
/performance   NAV, TWR, XIRR, P/L
/risk          Informational risk diagnostics
/snapshots     Daily snapshot history
/settings      Optional strategic references
/research      Isolated research lab
```

Primary operational API:

```text
GET  /api/portfolio
GET  /api/portfolio/transactions
POST /api/portfolio/transactions
POST /api/portfolio/sync
GET  /api/portfolio/performance
GET  /api/portfolio/risk
GET  /api/portfolio/snapshots
POST /api/portfolio/reference-weights
```

There is intentionally no endpoint such as:

```text
POST /api/portfolio/apply-optimizer
POST /api/portfolio/auto-rebalance
POST /api/portfolio/annual-allocation
```

---

## 13. Research boundary

The previous system remains available for research:

- backtests;
- ERC/Shannon experiments;
- Dynamic Alpha;
- NSGA-II;
- surrogate models;
- allocation timing experiments;
- walk-forward/holdout analysis.

Research lives under:

```text
/research
/research/optimizer
python/backtest/
python/research_main.py
python/optimize_main.py
python/research_legacy_server.py
```

Boundary:

```text
RESEARCH RESULT
      ↓
PROPOSAL / EVIDENCE
      ↓
HUMAN DECISION
      ↓
EXPLICIT LEDGER EVENT
      ↓
OPERATIONAL PORTFOLIO
```

Research cannot bypass the explicit ledger event.

---

## 14. Testing policy

Operational core must have dataset-independent tests for:

- deterministic ledger replay;
- oversell rejection;
- negative-cash rejection;
- dividends/splits;
- market sync not mutating shares;
- snapshot accounting;
- suggestion non-mutation;
- absence of event update/delete APIs;
- SSR/hydration of operational pages.

Network provider integration is tested separately and must not be required for
core accounting tests.

Research regression tests are maintained separately and may be run manually to
reduce CI cost.

---

## 15. Migration from the optimizer-first product

The following concepts are removed from the operational domain:

```text
allocation_frequency
allocation_days
allocation_count_per_year
optimized schedule
annual allocation event
quarterly benchmark
champion candidate
live-eligible optimizer winner
dynamic alpha membership
volatility-triggered automatic equity reduction
```

They may still exist inside Research Lab artifacts/code.

Operational portfolio state is now entirely derived from real user-recorded
portfolio events plus market prices.

---

## 16. Definition of done

The Buy & Hold refactor is operationally complete when:

1. `/` renders portfolio information, not an optimizer.
2. a fresh database starts with no fabricated holdings;
3. opening positions can be explicitly imported;
4. daily sync obtains/stores prices and creates a snapshot;
5. sync/risk/research cannot mutate shares or cash;
6. ledger transactions are append-only through the application API;
7. TWR/XIRR/performance use official snapshots correctly;
8. Research Lab is reachable but separated from operational state;
9. documentation identifies this specification as canonical;
10. operational core tests and frontend smoke tests pass locally/CI when run.
