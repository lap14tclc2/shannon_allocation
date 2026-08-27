---
id: TASK-20260827-004
title: Add authenticated TCBS universe provider
status: implemented
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance, tcbs, universe, authentication]
related: [TASK-20260827-003]
---

## Requirement

Use an authenticated TCBS endpoint for universe metadata when configured locally, while retaining Vnstock as a fallback.

## Acceptance Criteria

- [x] TCBS URL and Bearer token are read only from local environment variables.
- [x] Token is never logged, persisted, returned by the API, or committed.
- [x] TCBS response supports common JSON list envelopes.
- [x] QPORT_UNIVERSE_PROVIDER=tcbs fails clearly when credentials/request are invalid.
- [x] QPORT_UNIVERSE_PROVIDER=auto falls back to Vnstock.
- [x] Existing normalization and quality diagnostics apply to both sources.
- [x] Add environment-configuration tests.

## Configuration

\`\`\`powershell
$env:QPORT_UNIVERSE_PROVIDER="tcbs"
$env:TCBS_UNIVERSE_URL="https://YOUR-TCBS-ENDPOINT"
$env:TCBS_BEARER_TOKEN="YOUR-TOKEN"
\`\`\`

Use \`auto\` only when Vnstock fallback is desired.

## Validation Evidence

Unit tests cover environment validation. The authenticated endpoint must be verified locally with the user's authorized TCBS URL/token.

## Result

Implemented on dev without hard-coding an undocumented TCBS endpoint or exposing credentials.
