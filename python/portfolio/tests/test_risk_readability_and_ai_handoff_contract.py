from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
FRONTEND = REPO / "frontend" / "src"


def test_risk_page_is_plain_language_first_with_progressive_disclosure():
    page = (FRONTEND / "pages" / "RiskPage.jsx").read_text(encoding="utf-8")

    for phrase in (
        "Một mã có đang quá lớn không?",
        "Các mã có thường tăng/giảm cùng nhau?",
        "Gần đây danh mục rung lắc hơn hay ít hơn?",
        "Mã nào đang kéo rủi ro nhiều nhất?",
        "Mỗi mã đang ảnh hưởng danh mục như thế nào?",
        "Đánh giá tổng quan",
        "Chỉ số kỹ thuật và phương pháp tính",
    ):
        assert phrase in page

    assert "<details className=\"risk-technical-details\">" in page
    assert "Risk Score" not in page
    assert "73/100" not in page


def test_technical_risk_evidence_and_erc_are_preserved_but_advanced():
    page = (FRONTEND / "pages" / "RiskPage.jsx").read_text(encoding="utf-8")

    for phrase in (
        "VaR ngày 95%",
        "CVaR ngày 95%",
        "Tỷ lệ đa dạng hóa",
        "Biến động 63 phiên",
        "Biến động 252 phiên",
        "Số vị thế hiệu dụng",
    ):
        assert phrase in page
    assert "risk-technical-details" in page
    assert "Chỉ số kỹ thuật và phương pháp tính" in page


def test_risk_readability_styles_are_loaded_after_general_accessibility():
    entry = (FRONTEND / "entry-vercel.jsx").read_text(encoding="utf-8")
    assert "import './risk-readable.css';" in entry
    assert entry.index("import './accessibility-polish.css';") < entry.index("import './risk-readable.css';")

    css = (FRONTEND / "risk-readable.css").read_text(encoding="utf-8")
    assert ".risk-readable-page" in css
    assert ".risk-technical-details" in css
    assert "font-size: 13.5px" in css
    assert "var(--text-secondary)" in css


def test_ai_working_context_exists_and_documents_non_negotiable_boundaries():
    handoff = (REPO / "AI_WORKING_CONTEXT.md").read_text(encoding="utf-8")

    for phrase in (
        "Buy & Hold Portfolio Information System",
        "only explicit effective ledger events change holdings or cash",
        "diagnostic_reference_only",
        "ERC must not",
        "one canonical provider per refresh",
        "550 calendar days",
        "Fund Manager Review",
        "qport-appearance-v1",
        "Known limitations / future work",
        "Recommended reading order for a new AI session",
    ):
        assert phrase in handoff
