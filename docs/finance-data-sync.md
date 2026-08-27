# Finance data crawl and sync

## Runtime policy

Provider requests are allowed only from an external process with
QPORT_FINANCE_RUNTIME=local or worker. Vercel remains database-read-only.

## TCBS-only worker

The active worker uses the authenticated TCBS finance history endpoints:

- https://apiextaws.tcbs.com.vn/tcanalysis/v1/finance/{SYMBOL}/cashflow?yearly=0&isAll=true
- https://apiextaws.tcbs.com.vn/tcanalysis/v1/finance/{SYMBOL}/balancesheet?yearly=0&isAll=true
- https://apiextaws.tcbs.com.vn/tcanalysis/v1/finance/{SYMBOL}/incomestatement?yearly=0&isAll=true

Set the bearer token only in the local worker environment:

    $env:DATABASE_URL = 'postgresql://...'
    $env:QPORT_FINANCE_RUNTIME = 'worker'
    $env:TCBS_BEARER_TOKEN = '...'

The token is never written to the database, logs, frontend, or Git. The
worker uses standard authenticated HTTP with bounded retries. It does not use
TLS fingerprint evasion, CAPTCHA bypass, or browser challenge bypass.

## History parsing and Value Engine mapping

Each endpoint returns a history array, not one row for one requested period.
For one symbol the worker performs at most three endpoint requests, selects the
exact year and quarter locally, then stores one logical document per period.
Existing SUCCESS documents are skipped, so a later run fetches only new or
incomplete periods.

The sample fixture at docs/crawled/tcbs_FPT_financial_data.json maps as follows:

| TCBS field | Canonical fact | Policy |
|---|---|---|
| postTaxProfit | IS.PROFIT.NET | use exactly |
| operationProfit | IS.PROFIT.OPERATING | use exactly |
| debt | BS.DEBT.TOTAL | use exactly |
| cash | BS.ASSETS.CASH_AND_EQUIVALENTS | use exactly |
| investCost | CF.CAPEX | use exactly, preserving sign |
| absent | CF.OPERATING.NET | remain missing |
| absent | CF.OPERATING.DEPRECIATION | remain missing |
| absent | IS.SHARES.OUTSTANDING | remain missing |

Missing facts intentionally keep Value Engine in a safe unavailable/blocked
state. Do not map capital, shareHolderIncome, freeCashFlow, or EBITDA to a
different required fact.

## Recommended flow

1. Sync the local Vnstock universe and queue eligible HOSE/HNX equities.
2. Run the local worker:

    python scripts/finance_worker.py --limit 1

For the remaining queue:

    python scripts/finance_worker.py --poll-seconds 2

The terminal reports endpoint-level progress and per-symbol outcomes, for example:

    [finance-worker] claimed queue_id=... symbol=FPT
    [finance-crawl] symbol=FPT fetch provider=tcbs document=CASH_FLOW history
    [finance-crawl] symbol=FPT received provider=tcbs document=CASH_FLOW records=72
    [finance-crawl] symbol=FPT success provider=tcbs document=CASH_FLOW period=FY:2025
    [finance-worker] SUCCESS symbol=FPT queue_id=... success=...
    [finance-worker] summary processed=... success=... failed=...

3. Sync the complete local catalog to Vercel/Neon:

    $env:QPORT_LOCAL_DATABASE_URL = 'postgresql://...'
    $env:QPORT_VERCEL_DATABASE_URL = 'postgresql://...'
    python scripts/finance_sync.py --dry-run
    python scripts/finance_sync.py

The sync includes raw documents, canonical facts, parse errors, and
reconciliation tables. Never expose database URLs to browser code.

## Probe one symbol

Use a local token to check endpoint shape without printing the token or body:

    python scripts/tcbs_probe.py --symbol MWG

A successful probe prints only endpoint names, record counts, year range, and
field names. It exits nonzero if any endpoint fails.

## Remove legacy CafeF data

Stop all workers first, then run:

    python scripts/finance_db.py status
    python scripts/finance_db.py clear-cafef --confirm

This removes CafeF documents, CafeF canonical facts, CafeF parse errors, and
CafeF dividend observations, then rebuilds remaining dividend views for affected
symbols. It does not delete TCBS documents or securities.

## Universe logs

The universe endpoint may still use Vnstock only for symbol discovery. Its
[finance-universe] logs show loading, request heartbeat, row count,
persistence checkpoints, completion, and errors. The finance document worker
does not use Vnstock for financial statements.
