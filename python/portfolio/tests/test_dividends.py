from __future__ import annotations

from portfolio.dividends import (
    DividendEvent,
    FireAntDividendProvider,
    LatestDividendService,
    VietcapDividendProvider,
)


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload=None, status=200):
        self.payload = payload
        self.status = status
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.payload, self.status)


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


class StaticProvider:
    def __init__(self, name, events=None, error=None):
        self.name = name
        self._events = events or []
        self._error = error

    def health(self):
        return {"provider": self.name, "available": self._error is None}

    def events(self, symbol, start, end):
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
