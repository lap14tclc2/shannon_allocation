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
3. The worker consumes qport_finance.crawl_queue, calls TCBS/CafeF with bounded timeout/retries, and writes symbol-scoped documents.
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

The sync validates that the source schema exists, symbols are known, providers/statuses are allowed, successful rows contain payloads, and payload checksums match. It then performs an idempotent transaction and never replaces a newer target document with an older source document.

Never expose either database URL to browser code or commit them to Git.
