# QPort — Complete User Guide (English)

This guide starts from an empty machine/database and ends with the normal daily operating routine.

QPort is a **Buy & Hold portfolio information system for Vietnamese cash equities**. It is not an automatic trading system.

> Core invariant: **only explicit ledger events change shares or cash**. Market prices, risk metrics, research results, time and year-end schedules never create portfolio trades.

---

## 1. What QPort does

Operational QPort tracks:

- actual holdings and cash;
- average cost and cost basis;
- daily market prices;
- market value and NAV;
- realized and unrealized P/L;
- dividends, fees and taxes recorded in the ledger;
- TWR and XIRR;
- drawdown and volatility;
- portfolio concentration and risk contribution;
- optional long-lived strategic reference weights;
- BUY-only suggestions for deploying existing cash;
- immutable daily snapshots.

QPort does **not** automatically:

- buy or sell shares;
- rotate stocks;
- rebalance annually;
- reduce equity because volatility rises;
- apply optimizer results to the live portfolio.

Research tools remain isolated under `/research`.

---

## 2. Requirements

Recommended development/runtime environment:

- Python 3.11+
- Node.js 22+
- npm
- Internet access for market-data sync

The repository keeps the operational database local by default.

Default database path:

```text
python/data/portfolio.sqlite3
```

That runtime directory is ignored by Git.

---

## 3. Install from scratch

Clone/pull the repository and select the Buy & Hold branch:

```bash
git fetch origin
git checkout refactor-buy-hold
git pull origin refactor-buy-hold
```

Build the frontend:

```bash
cd frontend
npm ci
npm run build
npm run build:ssr
```

Install Python dependencies:

```bash
cd ../python
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Optional: enable Vnstock

The base system can operate with the VNDIRECT fallback. To also enable Vnstock:

```bash
pip install -r requirements-vnstock.txt
```

QPort's default market-data policy is:

```text
Vnstock when installed/reachable
        ↓ failure
VNDIRECT daily history
        ↓ failure
last stored price + explicit stale/missing state
```

---

## 4. Start QPort

From the `python` directory:

```bash
python serve.py
```

Open:

```text
http://127.0.0.1:8080/
```

The default operational navigation is:

```text
Portfolio | Transactions | Performance | Risk | Snapshots | Settings | Guide | Research
```

---

## 5. English / Vietnamese language

Use the `EN` / `VI` switch in the top navigation.

The selected language is stored in the `qport_lang` browser cookie and is reused on later visits.

If no language has been selected yet, QPort uses the browser `Accept-Language` header as the initial preference and falls back to English.

Operational QPort screens support both English and Vietnamese. Legacy optimizer/detail research screens are retained legacy tooling and may still contain English-only labels.

---

# PART A — CREATE THE INITIAL PORTFOLIO

## 6. Start with an empty database

On a new database the Portfolio page should show no holdings. This is intentional.

QPort does not create sample positions or infer holdings from market data.

The source of truth is the ledger.

---

## 7. Import existing holdings

Go to:

```text
Transactions → Record portfolio event
```

For every stock already owned before QPort starts tracking the portfolio, use:

```text
Opening position import
```

Required fields:

- Date
- Symbol
- Shares
- Price / share (VND)

For an opening import, **Price means the average cost basis per share you want QPort to track**, not today's market price.

Example:

```text
Symbol: FPT
Shares: 3,000
Average cost: 74,025 VND
```

Record:

```text
Event type: Opening position import
Symbol: FPT
Shares: 3000
Price/share: 74025
```

QPort creates:

```text
cost basis = 3,000 × 74,025
           = 222,075,000 VND
```

The opening import is treated as an external portfolio contribution for performance accounting. It does not pretend that QPort had cash and executed a historical BUY.

### Important

Enter prices in **full VND**:

```text
Correct:   72,000
Incorrect: 72
```

Vietnamese data providers may expose exchange-style values such as `72.0`; QPort normalizes provider market prices to canonical full VND before valuation.

---

## 8. Record opening cash

If the tracked portfolio has cash available, add it separately:

```text
Event type: Cash deposit
Amount: 50,000,000 VND
```

Do not include broker cash that is outside the portfolio scope you intend to track.

Your definition of portfolio scope must stay consistent over time.

---

## 9. Verify the imported state before continuing

After entering all opening positions and cash, go back to Portfolio.

Before trusting P/L, verify:

1. every ticker is present;
2. share quantities match the broker;
3. average cost matches the intended broker cost basis;
4. cash matches the tracked cash balance.

The application intentionally has no normal edit/delete API for ledger history. Verify entries carefully before submitting them.

If an incorrect historical event materially corrupts the ledger, prefer restoring a known-good database backup instead of inventing a fake market trade to hide the error.

---

# PART B — MARKET DATA AND DAILY SNAPSHOT

## 10. Run the first market-data sync

From Portfolio click:

```text
Sync daily prices
```

Or from the command line:

```bash
cd python
python -m portfolio.cli sync
```

For each held ticker, QPort attempts to:

1. download enough D1 history for analytics;
2. normalize OHLC prices to canonical VND;
3. persist market prices locally;
4. calculate portfolio risk diagnostics;
5. mark positions to market;
6. create/update the daily snapshot.

---

## 11. Verify the Holdings table

For every position, check these columns:

```text
Shares
Avg cost
Price
Cost value
Market value
Unrealized P/L
Return
Weight
Risk contribution
Status
```

Accounting identities:

```text
Cost value
= Shares × Average cost

Market value
= Shares × Current market price

Unrealized P/L
= Market value − Cost value

Unrealized return
= Unrealized P/L / Cost value
```

Example:

```text
FPT
Shares           3,000
Average cost    74,025 VND
Market price    72,000 VND

Cost value      222,075,000 VND
Market value    216,000,000 VND
Unrealized P/L   -6,075,000 VND
Return               -2.74%
```

If the market price appears as `72 VND` instead of about `72,000 VND`, stop and investigate the data normalization before trusting NAV or P/L.

---

## 12. Understand data status

Typical market-data states:

### VALID

All currently held symbols have the same latest trading date and the snapshot can be official.

### STALE

At least one held symbol has an older stored price than the freshest symbol.

QPort may display an estimated portfolio state for diagnosis, but stale data should not be treated as official performance evidence.

### MISSING

At least one held symbol has no usable stored market price.

Investigate the provider/symbol before trusting valuation.

---

## 13. Official vs non-official snapshots

A daily snapshot combines:

```text
immutable ledger state
+
stored market prices
+
derived portfolio analytics
```

Only a fully valid/fresh snapshot is marked official.

Performance charts use official snapshots.

This prevents a temporary provider failure from quietly becoming a fake official NAV point.

---

# PART C — RECORD REAL PORTFOLIO ACTIVITY

## 14. Event reference

### POSITION_IMPORT — Opening position import

Use only when establishing/migrating an already-owned position into QPort.

Effect:

```text
shares += quantity
cost basis += quantity × price
external contributions += same cost basis
```

It does not consume cash.

---

### CASH_DEPOSIT — Cash deposit

Use when new money enters the tracked portfolio.

Effect:

```text
cash += amount
external contributions += amount
```

External deposits are neutralized by TWR.

---

### BUY — Buy execution

Use only after a real broker BUY is executed.

Required:

- symbol;
- quantity;
- execution price;
- optional fee;
- optional tax.

Effect approximately:

```text
position cost basis += gross purchase + buy fee
shares += quantity
cash -= gross purchase + fee + tax
```

QPort rejects a BUY that makes tracked cash negative. Record the funding first.

---

### SELL — Sell execution

Use only after a real broker SELL is executed.

QPort rejects a SELL greater than the shares currently owned.

Realized P/L is based on the current average cost basis and execution costs.

---

### CASH_WITHDRAW — Cash withdrawal

Use when money leaves the tracked portfolio.

Effect:

```text
cash -= amount
external withdrawals += amount
```

This is an external flow, not investment loss.

---

### CASH_DIVIDEND — Cash dividend

Record the cash amount actually credited to the tracked portfolio.

Recommended practice: use the **net amount actually received from the broker account** so QPort does not need to guess tax treatment.

Effect:

```text
cash += amount
dividend income += amount
```

---

### STOCK_DIVIDEND — Stock dividend

Record the number of new shares actually credited.

Effect:

```text
shares += credited shares
cost basis unchanged
average cost falls mechanically
```

Example:

```text
Before: 3,000 shares
Credited stock dividend: 450 shares
After: 3,450 shares
```

---

### SPLIT — Stock split/share ratio

Enter the multiplicative ratio `new shares / old shares`.

Example 2-for-1 split:

```text
ratio = 2
```

Effect:

```text
shares *= ratio
cost basis unchanged
average cost changes inversely
```

---

### FEE — Standalone fee

Use for a portfolio-level fee not already attached to BUY/SELL.

Effect:

```text
cash -= amount
fees_and_taxes += amount
```

---

## 15. Ledger discipline

Treat the ledger as accounting history, not a scratchpad.

Rules:

- never enter a suggested trade before it actually happens;
- use broker-confirmed quantities/prices;
- record fees/taxes consistently;
- record corporate actions when shares/cash are actually credited;
- do not create fake BUY/SELL events to force the dashboard toward a desired number.

---

# PART D — READ THE DASHBOARD

## 16. NAV

Current portfolio NAV is:

```text
NAV = cash + Σ(position shares × current market price)
```

Price movement changes NAV and market value, but does **not** change shares.

---

## 17. Total P/L

The current system compares NAV against net external contributions for the displayed total P/L snapshot field.

Use Position Unrealized P/L for per-stock open P/L and Performance for time-series return measurement.

Do not confuse:

```text
P/L amount
with
TWR percentage return
with
XIRR investor return
```

They answer different questions.

---

## 18. HOLD / ADD / REVIEW

These labels are informational.

If no strategic reference weights are configured, positions normally remain HOLD unless another informational policy marks them otherwise.

With reference weights:

```text
materially below reference → ADD
near reference             → HOLD
materially above reference → REVIEW
```

They do not create transactions.

---

## 19. Deploy existing cash

QPort may display BUY-only cash-deployment suggestions.

Purpose:

```text
existing cash
→ prioritize underweight held positions
→ suggest amounts
```

A suggestion is not execution.

After actually executing the broker order, record a BUY event yourself.

---

# PART E — PERFORMANCE

## 20. TWR

Time-Weighted Return measures portfolio investment performance while neutralizing external flows such as deposits, withdrawals and opening imports.

Use TWR when asking:

> How did the portfolio itself perform independent of when I added money?

---

## 21. XIRR

XIRR uses dated investor cash flows and the latest official NAV.

Use XIRR when asking:

> What return did I personally experience given the timing of my money entering/leaving the portfolio?

TWR and XIRR can legitimately differ.

---

## 22. Official NAV history

The Performance chart uses official daily snapshots only.

If there are too few official snapshots, some period metrics will be unavailable. This is better than fabricating history.

---

# PART F — RISK

## 23. Risk is information, not execution

The Risk page may show:

- 63D volatility;
- 252D volatility;
- largest position;
- HHI concentration;
- risk contribution by ticker;
- ERC equal-risk reference;
- data coverage.

Operational QPort does not respond by automatically selling or reducing equity.

---

## 24. Risk contribution

Capital weight and risk contribution are different.

Example:

```text
DGC capital weight       40%
DGC risk contribution    58%
```

That tells you DGC contributes disproportionately to portfolio volatility/covariance risk.

It is a reason to **review information**, not an automatic sell instruction.

---

## 25. ERC reference

ERC asks what relative weights would roughly equalize marginal/total portfolio risk contribution given the covariance estimate.

In operational QPort ERC is diagnostic only.

It does not:

- expire annually;
- replace user holdings;
- create a rebalance schedule;
- create orders.

---

# PART G — STRATEGIC REFERENCE WEIGHTS

## 26. Configure references

Go to Settings.

Reference weights are optional.

If used, configured weights must total:

```text
100%
```

Example:

```text
ACB  30%
DGC  20%
FPT  30%
REE  20%
```

These references are long-lived until the user changes them.

They do not recalculate automatically each year.

---

## 27. What reference weights do

They may influence:

- HOLD / ADD / REVIEW labels;
- BUY-only existing-cash suggestions.

They do not mutate the ledger.

---

# PART H — DAILY OPERATING ROUTINE

## 28. Recommended EOD routine

After the Vietnam market closes:

1. Open Portfolio.
2. Run/confirm `Sync daily prices`.
3. Verify Data status is VALID.
4. Scan current NAV and daily/total P/L.
5. Check for obviously incorrect prices or quantities.
6. Review stale/missing tickers if any.
7. Open Risk only when you need concentration/risk context.
8. Record a new ledger event only if a real portfolio event occurred.

This should normally take only a few minutes.

---

## 29. Automatic EOD scheduler

When the server runs continuously, QPort starts an idempotent scheduler at:

```text
15:30 Asia/Ho_Chi_Minh
```

on weekdays.

Override the time:

```bash
set PORTFOLIO_SYNC_TIME=16:00
python serve.py
```

Linux shell example:

```bash
PORTFOLIO_SYNC_TIME=16:00 python serve.py
```

Disable the in-process scheduler:

```bash
python serve.py --no-daily-sync
```

You can then schedule:

```bash
python -m portfolio.cli sync
```

with Windows Task Scheduler or cron.

---

# PART I — BACKUP AND RECOVERY

## 30. What to back up

Most important file:

```text
python/data/portfolio.sqlite3
```

The ledger inside that database is the operational source of truth.

Recommended backup frequency:

- before bulk migration/import;
- after meaningful portfolio changes;
- periodically (for example daily or weekly).

---

## 31. Custom database location

Use `PORTFOLIO_DB` to store the database elsewhere.

Windows example:

```bash
set PORTFOLIO_DB=D:\qport-data\portfolio.sqlite3
python serve.py
```

Linux example:

```bash
PORTFOLIO_DB=/srv/qport/portfolio.sqlite3 python serve.py
```

---

## 32. Derived data vs source-of-truth data

Conceptually:

```text
Ledger events              SOURCE OF TRUTH
Reference weights          User configuration
Market prices              Re-fetchable/derived external data
Portfolio snapshots        Derived
Risk metrics               Derived
Performance metrics        Derived
Research results           Isolated evidence
```

Protect the ledger most carefully.

---

# PART J — TROUBLESHOOTING

## 33. Price is 72 instead of 72,000

Expected canonical unit is full VND/share.

QPort contains normalization/migration logic for VNDIRECT/Vnstock exchange-style price units.

Actions:

1. update to the latest branch code;
2. restart QPort so database migration executes;
3. run Sync daily prices again;
4. verify Price, Market value and Unrealized P/L.

Do not trust old P/L snapshots generated from the wrong price unit.

---

## 34. Data is STALE

Possible causes:

- provider failure;
- one ticker did not trade on the freshest date;
- symbol/provider issue;
- network problem.

Check:

- provider connectivity;
- latest trading date per holding;
- whether the market was actually open;
- retry Sync daily prices.

The portfolio holdings remain unchanged during provider failure.

---

## 35. Risk shows UNAVAILABLE

Risk analytics need enough overlapping price history.

Possible causes:

- newly imported ticker with insufficient stored history;
- provider gaps;
- too few eligible covariance observations.

This does not change portfolio shares.

---

## 36. BUY is rejected because cash would be negative

Record the cash funding first if it is genuinely part of the tracked portfolio:

```text
Cash deposit
→ real broker BUY
→ BUY event
```

Do not bypass this accounting invariant.

---

## 37. SELL is rejected

QPort prevents selling more shares than the ledger says are owned.

Verify:

- previous imports;
- stock dividends;
- splits;
- prior SELL events.

Correct the underlying ledger history rather than forcing the new SELL.

---

## 38. Snapshot does not become official

Check:

- data quality is VALID;
- no provider error remained during sync;
- every held symbol has a fresh price for the same latest trading date.

Estimated/stale snapshots remain useful for diagnosis but are excluded from official performance evidence.

---

# PART K — RESEARCH BOUNDARY

## 39. Research Lab

`/research` contains legacy/systematic research tools such as:

- backtests;
- Dynamic Alpha experiments;
- optimizer experiments;
- validation/holdout reports.

The intended information boundary is:

```text
Research
   ↓
evidence / proposal
   ↓
human decision
   ↓
real broker action
   ↓
explicit ledger event
   ↓
operational portfolio
```

There is deliberately no direct automatic Research → BUY/SELL path.

---

# PART L — FIRST-DAY CHECKLIST

Before considering a new QPort setup ready, confirm all items below:

- [ ] All opening holdings are imported.
- [ ] Share counts match the broker.
- [ ] Average costs match the intended broker cost basis.
- [ ] Opening cash matches the chosen portfolio scope.
- [ ] Daily price sync completes.
- [ ] Prices are displayed in full VND/share.
- [ ] Cost value matches `shares × average cost`.
- [ ] Market value matches `shares × market price`.
- [ ] Unrealized P/L matches broker calculations within expected fee/cost-basis differences.
- [ ] Data status is VALID for an official snapshot.
- [ ] A database backup exists.
- [ ] Optional strategic reference weights total 100% if configured.
- [ ] You understand that HOLD/ADD/REVIEW and Research outputs do not execute trades.

Once this checklist passes, QPort is ready for the normal daily Buy & Hold monitoring routine.
