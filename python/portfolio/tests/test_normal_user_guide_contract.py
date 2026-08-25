from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
FRONTEND = REPO / "frontend" / "src"


def test_guide_is_written_for_normal_users_not_developers():
    source = (FRONTEND / "pages" / "GuidePage.jsx").read_text(encoding="utf-8")
    assert "Bắt đầu quản lý danh mục trong vài bước" in source
    assert "Mỗi trang dùng để làm gì?" in source
    assert "Ghi giao dịch đúng cách" in source
    assert "Nếu số liệu trông không đúng" in source
    assert "Một nguyên tắc cần nhớ" in source
    assert "Thói quen sử dụng đơn giản" in source

    # Build/install instructions belong in README/docs, not the in-app normal-user guide.
    for developer_token in (
        "npm ci",
        "npm run build",
        "pip install",
        "python serve.py",
        "Institutional-lite daily workflow",
        "What Operations means",
        "NAV restatement",
    ):
        assert developer_token not in source


def test_guide_explains_actual_user_workflow_and_key_semantics():
    source = (FRONTEND / "pages" / "GuidePage.jsx").read_text(encoding="utf-8")
    for token in (
        "Danh mục",
        "Giao dịch",
        "Hiệu quả",
        "Phân tích",
        "Nhập danh mục ban đầu",
        "Mua thêm cổ phiếu",
        "Bán cổ phiếu",
        "cổ tức",
        "giá vốn",
        "giá vốn sau điều chỉnh",
    ):
        assert token in source


def test_guide_keeps_technical_integrity_rules_collapsed_and_optional():
    source = (FRONTEND / "pages" / "GuidePage.jsx").read_text(encoding="utf-8")
    assert "<details" in source
    assert "Một nguyên tắc cần nhớ" in source
    assert "QPort không tự mua bán thay bạn" in source
    assert "Số cổ phiếu chỉ thay đổi khi có giao dịch hoặc sự kiện doanh nghiệp thực sự được ghi nhận" in source
    assert "không cần hiểu" in source


def test_guide_has_friendly_readable_layout_loaded_globally():
    css = (FRONTEND / "guide-friendly.css").read_text(encoding="utf-8")
    entry = (FRONTEND / "entry-client.jsx").read_text(encoding="utf-8")
    assert "import './guide-friendly.css';" in entry
    assert "font-size: 13.5px" in css
    assert "font-size: 15px" in css
    assert ".guide-start-grid" in css
    assert ".guide-page-grid" in css
    assert ".guide-status-grid" in css
    assert ".guide-faq-grid" in css
