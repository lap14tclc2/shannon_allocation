"""T09 — Point-in-Time fundamental availability model.

The core guarantee: for analysis time T, no financial fact with
``available_from > T`` may be used. ``fetched_at`` / ``observed_at`` are crawl
times and are NEVER treated as publication time.

Canonical availability fields (per fact):

    period_end
    published_at        (optional verified date)
    known_at            (earliest the market could know the fact)
    received_at         (system receipt / crawl time)
    available_from      (the date from which the fact may be used)
    availability_source (VERIFIED_* | INFERRED_* | UNKNOWN)
    availability_confidence (VERIFIED | INFERRED)

Preference order for ``available_from``:
    1. verified ``published_at`` (source VERIFIED_*)
    2. conservative governance fallback: period_end + lag(period_type)

Governance fallback lags are ASSUMPTIONS, not exact filing dates:
    quarterly: 45 days
    annual (FY): 90 days
Both are configurable and clearly documented as INFERRED.
"""
from __future__ import annotations

from datetime import date, timedelta
from enum import Enum
from typing import Iterable

# Governance fallback lags (calendar days after period_end) — INFERRED only.
DEFAULT_LAGS: dict[str, int] = {
    "QUARTER": 45,
    "FY": 90,
}
# Documented label for the governance assumption.
LAG_POLICY_DOC = (
    "Inferred availability uses a fixed calendar lag after period_end "
    "(quarterly 45d, annual 90d). This is a conservative governance assumption, "
    "NOT a verified filing date."
)


class AvailabilitySource(str, Enum):
    VERIFIED_PROVIDER_TIMESTAMP = "VERIFIED_PROVIDER_TIMESTAMP"
    VERIFIED_EXCHANGE_DISCLOSURE = "VERIFIED_EXCHANGE_DISCLOSURE"
    VERIFIED_DOCUMENT_METADATA = "VERIFIED_DOCUMENT_METADATA"
    INFERRED_QUARTERLY_LAG = "INFERRED_QUARTERLY_LAG"
    INFERRED_ANNUAL_LAG = "INFERRED_ANNUAL_LAG"
    UNKNOWN = "UNKNOWN"


class AvailabilityConfidence(str, Enum):
    VERIFIED = "VERIFIED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


def _to_date(value) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _normalize_period_type(period_type) -> str:
    raw = str(period_type or "").upper()
    if "FY" in raw or "ANNUAL" in raw or "YEAR" in raw:
        return "FY"
    if "QUARTER" in raw or raw.startswith("Q"):
        return "QUARTER"
    return raw


def lag_days_for(period_type, lags: dict[str, int] | None = None) -> int:
    """Return the governance fallback lag (calendar days) for a period type."""
    config = dict(DEFAULT_LAGS)
    if lags:
        config.update({_normalize_period_type(k): int(v) for k, v in lags.items()})
    return int(config.get(_normalize_period_type(period_type), config["FY"]))


def availability_from_fact(
    fact: dict,
    *,
    lags: dict[str, int] | None = None,
    verified_source: str = AvailabilitySource.VERIFIED_PROVIDER_TIMESTAMP.value,
) -> dict:
    """Compute canonical availability fields for one fact row.

    ``fact`` must contain at least ``period_end`` and ``period_type``. Optional:
    ``published_at``, ``known_at``, ``received_at`` / ``observed_at`` /
    ``fetched_at``, ``availability_source``, ``availability_confidence``.

    ``fetched_at`` / ``observed_at`` are recorded as ``received_at`` only; they
    NEVER advance ``available_from``.
    """
    period_end = _to_date(fact["period_end"])
    period_type = _normalize_period_type(fact.get("period_type") or "FY")
    published_at = fact.get("published_at")
    received_at = (
        fact.get("received_at")
        or fact.get("observed_at")
        or fact.get("fetched_at")
    )

    if published_at:
        published_date = _to_date(published_at)
        available_from = published_date
        published_iso = published_date.isoformat()
        source = str(fact.get("availability_source") or verified_source)
        confidence = str(
            fact.get("availability_confidence")
            or AvailabilityConfidence.VERIFIED.value
        )
    else:
        lag = lag_days_for(period_type, lags)
        available_from = period_end + timedelta(days=lag)
        published_iso = None
        source = (
            AvailabilitySource.INFERRED_QUARTERLY_LAG.value
            if period_type == "QUARTER"
            else AvailabilitySource.INFERRED_ANNUAL_LAG.value
        )
        confidence = AvailabilityConfidence.INFERRED.value

    known_at = fact.get("known_at")
    if not known_at:
        # Without verified publication data, the earliest defensible known time
        # is the availability date itself.
        known_at = available_from.isoformat()

    return {
        "period_end": period_end.isoformat(),
        "published_at": published_iso,
        "known_at": str(known_at)[:10],
        "received_at": str(received_at)[:10] if received_at else None,
        "available_from": available_from.isoformat(),
        "availability_source": source,
        "availability_confidence": confidence,
    }


def _logical_key(fact: dict) -> tuple:
    """Identity of a logical fact (restatements share this key)."""
    return (
        str(fact.get("symbol") or "").upper(),
        str(fact.get("line_item_code") or ""),
        str(fact.get("period_type") or ""),
        str(fact.get("fiscal_year") or ""),
        str(fact.get("fiscal_quarter") or ""),
        str(fact.get("period_end") or ""),
    )


def _version_rank(fact: dict) -> tuple:
    """Order restatements: prefer later available_from, then explicit version."""
    return (
        str(fact.get("available_from") or ""),
        str(fact.get("version") or 0),
        str(fact.get("revision_no") or ""),
    )


def get_facts_as_of(
    facts: Iterable[dict],
    as_of_date,
    *,
    lags: dict[str, int] | None = None,
    select_latest_version: bool = True,
) -> list[dict]:
    """Return facts whose ``available_from <= as_of_date``.

    Guarantee: no fact with ``available_from > as_of_date`` is returned.

    Restatement handling: when multiple rows share a logical fact key and all
    are available as of ``as_of_date``, the latest version (by available_from,
    then explicit version) is kept. Earlier snapshots that were frozen before a
    restatement became available are NOT rewritten.
    """
    as_of = _to_date(as_of_date)
    available: list[dict] = []
    for fact in facts:
        avail = availability_from_fact(fact, lags=lags)
        if avail["available_from"] <= as_of.isoformat():
            available.append({**dict(fact), **avail})

    if not select_latest_version:
        return available

    best: dict[tuple, dict] = {}
    for row in available:
        key = _logical_key(row)
        current = best.get(key)
        if current is None or _version_rank(row) > _version_rank(current):
            best[key] = row
    return list(best.values())


def facts_from_canonical(
    symbol: str,
    *,
    limit: int = 5000,
    connection=None,
) -> list[dict]:
    """Load fact rows from the canonical facts table (production source).

    ``connection`` is optional; when omitted a Postgres connection to the
    finance schema is opened. Rows carry the fields the PIT model needs.
    """
    sql = (
        "SELECT symbol, statement_type, line_item_code, value, period_type, "
        "fiscal_year, fiscal_quarter, period_end, provider, quality_status, "
        "observed_at "
        "FROM canonical_facts WHERE symbol = ? ORDER BY fiscal_year DESC, "
        "fiscal_quarter DESC LIMIT ?"
    )
    if connection is not None:
        rows = connection.execute(sql, (str(symbol).upper(), int(limit))).fetchall()
    else:
        from ..finance_catalog import FINANCE_SCHEMA, _schema_connection

        with _schema_connection(FINANCE_SCHEMA) as db:
            rows = db.execute(sql, (str(symbol).upper(), int(limit))).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        # value is NUMERIC (could be Decimal); keep as-is for PIT filtering.
        item["symbol"] = str(item.get("symbol") or "").upper()
        out.append(item)
    return out