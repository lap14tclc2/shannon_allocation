"""Regression tests for the VSDC (official depository) ingestion module."""
from __future__ import annotations

import pytest

from portfolio.vsdc import (
    VsdcCorporateActionProvider,
    VsdcClient,
    parse_announcement,
    parse_share_registration_history,
)

CASH_ANN = """
<html><head><meta name="__VPToken" content="ABC123"></head>
<body>
<h3 class="title-category">SBT: Chi tr&#7843; c&#7893; t&#7913;c n&#259;m 2025 b&#7857;ng ti&#7873;n m&#7863;t</h3>
<div class="time-newstcph">C&#7853;p nh&#7853;t ng&#224;y 08/06/2026 - 16:45:45</div>
<div class="content-category">
  <div class="row">
    <div class="col-md-4 col-sm-6 item-info">M&#227; ch&#7913;ng kho&#225;n:</div>
    <div class="col-md-8 col-sm-6 item-info item-info-main">SBT</div>
  </div>
  <div class="row">
    <div class="col-md-4 col-sm-6 item-info">Ng&#224;y &#273;&#259;ng k&#253; cu&#7889;i c&#249;ng:</div>
    <div class="col-md-8 col-sm-6 item-info item-info-main">15/06/2026</div>
  </div>
  <div class="row">
    <div class="col-md-4 col-sm-6 item-info">L&#253; do m&#7909;c &#273;&#237;ch:</div>
    <div class="col-md-8 col-sm-6 item-info item-info-main">Tr&#7843; c&#7893; t&#7913;c b&#7857;ng ti&#7873;n m&#7863;t</div>
  </div>
  <div class="row">
    <div class="col-md-4 col-sm-6 item-info">Ng&#224;y thanh to&#225;n:</div>
    <div class="col-md-8 col-sm-6 item-info item-info-main">30/06/2026</div>
  </div>
  <div class="row">
    <div class="col-md-4 col-sm-6 item-info">T&#7927; l&#7879; th&#7921;c hi&#7879;n:</div>
    <div class="col-md-8 col-sm-6 item-info item-info-main">10%/c&#7893; phi&#7871;u (01 c&#7893; phi&#7871;u &#273;&#432;&#7907;c nh&#7853;n 1.000 &#273;&#7891;ng)</div>
  </div>
</div>
</body></html>
"""

SHARE_HIST = """
<html><body><div id="Detail_TCPH_TTDKCK">
<div class="table-portal"><table><tbody>
<tr><td style="text-align:center">1</td><td><span>Dang ky lan dau</span></td><td>Dang ky lan dau</td><td style="text-align:right">44.824.172</td><td>23/2008/GCNCP-CNTTLK</td><td style="text-align:center">14/02/2008</td></tr>
<tr><td style="text-align:center">17</td><td><span></span></td><td>Phat hanh co phieu de tra co tuc</td><td style="text-align:right">51.302.453</td><td></td><td style="text-align:center">18/05/2026</td></tr>
<tr><td colspan="3" class="text-center"><span id="SUM_TTDKCK">Tong cong:</span></td><td><span id="SUM_SL_DKCK">928.026.375</span></td><td colspan="2"></td></tr>
</tbody></table></div></div></body></html>
"""


class _FakeClient(VsdcClient):
    def __init__(self) -> None:
        super().__init__(session=None, timeout=1)

    def search_security(self, symbol: str):
        return 707 if symbol == "SBT" else None

    def search_announcements(self, security_id: int, page: int = 1):
        return [{"id": 196661, "title": "Chi trả cổ tức năm 2025 bằng tiền mặt"}]

    def search_rights(self, security_id: int, page: int = 1):
        return []

    def get_announcement(self, announcement_id: int):
        return CASH_ANN


def test_parse_announcement_cash_dividend():
    parsed = parse_announcement(CASH_ANN, 196661)
    assert parsed["symbol"] == "SBT"
    assert parsed["action_type"] == "CASH_DIVIDEND"
    assert parsed["record_date"] == "2026-06-15"
    assert parsed["payment_date"] == "2026-06-30"
    assert parsed["cash_per_share"] == 1000.0
    assert parsed["stock_ratio"] is None
    assert parsed["announcement_date"] == "2026-06-08"


def test_classify_cash_via_bang_tien_phrase():
    # "Chi trả cổ tức bằng tiền ... cổ phiếu ưu đãi" must be CASH, not STOCK.
    from portfolio.vsdc import _classify_vsdc
    assert _classify_vsdc("Chi trả cổ tức bằng tiền cho cổ đông sở hữu cổ phiếu ưu đãi") == "CASH_DIVIDEND"
    assert _classify_vsdc("Trả cổ tức bằng cổ phiếu niên độ 2024-2025") == "STOCK_DIVIDEND"
    assert _classify_vsdc("Thực hiện quyền mua trái phiếu chuyển đổi") == "RIGHTS_ISSUE"


def test_parse_share_registration_history():
    rows = parse_share_registration_history(SHARE_HIST, "SBT")
    assert len(rows) == 2
    assert rows[0]["reason"] == "Dang ky lan dau"
    assert rows[0]["quantity_delta"] == 44824172
    assert rows[0]["date"] == "2008-02-14"
    assert rows[1]["reason"] == "Phat hanh co phieu de tra co tuc"
    assert rows[1]["quantity_delta"] == 51302453


def test_provider_produces_corporate_action():
    provider = VsdcCorporateActionProvider(client=_FakeClient())
    actions = provider.events(["SBT"], "2026-01-01", "2026-12-31")
    assert len(actions) == 1
    action = actions[0]
    assert action.symbol == "SBT"
    assert action.action_type == "CASH_DIVIDEND"
    assert action.cash_per_share == 1000.0
    assert action.source == "vsdc"
    assert action.record_date == "2026-06-15"


def test_provider_filters_outside_window():
    provider = VsdcCorporateActionProvider(client=_FakeClient())
    actions = provider.events(["SBT"], "2020-01-01", "2020-12-31")
    assert actions == []


def test_provider_skips_unknown_symbol():
    provider = VsdcCorporateActionProvider(client=_FakeClient())
    actions = provider.events(["ZZZ"], "2026-01-01", "2026-12-31")
    assert actions == []