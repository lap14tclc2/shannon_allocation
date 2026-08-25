from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FRONTEND = REPO / "frontend" / "src"


def _panel() -> str:
    return (FRONTEND / "components" / "QuickImportPanel.jsx").read_text(encoding="utf-8")


def _quick_import_css() -> str:
    return (FRONTEND / "quick-import.css").read_text(encoding="utf-8")


def test_current_balance_mode_has_no_date_input():
    panel = _panel()
    assert 'type="date"' not in panel
    assert 'className="quick-import-textarea"' in panel


def test_current_balance_mode_shows_system_controlled_start_date():
    panel = _panel()
    assert "Ngày bắt đầu được hệ thống tự động ghi là hôm nay" in panel
    assert "không thể chọn hoặc sửa" in panel
    # The preview still surfaces the server-decided date, but it is not editable.
    assert "row.event_date" in panel


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
    assert "<details className=\"cost-basis-guide\">" in panel
    assert "<summary>" in panel
    assert "aria-describedby" in panel


def test_guidance_styles_are_present_for_mobile():
    css = _quick_import_css()
    assert ".cost-basis-guidance" in css
    assert ".cost-basis-guide" in css
    assert ".quick-import-date-note" in css


def test_current_balance_mode_requires_cost_basis_confirmation():
    panel = _panel()
    assert "type=\"checkbox\"" in panel
    assert "confirmed" in panel
    assert "Tôi xác nhận số lượng và giá vốn đã phản ánh toàn bộ chia/tách" in panel
    # The confirmation must be required (not pre-checked) and sent to the backend.
    assert "checked={confirmed}" in panel
    assert "cost_basis_adjusted: mode === 'CURRENT' ? confirmed : undefined" in panel
    # Preview stays disabled until confirmed in CURRENT mode.
    assert "mode === 'CURRENT' && !confirmed" in panel


def test_historical_mode_does_not_require_confirmation():
    panel = _panel()
    # Confirmation gate is scoped to CURRENT only.
    assert "mode === 'CURRENT' && !confirmed" in panel
    assert "mode === 'CURRENT' && <div className=\"cost-basis-guidance\"" in panel


def test_standard_transaction_form_keeps_date_field_defaulting_to_today():
    transactions = (FRONTEND / "pages" / "TransactionsPage.jsx").read_text(encoding="utf-8")
    assert 'type="date"' in transactions
    assert "event_date: today" in transactions
    assert "max={today || undefined}" in transactions
    assert "{type !== 'POSITION_IMPORT' && <label>" in transactions
    # Opening-position entry and Quick Import both use the server-controlled current date.
    # Other standard transaction types retain their visible date field.
    panel = _panel()
    assert 'type="date"' not in panel
