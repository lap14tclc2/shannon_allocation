# Portfolio Allocation — Current Implementation Specification

**Document type:** AI implementation/context specification  
**Status:** AS-IS specification derived from the current codebase  
**Project:** `portfolio_allocation`  
**Primary language:** TypeScript  
**Domain:** Quantitative portfolio allocation and rebalancing for equities  
**Currency assumption:** VND  
**Architecture status:** Working prototype / personal portfolio management application

---

# 1. Purpose

This project is a quantitative portfolio allocation and rebalancing application.

Its current purpose is to answer:

1. What should the target weight of each asset be?
2. How far is the current portfolio from those targets?
3. Should each asset be held, bought, or sold?
4. How much of the desired rebalance can actually be funded?
5. What would the portfolio approximately look like after executing those recommendations?

The current quantitative model combines:

- Equal Risk Contribution (ERC)
- Annual target allocation
- Target-relative drift bands
- Shannon-style rebalancing
- Sell-to-buy funding
- Optional cash reserve funding
- Snapshot-based portfolio history

The system is deterministic and rule-based.

It does **not** currently predict future prices.

---

# 2. Core Philosophy

The current system follows this conceptual flow:

```text
Portfolio holdings
        +
Historical price data
        +
Cash reserve
        ↓
Historical data validation
        ↓
Return calculation
        ↓
Covariance matrix
        ↓
Equal Risk Contribution
        ↓
Annual target weights
        ↓
Compare current weights to targets
        ↓
NORMAL / SOFT / HARD classification
        ↓
HOLD / BUY / SELL recommendation
        ↓
Funding allocation
        ↓
Simulated post-trade portfolio state
        ↓
Snapshot persistence
```

The main principle is:

```text
Data
  ↓
Mathematics
  ↓
Rules
  ↓
Portfolio decision
```

Not:

```text
News
  ↓
Opinion
  ↓
Prediction
  ↓
Trade
```

---

# 3. Important Scope Boundary

This document describes **what the repository currently implements**.

An AI modifying this project MUST NOT assume the following features already exist:

- authentication
- logged-in users
- trade ownership
- real broker execution
- execution confirmation
- pending trade approval
- suggestion staging
- stock screening
- VN100 automatic universe selection
- Vnstock automatic downloading
- live market-price ingestion
- hourly price refresh
- market regime detection
- momentum strategy
- machine learning
- transaction fees
- taxes
- Vietnamese exchange lot-size enforcement
- broker integration

These may be future features, but they are not part of the current implementation.

---

# 4. Technology Stack

## Backend

```text
TypeScript
Node.js
Native node:http server
tsx
```

There is no Express, Fastify, NestJS, Django, Flask, or similar web framework.

The HTTP server is created directly using:

```ts
http.createServer()
```

## Frontend

The client uses:

```text
HTML
CSS
Vanilla TypeScript
DOM APIs
ES modules
fetch()
```

There is no React, Angular, Vue, Svelte, or other UI framework.

Client TypeScript is transpiled to JavaScript dynamically by the backend when requested.

## Persistence

Two main environments exist.

### Local development

Primary persistence:

```text
filesystem
```

Important directories:

```text
data/
snapshots/
```

### Vercel/serverless

Primary persistence:

```text
PostgreSQL
```

Supported connection variables:

```text
POSTGRES_URL
POSTGRES_URL_NON_POOLING
DATABASE_URL
```

An in-memory store also exists as a runtime fallback.

## Testing

```text
Vitest
Supertest
```

---

# 5. Main Source Layout

```text
portfolio_allocation/
│
├── api/
│   └── index.ts
│
├── data/
│   ├── ACB.csv
│   ├── DGC.csv
│   ├── FPT.csv
│   ├── IDC.csv
│   ├── REE.csv
│   └── VNM.csv
│
├── docs/
│   ├── req.md
│   └── spec.md
│
├── snapshots/
│   └── YYYY-MM-DD/
│       └── *.txt
│
├── src/
│   ├── app.ts
│   ├── server.ts
│   │
│   ├── client/
│   │   ├── api.ts
│   │   ├── main.ts
│   │   ├── style.css
│   │   └── ui.ts
│   │
│   ├── config/
│   │   └── index.ts
│   │
│   ├── routes/
│   │   └── api.routes.ts
│   │
│   ├── services/
│   │   ├── backlog.service.ts
│   │   ├── erc.service.ts
│   │   ├── history.service.ts
│   │   ├── memory-store.service.ts
│   │   ├── portfolio-state.service.ts
│   │   ├── portfolio.service.ts
│   │   ├── postgres-store.service.ts
│   │   └── storage.service.ts
│   │
│   ├── types/
│   │   └── index.ts
│   │
│   └── utils/
│       └── logger.ts
│
├── tests/
│   ├── api.integration.test.ts
│   └── services.integration.test.ts
│
├── index.html
├── package.json
├── output.json
├── tsconfig.json
└── vercel.json
```

---

# 6. Domain Model

## 6.1 Stock

```ts
interface Stock {
  ticker: string;
  averageCostBasis: number;
  currentShares: number;
  currentPrice: number;
  active?: boolean;
}
```

Meaning:

- `ticker`: stock symbol
- `averageCostBasis`: historical average acquisition price
- `currentShares`: current share quantity
- `currentPrice`: price used for current portfolio valuation
- `active`: optional switch controlling rebalance eligibility

Current market value:

```text
marketValue = currentShares × currentPrice
```

---

# 7. Portfolio NAV

For each stock:

```text
value_i = currentShares_i × currentPrice_i
```

Equity NAV:

```text
equityNAV = Σ value_i
```

Total NAV:

```text
totalNAV = equityNAV + cashReserve
```

Current asset weight:

```text
currentWeight_i = value_i / totalNAV
```

Cash therefore participates in the denominator.

This means equity weights may sum to less than 100% when cash exists.

---

# 8. Historical Market Data

Historical data is loaded per ticker.

Expected filename convention:

```text
data/<TICKER>.csv
```

The parser accepts comma-separated or tab-separated data.

Supported date column names include:

```text
date
datetime
time
timestamp
```

Supported price columns are searched in the following order:

```text
adj close
adjusted close
close
price
```

Rows are rejected when:

- date is invalid
- price is not finite
- price <= 0

Dates are normalized to:

```text
YYYY-MM-DD
```

Duplicate dates are deduplicated.

The final series is sorted ascending by date.

Minimum required observations:

```text
60
```

---

# 9. ERC Configuration

Current configuration:

```text
annualizationFactor = 252
minimumObservations = 60
lookbackYears = 5

normalBand = 10%
softBand = 20%
```

---

# 10. Annual ERC Risk Window

The allocation year is the current system year.

For allocation year:

```text
Y
```

the risk window is:

```text
start = Y - 5 years, January 1
end   = Y - 1 year, December 31
```

Example:

```text
Allocation year: 2026

Risk window:
2021-01-01
through
2025-12-31
```

The current year is deliberately excluded from annual ERC calibration.

---

# 11. ERC Data Alignment

For every portfolio ticker:

1. Load historical data.
2. Filter history to the annual risk window.
3. Determine dates shared by every asset.
4. Keep only common dates.

If the common intersection contains fewer than:

```text
60 observations
```

ERC calculation fails.

This prevents covariance estimation from using differently aligned trading dates.

---

# 12. Return Calculation

The system uses daily logarithmic returns:

```text
r_t = ln(P_t / P_(t-1))
```

No arithmetic percentage returns are used for ERC.

---

# 13. Covariance

Sample covariance is calculated as:

```text
cov(X,Y) =
Σ((X_i - mean(X)) × (Y_i - mean(Y)))
-------------------------------------
                 N - 1
```

Daily covariance is annualized using:

```text
annualCovariance = dailyCovariance × 252
```

Annualized single-asset volatility:

```text
annualVolatility =
dailyStandardDeviation × sqrt(252)
```

---

# 14. Covariance Validation

The covariance matrix must be symmetric.

Validation tolerance:

```text
1e-10
```

Conceptually:

```text
cov[i][j] ≈ cov[j][i]
```

Otherwise ERC processing fails.

---

# 15. Equal Risk Contribution

Let:

```text
w = portfolio weights
Σ = covariance matrix
```

Portfolio variance:

```text
σ²p = wᵀ Σ w
```

Portfolio risk:

```text
σp = sqrt(wᵀ Σ w)
```

Marginal covariance vector:

```text
m = Σw
```

Component risk contribution:

```text
CRC_i = w_i × m_i / σp
```

Relative risk contribution:

```text
RC_i = CRC_i / σp
```

The ERC target for a portfolio containing `N` assets is:

```text
RC_i = 1 / N
```

for every asset.

Example with three stocks:

```text
ACB risk contribution ≈ 33.33%
DGC risk contribution ≈ 33.33%
FPT risk contribution ≈ 33.33%
```

This does **not** mean equal capital weights.

---

# 16. ERC Solver

Initial weights:

```text
1 / N
```

for every stock.

Maximum solver iterations:

```text
1000
```

Convergence tolerance:

```text
max |RC_i - 1/N| < 1e-7
```

Final validation requires:

```text
ercError < 1e-5
```

If any risk contribution becomes non-positive during solving, the solver throws:

```text
ERC solver failed.
```

---

# 17. ERC Output

ERC returns:

```ts
interface ERCResult {
  weights: number[];
  volatility: number[];
  riskContributions: number[];
  portfolioRisk: number;
  observations: number;
  diagnostics: ERCDiagnostics;
}
```

Diagnostics contain:

```text
valid
observations
actual aligned date range
configured risk window
portfolio risk
portfolio variance
weight sum
component-risk sum
relative-risk sum
ERC error
```

---

# 18. Annual Target

ERC is converted into an annual target:

```ts
interface AnnualTarget {
  year: number;
  allocationDate: string;
  riskWindow: RiskWindow;
  method: string;
  targets: Record<string, number>;
  locked: boolean;
  createdAt: string;
  diagnostics?: ERCDiagnostics;
}
```

Example:

```json
{
  "year": 2026,
  "allocationDate": "2026-01-01",
  "method": "ERC",
  "targets": {
    "ACB": 0.3942,
    "DGC": 0.2482,
    "FPT": 0.3576
  },
  "locked": true
}
```

---

# 19. Annual Target Lifecycle

When an analysis starts:

```text
Read existing annual target
        ↓
Does a locked target exist for current year?
        ↓
       yes
        ↓
Compare ticker universe
```

If the exact ticker set matches:

```text
reuse existing annual target
```

If the ticker set differs:

```text
recalculate ERC
        ↓
create new annual target
        ↓
lock new target
```

Therefore:

> The current implementation does NOT preserve the old annual target when the ticker universe changes.

This behavior is important.

Do not implement future logic based on the assumption that universe changes merely create a warning.

---

# 20. Manual Annual Reset

Endpoint:

```text
POST /api/annual-reset
```

forces:

```text
new ERC calculation
→ new annual target
→ locked target
```

for the current allocation year.

---

# 21. Shannon-Style Drift Model

Once target weights exist, the current portfolio is compared against them.

For asset `i`:

```text
drift_i =
currentWeight_i - targetWeight_i
```

Example:

```text
Target = 25%
Current = 32%

Drift = +7 percentage points
```

---

# 22. Rebalancing Bands

Bands are relative to each asset's ERC target.

Normal band:

```text
lower = target × 0.90
upper = target × 1.10
```

Soft outer limits:

```text
lower = target × 0.80
upper = target × 1.20
```

Example:

```text
ERC target = 30%

NORMAL:
27% → 33%

SOFT envelope:
24% → 36%
```

Classification:

```text
within NORMAL boundaries
    → NORMAL

outside NORMAL but within SOFT boundaries
    → SOFT

outside SOFT boundaries
    → HARD
```

---

# 23. Recommendation Rules

For an active asset:

```text
NORMAL
→ HOLD
```

Outside NORMAL:

```text
drift < 0
→ BUY

drift >= 0
→ SELL
```

For inactive assets:

```text
active === false
→ HOLD
```

regardless of drift.

Therefore SOFT and HARD currently differ in classification/severity only.

They do not use different trade-sizing algorithms.

---

# 24. Target Trade Amount

Target portfolio value:

```text
targetValue_i =
targetWeight_i × totalNAV
```

If asset is outside NORMAL:

```text
targetTradeAmount_i =
|targetValue_i - currentValue_i|
```

Inside NORMAL:

```text
targetTradeAmount_i = 0
```

Inactive asset:

```text
targetTradeAmount_i = 0
```

The current model attempts to rebalance directly toward the ERC target rather than merely back to the nearest band boundary.

---

# 25. Funding Model

The project uses a sell-to-buy funding mechanism.

Calculate:

```text
totalSell =
Σ targetTradeAmount for SELL recommendations

totalBuy =
Σ targetTradeAmount for BUY recommendations
```

Available buy funding:

```text
availableFunding =
totalSell + cashReserve
```

Funded buy total:

```text
fundedBuyTotal =
min(totalBuy, availableFunding)
```

---

# 26. Buy Scaling

If enough funding exists:

```text
all BUY requests are funded completely
```

If insufficient funding exists:

```text
buyScale =
fundedBuyTotal / totalBuy
```

Each BUY receives:

```text
fundedTradeAmount_i =
targetTradeAmount_i × buyScale
```

All buys are therefore scaled proportionally.

---

# 27. Sell Funding

SELL recommendations are currently assumed to be fully fundable:

```text
fundedTradeAmount =
targetTradeAmount
```

There is no partial sell scaling.

---

# 28. Hard Bank

The code exposes:

```text
hardBank = totalSell
```

Conceptually this represents capital released from overweight assets and made available for purchases.

---

# 29. Cash Deployment

Cash used for buys:

```text
cashDeployed =
min(
    cashReserve,
    max(0, fundedBuyTotal - totalSell)
)
```

Remaining cash:

```text
remainingCash =
cashReserve - cashDeployed
```

---

# 30. Share Calculation

For each recommendation:

```text
sharesToTrade =
fundedTradeAmount / price
```

Price selection:

```text
currentPrice
```

with fallback to:

```text
averageCostBasis
```

when necessary.

At this stage, `sharesToTrade` may be fractional.

---

# 31. Expected Portfolio Values

For BUY:

```text
expectedValue =
currentValue + fundedTradeAmount
```

For SELL:

```text
expectedValue =
currentValue - fundedTradeAmount
```

For HOLD:

```text
expectedValue =
currentValue
```

Expected weight:

```text
expectedWeight =
expectedValue / originalTotalNAV
```

The total NAV used here is not recalculated asset-by-asset.

---

# 32. Asset Analysis Result

Each asset returns approximately:

```ts
{
  ticker,
  averageCostBasis,
  currentShares,
  currentPrice,

  value,
  currentWeight,

  ercWeight,
  volatility,
  riskContribution,

  normal,
  soft,
  band,
  drift,

  recommendation,

  targetTradeAmount,
  fundedTradeAmount,
  sharesToTrade,

  expectedValue,
  expectedWeight,

  active
}
```

---

# 33. Portfolio Analysis Output

The portfolio-level result includes:

```text
generatedAt

nav
equityNav

cashReserve
cashDeployed
remainingCash

hardBank
fundedBuyTotal

annualTarget

erc

results[]
```

The `/api/analyze` route additionally attaches:

```text
inputs
portfolioState
```

---

# 34. Current “Executed State”

This is a critical implementation detail.

After recommendations are generated, `/api/analyze` currently calls:

```text
buildExecutedState()
```

The system therefore creates a projected post-allocation portfolio state immediately.

This state is **not confirmed broker execution**.

It is a simulation derived from recommendations.

Current flow:

```text
Analysis
   ↓
Recommendation
   ↓
Automatically construct simulated executed state
```

There is currently no:

```text
PENDING
→ USER CONFIRMS
→ EXECUTED
```

workflow.

Any future AI must preserve this distinction when describing the current system.

---

# 35. Integer Share Rounding

Although funding calculations allow fractional shares, the simulated portfolio state rounds shares to integers.

Trade shares:

```text
round(sharesToTrade)
```

BUY state:

```text
round(currentShares + sharesToTrade)
```

SELL state:

```text
max(
  0,
  round(currentShares - sharesToTrade)
)
```

This can introduce small differences between:

```text
expectedWeight
```

and:

```text
portfolioState.weight
```

because the former uses monetary funding while the latter uses rounded shares.

---

# 36. Simulated Holding State

A simulated holding contains:

```ts
interface Holding {
  ticker: string;
  shares: number;
  price: number;
  averageCost: number;
  marketValue: number;
  weight: number;

  active?: boolean;

  initialShares?: number;
  action?: 'HOLD' | 'BUY' | 'SELL';
  tradeShares?: number;
  ercTargetWeight?: number;
}
```

---

# 37. Portfolio State

```ts
interface PortfolioState {
  updatedAt: string;
  totalNav: number;
  equityNav: number;
  cashReserve: number;
  holdings: Holding[];
}
```

After simulated allocation:

```text
equityNAV =
Σ roundedShares × currentPrice
```

Total NAV:

```text
equityNAV + remainingCash
```

Weights are recalculated using this simulated total NAV.

---

# 38. Average Cost Limitation

The current simulated execution logic does not calculate a new weighted average cost after a BUY.

It effectively keeps:

```text
existing averageCostBasis
```

or falls back to current price.

Therefore:

> `averageCost` in simulated post-trade state is not a complete accounting-grade cost-basis engine.

Future work involving realized/unrealized P&L must address this explicitly.

---

# 39. Snapshot Model

Snapshots are central to current persistence.

Directory format:

```text
snapshots/
└── YYYY-MM-DD/
    └── <TICKERS>_<HHMMSS>.txt
```

Example:

```text
snapshots/
└── 2026-08-10/
    └── ACB_DGC_FPT_212720.txt
```

---

# 40. Snapshot Contents

A full snapshot can contain:

```text
1. Ticker input data
2. History validation section
3. ERC annual allocation
4. Shannon rebalancing
5. Portfolio state
6. Embedded JSON output
```

The JSON section acts as the most reliable structured representation when loading snapshots.

---

# 41. Snapshot Identity Rule

Before creating a new snapshot, the application compares the new input against the latest snapshot.

The comparison includes:

```text
cashReserve
ticker
averageCostBasis
currentShares
currentPrice
```

If all match:

```text
overwrite latest snapshot
```

If any parameter differs:

```text
create a new snapshot file
```

This prevents repeated analysis of identical inputs from generating unlimited snapshot files.

---

# 42. Snapshot Parsing

When loading an existing snapshot:

1. Try to locate the embedded `JSON_OUTPUT`.
2. Parse it as JSON.
3. If parsing fails, fall back to the legacy human-readable text parser.

This preserves compatibility with older snapshot formats.

---

# 43. Storage Architecture

## Local mode

Uses filesystem for:

```text
CSV history
snapshot files
legacy JSON files
event logs
```

## Vercel mode

Uses PostgreSQL tables:

```text
history_files
snapshot_records
app_state
```

### `history_files`

Stores:

```text
ticker
raw CSV text
updated_at
```

### `snapshot_records`

Stores:

```text
date
name
content
created_at
```

### `app_state`

Stores arbitrary JSON state by key, including:

```text
annual_target
portfolio_state
```

---

# 44. Initial Database Seeding

When PostgreSQL initializes, the server attempts to seed it from bundled filesystem data.

It imports:

```text
data/*.csv
snapshots/*/*.txt
```

using conflict-safe inserts.

This allows a Vercel deployment to start with repository-provided historical data and snapshots.

---

# 45. Memory Store

An in-memory store exists for:

```text
history
snapshots
annual target
portfolio state
output
output history
logs
```

It is runtime-only and non-durable.

It must not be treated as persistent storage.

---

# 46. API

Current API surface:

## Application

```text
GET /
```

Serve `index.html`.

---

## Client Assets

```text
GET /src/client/*
GET /client/*
```

Serve CSS or dynamically transpile TypeScript client modules.

---

## Latest Snapshot

```text
GET /api/snapshot/latest
```

Alias:

```text
GET /api/backlog
```

Returns:

```text
hasSnapshot
stocks
cashReserve
fullOutput
date
filename
```

---

## Snapshot Tree

```text
GET /api/snapshots/tree
```

Returns snapshot folders and files.

---

## Snapshot File

```text
GET /api/snapshots/file?date=<date>&name=<filename>
```

Loads one snapshot.

---

## Delete Snapshot

```text
DELETE /api/snapshots/file?date=<date>&name=<filename>
```

Deletes one snapshot.

---

## Historical Data

```text
GET /api/history/:ticker
```

Returns raw history content.

---

## Upload Historical Data

```text
POST /api/history/:ticker
```

Body:

```text
raw CSV/TSV text
```

The server validates the data before storing it.

---

## Analyze Portfolio

```text
POST /api/analyze
```

Request:

```json
{
  "stocks": [
    {
      "ticker": "ACB",
      "averageCostBasis": 19760,
      "currentShares": 19210,
      "currentPrice": 22650
    }
  ],
  "cashReserve": 50000000
}
```

Processing:

```text
parse payload
   ↓
load every ticker's history
   ↓
resolve annual ERC target
   ↓
calculate current ERC diagnostics
   ↓
build portfolio recommendation
   ↓
fund BUY recommendations
   ↓
build simulated executed state
   ↓
save snapshot
   ↓
return complete result
```

---

## Annual Target

```text
GET /api/annual-target
```

Returns current annual target.

---

## Reset Annual Target

```text
POST /api/annual-reset
```

Recalculates and locks the annual ERC allocation.

---

## Portfolio State

```text
GET /api/portfolio-state
```

Returns the state embedded in persisted storage/latest snapshot.

---

## Legacy Output

```text
GET /api/output
```

This reads the legacy configured `output.json`.

Current `/api/analyze` primarily persists snapshots rather than updating this file.

Treat this endpoint as legacy unless deliberately revived.

---

# 47. Browser UI

The frontend currently supports:

- add ticker
- remove ticker row
- input average cost
- input current shares
- input current price
- enter cash reserve
- upload ticker CSV
- detect existing ticker history
- run analysis
- view history validation
- view annual ERC allocation
- view portfolio risk
- view volatility
- view risk contribution
- view drift
- view bands
- view BUY/SELL/HOLD recommendation
- view target trade amount
- view funded trade amount
- view shares to trade
- view expected weights
- view simulated portfolio state
- browse snapshot tree
- load historical snapshots
- delete snapshots

---

# 48. Client Startup Flow

On page startup:

```text
GET latest snapshot
       ↓
Populate stock rows
       ↓
Populate cash reserve
       ↓
Check history availability
       ↓
Render existing output if available
       ↓
Load snapshot tree
```

If no snapshot exists:

```text
show empty stock row
```

---

# 49. Analyze Button Flow

```text
Read stock table
       ↓
Read cash reserve
       ↓
POST /api/analyze
       ↓
Render validation
       ↓
Render ERC
       ↓
Render Shannon results
       ↓
Render simulated state
       ↓
Reload state
       ↓
Refresh snapshot tree
```

---

# 50. Error Handling

At application level:

Unhandled route errors are converted to:

```json
{
  "error": "message"
}
```

with HTTP status:

```text
400
```

Missing routes return:

```text
404
```

Some specific handlers use their own:

```text
400
404
500
```

responses.

---

# 51. Server Lifecycle

Local server defaults to:

```text
PORT=3000
```

unless overridden.

It supports graceful shutdown for:

```text
SIGINT
SIGTERM
```

with a five-second forced shutdown timeout.

---

# 52. Vercel Entry Point

Vercel uses:

```text
api/index.ts
```

which:

```text
initializes storage
→ delegates request to the same requestListener
```

Local and Vercel deployments therefore reuse the same main routing logic.

---

# 53. Existing Tests

Current tests cover important integration paths.

## Service integration

Tests include:

- five-year risk-window calculation
- ERC calculation
- ERC weight sum
- volatility presence
- positive portfolio risk
- portfolio construction with cash
- snapshot overwrite for unchanged input
- new snapshot for changed input
- backlog parsing

## API integration

Tests include:

- serve index
- transpile client TypeScript
- analyze portfolio
- retrieve latest snapshot
- snapshot tree
- portfolio state
- historical data
- isolation between analyses using different cash reserves

---

# 54. Current Architectural Invariants

An AI modifying this repository should preserve these unless a new requirement explicitly changes them.

## INV-01 — Deterministic ERC

Given identical:

```text
ticker universe
historical prices
allocation year
```

ERC results should be deterministic.

---

## INV-02 — Common Dates Only

Covariance must use aligned observations shared by all portfolio assets.

---

## INV-03 — Annual Historical Window

Annual allocation must use only the configured previous-year lookback window.

---

## INV-04 — ERC Risk Equality

Successful ERC must satisfy approximately:

```text
RC_i = 1 / N
```

for all assets.

---

## INV-05 — Cash Included in NAV

Current portfolio weights must use:

```text
equityNAV + cashReserve
```

as denominator.

---

## INV-06 — Normal Band Means HOLD

Any active asset within the NORMAL band generates no trade.

---

## INV-07 — Underweight Means BUY

Outside NORMAL:

```text
currentWeight < targetWeight
→ BUY
```

---

## INV-08 — Overweight Means SELL

Outside NORMAL:

```text
currentWeight > targetWeight
→ SELL
```

---

## INV-09 — Sell Proceeds Fund Buys

Sell proceeds are part of available capital for BUY recommendations.

---

## INV-10 — Cash Is Secondary Funding

Cash reserve can supplement sell proceeds.

---

## INV-11 — No Unfunded Buys

Total funded BUY value must never exceed:

```text
totalSell + cashReserve
```

---

## INV-12 — Insufficient Funding Is Pro-Rata

When capital is insufficient, all BUY recommendations are scaled proportionally.

---

## INV-13 — Snapshot Is Historical Record

Analyses should preserve recoverable historical state through snapshots.

---

# 55. Current Code vs Old Documentation

The repository's existing `docs/spec.md` must NOT be treated as authoritative without checking source code.

Important differences include:

## Difference 1 — Suggestions Layer

Old documentation describes:

```text
PENDING
APPROVED
REJECTED
```

suggestions.

Current code has no active suggestions service or suggestions API.

---

## Difference 2 — Execution Approval

Old documentation suggests:

```text
recommendation
→ approval
→ execution
```

Current code does:

```text
recommendation
→ simulated executed state
```

immediately during `/api/analyze`.

---

## Difference 3 — Universe Change

Old documentation says annual allocation remains immutable and universe changes produce warnings.

Current code compares the ticker set and recalculates ERC when that set changes.

---

## Difference 4 — Solver Iterations

Old documentation mentions:

```text
10,000
```

iterations.

Current code uses:

```text
1,000
```

maximum iterations.

---

## Difference 5 — Persistence

Old documentation emphasizes separate JSON state files.

Current implementation increasingly uses snapshots as the primary local source of truth and PostgreSQL `app_state` in Vercel mode.

---

# 56. Known Technical Limitations

The current implementation has several limitations that future development should understand.

## 56.1 No Real Execution Ledger

The application cannot distinguish:

```text
recommended trade
```

from:

```text
broker-executed trade
```

in a proper execution workflow.

---

## 56.2 No User Ownership

There is no authentication.

There is no:

```text
createdBy
executedBy
userId
```

associated with trades or snapshots.

---

## 56.3 No Automatic Market Data

Users manually provide current prices.

Historical CSV data is manually uploaded or bundled.

---

## 56.4 No Vnstock Integration

The repository does not currently call Vnstock.

---

## 56.5 No Transaction Costs

Trade calculations ignore:

```text
broker fee
tax
slippage
```

---

## 56.6 No Vietnamese Lot-Size Rules

Funding is first calculated fractionally and simulated execution then rounds to an integer share.

No exchange-specific lot-size logic is implemented.

---

## 56.7 Cost Basis Is Incomplete

A BUY does not recompute weighted average cost basis.

---

## 56.8 No Cash Target Allocation

Cash is funding/reserve capital.

ERC itself allocates only among stocks supplied to the engine.

Cash is not treated as an ERC asset.

---

## 56.9 No Portfolio Universe Engine

The user manually chooses tickers.

No VN100 screening logic exists.

---

## 56.10 No Regime Engine

There is currently no BULL/BEAR/NEUTRAL regime detection.

---

# 57. Features That Should Be Considered Future Extensions

These are reasonable future capabilities but MUST remain separate from the AS-IS implementation.

```text
Vnstock data provider
VN100 universe
quantitative stock screener
automatic D1 history synchronization
latest-price synchronization
regime classification
trade proposal entity
execution confirmation
trade ledger
authentication
logged-user ownership
fees and tax model
Vietnamese lot sizing
portfolio performance analytics
CAGR
Sharpe
Sortino
maximum drawdown
benchmark comparison
```

---

# 58. Recommended Future Domain Separation

When the system is expanded, preferred conceptual boundaries are:

```text
MarketData
    ↓
Universe
    ↓
QuantResearch
    ↓
AllocationPolicy
    ↓
PortfolioDecision
    ↓
TradeProposal
    ↓
TradeExecution
    ↓
PortfolioLedger
```

Current ERC and Shannon logic should belong to:

```text
AllocationPolicy
PortfolioDecision
```

and should not directly own broker execution.

---

# 59. Recommended Future End-State

A more mature architecture can eventually become:

```text
                VNStock / Market Data
                         │
                         ▼
                 Market Data Layer
                         │
                         ▼
                     VN100
                         │
                         ▼
                 Quant Screener
                         │
                         ▼
                Candidate Universe
                         │
                         ▼
                  ERC Allocator
                         │
                         ▼
               Annual Target Policy
                         │
                         ▼
               Regime Risk Modifier
                         │
                         ▼
               Shannon Rebalancer
                         │
                         ▼
                 Trade Proposal
                         │
                         ▼
                  User Approval
                         │
                         ▼
                Broker Execution
                         │
                         ▼
                  Trade Ledger
                         │
                         ▼
                 Portfolio State
```

This is a future direction, not the current architecture.

---

# 60. Instructions for an AI Working on This Repository

Before implementing any task:

1. Read `src/types/index.ts`.
2. Read `src/config/index.ts`.
3. Read `src/services/history.service.ts`.
4. Read `src/services/erc.service.ts`.
5. Read `src/services/portfolio.service.ts`.
6. Read `src/services/portfolio-state.service.ts`.
7. Read `src/services/storage.service.ts`.
8. Read `src/routes/api.routes.ts`.
9. Read `src/client/main.ts`.
10. Read both integration test files.

Do not implement behavior solely from `docs/spec.md`.

When documentation and code disagree:

```text
current code
> current tests
> current runtime behavior
> old documentation
```

unless the task explicitly requires changing the architecture.

---

# 61. AI Change Protocol

For every implementation task, the AI should identify:

```text
CURRENT BEHAVIOR
REQUESTED BEHAVIOR
INVARIANTS AFFECTED
FILES AFFECTED
TESTS REQUIRED
MIGRATION RISK
```

Before changing quantitative logic, explicitly state whether the change affects:

```text
historical window
returns
covariance
ERC weights
risk contribution
NAV
bands
trade sizing
funding
share rounding
snapshot compatibility
```

Quantitative behavior must not be silently modified.

---

# 62. Definition of Correctness

A change to this project is correct only if:

```text
TypeScript compiles
+
lint passes
+
Vitest passes
+
existing snapshots remain readable where required
+
ERC mathematical invariants remain valid
+
NAV remains internally consistent
+
funded buys never exceed available capital
+
annual-target behavior is explicit
+
no recommendation is silently represented as real broker execution
```

---

# 63. Concise System Definition

The current application can be summarized as:

> A deterministic TypeScript portfolio-allocation application that derives annual Equal Risk Contribution targets from aligned historical daily price data, classifies current holdings by target-relative drift bands, generates Shannon-style BUY/SELL/HOLD recommendations, funds purchases from sells and cash reserves, simulates integer-share post-trade holdings, and persists each analysis as a recoverable snapshot.

---

# 64. Mental Model for AI

Use this mental model when reasoning about the repository:

```text
Historical Data
      │
      ▼
     ERC
      │
      ▼
Annual Target
      │
      ├──────────────┐
      │              │
      ▼              ▼
Current Holdings    Cash
      │              │
      └──────┬───────┘
             ▼
            NAV
             │
             ▼
          Drift
             │
             ▼
          Bands
             │
             ▼
      BUY / SELL / HOLD
             │
             ▼
       Funding Engine
             │
             ▼
     Suggested Trades
             │
             ▼
Simulated Post-Trade State
             │
             ▼
          Snapshot
```

That is the current system.