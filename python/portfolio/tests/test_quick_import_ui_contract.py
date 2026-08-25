from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FRONTEND = REPO / "frontend" / "src"


def _panel() -> str:
    return (FRONTEND / "components" / "QuickImportPanel.jsx").read_text(encoding="utf-8")


def _quick_import_css() -> str:
    return (FRONTEND / "quick-import.css").read_text(encoding="utf-8")


def test_quick_import_is_current_balance_only_without_date_controls():
    panel = _panel()
    assert 'type="date"' not in panel
    assert "Lịch sử đầy đủ" not in panel
    assert "HISTORICAL" not in panel
    assert "import-mode-switch" not in panel
    assert "mode: 'CURRENT'" in panel
    assert "<th>Ngày</th>" not in panel
    assert "row.event_date" not in panel
    assert "QPort tự ghi ngày hôm nay" in panel


def test_field_label_and_helper_use_adjusted_cost_basis():
    panel = _panel()
    assert "Giá vốn sau điều chỉnh" in panel
    assert "Giá vốn sau điều chỉnh (VND/cp)" in panel
    assert "Không tự trừ cổ tức tiền mặt khỏi giá vốn" in panel
    assert "không tái dựng các sự kiện trước ngày này" in panel


def test_guide_explains_split_and_stock_dividend_examples():
    panel = _panel()
    assert "100 CP × 100.000 VND" in panel
    assert "200 CP × 50.000 VND" in panel
    assert "Tổng giá vốn vẫn là" in panel
    assert "cổ tức bằng cổ phiếu" in panel
    assert "Cổ tức tiền mặt không làm thay đổi giá vốn" in panel
    assert "VND đầy đủ trên mỗi cổ phiếu" in panel


def test_guide_is_expandable_and_accessible_via_keyboard():
    panel = _panel()
    assert '<details className="cost-basis-guide">' in panel
    assert "<summary>" in panel
    assert 'aria-describedby="quick-import-guidance quick-import-cost-guidance"' in panel


def test_guidance_styles_are_present_for_mobile():
    css = _quick_import_css()
    assert ".cost-basis-guidance" in css
    assert ".cost-basis-guide" in css


def test_current_balance_mode_requires_cost_basis_confirmation():
    panel = _panel()
    assert 'type="checkbox"' in panel
    assert "checked={confirmed}" in panel
    assert "Tôi xác nhận số lượng và giá vốn đã phản ánh toàn bộ chia/tách" in panel
    assert "cost_basis_adjusted: confirmed" in panel
    assert "disabled={busy || !text.trim() || !confirmed}" in panel


def test_standard_transactions_keep_date_but_opening_position_hides_it():
    transactions = (FRONTEND / "pages" / "TransactionsPage.jsx").read_text(encoding="utf-8")
    assert 'type="date"' in transactions
    assert "event_date: today" in transactions
    assert "const isOpeningPosition = type === 'POSITION_IMPORT'" in transactions
    assert '{!isOpeningPosition && <label className="transaction-date-field">' in transactions
    assert "data-event-type={type}" in transactions


def test_desktop_portfolio_menu_uses_body_portal_and_closes_on_navigation():
    nav = (FRONTEND / "components" / "AppNav.jsx").read_text(encoding="utf-8")
    css = (FRONTEND / "header-v2.css").read_text(encoding="utf-8")
    assert "const desktopPortfolioMenu" in nav
    assert 'id="desktop-portfolio-menu"' in nav
    assert "portfolioTriggerRef.current?.getBoundingClientRect()" in nav
    assert "setPortfolioOpen(false);" in nav
    assert "position: fixed;" in css
    assert "z-index: 611;" in css
