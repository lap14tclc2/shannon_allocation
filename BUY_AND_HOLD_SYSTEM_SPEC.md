# QPort — Buy & Hold Portfolio Information System Specification

**Status:** Canonical  
**Version:** 2.0  
**Date:** 2026-08-23

## 1. Purpose

QPort tracks a user-owned Vietnamese equity portfolio. It is an information and
accounting system, not a portfolio optimizer or trading engine.

The user decides what to own and records real portfolio events. QPort provides:

- immutable accounting and cost basis;
- available cash tracking;
- Vnstock/VNDIRECT daily market data;
- live NAV and P/L;
- reconstructed daily portfolio history;
- TWR, XIRR and drawdown;
- volatility, concentration, correlation and tail-risk diagnostics;
- optional target-weight guidance for ADD / HOLD / REVIEW;
- bilingual English/Vietnamese UI.

## 2. Non-negotiable invariants

```text
INV-01 Price movement never changes shares.
INV-02 Risk output never changes shares or cash.
INV-03 Time/year-end never changes shares or cash.
INV-04 Only explicit immutable ledger events change holdings/cash.
INV-05 SELL may not exceed owned shares.
INV-06 BUY/withdraw/fee may not create negative cash.
INV-07 Missing/stale market data is visible, never hidden.
INV-08 OFFICIAL snapshots require exact same-date prices for all active holdings.
INV-09 Suggestions are information only and never execution.
INV-10 ERC is a diagnostic reference, never an allocation instruction.
```

There is no optimizer, stock-rotation, annual-allocation, auto-rebalance or
automatic-trading subsystem in QPort.

## 3. Architecture

```text
                     USER
                      │
               explicit events
                      ▼
             IMMUTABLE LEDGER
                      │
                holdings + cash
                      ▲
                      │
              DAILY MARKET DATA
             Vnstock → VNDIRECT
                      │
                      ▼
               CANONICAL VND D1
                      │
                      ▼
            DAILY SNAPSHOT REBUILD
          ┌───────────┼───────────┐
          ▼           ▼           ▼
         NAV      PERFORMANCE    RISK
          │           │           │
          └───────────┼───────────┘
                      ▼
                 INFORMATION
                      ▼
                     USER
```

Operational package:

```text
python/portfolio/
  domain.py
  storage.py
  accounting.py
  market_data.py
  analytics.py
  risk.py
  locale.py
  service.py
  scheduler.py
  cli.py
```

Primary web server: `python/buyhold_server.py`.

## 4. Immutable ledger

Supported event types:

### `POSITION_IMPORT`

Migrates an existing holding into QPort. Adds shares and cost basis without
pretending a historical cash trade happened inside QPort.

Required:

```text
symbol
quantity > 0
price/cost per share > 0
```

Use an honest acquisition/migration date because historical performance starts
from ledger dates.

### `CASH_DEPOSIT` / `CASH_WITHDRAW`

Investor cash flows. The current ledger cash balance is the available cash shown
on Portfolio.

### `BUY`

```text
cash -= quantity × price + fee + tax
shares += quantity
cost basis += gross + buy fee
```

BUY requires sufficient recorded cash.

### `SELL`

Cannot exceed owned shares. Cash increases by net proceeds and realized P/L uses
average cost.

### Income/corporate actions

```text
CASH_DIVIDEND
STOCK_DIVIDEND
SPLIT
FEE
```

Cash dividends are investment return, not external contributions. Stock dividends
and splits change shares explicitly while preserving cost basis as defined by the
accounting engine.

The normal application API has no ledger-event update/delete operation.

## 5. Market data

Provider contract:

```python
class MarketDataProvider:
    def daily_history(symbol, start, end): ...
    def health(): ...
```

Policy:

```text
optional Vnstock
       ↓ unavailable/error
VNDIRECT public D1
       ↓ unavailable/error
stored price + explicit STALE/MISSING state
```

All Vietnamese equity OHLC prices are normalized to **full VND per share** before
persistence and valuation.

Market-price storage is idempotent on `(symbol, trading_date)`.

## 6. Live valuation and P/L

For every position:

```text
Cost Value       = shares × average cost
Market Value     = shares × current market price
Unrealized P/L   = Market Value - Cost Value
Unrealized Return= Unrealized P/L / Cost Value
```

Portfolio:

```text
NAV        = cash + Σ Market Value
Total P/L  = NAV - Net External Contributions
```

`Total P/L` is calculated from current ledger state and current stored prices. It
does not require a daily snapshot to exist.

Cash dividends, realized P/L, fees and current unrealized P/L therefore flow into
portfolio Total P/L through NAV/accounting rather than being hard-coded UI values.

## 7. Historical rebuild and snapshots

A user does not manually create snapshots.

`sync_daily()`:

```text
sync D1 prices for all ledger symbols
→ rebuild daily states from immutable ledger
→ value each date from stored prices
→ neutralize external flows
→ chain TWR
→ calculate drawdown
→ save derived snapshots
```

This allows QPort to populate Performance and Drawdown after the first sync,
provided the ledger dates and historical D1 data are available.

### Snapshot quality

`OFFICIAL`:
- every active holding has an exact price for that trading date.

`STALE`:
- at least one active holding is valued from a previous known price.

Stale rows remain visible for diagnosis but are excluded from official performance
statistics.

Snapshots are rebuildable derived data. The ledger remains the source of truth.

## 8. Performance

### External-flow neutralized daily return

```text
daily_pnl    = NAV_t - NAV_t-1 - external_flow_t
daily_return = daily_pnl / NAV_t-1
```

### TWR

Official daily returns are chain-linked. Investor deposits/withdrawals do not
create fake investment return.

### XIRR

Uses dated external investor cash flows plus terminal current NAV. It represents
the investor's money-weighted experience.

### Drawdown

Drawdown is calculated from the TWR wealth index:

```text
DD_t = TWR_index_t / running_peak - 1
```

This prevents deposits and withdrawals from creating artificial peaks/losses.

Performance output includes:

- daily / MTD / YTD return;
- TWR since inception and annualized TWR;
- XIRR;
- current/max drawdown;
- best/worst daily return;
- positive-day ratio;
- live total/unrealized/realized P/L;
- dividend income;
- fees/taxes;
- history coverage.

## 9. Risk and Portfolio Health

Risk is information only.

Current diagnostics include:

```text
63D realized volatility
252D realized volatility
63D / 252D volatility ratio
largest capital position
HHI concentration
effective positions = 1 / HHI
average pairwise correlation
maximum pairwise correlation
diversification ratio
risk contribution by holding
risk-contribution HHI
largest risk contributor
ERC equal-risk reference
historical daily VaR 95%
historical daily CVaR 95%
downside volatility
worst observed day
positive-day ratio
history coverage
```

Historical VaR/CVaR describes the observed sample. It is not a forecast or a loss
limit.

Portfolio Health summarizes accounting/performance/risk quality and raises
informational warnings for conditions such as:

- stale data;
- large single-position concentration;
- high HHI;
- high correlation;
- large drawdown;
- high volatility;
- incomplete risk-history coverage.

None of these warnings can create a trade.

## 10. Optional target-weight guidance

QPort works without target weights. This is **pure Buy & Hold monitoring**.

If the user explicitly enables target-weight guidance, all active holdings must
have persistent weights summing to 100%.

Then:

```text
current < 80% of reference  → ADD
current > 120% of reference → REVIEW
otherwise                   → HOLD
```

References do not expire, do not recalculate annually and do not create trades.

Available cash may be shown as BUY-only contribution suggestions toward positive
deficits. Actual broker executions must still be recorded explicitly.

## 11. Web product

Routes:

```text
/              Portfolio Dashboard
/transactions  Ledger entry/history
/performance   P/L, TWR, XIRR, drawdown, NAV history
/risk          Detailed portfolio-risk diagnostics
/snapshots     Daily checkpoint history and data quality
/settings      Fixed system policy + optional target-weight guidance
/guide         Start-to-finish EN/VI guide
```

API:

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

No other investment-decision or automatic-execution API is part of the product.

## 12. Daily operation

Typical workflow:

```text
after market close
→ sync prices
→ rebuild snapshots
→ inspect Portfolio Health / Performance / Risk
→ record only real portfolio events when they actually occur
```

Default in-process sync time:

```text
15:30 Asia/Ho_Chi_Minh
```

Manual equivalent:

```bash
python -m portfolio.cli sync
```

## 13. EN / VI

The operational UI supports:

```text
EN — English
VI — Tiếng Việt
```

Locale is presentation-only state persisted in the `qport_lang` cookie and cannot
affect accounting or risk calculations.

## 14. Testing requirements

Core regression tests must cover:

- deterministic ledger replay;
- oversell and negative-cash rejection;
- cash/dividend/share corporate actions;
- market sync never changing shares;
- full-VND price normalization;
- live Total P/L without requiring snapshots;
- first-sync historical snapshot reconstruction;
- TWR/drawdown series availability;
- risk diagnostic fields;
- absence of any optimizer/research runtime or route;
- bilingual SSR/hydration.

Core tests must not require external network access.

## 15. Definition of done

QPort is considered coherent when:

1. a fresh database starts empty;
2. existing holdings/cash can be migrated honestly;
3. live NAV/P&L reconcile with the broker;
4. one market sync can reconstruct available daily history;
5. Performance and Drawdown are populated from that history;
6. Risk and Portfolio Health provide useful diagnostics;
7. snapshots are automatic and clearly explain OFFICIAL/STALE;
8. Settings exposes only understandable long-lived preferences;
9. no optimizer/research/automatic-allocation code or route exists;
10. only explicit ledger events can change holdings or cash.
