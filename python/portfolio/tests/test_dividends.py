from __future__ import annotations

from portfolio.dividends import (
    DividendEvent,
    FireAntDividendProvider,
    FireAntPublicContentProvider,
    LatestDividendService,
    VietcapDividendProvider,
    VpsDividendProvider,
)


class FakeResponse:
    def __init__(self, payload, status=200, text=""):
        self.payload = payload
        self.status_code = status
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class FakeSession:
    def __init__(self, payload=None, status=200, text=""):
        self.payload = payload
        self.status = status
        self.text = text
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.payload, self.status, self.text)


def test_vietcap_parses_cash_and_stock_dividends():
    session = FakeSession({
        "data": {
            "content": [
                {
                    "id": "cash-1",
                    "ticker": "FPT",
                    "eventCode": "DIV",
                    "eventTitleVi": "Trả cổ tức bằng tiền 1.000 đồng/cp",
                    "publicDate": "2026-05-01T00:00:00Z",
                    "recordDate": "2026-05-29T00:00:00Z",
                    "exrightDate": "2026-05-28T00:00:00Z",
                    "payoutDate": "2026-06-10T00:00:00Z",
                    "valuePerShare": 1000,
                    "exerciseRatio": 0,
                },
                {
                    "id": "stock-1",
                    "ticker": "FPT",
                    "eventCode": "ISS",
                    "eventTitleVi": "Trả cổ tức bằng cổ phiếu tỷ lệ 15%",
                    "recordDate": "2026-07-20T00:00:00Z",
                    "exrightDate": "2026-07-17T00:00:00Z",
                    "exerciseRatio": 0.15,
                },
            ]
        }
    })
    provider = VietcapDividendProvider(session=session)
    rows = provider.events("FPT", "2026-01-01", "2026-12-31")

    assert len(rows) == 2
    assert rows[0].dividend_type == "CASH_DIVIDEND"
    assert rows[0].cash_per_share == 1000
    assert rows[1].dividend_type == "STOCK_DIVIDEND"
    assert rows[1].stock_ratio == 0.15


def test_fireant_parses_documented_event_shape():
    session = FakeSession([
        {
            "eventID": 101,
            "symbol": "ACB",
            "name": "Cổ tức bằng tiền",
            "title": "Cổ tức bằng tiền 700 đồng/cp",
            "recordDate": "2026-06-16T00:00:00Z",
            "registrationDate": "2026-06-15T00:00:00Z",
            "executionDate": "2026-07-01T00:00:00Z",
            "type": 1,
        },
        {
            "eventID": 102,
            "symbol": "ACB",
            "name": "Cổ tức bằng cổ phiếu",
            "title": "Cổ tức bằng cổ phiếu tỷ lệ 15%",
            "recordDate": "2026-06-16T00:00:00Z",
            "registrationDate": "2026-06-15T00:00:00Z",
            "executionDate": "2026-07-01T00:00:00Z",
            "type": 2,
        },
    ])
    provider = FireAntDividendProvider(session=session)
    rows = provider.events("ACB", "2026-01-01", "2026-12-31")

    assert len(rows) == 2
    assert rows[0].cash_per_share == 700
    assert rows[1].stock_ratio == 0.15
    assert rows[0].source_event_id == "101"


def test_vps_parses_nested_dividend_events_and_ignores_unrelated_company_events():
    session = FakeSession({
        "status": "ok",
        "data": {
            "events": [
                {
                    "eventId": "vps-cash-1",
                    "ticker": "ACB",
                    "eventName": "Chi trả cổ tức bằng tiền 700 đồng/cp",
                    "recordDate": "2026-06-16",
                    "executionDate": "2026-07-01",
                },
                {
                    "eventId": "not-dividend",
                    "ticker": "ACB",
                    "eventName": "Đại hội đồng cổ đông thường niên",
                    "eventDate": "2026-05-01",
                },
            ]
        },
    })
    provider = VpsDividendProvider(session=session)
    rows = provider.events("ACB", "2026-01-01", "2026-12-31")

    assert len(rows) == 1
    assert rows[0].source == "vps_events"
    assert rows[0].source_event_id == "vps-cash-1"
    assert rows[0].dividend_type == "CASH_DIVIDEND"
    assert rows[0].record_date == "2026-06-16"
    assert rows[0].payment_date == "2026-07-01"
    assert rows[0].cash_per_share == 700


def test_vps_parses_stock_dividend_ratio_from_title():
    session = FakeSession({
        "items": [
            {
                "id": "vps-stock-1",
                "symbol": "FPT",
                "title": "Trả cổ tức bằng cổ phiếu tỷ lệ 15%",
                "lastRegistrationDate": "20/07/2026",
                "exDate": "17/07/2026",
            }
        ]
    })
    rows = VpsDividendProvider(session=session).events("FPT", "2026-01-01", "2026-12-31")

    assert len(rows) == 1
    assert rows[0].dividend_type == "STOCK_DIVIDEND"
    assert rows[0].stock_ratio == 0.15
    assert rows[0].record_date == "2026-07-20"
    assert rows[0].ex_date == "2026-07-17"


def test_fireant_public_bff_can_parse_nested_json_without_oauth():
    session = FakeSession({
        "content": {
            "corporateActions": [
                {
                    "eventID": "fa-public-1",
                    "symbol": "DGC",
                    "title": "Cổ tức bằng tiền 3.000 đồng/cp",
                    "recordDate": "2026-04-10",
                    "executionDate": "2026-04-25",
                }
            ]
        }
    })
    rows = FireAntPublicContentProvider(session=session).events("DGC", "2026-01-01", "2026-12-31")

    assert len(rows) == 1
    assert rows[0].source == "fireant_public"
    assert rows[0].cash_per_share == 3000


class StaticProvider:
    def __init__(self, name, events=None, error=None):
        self.name = name
        self._events = events or []
        self._error = error
        self.calls = 0

    def health(self):
        return {"provider": self.name, "available": self._error is None}

    def events(self, symbol, start, end):
        self.calls += 1
        if self._error:
            raise self._error
        return list(self._events)


def test_latest_selects_latest_record_date_not_latest_payment_of_old_event():
    old = DividendEvent(
        symbol="FPT", dividend_type="CASH_DIVIDEND", source="vci_iq",
        source_event_id="old", record_date="2026-05-29", payment_date="2026-12-31", cash_per_share=1000,
    )
    new = DividendEvent(
        symbol="FPT", dividend_type="STOCK_DIVIDEND", source="vci_iq",
        source_event_id="new", record_date="2026-07-20", payment_date="2026-08-01", stock_ratio=0.15,
    )
    service = LatestDividendService([StaticProvider("vci_iq", [old, new])])
    result = service.latest("FPT")

    assert result["found"] is True
    assert result["latest"]["source_event_id"] == "new"
    assert result["latest"]["effective_event_date"] == "2026-07-20"


def test_provider_failure_does_not_block_fallback():
    fallback = DividendEvent(
        symbol="DGC", dividend_type="CASH_DIVIDEND", source="fireant",
        source_event_id="fa-1", record_date="2026-04-10", cash_per_share=3000,
    )
    service = LatestDividendService([
        StaticProvider("vci_iq", error=RuntimeError("temporary outage")),
        StaticProvider("fireant", [fallback]),
    ])
    result = service.latest("DGC")

    assert result["found"] is True
    assert result["latest"]["source"] == "fireant"
    assert result["errors"][0]["provider"] == "vci_iq"


def test_equivalent_events_are_cross_source_matched():
    vci = DividendEvent(
        symbol="FPT", dividend_type="CASH_DIVIDEND", source="vci_iq",
        source_event_id="vci-1", record_date="2026-05-29", ex_date="2026-05-28",
        payment_date="2026-06-10", cash_per_share=1000,
    )
    fireant = DividendEvent(
        symbol="FPT", dividend_type="CASH_DIVIDEND", source="fireant",
        source_event_id="fa-1", record_date="2026-05-29", ex_date="2026-05-28",
        payment_date="2026-06-10", cash_per_share=1000,
    )
    service = LatestDividendService([
        StaticProvider("vci_iq", [vci]),
        StaticProvider("fireant", [fireant]),
    ])
    result = service.latest("FPT")

    assert result["latest"]["source"] == "vci_iq"
    assert result["latest"]["cross_source_match"] is True
    assert {e["source"] for e in result["latest"]["evidence"]} == {"vci_iq", "fireant"}


def test_default_provider_order_prefers_unauthenticated_sources():
    service = LatestDividendService()
    assert [p.name for p in service.providers] == [
        "vps_events",
        "fireant_public",
        "vci_iq",
        "fireant",
    ]
    assert service.stop_on_first_data is True


def test_failover_short_circuits_after_first_usable_provider():
    event = DividendEvent(
        symbol="ACB",
        dividend_type="CASH_DIVIDEND",
        source="vps_events",
        source_event_id="vps-1",
        record_date="2026-06-16",
        cash_per_share=700,
    )
    primary = StaticProvider("vps_events", [event])
    blocked = StaticProvider("vci_iq", error=RuntimeError("should never be called"))
    service = LatestDividendService([primary, blocked], stop_on_first_data=True)

    result = service.latest("ACB")

    assert result["found"] is True
    assert result["latest"]["source"] == "vps_events"
    assert primary.calls == 1
    assert blocked.calls == 0
    assert result["provider_attempts"] == [
        {"provider": "vps_events", "status": "SUCCESS", "count": 1}
    ]
