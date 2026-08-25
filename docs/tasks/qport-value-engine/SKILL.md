---
name: qport-value-engine
description: Design, implement, review, and validate QPort's deterministic Buffett-inspired valuation system for Vietnamese buy-and-hold portfolios. Use for Owner Earnings, normalized earnings, per-share economics, business-quality diagnostics, sector-specific valuation routing, DCF, EPV, residual income, justified P/B, SOTP, RNAV, reverse DCF, scenarios, margin of safety, confidence, valuation reports, data lineage, testing, UX, and informational-only portfolio integration.
---

# QPort Value Engine

## Workflow

1. Parse the request into valuation topic, sector, data period, model scope, assumptions, and expected output.
2. Read [the knowledge index](references/maps/index.md).
3. Read only the smallest relevant topic map and permanent notes.
4. Announce every map, note, or source at first use with `[Using reference: <relative-path>]`.
5. Treat `draft` notes as proposed contracts, not implemented facts. Treat `inferred` philosophy notes as requiring source verification before quoting them as authoritative.
6. Validate data quality and sector support before selecting or running a valuation model.
7. Keep calculations deterministic and reproducible. Preserve missing values as `null`; never invent inputs or silently replace missing values with zero.
8. Return ranges, sensitivity, assumptions, warnings, and confidence instead of false precision.
9. Keep the Value Engine informational only. Never create transactions or mutate holdings, cash, shares, or the portfolio ledger.
10. Validate implementation proposals against testing, roadmap, and Definition of Done notes, then cite relevant `QVE-*` IDs and source notes.

## Routing

- Goals, Buffett-inspired philosophy, deterministic rules, and architecture: [foundations and philosophy](references/maps/foundations-philosophy.md).
- Financial inputs, share data, market price, and valuation blocking rules: [data contracts and quality](references/maps/data-contract-quality.md).
- Sector model choice and quality diagnostics: [sector and business quality](references/maps/sector-business-quality.md).
- Earnings normalization, maintenance CAPEX, working capital, and Owner Earnings: [normalization and Owner Earnings](references/maps/normalization-owner-earnings.md).
- DCF, EPV, DDM, residual income, justified P/B, SOTP, and RNAV: [valuation models](references/maps/valuation-models.md).
- Scenarios, margin of safety, reverse DCF, sensitivity, and confidence: [scenarios and risk](references/maps/scenarios-risk-confidence.md).
- Immutable reports, storage, and APIs: [reporting, storage, and API](references/maps/reporting-storage-api.md).
- Explainable UX, optional AI, forbidden behavior, and portfolio isolation: [governance, UX, and AI](references/maps/governance-ux-ai.md).
- Formula tests, fixtures, invariants, delivery phases, and MVP acceptance: [testing and roadmap](references/maps/testing-roadmap.md).

## Reliability rules

- Do not present illustrative rates or scenarios as Vietnamese market defaults.
- Do not use a generic DCF for banks or silently fall back from an unsupported sector model.
- Do not derive BUY/SELL actions from valuation states, colors, confidence, or quality diagnostics.
- Do not use total growth without evaluating dilution and per-share outcomes.
- Do not let optional AI alter raw facts, policies, assumptions, calculations, or ledger state.
- Do not claim the proposal is implemented unless repository evidence confirms it.
