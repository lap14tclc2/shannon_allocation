# Dividend cache and reconciliation

## Runtime contract

QPort uses cache-aside for dividend history:

1. GET /api/portfolio/dividends/latest/{symbol} checks the portfolio database.
2. If dividend_fetch_state exists and the request is not a forced refresh, the response is database-only (data_origin=SQLITE_CACHE).
3. On a miss, or when the user explicitly requests refresh, the service may call VPS/CafeF, persist canonical events and fetch state, then return the result.
4. Set QPORT_DIVIDEND_PROVIDER_FETCH=0 to make user requests database-only. A miss returns pending_sync=true and contact admin instead of making a provider request.

This flag is intentionally isolated in SqliteDividendService; an admin/worker can later switch it off globally without changing UI routes.

## Normalize -> reconcile -> conflict

Provider crawlers should send each parsed event through:

~~~text
raw provider document
  -> normalize_observation(...)
  -> persist_observations(...)
  -> reconcile_symbol(...)
  -> dividend_canonical / dividend_conflicts
  -> user cache / ledger consumers
~~~

python/portfolio/dividend_reconciliation.py stores immutable provider observations in the shared qport_finance schema. Normalization standardizes symbol, event type, dates, amounts, ratios and payload hash. Reconciliation groups observations within a two-day date tolerance and selects the highest-priority source (tcbs, then cafef, then other providers). Matching multi-source observations become VERIFIED; one source becomes SINGLE_SOURCE. Materially different values are never silently merged: they remain CONFLICT and create an OPEN row in dividend_conflicts for admin review.

Example worker usage:

~~~python
from portfolio.dividend_reconciliation import (
    normalize_observation, persist_observations, reconcile_symbol,
)

rows = [
    normalize_observation(event, provider="vps", source_document_id=document_id)
    for event in parsed_events
]
persist_observations(rows)
reconcile_symbol("VNM")
~~~

The finance-data admin page now presents four independent document groups: Báo cáo tài chính, Kết quả kinh doanh, Lưu chuyển tiền tệ, and Cổ tức. Provider/period/status evidence remains visible under each symbol.
