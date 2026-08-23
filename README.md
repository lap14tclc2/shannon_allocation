# QPort — Buy & Hold Portfolio Information System

QPort is a rule-based portfolio tracker for Vietnamese cash equities.

The operational product is deliberately **not an optimizer**. The user owns the
investment decisions; QPort owns the information, accounting, daily market-data
sync, portfolio snapshots, performance measurement and risk diagnostics.

Operational UI languages:

```text
English (EN)
Vietnamese / Tiếng Việt (VI)
```

The selected language is persisted in the browser with the `qport_lang` cookie.

```text
USER portfolio events
        ↓
immutable ledger
        ↓
current holdings + cash
        ↑
VNDIRECT / optional Vnstock daily prices
        ↓
daily snapshot
        ↓
NAV · P/L · TWR · XIRR · drawdown · volatility · concentration · risk contribution
        ↓
HOLD / ADD / REVIEW information
```

## Core invariants

- Price movement never changes shares.
- A model/risk signal never changes shares.
- Time, year-end, or a schedule never changes shares.
- Only explicit ledger events change holdings or cash.
- Research results cannot write to the operational portfolio ledger.
- Market-data failure is visible as stale/missing data; the system does not invent a fresh NAV.

## Operational event types

- `POSITION_IMPORT` — migration/opening holding; adds shares/cost basis without fake historical cash trading.
- `BUY` / `SELL` — actual user-recorded executions.
- `CASH_DEPOSIT` / `CASH_WITHDRAW`.
- `CASH_DIVIDEND` / `STOCK_DIVIDEND`.
- `SPLIT`.
- `FEE`.

The application exposes no normal update/delete API for ledger history. Verify
ledger entries carefully and keep database backups before bulk migration.

## Market data

Daily market data is normalized behind a provider contract:

1. Vnstock when installed and reachable.
2. VNDIRECT public dchart fallback.
3. Last stored price remains visible with a stale/missing quality flag if live sync fails.

Vietnamese equity prices are normalized to canonical **full VND per share** before
portfolio valuation.

Base installation works with VNDIRECT:

```bash
cd python
pip install -r requirements.txt
```

To enable Vnstock too:

```bash
pip install -r requirements-vnstock.txt
```

The provider pattern is adapted from the separate `dnse_bot` project, but the
portfolio core contains no provider-specific dependency.

## Run

```bash
cd frontend
npm ci
npm run build
npm run build:ssr

cd ../python
python serve.py
```

Open:

```text
http://127.0.0.1:8080/
```

Navigation:

```text
Portfolio | Transactions | Performance | Risk | Snapshots | Settings | Guide | Research
```

The server starts an idempotent EOD market sync at **15:30 Asia/Ho_Chi_Minh** on
weekdays. Override with `PORTFOLIO_SYNC_TIME=HH:MM` or run with
`python serve.py --no-daily-sync`.

For Windows Task Scheduler / cron instead of a continuously running server:

```bash
python -m portfolio.cli sync
```

## Complete guides

English:

[`docs/USER_GUIDE_EN.md`](docs/USER_GUIDE_EN.md)

Vietnamese / Tiếng Việt:

[`docs/USER_GUIDE_VI.md`](docs/USER_GUIDE_VI.md)

The same start-to-finish workflow is also available inside the application at:

```text
/guide
```

## Research boundary

All previous ERC/Shannon backtests, Dynamic Alpha, NSGA-II, surrogate search and
optimizer experiments are retained under **Research Lab**:

```text
/research
/research/optimizer
```

They are evidence/proposal tools only. The old HTTP/CLI implementation is kept in
`research_legacy_server.py`, `research_main.py`, `optimize_main.py` and
`backtest/`; the primary operational server does not allow research output to
mutate the portfolio ledger.

Legacy optimizer/detail research screens may retain English-only labels. The
operational Buy & Hold product and Research landing page support EN/VI.

See [`BUY_AND_HOLD_SYSTEM_SPEC.md`](BUY_AND_HOLD_SYSTEM_SPEC.md) and
[`user-guide.md`](user-guide.md).
