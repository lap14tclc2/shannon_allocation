from __future__ import annotations

import pandas as pd

from portfolio.corporate_actions import VnstockCorporateActionProvider, normalize_event_row
from portfolio.dividends import DividendEvent


class CommunityCompany:
    def events(self, symbol=None):
        return pd.DataFrame([{"symbol":symbol,"event_name":"Cổ tức bằng cổ phiếu tỷ lệ 10%","record_date":"2026-08-20","payment_date":"2026-09-15"}])
class CommunityReference:
    def __init__(self): self.company=CommunityCompany()
class LegacyCompanyObject:
    def __init__(self,symbol): self.symbol=symbol
    def events(self): return pd.DataFrame([{"event_name":"Cổ tức bằng tiền 2.000 đồng/cp","record_date":"2026-08-20"}])
class LegacyCompanyFactory:
    def __call__(self,symbol): return LegacyCompanyObject(symbol)
class LegacyReference:
    def __init__(self): self.company=LegacyCompanyFactory()


def test_community_v4_company_events_shape_is_supported():
    provider=VnstockCorporateActionProvider(reference_factory=CommunityReference,provider_name="vnstock")
    actions=provider.events(["FPT"],"2026-01-01","2026-12-31")
    assert provider.health()["available"] is True
    assert len(actions)==1 and actions[0].action_type=="STOCK_DIVIDEND" and actions[0].stock_ratio==0.10


def test_legacy_company_callable_shape_remains_supported():
    actions=VnstockCorporateActionProvider(reference_factory=LegacyReference,provider_name="vnstock_data").events(["ACB"],"2026-01-01","2026-12-31")
    assert len(actions)==1 and actions[0].action_type=="CASH_DIVIDEND" and actions[0].cash_per_share==2000


def test_provider_deduplicates_identical_rows():
    class DuplicateCompany:
        def events(self,symbol=None):
            row={"symbol":symbol,"event_name":"Cổ tức bằng cổ phiếu tỷ lệ 5%","record_date":"2026-08-20"}
            return pd.DataFrame([row,row])
    class DuplicateReference:
        def __init__(self): self.company=DuplicateCompany()
    actions=VnstockCorporateActionProvider(reference_factory=DuplicateReference).events(["FPT"],"2026-01-01","2026-12-31")
    assert len(actions)==1


def test_same_symbol_can_have_multiple_dividend_installments():
    class MultiCompany:
        def events(self,symbol=None):
            return pd.DataFrame([
                {"symbol":symbol,"event_name":"Tạm ứng cổ tức đợt 1 bằng tiền 1.000 đồng/cp","record_date":"2026-05-29","payment_date":"2026-06-10"},
                {"symbol":symbol,"event_name":"Tạm ứng cổ tức đợt 2 bằng tiền 1.000 đồng/cp","record_date":"2026-11-20","payment_date":"2026-12-05"},
            ])
    class MultiReference:
        def __init__(self): self.company=MultiCompany()
    actions=VnstockCorporateActionProvider(reference_factory=MultiReference).events(["FPT"],"2026-01-01","2026-12-31")
    assert len(actions)==2
    assert actions[0].external_key!=actions[1].external_key
    assert {a.record_date for a in actions}=={"2026-05-29","2026-11-20"}


def test_provider_payload_noise_does_not_change_event_identity():
    base={"symbol":"FPT","event_name":"Cổ tức bằng tiền 1.000 đồng/cp","record_date":"2026-05-29","payment_date":"2026-06-10"}
    first=normalize_event_row({**base,"fetched_at":"2026-05-01T10:00:00"})
    second=normalize_event_row({**base,"fetched_at":"2026-05-02T10:00:00","temporary_vendor_field":"x"})
    assert first is not None and second is not None and first.external_key==second.external_key


class StaticDividendProvider:
    def __init__(self,name,rows=None,error=None): self.name=name; self.rows=rows or []; self.error=error; self.calls=[]
    def health(self): return {"provider":self.name,"available":self.error is None}
    def events(self,symbol,start,end):
        self.calls.append(symbol)
        if self.error: raise self.error
        return [row for row in self.rows if row.symbol==symbol]


def test_runtime_corporate_action_sync_falls_back_and_keeps_combined_components():
    blocked=StaticDividendProvider("vps_events",error=RuntimeError("temporary failure"))
    public=StaticDividendProvider("cafef_public",[
        DividendEvent(symbol="ACB",dividend_type="CASH_DIVIDEND",source="cafef_public",source_event_id="same-event",ex_date="2026-06-15",record_date="2026-06-16",cash_per_share=700),
        DividendEvent(symbol="ACB",dividend_type="STOCK_DIVIDEND",source="cafef_public",source_event_id="same-event",ex_date="2026-06-15",record_date="2026-06-16",stock_ratio=0.13),
    ])
    never=StaticDividendProvider("vci_iq",error=RuntimeError("should not be called"))
    provider=VnstockCorporateActionProvider(dividend_providers=[blocked,public,never])
    actions=provider.events(["ACB"],"2026-01-01","2026-12-31")
    assert len(actions)==2
    assert {a.action_type for a in actions}=={"CASH_DIVIDEND","STOCK_DIVIDEND"}
    assert len({a.external_key for a in actions})==2
    assert all(a.verification_status=="UNVERIFIED" for a in actions)
    assert blocked.calls==["ACB"] and public.calls==["ACB"] and never.calls==[]
    health=provider.health()
    assert health["available"] is True and health["last_success_source"]=="cafef_public"


def test_runtime_provider_status_is_not_probed_before_first_sync():
    provider=VnstockCorporateActionProvider(dividend_providers=[])
    health=provider.health()
    assert health["available"] is None and health["status"]=="NOT_PROBED"
