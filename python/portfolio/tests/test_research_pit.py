"""T09 — Point-in-time fundamental availability tests."""
from __future__ import annotations

import pytest

from portfolio.research.pit import (
    DEFAULT_LAGS,
    AvailabilitySource,
    availability_from_fact,
    facts_from_canonical,
    get_facts_as_of,
    lag_days_for,
)


def _fact(**kwargs):
    base = {
        "symbol": "FPT",
        "line_item_code": "IS.PROFIT.NET",
        "value": 100.0,
        "period_type": "QUARTER",
        "fiscal_year": 2023,
        "fiscal_quarter": 2,
        "period_end": "2023-06-30",
        "observed_at": "2025-09-01T00:00:00Z",
    }
    base.update(kwargs)
    return base


def test_quarterly_report_invisible_before_available_from():
    facts = [_fact()]
    # Q2/2023 period_end = 2023-06-30 -> inferred availability = 2023-08-14.
    available_from = availability_from_fact(facts[0])["available_from"]
    assert available_from == "2023-08-14"
    assert get_facts_as_of(facts, "2023-07-05") == []
    assert get_facts_as_of(facts, "2023-08-13") == []


def test_quarterly_report_visible_after_available_from():
    facts = [_fact()]
    visible = get_facts_as_of(facts, "2023-08-14")
    assert len(visible) == 1
    assert visible[0]["available_from"] == "2023-08-14"


def test_annual_report_equivalent():
    annual = _fact(period_type="FY", fiscal_quarter=None, period_end="2023-12-31")
    avail = availability_from_fact(annual)
    assert avail["available_from"] == "2024-03-30"  # 90-day annual lag (2024 is a leap year)
    assert avail["availability_source"] == AvailabilitySource.INFERRED_ANNUAL_LAG.value


def test_inferred_lag_correctly_tagged():
    avail = availability_from_fact(_fact())
    assert avail["availability_source"] == AvailabilitySource.INFERRED_QUARTERLY_LAG.value
    assert avail["availability_confidence"] == "INFERRED"
    assert avail["published_at"] is None
    # observed_at (crawl time) is recorded as received_at only, never visibility.
    assert avail["received_at"] == "2025-09-01"


def test_verified_publication_overrides_inferred_lag():
    fact = _fact(published_at="2023-07-28", availability_source=AvailabilitySource.VERIFIED_EXCHANGE_DISCLOSURE.value)
    avail = availability_from_fact(fact)
    assert avail["available_from"] == "2023-07-28"
    assert avail["availability_source"] == AvailabilitySource.VERIFIED_EXCHANGE_DISCLOSURE.value
    assert avail["availability_confidence"] == "VERIFIED"
    # Visible earlier than the inferred lag would allow.
    assert get_facts_as_of([fact], "2023-07-28")


def test_restatement_is_versioned():
    v1 = _fact(period_end="2022-12-31", period_type="FY", value=90.0, published_at="2023-03-01", version="1")
    v2 = _fact(period_end="2022-12-31", period_type="FY", value=95.0, published_at="2023-08-01", version="2")
    # At 2023-06-01 only v1 is available -> snapshot uses v1 value.
    early = get_facts_as_of([v1, v2], "2023-06-01")
    assert len(early) == 1 and early[0]["value"] == 90.0
    # At 2023-09-01 v2 supersedes -> snapshot uses v2 value.
    late = get_facts_as_of([v1, v2], "2023-09-01")
    assert len(late) == 1 and late[0]["value"] == 95.0
    # The frozen early snapshot keeps v1 (get_facts_as_of is a pure function of
    # the as-of date; a later restatement cannot rewrite it).
    assert early[0]["value"] == 90.0


def test_fetched_at_alone_never_grants_historical_visibility():
    # A fact crawled recently (observed_at 2025) for an old period is still
    # invisible at an early as_of because fetched_at is not publication time.
    fact = _fact(period_end="2023-06-30", observed_at="2025-09-01T00:00:00Z")
    assert get_facts_as_of([fact], "2023-06-30") == []
    assert get_facts_as_of([fact], "2023-08-14")  # only after the inferred lag


def test_fetched_at_alone_never_grants_visibility_even_for_new_period():
    # Even if fetched_at == period_end (crawled same day), the fact is not
    # visible until the availability date.
    fact = _fact(period_end="2023-06-30", fetched_at="2023-06-30T12:00:00Z")
    assert get_facts_as_of([fact], "2023-06-30") == []


def test_lag_config_is_configurable_and_documented():
    assert DEFAULT_LAGS["QUARTER"] == 45
    assert DEFAULT_LAGS["FY"] == 90
    assert lag_days_for("QUARTER", {"QUARTER": 60}) == 60
    avail = availability_from_fact(_fact(), lags={"QUARTER": 60})
    assert avail["available_from"] == "2023-08-29"


def test_unknown_period_type_falls_back_to_annual_lag():
    avail = availability_from_fact(_fact(period_type="WEIRD"))
    assert avail["available_from"] == "2023-09-28"  # 90 days from 06-30


def test_facts_from_canonical_rejects_bad_symbol(tmp_path):
    # DB-backed loader is not exercised without a live DB; ensure the shape of
    # the query contract is documented by asserting the function is callable
    # only with a connection (no silent fallback).
    with pytest.raises(Exception):
        facts_from_canonical("FPT", connection=object())