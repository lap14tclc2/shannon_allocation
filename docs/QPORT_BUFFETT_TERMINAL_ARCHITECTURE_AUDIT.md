# QPort Buffett Terminal Architecture Audit (T00)

> **Document Status:** Completed Audit Report  
> **Task Reference:** [TASK-20260909-115](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260909-115-qport-buffett-terminal-audit.md)  
> **Date:** 2026-09-09  
> **Scope:** Full codebase classification across `python/portfolio/`, `app/`, `api/`, and `frontend/src/`

---

## 1. Executive Summary

This architecture audit establishes the exact module classification matrix, dependency graph, and legacy route migration map required for transforming QPort into a professional personal capital decision system inspired by Warren Buffett and Charlie Munger.

---

## 2. Component Classification Matrix

Legend:
- **`KEEP`**: Core domain logic, models, or UI components retained without structural change.
- **`REUSE`**: Utilities, storage adapters, or sub-engines consumed as dependencies.
- **`REFACTOR`**: Modules modified to align with Buffett-Munger decision rules, value trap gate, or balance sheet domain.
- **`MERGE`**: Legacy modules/pages combined into new consolidated workspaces (`Terminal`, `Business`, `Capital`, `History`).
- **`HIDE`**: Legacy UI routes removed from main navigation but accessible directly during transition.
- **`DEPRECATE`**: Legacy logic or routes marked for phased removal post-verification.
- **`DELETE_LATER`**: Unused code removed after zero-dependency confirmation.

### 2.1 Backend Modules (`python/portfolio/`)

| Path / Module | Purpose | Action | Rationale | Target Owner |
|---|---|---|---|---|
| `python/portfolio/value_engine/` | Valuation models (DCF, EPV, RIM, SOTP, Archetypes) | **REFACTOR** | Integrate strict Value Trap Gate, Bear case protection, and missing data degradation rules. | Core Valuation Engine |
| `python/portfolio/value_engine/engine.py` | Main valuation router & report generator | **REFACTOR** | Route model selection strictly through archetype rules; output Bear/Base/Bull IV and confidence. | Core Valuation Engine |
| `python/portfolio/value_engine/margin_of_safety.py` | MOS calculations | **REFACTOR** | Require quality gate & Bear IV protection before MOS is marked attractive. | Core Valuation Engine |
| `python/portfolio/allocation/` | Candidate discovery & portfolio allocation | **REFACTOR** | Remove risk-driven REDUCE triggers; enforce personal available capital gate & position capacity. | Decision Engine |
| `python/portfolio/financial_data/` | Financial data catalog & facts extraction | **REUSE** | Acts as canonical facts provider. Maintain isolation from raw external vendors. | Data Layer |
| `python/portfolio/market_data.py` | Price fetching & historical candles | **REUSE** | Used for price snapshots and crash stress tests. Cannot trigger BUY/SELL decisions directly. | Data Layer |
| `python/portfolio/risk.py` | VaR, CVaR, risk contribution, correlation | **REFACTOR** | Demote from decision driver to advanced diagnostic overlay only. | Diagnostic Layer |
| `python/portfolio/permanent_loss_risk.py` | Permanent loss metrics & thesis monitoring | **REUSE** | Provide structural risk flags for Value Trap Gate & Business Review. | Quality Layer |
| `python/portfolio/accounting.py` | NAV, cost basis, transactions ledgers | **KEEP** | Core ledger invariant: transactions & split events alter holdings, price fluctuations do not. | Ledger Layer |
| `python/portfolio/activity.py` | Activity recording & transaction validation | **KEEP** | Essential ledger recording service. | Ledger Layer |
| `python/portfolio/dividends.py` | Dividend tracking & reconciliation | **KEEP** | Pure cashflow recording & dividend yield metrics. | Ledger Layer |
| `python/portfolio/personal_finance/` | Personal Balance Sheet & Fortress Engine | **NEW** | New package for personal balance sheet, survival reserve, and long-term capital availability. | Balance Sheet Domain |
| `python/portfolio/policy/` | Buffett/Munger Decision Policy Engine | **NEW** | New package enforcing deterministic state engine (BUY, HOLD, WAIT, REVIEW, SELL). | Decision Engine |
| `python/portfolio/coach/` | AI Buffett/Munger Evidence Coach | **NEW** | Explanation & challenge layer operating strictly on deterministic decision evidence payloads. | AI Coach Layer |

### 2.2 API Layer (`app/main.py`)

| Endpoint Route | Current Functionality | Action | Target Mapping |
|---|---|---|---|
| `/api/portfolio/summary` | Portfolio holdings & NAV | **REFACTOR** | Surface `InvestmentDecisionContext` aggregate for Terminal homepage. |
| `/api/portfolio/valuation` | Valuation reports | **REFACTOR** | Return full valuation evidence, Bear/Base/Bull IVs, and Value Trap statuses. |
| `/api/portfolio/allocation` | Allocation recommendations | **REFACTOR** | Limit capital deployment to `Available Long-Term Capital`. Remove volatility rebalancing. |
| `/api/portfolio/risk` | Risk contribution & VaR | **REFACTOR** | Return strictly as diagnostic payload. Exclude trade recommendations. |
| `/api/portfolio/personal-finance` | N/A | **NEW** | Manage balance sheet inputs, fortress health, and stress engine scenarios. |
| `/api/portfolio/decision/:symbol` | N/A | **NEW** | Expose deterministic decision context, rule triggers, and coach explanation. |

### 2.3 Frontend Workspace Mapping (`frontend/src/`)

| Legacy Page | Primary Content | Target Action | New Workspace Location |
|---|---|---|---|
| `PortfolioDashboardPage.jsx` | NAV, holdings, asset distribution | **MERGE / REFACTOR** | `/terminal` (Terminal Homepage — Section B Portfolio & Personal Fortress) |
| `ValuationPage.jsx` | IV models, MOS, quality pillars | **MERGE / REFACTOR** | `/business/:symbol` (Business Workspace) |
| `ScreenerPage.jsx` | Universe filtering & sorting | **MERGE** | `/business` (Business Discovery & Watchlist) |
| `AllocationPage.jsx` | Capital deployment recommendations | **MERGE / REFACTOR** | `/capital` (Capital Workspace) |
| `TransactionsPage.jsx` | Transaction ledger & activity | **MERGE** | `/history` (Compounding History Workspace) |
| `PerformancePage.jsx` | TWR, NAV growth, returns | **MERGE** | `/history` (Compounding History Workspace) |
| `DividendHistoryPage.jsx` | Dividend records & yield | **MERGE** | `/history` & `/capital` |
| `RiskPage.jsx` | Risk analytics & concentration | **HIDE** | Accessible as diagnostic link from `/terminal` |
| `SnapshotsPage.jsx` | Historical NAV snapshots | **HIDE / MERGE** | `/history` |
| `GuidePage.jsx` | System documentation | **REUSE** | Help modal / drawer in `/terminal` |
| `OperationsPage.jsx` | Maintenance operations | **DEPRECATE** | Replaced by `/admin` tool suite |

---

## 3. Explicit Dependency Graph

### Current Dependency Flow (Fragmented & Risk-Contaminated)
```text
Raw Market Data / Vendor Specs
       │
       ├──► Valuation Engine ────────┐
       ├──► Risk Engine (VaR/CVaR) ──┼──► Allocation Engine ──► Trade Signals (REDUCE / BUY)
       └──► Accounting / NAV ────────┘
```

### Target Architectural Dependency Flow (Buffett-Munger Clean Precedence)
```text
                      Canonical Financial Facts
                                 │
                                 ▼
                         Business Analysis
                                 │
                          Valuation Engine
                                 │
                                 ▼
Personal Balance Sheet ───────────────┐
                                      │
Portfolio Holdings Ledger ────────────┼──► InvestmentDecisionContext
                                      │              │
Available Long-Term Capital ──────────┘              ▼
                                          Business Review & Value Trap Gate
                                                     │
                                                     ▼
                                          Buffett/Munger Policy Engine
                                                     │
                                      ┌──────────────┴──────────────┐
                                      ▼                             ▼
                               Deterministic State            Decision Evidence Payload
                                      │                             │
                                      ▼                             ▼
                               New Terminal UI               Buffett/Munger AI Coach
```

---

## 4. Risk Mitigation & Regression Baseline Plan

### 4.1 Golden Baseline Preservation
Before implementing T02–T20:
- Baseline symbols: **`ACB`**, **`DGC`**, **`FPT`**.
- Tracked invariants:
  1. `holdings_quantity` is invariant to price/risk metric changes.
  2. `cost_basis` calculation remains unchanged.
  3. `historical_nav` and `transaction_ledger` integrity maintained.
  4. Core valuation logic produces deterministic outputs for identical input hashes.

### 4.2 Legacy Navigation Transition Strategy
1. Keep existing routes functional while building `/terminal`, `/business`, `/capital`, `/history`.
2. Update `AppNav.jsx` once new workspaces reach feature parity.
3. Classify legacy routes as `HIDE` in secondary menus rather than deleting code prematurely.

---

## 5. Audit Verification & Sign-off

- [x] Backend and frontend components fully cataloged and classified.
- [x] Zero production behavior changes introduced during T00 audit.
- [x] Canonical implementation order T00 -> T20 validated.
- [x] Task T00 complete and ready for T01 execution.
