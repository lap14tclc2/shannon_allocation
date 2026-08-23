# QPort AI Working Context

> Read this file before making non-trivial changes to QPort.
>
> This is a living handoff document for AI assistants and developers. `main` is the implementation source of truth. Verify current files before editing because the repository may have moved forward since this document was last updated.

Last consolidated: **2026-08-23**

---

## 1. Product identity

QPort is a bilingual (EN/VI) **Buy & Hold Portfolio Information System** for Vietnamese cash equities.

It is deliberately **not**:

- an automatic trading engine;
- an optimizer-driven portfolio allocator;
- a yearly rebalance engine;
- a stock-selection engine;
- an ERC target-execution engine;
- a model that silently changes user holdings.

The system observes, records, reconciles, measures and explains a portfolio. It can automatically post defined corporate-action ledger events, but it must never invent discretionary BUY/SELL decisions.

Canonical philosophy string returned by the dashboard:

```text
BUY_AND_HOLD_INFORMATION_SYSTEM
```

### Non-negotiable invariants

```text
price movement never changes shares
risk information never changes shares
time/year-end never changes shares
only explicit effective ledger events change holdings or cash
```

Corporate-action automation is an explicit system event path and is therefore compatible with the ledger invariant.

---

## 2. Repository / workflow expectations

Repository:

```text
lap14tclc2/shannon_allocation
```

Working branch policy used in the latest development cycle:

```text
main = source of truth
direct commits to main
no PR unless explicitly requested
```

Before changing code:

1. fetch current `main`;
2. read the exact files involved;
3. preserve the event-ledger source of truth;
4. add/update regression contracts;
5. do not claim GitHub Actions is green unless workflow/status evidence is actually returned.

The GitHub connector used during this work often returned:

```json
{"statuses": []}
```

for direct-main commits. Treat that as **no CI evidence**, not success.

---

## 3. Runtime architecture

High-level flow:

```text
authenticated normal user
        ↓
private per-user SQLite portfolio book
        ↓
validated user/system events
        ↓
immutable source ledger + append-only corrections
        ↓
effective ledger
        ↓
accounting state + FIFO tax lots + holdings + cash
        ↑
stored D1 provider prices
        ↓
official daily snapshots
        ↓
NAV / P&L / performance / risk / portfolio review
        ↓
information for user and AI audit
```

Important runtime service currently used by the server is based on `PortfolioService` / `CorrectablePortfolioService`. Do not assume an alternate service subclass is active merely because it contains a desirable implementation; verify server wiring first.

---

## 4. Authentication / admin boundary

The security model is intentionally simple for local/trusted use.

### Normal users

- unique username;
- no password by explicit product decision;
- each user has a separate SQLite portfolio database.

### Admin

- admin requires password;
- admin is administration-only;
- admin must always remain on `/admin`;
- admin cannot browse portfolio pages;
- `/api/portfolio/**` is forbidden to admin;
- scheduler skips admin as a portfolio user.

Do not silently redesign this into a complex public-internet authentication framework unless explicitly requested.

---

## 5. Ledger and accounting source of truth

Supported event families include:

```text
POSITION_IMPORT
CASH_DEPOSIT
CASH_WITHDRAW
BUY
SELL
CASH_DIVIDEND
STOCK_DIVIDEND
SPLIT
FEE
```

### Current transaction UX

Normal Transaction UI intentionally exposes only:

```text
POSITION_IMPORT
CASH_DEPOSIT
BUY
SELL
CASH_WITHDRAW
SPLIT
FEE
```

`CASH_DIVIDEND` and `STOCK_DIVIDEND` are hidden from manual entry. Existing automatic dividend rows remain visible in history as read-only.

`BUY` also represents a paid rights/new-issue subscription when the user records the actual subscribed shares, paid price, broker and account.

### Synchronization rule

Holdings and Transactions must never become separate books. Transaction create/edit/delete changes the effective ledger and derived state; Holdings follows that same ledger.

---

## 6. Broker/account and tax lots

Broker/account identity is part of event metadata and tax-lot accounting.

Defaults:

```text
broker_code = UNASSIGNED
account_id  = PRIMARY
```

BUY/POSITION_IMPORT create FIFO tax lots using broker/account identity.

Broker-assigned SELL may only consume FIFO lots from that same broker/account. It must not silently consume another broker's shares. Legacy `UNASSIGNED` behavior may operate on the consolidated book where required for backward compatibility.

### Holdings expanded row

Holdings are consolidated by ticker in the parent row. Expanding a holding shows broker/account detail derived from open tax lots, including:

- current shares;
- stock-dividend shares historically received at that broker/account;
- net cash dividends historically received;
- average cost;
- cost value;
- market value;
- unrealized P/L;
- percentage of symbol.

Historical dividend receipt attribution is intentionally distinct from current shares. A later sale should not erase the historical fact that a broker account received a dividend.

---

## 7. Dividend architecture

### Provider history

Normal dividend history uses **one canonical provider per refresh**. It must not show duplicate VPS/CafeF/etc records for the same economic event.

Current dedupe/canonicalization behavior includes:

- provider priority;
- economic-event matching across provider IDs;
- date tolerance for provider date differences;
- merge of evidence rather than duplicate display rows;
- suppression of known parser artifacts such as a stock ratio accidentally inferred from cash percentage where a distinct real stock ratio exists.

Provider failures preserve the last good cache.

### Automatic received dividends

Due corporate actions may automatically post idempotent ledger events on payment date when entitlement evidence is sufficient.

Broker/account allocation is derived from open entitlement-date tax lots and stored in automatic dividend ledger metadata as `broker_account_allocations`.

### Dividends received section

The received-dividend ledger section must **not render at all** when there are no actual received dividend ledger events. Do not show an empty decorative card.

### Tax policy implemented in QPort

Cash dividend:

```text
gross entitlement
- 5% withholding
= net cash added to portfolio
```

Stock dividend:

- no investment-income tax at receipt;
- taxable dividend-share pool is tracked;
- when taxable stock-dividend shares are sold, QPort adds 5% investment-income tax using par value VND 10,000/share, or the lower transfer price when sold below par;
- ordinary user-entered SELL tax remains additive rather than overwritten.

---

## 8. Market data and D1 background history

Market adapter policy:

```text
vnstock preferred
    ↓ fallback
VNDIRECT
    ↓ provider failure
last stored value + explicit stale/missing state
```

Vnstock may run in a child process, making it suitable for background work.

### Important D1 backfill fix

A newly imported portfolio must not fetch only from the transaction date. If a symbol has fewer than about 260 stored D1 bars, `_sync_symbol()` backfills from at least roughly **550 calendar days** before today (or earlier where event history requires it).

Once enough history exists, subsequent syncs use a short incremental overlap window.

### Market-history status surfaced to UI

Dashboard market metadata includes per-symbol history information such as:

```text
symbol
bars
required_bars
risk_ready
latest
source
```

The Portfolio UI exposes user-understandable states such as:

```text
SYNCING
BUILDING
READY
PARTIAL
ERROR
```

Do not present `BUILDING` as if it were a failure.

---

## 9. Performance methodology

Performance is based on **actual tracked portfolio snapshots**, not backfilled hypothetical ownership.

This distinction is critical:

```text
D1 market history may reach backward before the user started tracking
→ used for risk diagnostics

portfolio performance history begins from real tracked/effective portfolio history
→ used for TWR/drawdown/performance
```

External-flow handling includes CASH_DEPOSIT, CASH_WITHDRAW and opening POSITION_IMPORT semantics so daily TWR is not distorted by capital contributions/withdrawals.

Current performance evidence includes:

- daily / MTD / YTD / since-inception returns;
- TWR;
- annualized TWR when history permits;
- XIRR where cash-flow history supports it;
- current/max drawdown;
- best/worst day;
- positive-day ratio;
- accounting P/L bridge;
- dividend/tax effects;
- trailing return/volatility history derived from official snapshot series in the richer UI.

Missing history should appear as `-` / `BUILDING`, never fabricated `0%`.

---

## 10. Risk engine

Risk engine lives in `python/portfolio/risk.py` and is **information only**.

Current quantitative evidence includes:

- concentration / HHI;
- effective positions;
- 63D and 252D annualized volatility;
- volatility ratio;
- pairwise correlation;
- diversification ratio;
- modeled risk contributions;
- risk-contribution HHI;
- historical daily VaR 95%;
- historical daily CVaR 95%;
- worst observed day;
- downside volatility;
- positive-day ratio;
- data coverage and missing-symbol evidence;
- ERC reference weights.

Methodology currently includes D1 log returns, annualization 252, covariance requiring overlapping history with diagonal shrinkage, and historical tail-loss estimates.

### ERC rule — very important

ERC **is calculated**, but it is only:

```text
diagnostic_reference_only
```

ERC must not:

- set portfolio target weights;
- create BUY/SELL;
- rebalance holdings;
- drive contribution suggestions;
- silently become the portfolio policy.

`erc_reference_weight` may exist in enriched internal position/risk output, but product UX should keep ERC inside advanced risk / AI audit context so normal users do not mistake it for an allocation target.

### Current Risk UX (latest direction)

The Risk page was redesigned for non-fund-manager users using progressive disclosure.

Default view answers six plain-language questions:

1. Is the portfolio too concentrated?
2. Do the holdings move together?
3. Is price movement getting stronger?
4. How bad have bad days been historically?
5. Which holding drives the most modeled risk?
6. Can the user trust the conclusions yet?

The default page uses descriptive states such as:

```text
BUILDING
BALANCED
ELEVATED
HIGH
LOW
MODERATE
RISING
CALMER
DOMINANT
DISTRIBUTED
```

It deliberately does **not** manufacture a `73/100` style risk score.

Raw metrics, ERC, HHI, VaR/CVaR terminology, methodology and data-quality fields remain under a collapsed:

```text
Technical details & methodology
```

This preserves full information while reducing cognitive load.

---

## 11. Portfolio page UX

Primary information hierarchy should favor actual ownership over diagnostics:

```text
Portfolio summary
→ Holdings
→ Professional fund-manager review / portfolio intelligence
→ Dividends / income
→ deeper Risk / Performance diagnostics
```

Do not let a huge risk grid push actual holdings out of the primary viewport.

### Holding rows

- ticker uppercase;
- expandable broker/account detail;
- `INFO` button at the far end of each holding row;
- the old `(i)` icon beside ticker was removed.

The `INFO` control is currently reserved for a future fundamental-analysis overlay. Do not invent the full fundamental-analysis subsystem unless requested.

---

## 12. Professional Fund Manager Review

Portfolio includes a deterministic professional review layer that synthesizes evidence already stored in QPort.

It considers:

- construction/concentration;
- risk evidence readiness;
- performance maturity;
- accounting P/L;
- cash/liquidity;
- dividend income/tax;
- broker/account coverage;
- operational exceptions;
- monitoring priorities.

It must lower confidence when history is immature instead of pretending the evidence is decision-grade.

The review is **not** a trade recommendation engine. Monitoring priorities may say to review concentration, data quality, thesis integrity or reconciliation; they must not silently create trade instructions.

---

## 13. AI export

AI export schema is designed for audit, not a pretty summary only. It includes broad evidence categories such as:

- current accounting;
- holdings;
- tax lots by broker/account;
- dividend receipts by broker/account;
- canonical dividend provider history;
- complete effective ledger and metadata;
- corrections;
- corporate actions;
- settlement;
- reconciliation;
- security master;
- operational exceptions;
- P/L attribution;
- activity chain/integrity;
- snapshot history returned by API;
- data lineage;
- performance methodology;
- strategic cash policy;
- full machine-readable payload.

Known limitation: client-side export no longer truncates its inputs, but some server/API endpoints may still have finite return limits. Do not claim mathematically unlimited history without verifying backend pagination/limits.

---

## 14. Appearance / accessibility

QPort keeps a terminal/monospace identity, but readability takes priority over tiny text.

Current accessibility direction:

- body around 15px desktop;
- table/data text roughly 13.5–14px;
- secondary text about 13px;
- long text uses comfortable line height;
- uppercase reserved mainly for navigation/status/table semantics rather than all prose headings;
- semantic colors should have meaning rather than decorative overuse.

### Custom palette overlay

The old light/dark switch was removed.

Default is always QPort dark. QPort no longer follows OS `prefers-color-scheme`.

Navigation now exposes a compact `COLORS`/`MÀU` overlay where user can customize:

```text
background
primary text
secondary text
muted text
accent / links
positive / ready
warning / building
negative / error
information
```

Palette is stored in browser `localStorage` under:

```text
qport-appearance-v1
```

Stored appearance is applied before React hydration. Card/input/border/overlay colors are derived from background + primary text so users do not need to manage every surface token.

`Reset default dark` clears custom appearance.

---

## 15. Navigation / product surface

Normal-user primary navigation remains intentionally small:

```text
Portfolio
Transactions
Performance
Guide
```

Advanced routes remain accessible but are intentionally omitted from primary nav:

```text
/risk
/snapshots
/operations
/logs
/settings
```

Legacy optimizer/research/run/combo product surfaces were removed from normal product flow. Do not reintroduce optimizer-centric navigation unless explicitly requested.

---

## 16. Institutional-lite capabilities that must remain available

Although primary UX is simple, the underlying accounting/control layer retains:

- IBOR-style book state;
- FIFO tax lots;
- broker/account identities;
- settlement-aware cash;
- broker reconciliation;
- corporate actions;
- security master;
- NAV controls/restatement;
- P/L attribution;
- append-only correction audit;
- activity hash/integrity chain;
- operational exceptions.

Do not delete these capabilities merely because they are hidden from primary navigation.

---

## 17. UI / design language

Desired visual character:

```text
terminal / quant workstation
flat surfaces
thin borders
no decorative gradients/shadows
compact but readable
responsive
EN/VI
```

Responsive expectations:

- mobile-first behavior;
- forms stack on narrow screens;
- wide tables scroll horizontally;
- desktop/tablet tables fill their cards;
- dense institutional tables may keep an explicit minimum width instead of crushing columns.

Use color semantically:

```text
accent/green → action / active / ready / positive
warning      → building / attention
red          → negative / error
info         → neutral information
primary text → titles / values / core reading
secondary    → labels / explanations
```

---

## 18. Completed progress summary

Major work completed in the current Buy & Hold refactor cycle:

- Buy & Hold philosophy replaced annual-allocation/optimizer emphasis.
- Portfolio became the primary start surface.
- EN/VI product UX and full user guides added.
- Authentication and admin-only isolation implemented.
- Transaction ↔ Holding synchronization kept ledger-derived.
- Broker/account and FIFO tax-lot accounting retained.
- Vietnamese dividend tax treatment implemented.
- Dividend provider cache/canonicalization and cross-provider dedupe improved.
- Automatic dividend posting kept idempotent.
- Broker-level dividend receipt attribution added.
- Manual dividend entry removed from normal Transaction form.
- BUY preserved for paid rights/new issuance.
- Holdings expanded source table enriched.
- `INFO` button moved to end of holding row.
- AI audit export expanded substantially.
- D1 backfill bug fixed so new holdings receive meaningful history.
- Market-history sync readiness surfaced to user.
- Risk and Performance evidence/readiness presentation expanded.
- Portfolio information hierarchy moved Holdings ahead of deep diagnostics.
- Professional Fund Manager Review added.
- Typography/accessibility enlarged for comfortable reading.
- Theme toggle replaced by custom color palette overlay; default is dark.
- Risk page simplified for normal investors while preserving technical details under disclosure.

---

## 19. Known limitations / future work

These are known and should not be accidentally misrepresented as solved:

1. **Fundamental INFO overlay** — button exists, full fundamental-analysis implementation is not yet defined.
2. **Risk data lineage** — long-window analytics series adjustment around corporate actions may still be marked `UNVERIFIED`; verify provider adjustment semantics before making strong claims.
3. **AI export total-history guarantee** — client does not truncate, but backend/API limits may still exist.
4. **Legacy dividend broker attribution** — old automatic dividend events created before `broker_account_allocations` may fall back to `UNASSIGNED/PRIMARY`; historical backfill would need entitlement-date reconstruction.
5. **Dividend fuzzy dedupe** — cross-provider near-date matching is intentionally tolerant; if legitimate close-together equal-value events are ever suppressed, tighten fuzzy matching so same-source rows require stronger identity.
6. **CI evidence** — direct commits through the connector may not expose workflow runs/statuses. Verify separately before stating CI is green.
7. **Appearance persistence** — custom colors are browser-local via `localStorage`, not a server-side user preference.

---

## 20. Rules for the next AI/developer

Before implementing a new feature, ask whether it preserves these boundaries:

### Portfolio state

```text
Does it mutate shares/cash?
→ must be an explicit effective ledger event.
```

### Risk/quant analytics

```text
Does it produce a metric/reference?
→ information only unless the user explicitly designs a separate execution policy.
```

### ERC

```text
reference only
not portfolio target
not automatic rebalance
```

### Corporate-action/provider data

```text
provider discovery must not silently rewrite historical holdings
except through the defined verified/idempotent automatic posting path
```

### UX

```text
simple user-facing layer first
advanced institutional/quant evidence behind progressive disclosure
```

### Missing data

```text
missing != zero
building != error
stale != fresh
```

### Source of truth

```text
ledger > holdings UI
stored evidence > invented value
main branch > this document when they disagree
```

---

## 21. Recommended reading order for a new AI session

1. `AI_WORKING_CONTEXT.md` — this handoff.
2. `BUY_AND_HOLD_SYSTEM_SPEC.md` — product architecture/philosophy.
3. `README.md` — runtime and user-facing overview.
4. `python/portfolio/service.py` — current orchestration/runtime semantics.
5. `python/portfolio/accounting.py` and tax policy — ledger/accounting truth.
6. `python/portfolio/risk.py` — quantitative diagnostics and ERC reference.
7. `frontend/src/pages/PortfolioDashboardPage.jsx` and `PortfolioPage.jsx` — main UX.
8. `frontend/src/pages/RiskPage.jsx` — progressive risk UX.
9. `frontend/src/components/FundManagerReview.jsx` — professional synthesis layer.
10. `frontend/src/lib/aiExport.js` — audit/export contract.
11. relevant tests under `python/portfolio/tests/` before changing behavior.

If a future change conflicts with this file and current `main`, trust verified current code, then update this handoff so it remains useful.
