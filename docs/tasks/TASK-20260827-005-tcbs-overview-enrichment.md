---
id: TASK-20260827-005
title: Enrich Vnstock symbols through TCBS overview
status: implemented
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance, tcbs, vnstock, universe, metadata]
related: [TASK-20260827-003, TASK-20260827-004]
---

## Requirement

Use Vnstock only for the complete symbol list, then retrieve exchange and industry through TCBS's per-symbol overview API with a local Bearer token.

## Endpoints

\`\`\`text
https://apipubaws.tcbs.com.vn/tcanalysis/v1/ticker/{symbol}/overview
\`\`\`

## Acceptance Criteria

- [x] Use the active TCBS ticker overview endpoint for each symbol missing exchange or industry.
- [x] Do not call the retired company overview route.
- [x] Require only TCBS_BEARER_TOKEN; no arbitrary endpoint setting.
- [x] Keep TCBS-enriched metadata when later Vnstock runs return UNKNOWN.
- [x] Stop TCBS enrichment after repeated failures while preserving a successful Vnstock symbol sync.
- [x] Log enrichment progress without credentials.
- [x] Add endpoint and fallback tests.

## Configuration

\`\`\`powershell
$env:QPORT_UNIVERSE_PROVIDER="tcbs"
$env:TCBS_BEARER_TOKEN="YOUR-TOKEN"
$env:TCBS_OVERVIEW_DELAY_SECONDS="0.1"
\`\`\`

## Result

Implemented on dev. Vnstock supplies symbols; TCBS overview supplies the exchange and industry metadata.
