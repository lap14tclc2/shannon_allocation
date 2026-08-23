from __future__ import annotations

import pandas as pd

from portfolio.corporate_actions import VnstockCorporateActionProvider


class CommunityCompany:
    def events(self, symbol=None):
        return pd.DataFrame([
            {
                "symbol": symbol,
                "event_name": "Cổ tức bằng cổ phiếu tỷ lệ 10%",
                "record_date": "2026-08-20",
                "payment_date": "2026-09-15",
            }
        ])


class CommunityReference:
    def __init__(self):
        self.company = CommunityCompany()


class LegacyCompanyObject:
    def __init__(self, symbol):
        self.symbol = symbol

    def events(self):
        return pd.DataFrame([
            {
                "event_name": "Cổ tức bằng tiền 2.000 đồng/cp",
                "record_date": "2026-08-20",
            }
        ])


class LegacyCompanyFactory:
    def __call__(self, symbol):
        return LegacyCompanyObject(symbol)


class LegacyReference:
    def __init__(self):
        self.company = LegacyCompanyFactory()


def test_community_v4_company_events_shape_is_supported():
    provider = VnstockCorporateActionProvider(
        reference_factory=CommunityReference,
        provider_name="vnstock",
    )
    actions = provider.events(["FPT"], "2026-01-01", "2026-12-31")

    assert provider.health()["available"] is True
    assert provider.health()["provider"] == "vnstock"
    assert len(actions) == 1
    assert actions[0].symbol == "FPT"
    assert actions[0].action_type == "STOCK_DIVIDEND"
    assert actions[0].stock_ratio == 0.10
    assert actions[0].verification_status == "UNVERIFIED"


def test_legacy_company_callable_shape_remains_supported():
    provider = VnstockCorporateActionProvider(
        reference_factory=LegacyReference,
        provider_name="vnstock_data",
    )
    actions = provider.events(["ACB"], "2026-01-01", "2026-12-31")

    assert len(actions) == 1
    assert actions[0].symbol == "ACB"
    assert actions[0].action_type == "CASH_DIVIDEND"
    assert actions[0].cash_per_share == 2000
    assert actions[0].source == "vnstock_data"


def test_provider_deduplicates_identical_rows():
    class DuplicateCompany:
        def events(self, symbol=None):
            row = {
                "symbol": symbol,
                "event_name": "Cổ tức bằng cổ phiếu tỷ lệ 5%",
                "record_date": "2026-08-20",
            }
            return pd.DataFrame([row, row])

    class DuplicateReference:
        def __init__(self):
            self.company = DuplicateCompany()

    provider = VnstockCorporateActionProvider(
        reference_factory=DuplicateReference,
        provider_name="vnstock",
    )
    actions = provider.events(["FPT"], "2026-01-01", "2026-12-31")
    assert len(actions) == 1
