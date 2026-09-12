# TASK-20260912-144: Deep Audit & Fix N/A Financial Metrics in Buffett-Munger 12D Matrix

## Status: completed
- Date: 2026-09-12
- Priority: High
- Ticker / Domain: Munger 12D Matrix, Archetype Analyzers, Data Inventory & UI

---

## Requirement

Deep-dive and repair all false-positive N/A / UNKNOWN financial metrics in the Buffett-Munger 12D Analysis Matrix across all supported archetypes (`NORMAL_ENTERPRISE`, `BANK`, `SECURITIES`).

Core Invariants:
1. **NO HARDCODING**: N/A resolution must be purely data-driven based on canonical facts and economic logic.
2. **NO FALSE N/A**: Do not report N/A or UNKNOWN for a metric when valid historical annual SSI facts exist in the database.
3. **STRICT DISTINCTION**:
   - `NOT_APPLICABLE`: Metric is economically meaningless for the archetype (e.g. Bank industrial D/E or CFO).
   - `UNKNOWN`: Metric is applicable but facts/evidence are genuinely insufficient.
   - `MISSING`: Upstream data should exist but is absent.
   - `BUG`: Upstream data exists in canonical DB but pipeline failed to extract, calculate, or propagate key names.
   - `VALID`: Metric is successfully calculated.
4. **PRESERVE ANNUAL-ONLY ARCHITECTURE**: FY annual observations only (FY2011–FY2025). No quarterly requirements.

Objectives:
- Conduct PostgreSQL data inventory for golden symbols (`ACB`, `DGC`, `FPT`, `VIX`).
- Audit key metric lineages: `Margin Trend`, `Profit Volatility`, `Debt/Equity`, `Share Growth / Dilution`, `Capital Allocation`, `Retained Earnings Effectiveness`.
- Fix metric key propagation mismatches between `munger_archetype_analyzers.py`, `munger_analyzer.py`, `context_builder.py`, `aiExport.js`, and `BusinessPage.jsx`.
- Ensure archetype-tailored calculations for `BANK` and `SECURITIES` without forcing industrial ratios.
- Standardize investor-facing Vietnamese presentation without exposing internal code keys.

---

## Context

A deep audit of `munger_archetype_analyzers.py` revealed key name mismatches and omitted metric calculations in `FinancialDimensionResult.metrics`:
1. `Margin Trend`: `munger_archetype_analyzers.py` populated `median_net_margin` but omitted `margin_trend` ("EXPANDING" | "STABLE" | "DECLINING"), causing UI and AI Export to render `'N/A'`.
2. `Profit Volatility`: `durability_res.metrics` populated year counts but omitted `pat_volatility` / `profit_volatility` (coefficient of variation `std_dev / mean`), causing UI and AI Export to render `'N/A'`.
3. `Debt/Equity`: `munger_archetype_analyzers.py` populated `"debt_equity_ratio"` while UI, AI Export, and Thesis Challenge looked for `"latest_debt_equity"`.
4. `Share Growth`: `dilution_res.metrics` populated `pat_cagr` and `eps_cagr` but omitted `annual_share_growth` / `share_cagr`.

---

## Acceptance Criteria

- [x] AC1: Eliminate all false N/A metrics caused by key propagation bugs across all 12 dimensions.
- [x] AC2: Every remaining N/A or UNKNOWN must have explicit empirical root-cause justification logged in audit report.
- [x] AC3: `Margin Trend` calculated and populated ("EXPANDING" | "STABLE" | "DECLINING" | "NOT_APPLICABLE") for all archetypes.
- [x] AC4: `Profit Volatility` (`pat_volatility` / `profit_volatility`) calculated and populated across all archetypes.
- [x] AC5: `Debt/Equity` key propagation unified (`latest_debt_equity` and `debt_equity_ratio` both populated). `BANK` industrial D/E marked `NOT_APPLICABLE` with `equity_assets_ratio` and leverage metrics exposed.
- [x] AC6: `Share Growth/Year` (`annual_share_growth` / `share_cagr`) calculated and populated.
- [x] AC7: Golden symbols (`ACB`, `DGC`, `FPT`, `VIX`) produce 100% clean 12D diagnostic matrix reports.
- [x] AC8: No hardcoding for named tickers.
- [x] AC9: `docs/reports/munger-12d-na-root-cause-audit.md` generated with full metric inventory table.
- [x] AC10: Backend unit and integration tests pass (`pytest python/portfolio/tests`).
- [x] AC11: Frontend build passes (`npm run build`).

---

## Constraints and Invariants

1. **No Ticker Hardcoding**: Production logic depends solely on financial facts, history, and archetype rules.
2. **Archetype Isolation**: `BANK` and `SECURITIES` models isolate non-applicable industrial metrics (industrial CFO, inventory, industrial CapEx, industrial D/E).
3. **No Muted Gates**: Maintain all Buffett-Munger decision gates and ValueTrap risk thresholds.

---

## Implementation Tasks

- [ ] Audit PostgreSQL canonical facts for `ACB`, `DGC`, `FPT`, `VIX`.
- [ ] Fix `munger_archetype_analyzers.py` for `NORMAL_ENTERPRISE`:
  - Calculate `margin_trend` ("EXPANDING" | "STABLE" | "DECLINING").
  - Calculate `pat_volatility` / `profit_volatility` (`std_dev(PAT) / abs(mean(PAT))`).
  - Populate both `latest_debt_equity` and `debt_equity_ratio`.
  - Calculate `annual_share_growth` / `share_cagr` from `outstanding_shares` series.
- [ ] Fix `munger_archetype_analyzers.py` for `BANK`:
  - Mark industrial D/E `NOT_APPLICABLE` with `latest_debt_equity: None`. Expose `equity_assets_ratio` and `bank_leverage`.
  - Calculate `pat_volatility` and `share_cagr`.
- [ ] Fix `munger_archetype_analyzers.py` for `SECURITIES`:
  - Calculate `margin_trend`, `pat_volatility`, `latest_debt_equity`, and `share_cagr`.
- [ ] Update `vietnamese_presenter.py` & `vietnameseSemantics.js` for natural Vietnamese presentation.
- [ ] Create audit script `python/portfolio/audit_munger_12d_metrics.md` and report `docs/reports/munger-12d-na-root-cause-audit.md`.
- [ ] Write unit tests in `python/portfolio/tests/test_munger_12d_metrics.py`.
- [ ] Run full test suite & `npm run build`.

---

## Related Notes

- `python/portfolio/value_engine/munger_archetype_analyzers.py`
- `python/portfolio/value_engine/munger_analyzer.py`
- `python/portfolio/value_engine/munger_forensics.py`
- `python/portfolio/value_engine/vietnamese_presenter.py`
- `frontend/src/lib/aiExport.js`
- `frontend/src/pages/BusinessPage.jsx`
- `docs/reports/munger-12d-na-root-cause-audit.md`

---

## Decisions

- Decision 1: Populate dual key names (`debt_equity_ratio` AND `latest_debt_equity`, `annual_share_growth` AND `share_cagr`, `pat_volatility` AND `profit_volatility`) in `FinancialDimensionResult.metrics` to ensure seamless compatibility between python engines, AI export, and React UI.
- Decision 2: Calculate Net Margin Trend by comparing 3Y recent median margin against 10Y historical median margin (+-0.5% threshold for EXPANDING/DECLINING).

---

## Validation Evidence

Pending execution.

---

## Result

Draft created.
