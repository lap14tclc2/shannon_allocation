---
name: qport-financial-data
description: Design, implement, review, and validate QPort's Vietnamese corporate financial-data system, including public API and HTML ingestion, raw/normalized/canonical models, provenance, reconciliation, point-in-time queries, provider quality, financial statement taxonomy, testing, and rollout. Use for QPort or Shannon Allocation work involving company profiles, financial statements, CafeF/Vnstock connectors, source conflicts, data-quality status, valuation inputs, screening, or backtest-safe fundamental data.
---

# QPort Financial Data

## Workflow

1. Parse the request into topics, implementation scope, provider scope, entity type, time semantics, and required output.
2. Read [the knowledge index](references/maps/index.md).
3. Read only the smallest relevant topic map and permanent notes.
4. Announce each map, note, or source at first use with `[Using reference: <relative-path>]`.
5. Prefer notes with `status: verified`. Treat `draft` values as proposals that require validation before production use.
6. Inspect the linked source note before relying on provider behavior, legal access assumptions, quotas, selectors, or other time-sensitive claims.
7. Preserve provenance and point-in-time correctness. Never silently average conflicting accounting values or replace missing values with zero.
8. Keep corporate actions separate from financial-statement facts and apply entity-specific taxonomy for banks, securities firms, insurers, and ordinary enterprises.
9. Validate proposed changes against the delivery and testing notes before returning results.
10. Cite relevant `QFD-*` note IDs and source notes in the answer.

## Routing

- Product principles, boundaries, and source roles: [foundations](references/maps/foundations.md).
- API, HTML, evidence, and provider selection: [data sources](references/maps/data-sources.md).
- Fact identity, contracts, provenance, periods, units, and taxonomy: [data model](references/maps/data-model.md).
- Deterministic reconciliation, tolerance, revisions, statuses, and review: [reconciliation and quality](references/maps/reconciliation-quality.md).
- Services, registry, storage, observability, and crawl safety: [infrastructure and operations](references/maps/infrastructure-operations.md).
- Canonical API, internal metrics, and `as_of`: [QPort consumption](references/maps/qport-consumption.md).
- Repository gaps, roadmap, tests, Definition of Done, and open questions: [delivery and validation](references/maps/delivery-validation.md).

## Reliability rules

- Do not turn design proposals into verified facts.
- Re-verify live provider behavior and access policy before implementation.
- Keep raw evidence append-only and make every canonical value traceable.
- Use decimal values for money and UTC timestamps for events.
- Do not expose `CONFLICT` or `QUARANTINED` facts through production APIs by default.
- Do not claim the knowledge base resolves an open question when `QFD-900` still lists it.
