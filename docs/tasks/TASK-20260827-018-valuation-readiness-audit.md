---
id: TASK-20260827-018
title: Add valuation-readiness audit and strict value-engine inputs
status: ready
priority: critical
created: 2026-08-27
updated: 2026-08-27
---

## Requirement

Audit crawled finance documents against the factual inputs required by QPort's value engine. Expose an admin report and block valuations that rely on missing, parse-invalid, conflicting, mixed-period, or fabricated data.

## Acceptance Criteria

- [ ] Audit reports source/parse/document/fact/period/reconciliation readiness for a symbol.
- [ ] Audit requires net income, operating cash flow, D&A, CAPEX, cash, total debt, and shares outstanding from one reporting period.
- [ ] Audit reports parse errors and does not treat a document row as usable merely because fetch status is SUCCESS.
- [ ] Valuation snapshot blocks when readiness is not READY and returns audit reasons.
- [ ] Admin API and Finance Data UI expose readiness for an expanded symbol.
- [ ] Value engine rejects quarterly input without an explicit TTM bridge and removes fabricated owner-earnings fallback.
- [ ] Owner Earnings uses explicit factual inputs; no synthetic D&A, CAPEX, or working-capital values in strict valuation mode.
- [ ] Add contract tests.

## Constraints and Invariants

- Preserve raw documents, canonical facts, provider URLs, and checksums.
- A provider fetch is not equivalent to a valuation-valid fact.
- Do not silently average conflicts or mix fiscal periods.
- Do not create a valuation from a fallback numeric constant.
- Banks/financials are outside this normal-enterprise owner-earnings readiness contract until a dedicated model exists.

## Result

Pending implementation.
