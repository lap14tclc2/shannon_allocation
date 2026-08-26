# ZK-20260826-005 — Dividend cache-aside and finance document categories

- Status: done
- Context: User wants VPS/CafeF first-fetch then database reads, with a future admin-only switch.
- Decision: cache-aside remains default; QPORT_DIVIDEND_PROVIDER_FETCH=0 disables provider calls. Normalize provider observations before reconcile; conflicts remain open.
- Links: dividend_store.py, dividend_reconciliation.py, FinanceDataPage.jsx
- Acceptance:
  - cache hit never calls provider;
  - cache miss/forced refresh can fetch and persist when enabled;
  - disabled mode returns pending_sync/contact admin;
  - source disagreements are auditable and not silently merged;
  - admin finance documents are shown in four categories.
