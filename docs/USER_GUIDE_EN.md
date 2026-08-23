# QPort — Complete User Guide (English)

QPort is a **Buy & Hold portfolio information system for Vietnamese cash equities**.
It tracks what you actually own; it does not choose stocks, optimize schedules or
place trades automatically.

> Core rule: **only explicit ledger events change shares or cash**.

---

## 1. What QPort tracks

QPort stores and calculates:

- owned shares;
- cost basis and average cost;
- available portfolio cash;
- daily market prices;
- market value and NAV;
- unrealized and realized P/L;
- dividend income, fees and taxes;
- daily portfolio snapshots;
- TWR and XIRR;
- current/max drawdown;
- 63D/252D volatility;
- concentration, HHI and effective positions;
- correlations and diversification ratio;
- risk contribution and ERC reference;
- historical VaR/CVaR and downside diagnostics;
- optional target-weight guidance.

QPort never changes holdings because a metric, date or warning changed.

---

## 2. Install and start

### 2.1 Frontend

```bash
cd frontend
npm ci
npm run build
npm run build:ssr
```

### 2.2 Python

```bash
cd ../python
pip install -r requirements.txt
```

This base installation can use VNDIRECT.

Optional Vnstock:

```bash
pip install -r requirements-vnstock.txt
```

### 2.3 Start the server

```bash
python serve.py
```

Open:

```text
http://127.0.0.1:8080/
```

Navigation:

```text
Portfolio | Transactions | Performance | Risk | Snapshots | Settings | Guide
```

Use the `EN / VI` switch to change language.

---

## 3. Understand the database

Default database:

```text
python/data/portfolio.sqlite3
```

The most important data is the **ledger**. Market prices and snapshots are derived
and can be rebuilt.

Back up the database before bulk migration or major changes.

To use another database:

```text
PORTFOLIO_DB=/path/to/portfolio.sqlite3
```

---

## 4. Migrate an existing portfolio from scratch

Assume your broker currently shows:

```text
ACB   19,210 shares   average cost 19,780 VND
DGC   10,000 shares   average cost 52,340 VND
FPT    3,000 shares   average cost 74,025 VND
Cash  50,000,000 VND
```

### Step 1 — Import each existing holding

Open **Transactions**.

Choose:

```text
Opening position import
```

For each holding enter:

- date;
- ticker;
- current share count;
- broker average cost per share in **full VND**.

Example:

```text
Symbol: FPT
Shares: 3000
Price / share: 74025
```

`POSITION_IMPORT` creates shares and cost basis without consuming QPort cash.

Use an honest acquisition/migration date. Historical Performance starts from the
dates represented in the ledger; do not invent old dates simply to create a
longer chart.

### Step 2 — Record available cash

You can do either:

- Portfolio → **Cash management → Add cash**; or
- Transactions → **Cash deposit**.

For the example:

```text
50,000,000 VND
```

The ledger cash balance is the source of truth for available cash.

### Step 3 — Run the first sync

Return to **Portfolio** and click:

```text
Sync daily prices
```

The first sync is important. QPort will:

1. fetch D1 history for every symbol in the ledger;
2. normalize Vietnamese equity prices to full VND;
3. store market prices;
4. replay the ledger through historical market dates;
5. rebuild daily snapshots;
6. build TWR and drawdown history;
7. populate Performance and Risk.

You do **not** need to create snapshots manually.

---

## 5. Verify accounting before trusting analytics

Before using Performance or Risk, compare the Portfolio table with your broker.

For every holding verify:

```text
Shares
Avg cost
Price
Cost value
Market value
Unrealized P/L
Return
```

Formulas:

```text
Cost Value        = Shares × Average Cost
Market Value      = Shares × Current Price
Unrealized P/L    = Market Value - Cost Value
Unrealized Return = Unrealized P/L / Cost Value
```

Example:

```text
FPT
Shares        = 3,000
Average cost  = 74,025 VND
Current price = 72,000 VND

Cost Value    = 222,075,000 VND
Market Value  = 216,000,000 VND
Unrealized P/L=  -6,075,000 VND
Return        ≈ -2.74%
```

Portfolio formulas:

```text
NAV       = Cash + Σ Market Value
Total P/L = NAV - Net External Contributions
```

Total P/L is a live accounting value. It does not require a snapshot to exist.

If Price, Cost Value, Market Value or P/L does not match the broker, stop and fix
the ledger/data before interpreting Risk or Performance.

---

## 6. Price units and market data

QPort stores Vietnamese equity prices as **full VND per share**.

Correct:

```text
FPT = 72,000 VND
```

Incorrect:

```text
FPT = 72 VND
```

Provider policy:

```text
Vnstock when installed
       ↓ fallback
VNDIRECT
       ↓ failure
stored last price + STALE/MISSING status
```

### Data status

**VALID** — current holdings have consistent latest data.

**STALE** — one or more holdings are valued using an older known price.

**MISSING** — a required price is unavailable.

Never interpret stale estimated values as fully current broker reconciliation.

---

## 7. Portfolio page

The top cards show:

### NAV

Current portfolio value:

```text
cash + market value of all holdings
```

### Equity

Current total value of owned shares.

### Cash

Available portfolio cash from ledger events.

### Total P/L

Current wealth relative to net investor contributions.

It includes the economic effect of:

- current unrealized P/L;
- realized P/L;
- dividends;
- fees/taxes;
- cash still held in the portfolio.

### Current drawdown

Peak-to-current decline of the TWR wealth index. If history has been rebuilt, it
should show a numeric value, including `0.00%` when at a peak.

### 252D volatility

Annualized realized volatility from stored market history.

---

## 8. Cash management

Portfolio contains a dedicated **Cash management** card.

### Add cash

Use when money is actually available inside the portfolio/account being tracked.
It creates a `CASH_DEPOSIT` ledger event.

### Withdraw cash

Use only when cash actually leaves the tracked portfolio. It creates a
`CASH_WITHDRAW` event and cannot make cash negative.

### BUY uses recorded cash

A `BUY` event is rejected if the ledger does not contain enough cash.

That is intentional. Record funding first.

---

## 9. Recording normal portfolio events

Use **Transactions** whenever a real event occurs.

### BUY

Enter executed quantity, executed price, fees and taxes.

### SELL

Enter actual execution. QPort rejects selling more shares than owned.

### Cash dividend

Use `CASH_DIVIDEND` for cash actually received. It increases cash and investment
return; it is not an investor contribution.

### Stock dividend

Use `STOCK_DIVIDEND` with the number of new shares actually credited. Cost basis
stays unchanged, so average cost falls mechanically.

### Split

Use `SPLIT` with the share ratio. Example: a 2:1 split uses ratio `2`.

### Fee

Use `FEE` for a standalone portfolio fee not already included in a BUY/SELL event.

---

## 10. Portfolio Health

Portfolio Health is a diagnostic summary, not a trading command.

It includes:

- total return;
- current/max drawdown;
- 63D/252D volatility;
- largest position;
- effective number of positions;
- average/max pairwise correlation;
- diversification ratio;
- largest risk contributor;
- historical daily VaR/CVaR 95%;
- risk-data coverage;
- official snapshot count;
- cash weight.

Warnings can include:

- stale market data;
- a position >= 40% of NAV;
- high HHI concentration;
- high average correlation;
- drawdown >= 20%;
- volatility >= 35%;
- insufficient risk-history coverage.

A warning means **inspect**, not **sell**.

---

## 11. Performance page

After the first successful historical sync, Performance should no longer be empty.

### Total P/L

Live accounting P/L from current NAV and net external contributions.

### TWR

Time-weighted return neutralizes external deposits/withdrawals.

Use TWR when asking:

> How did the portfolio itself perform?

### XIRR

Money-weighted annualized return using your dated investor cash flows and current
NAV.

Use XIRR when asking:

> What annualized return did my actual money experience?

### Drawdown

Calculated from the TWR wealth index:

```text
Drawdown = current TWR index / running peak - 1
```

Deposits and withdrawals therefore do not create artificial peaks/losses.

### Other metrics

- Daily / MTD / YTD return;
- annualized TWR;
- best/worst day;
- positive-day ratio;
- history start/latest date;
- official snapshot count;
- realized/unrealized P/L;
- dividends and fees.

If the chart is empty, click **Rebuild performance history**. If it remains empty,
check that opening ledger dates overlap available market history.

---

## 12. Risk page

Risk is entirely informational.

### 63D / 252D volatility

Shorter and longer realized volatility horizons. The volatility ratio shows if
recent risk is elevated relative to the longer window.

### HHI and effective positions

```text
HHI = Σ weight²
Effective positions = 1 / HHI
```

A portfolio can own many tickers but still have a low effective-position count if
capital is concentrated.

### Correlation

QPort reports average and maximum pairwise correlation from recent stored history.
High correlation means holdings may provide less diversification than the ticker
count suggests.

### Diversification ratio

Compares weighted individual volatility with portfolio volatility. Values above 1
indicate diversification benefit in the measured sample.

### Risk contribution

Shows how much of estimated portfolio variance each holding contributes.

### ERC reference

Shows an equal-risk reference only. It is not a target allocation and never creates
trades.

### Historical VaR 95%

5th-percentile observed daily portfolio return.

### Historical CVaR 95%

Average daily return in observations at or below the VaR threshold.

These are sample diagnostics, not forecasts or guaranteed loss limits.

### Data coverage

Always inspect coverage and missing symbols before trusting covariance/risk output.

---

## 13. Snapshots page

A snapshot is an automatic daily checkpoint containing:

```text
date
holdings from ledger
cash
closing prices
NAV
daily P/L
daily return
TWR index
drawdown
selected risk fields
data quality
```

### OFFICIAL

All active holdings have an exact price for the same trading date. These rows are
used for official performance.

### STALE

At least one active holding uses a previous known price. The row remains visible
for diagnosis but is excluded from official performance.

### How to create snapshots

Do not enter them manually. Use:

```text
Portfolio → Sync daily prices
```

or:

```text
Snapshots → Sync & rebuild snapshots
```

QPort reconstructs available historical checkpoints from ledger dates.

---

## 14. Settings page

QPort intentionally has very few settings.

### Fixed system policy

You cannot turn these into optimization parameters:

```text
Investment mode      BUY & HOLD
Automatic trading    OFF
Portfolio mutations  Ledger events only
Daily tracking       ON
```

### Market-data policy

Displayed so you understand where data comes from; normally no action is needed.

### Optional target-weight guidance

Default can remain **Disabled — pure Buy & Hold**.

Enable only if you want:

- ADD / HOLD / REVIEW labels;
- BUY-only suggestions for deploying available cash.

If enabled, enter a reference weight for every active holding and make the total
exactly 100%.

Reference weights:

- do not expire annually;
- are not automatically recalculated;
- do not create trades.

---

## 15. Daily routine

After market close:

1. Open Portfolio.
2. Sync daily prices (or let the 15:30 scheduler run).
3. Confirm market data is VALID or understand any stale symbols.
4. Reconcile NAV/P&L when needed.
5. Review Portfolio Health warnings.
6. Use Performance for return/drawdown context.
7. Use Risk for concentration/diversification context.
8. Record a transaction only if a real portfolio event happened.

QPort should be mostly observational on normal days.

---

## 16. Scheduler

Default in-process schedule:

```text
15:30 Asia/Ho_Chi_Minh on weekdays
```

Disable it when starting the server:

```bash
python serve.py --no-daily-sync
```

For Windows Task Scheduler / cron:

```bash
python -m portfolio.cli sync
```

---

## 17. Backup and recovery

Regularly copy:

```text
python/data/portfolio.sqlite3
```

If market prices/snapshots are damaged but the ledger is safe, derived history can
be rebuilt by syncing again.

Do not casually modify ledger rows directly in SQLite.

---

## 18. Troubleshooting

### Total P/L is zero but it should not be

Check:

- holdings/cost basis are imported;
- current prices exist;
- cash deposits/withdrawals match the tracked account;
- NAV matches the broker.

Total P/L is calculated live as:

```text
NAV - net external contributions
```

### Drawdown shows no history

Run a sync/rebuild and confirm your ledger dates overlap stored D1 market history.

### Performance chart is empty

Run **Rebuild performance history**. Then inspect Snapshots for official rows.

### Cash is zero

Record actual available cash on Portfolio → Cash management or via a Cash deposit
event.

### P/L is off by roughly 1,000×

Check price units. Vietnamese stock prices must be stored/displayed as full VND,
e.g. `72,000`, not `72`.

### Risk is unavailable/partial

Inspect Risk → Data quality. Some holdings may not have enough historical returns.

### A snapshot is STALE

At least one active symbol lacks an exact price for that date. It is intentionally
excluded from official performance.

---

## 19. Before trusting QPort

Use this checklist:

```text
[ ] Shares match broker
[ ] Average cost matches broker
[ ] Prices use full VND
[ ] Cost Value matches shares × cost
[ ] Market Value matches shares × price
[ ] Available cash matches tracked account
[ ] NAV matches broker closely
[ ] Unrealized P/L matches broker methodology closely
[ ] Market data status is understood
[ ] Official snapshots exist after sync
[ ] Risk coverage is sufficient before interpreting risk metrics
[ ] Database backup exists
```

Once the accounting layer reconciles, QPort's Performance, Drawdown and Risk pages
become meaningful information rather than decorative metrics.
