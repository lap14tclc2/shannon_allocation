from __future__ import annotations

import pandas as pd

from portfolio.corporate_actions import VnstockCorporateActionProvider, normalize_event_row


class CommunityCompany:
    def events(self, symbol=None):
        return pd.DataFrame([
            {"symbol": symbol, "event_name": "Cổ tức bằng cổ phiếu tỷ lệ 10%", "record_date": "2026-08-20", "payment_date": "2026-09-15"}
        ])


class CommunityReference:
    def __init__(self): self.company = CommunityCompany()


class LegacyCompanyObject:
    def __init__(self, symbol): self.symbol = symbol
    def events(self):
        return pd.DataFrame([{"event_name": "Cổ tức bằng tiền 2.000 đồng/cp", "record_date": "2026-08-20"}])


class LegacyCompanyFactory:
    def __call__(self, symbol): return LegacyCompanyObject(symbol)


class LegacyReference:
    def __init__(self): self.company = LegacyCompanyFactory()


def test_community_v4_company_events_shape_is_supported():
    provider = VnstockCorporateActionProvider(reference_factory=CommunityReference, provider_name="vnstock")
    actions = provider.events(["FPT"], "2026-01-01", "2026-12-31")
    assert provider.health()["available"] is True
    assert len(actions) == 1
    assert actions[0].symbol == "FPT"
    assert actions[0].action_type == "STOCK_DIVIDEND"
    assert actions[0].stock_ratio == 0.10
    assert actions[0].verification_status == "UNVERIFIED"


def test_legacy_company_callable_shape_remains_supported():
    provider = VnstockCorporateActionProvider(reference_factory=LegacyReference, provider_name="vnstock_data")
    actions = provider.events(["ACB"], "2026-01-01", "2026-12-31")
    assert len(actions) == 1
    assert actions[0].symbol == "ACB"
    assert actions[0].action_type == "CASH_DIVIDEND"
    assert actions[0].cash_per_share == 2000


def test_provider_deduplicates_identical_rows():
    class DuplicateCompany:
        def events(self, symbol=None):
            row = {"symbol": symbol, "event_name": "Cổ tức bằng cổ phiếu tỷ lệ 5%", "record_date": "2026-08-20"}
            return pd.DataFrame([row, row])
    class DuplicateReference:
        def __init__(self): self.company = DuplicateCompany()
    actions = VnstockCorporateActionProvider(reference_factory=DuplicateReference).events(["FPT"], "2026-01-01", "2026-12-31")
    assert len(actions) == 1


def test_same_symbol_can_have_multiple_dividend_installments():
    class MultiCompany:
        def events(self, symbol=None):
            return pd.DataFrame([
                {"symbol": symbol, "event_name": "Tạm ứng cổ tức đợt 1 bằng tiền 1.000 đồng/cp", "record_date": "2026-05-29", "payment_date": "2026-06-10"},
                {"symbol": symbol, "event_name": "Tạm ứng cổ tức đợt 2 bằng tiền 1.000 đồng/cp", "record_date": "2026-11-20", "payment_date": "2026-12-05"},
            ])
    class MultiReference:
        def __init__(self): self.company = MultiCompany()
    actions = VnstockCorporateActionProvider(reference_factory=MultiReference).events(["FPT"], "2026-01-01", "2026-12-31")
    assert len(actions) == 2
    assert actions[0].external_key != actions[1].external_key
    assert {a.record_date for a in actions} == {"2026-05-29", "2026-11-20"}


def test_provider_payload_noise_does_not_change_event_identity():
    base = {
        "symbol": "FPT", "event_name": "Cổ tức bằng tiền 1.000 đồng/cp",
        "record_date": "2026-05-29", "payment_date": "2026-06-10",
    }
    first = normalize_event_row({**base, "fetched_at": "2026-05-01T10:00:00"})
    second = normalize_event_row({**base, "fetched_at": "2026-05-02T10:00:00", "temporary_vendor_field": "x"})
    assert first is not None and second is not None
    assert first.external_key == second.external_key
