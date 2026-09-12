# TASK-20260912-143: Deep-Dive & Repair Receivables Forensic Semantics

## Status: completed
- Date: 2026-09-12
- Priority: High
- Ticker / Domain: Forensics Engine, Munger Analyzer & Universe Scanner

---

## Requirement

Deep-dive and repair the economic, accounting, canonical-data, and presentation semantics behind:
`RECEIVABLES_GROW_FASTER_THAN_REVENUE`

Core Invariants:
1. **BAD OR AMBIGUOUS DATA != BAD BUSINESS**
2. **ONE WORKING-CAPITAL WARNING MUST NOT, BY ITSELF, CAUSE STRUCTURAL DETERIORATION OR AVOID.**

Objectives:
- Trace and document the full data lineage from raw SSI XLSX rows to final investment decisions.
- Establish a canonical trade receivables contract distinguishing trade receivables (`BS.RECEIVABLES.TRADE.NET`, `BS.RECEIVABLES.TRADE.GROSS`) from aggregate receivables (`BS.RECEIVABLES.TOTAL`), other receivables, related party balances, supplier advances, and contract assets.
- Eliminate silent alias overwrites and iteration-order ambiguity in `munger_history_builder.py`.
- Preserve explicit `is not None` logic (`NULL != 0`, `UNKNOWN != PASS`, `MISSING != SAFE`).
- Implement a two-stage anomaly architecture: Stage A (Semantic Validation) -> Stage B (Economic Forensic Assessment).
- Calculate Receivable Intensity (`Trade Receivables / Revenue`) and Days Sales Outstanding (DSO: `Average Trade Receivables / Revenue * 365`) across 1Y, 3Y, 5Y, and historical periods.
- Require multi-year persistence and corroborating evidence (e.g., weakening CFO/PAT, cash consumption) before escalating severity.
- Ensure an isolated receivables finding never triggers `CATASTROPHIC_HARD_FAILURE`, `HIGH_RISK` ValueTrap, `POSSIBLY_STRUCTURAL` deterioration, or `AVOID` decision.
- Enforce archetype applicability (`BANK` & `SECURITIES` -> `NOT_APPLICABLE`).
- Localize findings under Vietnamese title `"Khả năng thu hồi tiền bán hàng"`.
- Audit regression sample (DGC, FPT, AAA, AAH, ACB, VIX) and full SSI universe (~390-400 symbols), outputting reports `docs/reports/task-143-receivables-semantic-audit.md` and `docs/reports/task-143-receivables-universe.csv`.

---

## Context

The previous forensics implementation evaluated receivables CAGR over arbitrary endpoints using aggregate receivables without distinguishing trade receivables from other subcomponents. Furthermore, any `HIGH` severity finding automatically entered `hard_failures`, triggering `HIGH_RISK` ValueTrap and forcing an `AVOID` decision on good businesses (e.g. DGC) even when cash flow and fundamental profitability remained exceptionally strong.

---

## Acceptance Criteria

- [x] Exact trade-receivables semantic contract documented and implemented.
- [x] Aggregate and trade receivables are explicitly distinguished.
- [x] No iteration-order alias overwrite in history builder.
- [x] Zero is not treated as missing (`is not None`).
- [x] Semantic conflicts block forensic interpretation (`DATA_CONFLICT`).
- [x] FY-only multi-year calculations preserved.
- [x] DSO implemented ("Thời gian thu tiền từ khách hàng").
- [x] 1Y, 3Y, 5Y, and full-history trends calculated for revenue, receivables, intensity, and DSO.
- [x] Persistence and materiality required before flagging.
- [x] Isolated receivables warning cannot be a `CATASTROPHIC_HARD_FAILURE`.
- [x] One working-capital finding cannot cause structural deterioration.
- [x] One working-capital finding cannot alone cause `HIGH_RISK` ValueTrap.
- [x] One working-capital finding cannot alone cause `AVOID`.
- [x] `BANK` rule = `NOT_APPLICABLE`.
- [x] `SECURITIES` rule = `NOT_APPLICABLE`.
- [x] Real-estate / construction contract assets explicitly handled.
- [x] DGC source-to-decision trace completed and verified.
- [x] Full SSI universe scan completed (~390-400 stocks).
- [x] No ticker-specific exceptions or hardcoded whitelists.
- [x] Vietnamese semantic presentation completed ("Khả năng thu hồi tiền bán hàng").
- [x] Raw machine codes hidden from normal UI.
- [x] Backend and frontend tests pass.
- [x] `docs/reports/task-143-receivables-semantic-audit.md` & `docs/reports/task-143-receivables-universe.csv` generated.

---

## Constraints and Invariants

1. **No Ticker Exceptions**: Production logic must depend solely on financial facts, history, archetype, and economic relationships — NOT ticker identity.
2. **Formula & Accounting Integrity**: Trade receivables must be isolated from supplier advances, related party receivables, and contract assets.
3. **Non-Catastrophic Working Capital**: Working capital anomalies are quality signals (`FORENSIC_WARNING`), not catastrophic business destruction.

---

## Implementation Tasks

- [x] Trace raw SSI row definitions in `ssi_ingestion.py` and `financial_data.py`.
- [x] Update `munger_history_builder.py` to extract canonical trade receivables (`BS.RECEIVABLES.TRADE.NET` / `BS.RECEIVABLES.TRADE.GROSS`) and aggregate receivables (`BS.RECEIVABLES.TOTAL`).
- [x] Update `munger_forensics.py` to implement two-stage anomaly validation, DSO calculations, multi-period trends, persistence checks, and corroboration escalation.
- [x] Update `munger_analyzer.py` and `value_trap.py` so working-capital findings do not automatically trigger hard failures, `HIGH_RISK` ValueTrap, or `AVOID`.
- [x] Add Vietnamese presentation semantics in `vietnamese_presenter.py` and `vietnameseSemantics.js`.
- [x] Create audit script `python/portfolio/audit_receivables_universe.py` to run DGC/golden sample trace and full SSI universe scan.
- [x] Generate reports `docs/reports/task-143-receivables-semantic-audit.md` and `docs/reports/task-143-receivables-universe.csv`.
- [x] Write unit and integration tests in `python/portfolio/tests/test_receivables_forensics_semantic_contract.py`.
- [x] Run full test suite and verify `npm run build`.

---

## Related Notes

- `python/portfolio/value_engine/munger_forensics.py`
- `python/portfolio/value_engine/munger_analyzer.py`
- `python/portfolio/value_engine/value_trap.py`
- `python/portfolio/financial_data/ssi_ingestion.py`
- `python/portfolio/value_engine/vietnamese_presenter.py`
- `TASK-20260912-139-forensic-correctness-and-canonical-mos-authority.md`
- `TASK-20260912-142-vietnamese-semantics-overhaul-and-editable-portfolio.md`

---

## Decisions

- Decision 1: Create distinct canonical keys `BS.RECEIVABLES.TRADE.NET`, `BS.RECEIVABLES.TRADE.GROSS`, `BS.RECEIVABLES.OTHER`, `BS.RECEIVABLES.RELATED_PARTY`, `BS.ADVANCES.SUPPLIERS`, `BS.CONTRACT_ASSETS`, `BS.RECEIVABLES.TOTAL` to prevent conflating aggregate balances with customer sales receivables.
- Decision 2: Forensics findings are categorized into `FORENSIC_WARNING` / `QUALITY_FAILURE` versus `CATASTROPHIC_HARD_FAILURE`. Working-capital anomalies (like receivables growth gap) are `FORENSIC_WARNING` and cannot by themselves force `HIGH_RISK` ValueTrap or `AVOID`.
- Decision 3: Enforce Stage A semantic validation (checking data conflict and total proxy status) prior to Stage B economic evaluation. Total proxies cap maximum severity at `MEDIUM` (`WATCH`).

---

## Validation Evidence

- Executed `python/portfolio/audit_receivables_universe.py` across all 390 SSI universe symbols:
  - `BANK`: 19 symbols, 100% `NOT_APPLICABLE`.
  - `SECURITIES`: 13 symbols, 100% `NOT_APPLICABLE`.
  - `NORMAL_ENTERPRISE`: 358 symbols, 0% invalid `FAIL` rate.
- Generated audit reports: `docs/reports/task-143-receivables-semantic-audit.md` & `docs/reports/task-143-receivables-universe.csv`.
- Unit tests: `python/portfolio/tests/test_receivables_forensics_semantic_contract.py` (4/4 passed), `python/portfolio/tests/test_forensic_mos_correctness.py` & `test_munger_financial_analysis.py` (18/18 passed).
- Frontend compilation: `npm run build` completed cleanly in 1.22s.

---

## Result

Task completed successfully. All acceptance criteria met.
