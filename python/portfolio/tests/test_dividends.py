from __future__ import annotations

from portfolio.dividends import (
    CafeFDividendProvider,
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
    session = FakeSession({"data":{"content":[
        {"id":"cash-1","ticker":"FPT","eventCode":"DIV","eventTitleVi":"Trả cổ tức bằng tiền 1.000 đồng/cp","publicDate":"2026-05-01T00:00:00Z","recordDate":"2026-05-29T00:00:00Z","exrightDate":"2026-05-28T00:00:00Z","payoutDate":"2026-06-10T00:00:00Z","valuePerShare":1000,"exerciseRatio":0},
        {"id":"stock-1","ticker":"FPT","eventCode":"ISS","eventTitleVi":"Trả cổ tức bằng cổ phiếu tỷ lệ 15%","recordDate":"2026-07-20T00:00:00Z","exrightDate":"2026-07-17T00:00:00Z","exerciseRatio":0.15},
    ]}})
    rows = VietcapDividendProvider(session=session).events("FPT", "2026-01-01", "2026-12-31")
    assert len(rows) == 2
    assert rows[0].dividend_type == "CASH_DIVIDEND" and rows[0].cash_per_share == 1000
    assert rows[1].dividend_type == "STOCK_DIVIDEND" and rows[1].stock_ratio == 0.15


def test_fireant_parses_documented_event_shape():
    session = FakeSession([
        {"eventID":101,"symbol":"ACB","name":"Cổ tức bằng tiền","title":"Cổ tức bằng tiền 700 đồng/cp","recordDate":"2026-06-16T00:00:00Z","registrationDate":"2026-06-15T00:00:00Z","executionDate":"2026-07-01T00:00:00Z","type":1},
        {"eventID":102,"symbol":"ACB","name":"Cổ tức bằng cổ phiếu","title":"Cổ tức bằng cổ phiếu tỷ lệ 15%","recordDate":"2026-06-16T00:00:00Z","registrationDate":"2026-06-15T00:00:00Z","executionDate":"2026-07-01T00:00:00Z","type":2},
    ])
    rows = FireAntDividendProvider(session=session).events("ACB", "2026-01-01", "2026-12-31")
    assert len(rows) == 2
    assert rows[0].cash_per_share == 700
    assert rows[1].stock_ratio == 0.15


def test_vps_parses_nested_dividend_events_and_ignores_unrelated_company_events():
    session = FakeSession({"status":"ok","data":{"events":[
        {"eventId":"vps-cash-1","ticker":"ACB","eventName":"Chi trả cổ tức bằng tiền 700 đồng/cp","recordDate":"2026-06-16","executionDate":"2026-07-01"},
        {"eventId":"not-dividend","ticker":"ACB","eventName":"Đại hội đồng cổ đông thường niên","eventDate":"2026-05-01"},
    ]}})
    rows = VpsDividendProvider(session=session).events("ACB", "2026-01-01", "2026-12-31")
    assert len(rows) == 1
    assert rows[0].source == "vps_events"
    assert rows[0].cash_per_share == 700
    assert rows[0].record_date == "2026-06-16"


def test_vps_single_source_row_can_emit_cash_and_stock_components():
    session = FakeSession({"events":[{
        "eventId":"acb-combined",
        "symbol":"ACB",
        "title":"Trả cổ tức bằng tiền 700 đồng/cp và trả cổ tức bằng cổ phiếu tỷ lệ 100:13",
        "recordDate":"2026-06-16",
        "exDate":"2026-06-15",
    }]})
    rows = VpsDividendProvider(session=session).events("ACB", "2026-01-01", "2026-12-31")
    assert len(rows) == 2
    assert {row.dividend_type for row in rows} == {"CASH_DIVIDEND", "STOCK_DIVIDEND"}
    cash = next(row for row in rows if row.dividend_type == "CASH_DIVIDEND")
    stock = next(row for row in rows if row.dividend_type == "STOCK_DIVIDEND")
    assert cash.cash_per_share == 700
    assert stock.stock_ratio == 0.13
    assert cash.source_event_id == stock.source_event_id == "acb-combined"


def test_fireant_public_bff_can_parse_nested_json_without_oauth():
    session = FakeSession({"content":{"corporateActions":[{"eventID":"fa-public-1","symbol":"DGC","title":"Cổ tức bằng tiền 3.000 đồng/cp","recordDate":"2026-04-10","executionDate":"2026-04-25"}]}})
    rows = FireAntPublicContentProvider(session=session).events("DGC", "2026-01-01", "2026-12-31")
    assert len(rows) == 1 and rows[0].cash_per_share == 3000


def test_cafef_public_html_parses_combined_acb_dividend():
    page = """
    <html><body><a>ACB: 15.6.2026, ngày GDKHQ trả cổ tức năm 2025 bằng tiền (700 đ/cp), trả cổ tức bằng cổ phiếu (tỷ lệ 100:13)</a></body></html>
    """
    rows = CafeFDividendProvider(session=FakeSession(payload=ValueError("not json"), text=page)).events("ACB", "2026-01-01", "2026-12-31")
    assert len(rows) == 2
    assert {row.dividend_type for row in rows} == {"CASH_DIVIDEND", "STOCK_DIVIDEND"}
    cash = next(row for row in rows if row.dividend_type == "CASH_DIVIDEND")
    stock = next(row for row in rows if row.dividend_type == "STOCK_DIVIDEND")
    assert cash.ex_date == stock.ex_date == "2026-06-15"
    assert cash.cash_per_share == 700
    assert stock.stock_ratio == 0.13


class StaticProvider:
    def __init__(self, name, events=None, error=None):
        self.name = name; self._events = events or []; self._error = error; self.calls = 0
    def health(self): return {"provider":self.name,"available":self._error is None}
    def events(self, symbol, start, end):
        self.calls += 1
        if self._error: raise self._error
        return list(self._events)


def test_latest_selects_latest_record_date_not_latest_payment_of_old_event():
    old = DividendEvent(symbol="FPT",dividend_type="CASH_DIVIDEND",source="vci_iq",source_event_id="old",record_date="2026-05-29",payment_date="2026-12-31",cash_per_share=1000)
    new = DividendEvent(symbol="FPT",dividend_type="STOCK_DIVIDEND",source="vci_iq",source_event_id="new",record_date="2026-07-20",payment_date="2026-08-01",stock_ratio=0.15)
    result = LatestDividendService([StaticProvider("vci_iq",[old,new])]).latest("FPT")
    assert result["latest"]["source_event_id"] == "new"
    assert result["latest_event_date"] == "2026-07-20"


def test_latest_returns_all_components_on_same_latest_event_date():
    cash = DividendEvent(symbol="ACB",dividend_type="CASH_DIVIDEND",source="cafef_public",source_event_id="same",ex_date="2026-06-15",cash_per_share=700)
    stock = DividendEvent(symbol="ACB",dividend_type="STOCK_DIVIDEND",source="cafef_public",source_event_id="same",ex_date="2026-06-15",stock_ratio=0.13)
    result = LatestDividendService([StaticProvider("cafef_public",[cash,stock])]).latest("ACB")
    assert result["found"] is True
    assert len(result["latest_components"]) == 2
    assert result["latest"]["dividend_type"] == "CASH_DIVIDEND"


def test_provider_failure_does_not_block_fallback():
    fallback = DividendEvent(symbol="DGC",dividend_type="CASH_DIVIDEND",source="cafef_public",source_event_id="cf-1",ex_date="2026-04-10",cash_per_share=3000)
    result = LatestDividendService([StaticProvider("vps_events",error=RuntimeError("temporary outage")),StaticProvider("cafef_public",[fallback])]).latest("DGC")
    assert result["latest"]["source"] == "cafef_public"
    assert result["errors"][0]["provider"] == "vps_events"


def test_equivalent_events_are_cross_source_matched_in_aggregate_mode():
    a = DividendEvent(symbol="FPT",dividend_type="CASH_DIVIDEND",source="vci_iq",source_event_id="vci-1",record_date="2026-05-29",ex_date="2026-05-28",payment_date="2026-06-10",cash_per_share=1000)
    b = DividendEvent(symbol="FPT",dividend_type="CASH_DIVIDEND",source="fireant",source_event_id="fa-1",record_date="2026-05-29",ex_date="2026-05-28",payment_date="2026-06-10",cash_per_share=1000)
    result = LatestDividendService([StaticProvider("vci_iq",[a]),StaticProvider("fireant",[b])]).latest("FPT")
    assert result["latest"]["cross_source_match"] is True


def test_default_provider_order_prefers_public_no_auth_sources():
    service = LatestDividendService()
    assert [p.name for p in service.providers] == ["vps_events","cafef_public","fireant_public","vci_iq","fireant"]
    assert service.stop_on_first_data is True


def test_failover_short_circuits_after_first_usable_provider():
    event = DividendEvent(symbol="ACB",dividend_type="CASH_DIVIDEND",source="vps_events",source_event_id="vps-1",record_date="2026-06-16",cash_per_share=700)
    primary = StaticProvider("vps_events",[event]); blocked = StaticProvider("vci_iq",error=RuntimeError("should never be called"))
    result = LatestDividendService([primary,blocked],stop_on_first_data=True).latest("ACB")
    assert result["latest"]["source"] == "vps_events"
    assert primary.calls == 1 and blocked.calls == 0
