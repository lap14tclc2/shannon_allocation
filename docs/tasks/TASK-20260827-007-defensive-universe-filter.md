---
id: TASK-20260827-007
title: Defensively hide legacy non-equity universe rows
status: implemented
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance, universe, data-quality, crawl]
related: [TASK-20260827-006]
---

## Requirement

Ensure legacy invalid records cannot appear in Finance Data or enter a crawl, even before the next successful universe refresh removes them from the active database set.

## Context

The UI still showed old warrant-style symbols such as 41B5G9000 and rows with company name nan. These records were imported before the universe filter and could remain marked active when the local sync had not yet been rerun.

## Acceptance Criteria

- [x] Apply a read-time active-equity predicate to Finance Data listing and total count.
- [x] Apply the same predicate to crawl-all queue selection.
- [x] Reject direct crawl attempts for records failing the predicate.
- [x] Require a recognised HOSE/HNX/UPCOM exchange and a non-sentinel company name.
- [x] Preserve old documents for audit without exposing their symbols as crawlable securities.
- [x] Add no credential or provider calls to the defensive filtering path.

## Constraints and Invariants

- This is a compatibility guard for legacy rows; the write-time Vnstock filter remains authoritative for refreshed data.
- UNKNOWN, null, empty, nan, unknown, none and - company metadata is not crawlable.
- Existing valid symbols remain visible and queueable.

## Validation Evidence

- Screenshot on 2026-08-27 showed invalid legacy rows still active after the initial filtering implementation.
- Run the targeted universe tests and refresh the Finance Data endpoint after pulling the commit.

## Result

Legacy warrant/incomplete rows are excluded at read and crawl boundaries, independently of database cleanup timing.
