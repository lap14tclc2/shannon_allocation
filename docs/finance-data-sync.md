# Finance data crawl and sync

## Runtime policy

Provider requests are allowed only when the crawler process sets:

    QPORT_FINANCE_RUNTIME=local

or:

    QPORT_FINANCE_RUNTIME=worker

The Vercel runtime is always database-read-only. It returns CRAWL_RUNTIME_INVALID for provider crawl attempts.

## Recommended flow

1. Set the local database URL and run the admin/universe sync from the external worker.
2. Queue symbols from /admin/finance-data.
3. The worker consumes qport_finance.crawl_queue, calls CafeF with bounded timeout/retries (TCBS is temporarily disabled), and writes symbol-scoped documents.
4. Validate and sync the local catalog to the Vercel database:

    export QPORT_LOCAL_DATABASE_URL='postgresql://...'
    export QPORT_VERCEL_DATABASE_URL='postgresql://...'
    python scripts/finance_sync.py --dry-run
    python scripts/finance_sync.py

On PowerShell:

    $env:QPORT_LOCAL_DATABASE_URL = 'postgresql://...'
    $env:QPORT_VERCEL_DATABASE_URL = 'postgresql://...'
    python scripts/finance_sync.py --dry-run
    python scripts/finance_sync.py

The sync copies securities, crawl metadata, raw documents, canonical facts, parse errors, dividend observations, canonical dividend events, and conflict records. It validates the source schema, symbols, providers/statuses, cross-table references, successful payloads, and checksums before opening the target transaction. Repeated runs are idempotent and never replace a newer target row with an older source document.

Never expose either database URL to browser code or commit them to Git.


## What is synchronized

The script synchronizes the complete finance catalog required by Vercel reads:

- `securities` and crawl metadata;
- raw `documents`;
- `canonical_facts` and `parse_errors`;
- `dividend_observations`, `dividend_canonical`, and `dividend_conflicts`.

The source database is read and validated first. The target database is changed only inside one transaction. A failed validation stops before any target mutation.

After sync, Vercel does not need a provider request or a second crawl. Its valuation route reads `canonical_facts`, and its dividend route reads only non-conflicted canonical dividend events.


## Local universe-sync progress logs

The universe endpoint continues to use Vnstock for the symbol list. Run it from
the local worker with `QPORT_FINANCE_RUNTIME=local`. The terminal now prints
`[finance-universe]` messages for runtime validation, Vnstock loading, the
listing method call, received row count, persistence checkpoints, completion,
and errors. While Vnstock is waiting on its listing request, a heartbeat is
printed every 10 seconds, for example:

    [finance-universe] calling Listing.all_symbols()
    [finance-universe] Listing.all_symbols() still running (10s)
    [finance-universe] received 3900 symbol rows via Listing.all_symbols
    [finance-universe] persisted 390/3900 symbols (latest=AAA)
    [finance-universe] completed count=3900 elapsed=...

These logs are flushed immediately and do not include database URLs, tokens, or
provider credentials. Finance document crawling remains separate and currently uses CafeF only.
TCBS records remain in the database and can be re-enabled later.


## Running the local queue worker

After clicking Xếp hàng crawl tất cả, start a separate PowerShell process from the repository root:

    $env:QPORT_FINANCE_RUNTIME = 'worker'
    python scripts/finance_worker.py --limit 1

Process the remaining queue continuously:

    python scripts/finance_worker.py --poll-seconds 2

Useful logs:

    [finance-worker] claimed queue_id=... symbol=AAA
    [finance-crawl] symbol=AAA start ...
    [finance-worker] finished queue_id=... symbol=AAA status=COMPLETED ...

The worker runs outside Vercel, uses bounded provider requests, skips existing SUCCESS documents, and continues after an individual symbol failure.


## Provider scope

TCBS is temporarily disabled in the worker because its current finance routes
may return HTTP 403/404. The worker does not read `TCBS_BEARER_TOKEN` and
does not issue TCBS requests. Existing TCBS documents/canonical facts are
preserved; re-enabling TCBS is a separate provider-scope change.

## Current CafeF route

CafeF financial pages are HTML, not JSON. The worker uses the current
`/du-lieu/bao-cao-tai-chinh/{symbol}/{segment}/{year}/{quarter}/...` route and
extracts label/value rows from the HTML table. A successful request is stored
as raw HTML and then normalized into canonical facts. TCBS requests remain
optional and must be verified independently because its legacy finance route
may return HTTP 404.


## Single-document retry

The Finance Data admin panel retries the selected CafeF document only. It sends
the provider, document type, fiscal period, and quarter identity to the API. The
API returns the updated symbol row, so the UI updates that row in local state
without reloading the whole catalog page or changing search, filter, or
pagination state.
