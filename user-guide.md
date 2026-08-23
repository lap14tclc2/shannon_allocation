# QPort — Buy & Hold User Guide

This guide covers the operational portfolio product. Optimizers and Dynamic Alpha
are available only inside **Research Lab**.

## 1. Start QPort

```bash
git checkout main
git pull origin main

cd frontend
npm ci
npm run build
npm run build:ssr

cd ../python
pip install -r requirements.txt
python serve.py
```

Open:

```text
http://127.0.0.1:8080/
```

Optional Vnstock support:

```bash
pip install -r requirements-vnstock.txt
```

Without Vnstock, QPort can still use VNDIRECT as its market-data source.

---

## 2. What QPort does

QPort follows a Buy & Hold information-system model:

```text
real portfolio events
→ immutable ledger
→ current holdings + cash
→ daily market prices
→ portfolio snapshot
→ NAV / P&L / performance / risk
→ HOLD / ADD / REVIEW information
```

QPort does not automatically choose stocks, sell holdings, reduce exposure, or
rebalance at year-end.

Only events you explicitly record can change holdings/cash.

---

## 3. First-time portfolio migration

Go to:

```text
Transactions
```

For every existing holding, choose:

```text
Opening position import
```

Enter:

- date;
- ticker;
- current shares;
- average/cost basis per share.

Example:

```text
FPT
3,000 shares
average cost 73,980 VND
```

Use the real acquisition date when practical, especially if you want meaningful
XIRR from the beginning of the investment. If only the current consolidated cost
basis is known, record the migration honestly rather than inventing historical
trades.

An opening-position import adds shares and cost basis without consuming portfolio
cash.

If you have available cash, record a separate:

```text
Cash deposit
```

---

## 4. Recording real activity

Transactions are the source of truth.

Supported events:

```text
Opening position import
Cash deposit
Buy execution
Sell execution
Cash withdrawal
Cash dividend
Stock dividend
Stock split
Standalone fee
```

### BUY
Record the actual broker execution:

```text
symbol
shares
execution price
fee
tax if applicable
execution date
```

QPort requires enough previously recorded cash.

### SELL
Record the actual execution. QPort will not allow selling more shares than the
ledger owns.

### Cash dividend
Record the amount actually credited to the portfolio. It remains investment
return unless you later record a cash withdrawal.

### Stock dividend
Record the new shares credited. Cost basis is unchanged and average cost falls
mechanically.

### Split
Record the share multiplication ratio. For a 2:1 split, enter `2`.

Existing ledger events are not edited/deleted through the application. A mistake
should be corrected with explicit compensating portfolio events so the audit trail
remains visible.

---

## 5. Daily market monitoring

When the server stays running, QPort attempts its daily market sync at:

```text
15:30 Asia/Ho_Chi_Minh
```

on weekdays.

You can also press:

```text
Sync daily prices
```

from the Portfolio page.

Or use Windows Task Scheduler / cron:

```bash
cd python
python -m portfolio.cli sync
```

Provider policy:

```text
Vnstock when installed/reachable
        ↓ fallback
VNDIRECT public daily data
        ↓ failure
last stored price + STALE/MISSING warning
```

A market-data failure never changes your shares.

---

## 6. Portfolio Dashboard

The start page is now the actual portfolio, not an optimizer.

It shows:

```text
NAV
Equity value
Cash
Total P/L
Current drawdown
252D volatility
```

For each holding:

```text
Ticker
Shares
Average cost
Latest price
Market value
Portfolio weight
Unrealized P/L
Risk contribution
HOLD / ADD / REVIEW status
Price date/source
```

If no portfolio has been entered, QPort shows an empty state. It never creates a
sample or synthetic holding in the operational database.

---

## 7. Data freshness

A daily portfolio snapshot can be:

```text
OFFICIAL
STALE
MISSING
```

`OFFICIAL` requires all active holdings to have the same latest trading date and
no provider error during the current sync.

Example:

```text
ACB  2026-08-21
FPT  2026-08-21
REE  2026-08-20
```

The portfolio can still show an estimated NAV, but it is not considered an
official performance snapshot until the data is coherent.

This prevents one stale holding from silently becoming part of a supposedly
fresh NAV.

---

## 8. Performance

Go to:

```text
Performance
```

QPort reports:

```text
Daily return
MTD
YTD
TWR since inception
XIRR
NAV history
Realized P/L
Dividend income
Fees/taxes
Net external contributions
```

### TWR
Time-weighted return removes the effect of deposits/withdrawals from portfolio
performance.

A 100M deposit therefore cannot create a fake +100M investment gain.

### XIRR
XIRR uses the dates of investor cash flows plus the latest official NAV. It is the
money-weighted investor experience and can differ materially from TWR.

Only official snapshots enter the displayed performance series.

---

## 9. Risk page

Risk is information, not execution.

QPort currently reports:

```text
63D volatility
252D volatility
largest position weight
HHI concentration
risk contribution by ticker
ERC reference weight
history coverage / missing data
```

A high-risk result means:

```text
REVIEW
```

It does not mean:

```text
automatically sell
automatically lower equity exposure
automatically rebalance
```

ERC is retained because it is useful for understanding how portfolio risk is
distributed. It is no longer a mandatory portfolio target.

---

## 10. HOLD / ADD / REVIEW

These statuses are intentionally simple.

### Without strategic reference weights
The system primarily reports the actual portfolio. Cash-deployment suggestions
may use equal-weight deficits as a neutral baseline.

### With optional strategic reference weights
A reference weight is a long-lived user preference, not an annual target.

Example:

```text
ACB 25%
DGC 20%
FPT 30%
REE 25%
```

The references remain unchanged until you change them.

Status policy:

```text
current < 80% of reference  → ADD
current > 120% of reference → REVIEW
otherwise                   → HOLD
```

No status creates a broker order.

---

## 11. Deploying new cash

If the portfolio contains unused cash, QPort may show:

```text
Deploy existing cash
```

This is **BUY-only information**.

QPort calculates positive deficits relative to your strategic references, or to
an equal-weight baseline when no references exist.

Example:

```text
Available cash: 50M

FPT  +30M
REE  +20M
```

The system deliberately does not sell an overweight winner merely to satisfy
this suggestion.

If you actually buy, record the real broker fill as a `BUY` transaction afterward.

---

## 12. Daily snapshots

Go to:

```text
Snapshots
```

Every snapshot contains the portfolio state used for that date:

```text
NAV
cash
equity
daily P/L
daily return
drawdown
volatility
positions
data quality
```

Historical snapshot values remain audit records of what QPort knew/used on that
date.

---

## 13. Research Lab

All advanced quant work remains available at:

```text
/research
```

This includes legacy:

```text
Dynamic Alpha
combination search
NSGA-II
surrogate models
allocation timing
walk-forward testing
holdout reports
ERC/Shannon backtests
```

But Research has a hard boundary:

```text
research result
→ proposal/evidence
→ user decides
→ user performs a real trade
→ explicit ledger event
```

Research cannot apply a candidate directly to the operational portfolio.

Old `/optimizer` URLs remain compatibility aliases into Research Lab; they are no
longer the product home.

---

## 14. Operational CLI

Current portfolio status:

```bash
python -m portfolio.cli status
```

Daily market sync:

```bash
python -m portfolio.cli sync
```

Performance:

```bash
python -m portfolio.cli performance
```

The old random ranking CLI now lives at:

```bash
python research_main.py ...
```

and the optimizer CLI remains research-only:

```bash
python optimize_main.py ...
```

---

## 15. Backup

The operational database is local SQLite:

```text
python/data/portfolio.sqlite3
```

It is intentionally excluded from Git.

Back it up separately. The database contains the actual portfolio ledger and is
more important operationally than generated optimizer artifacts.

Override its path with:

```text
PORTFOLIO_DB=<path>
```

---

## 16. Core mental model

When in doubt, use this rule:

```text
PRICE MOVEMENT        does not change shares
MODEL OUTPUT          does not change shares
RISK WARNING          does not change shares
YEAR END              does not change shares
RESEARCH RESULT       does not change shares

ONLY A REAL PORTFOLIO EVENT
changes shares or cash.
```

That is the operating philosophy of QPort Buy & Hold.
