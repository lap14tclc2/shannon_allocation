"""Automated Semantic Coverage Test for QPort Enums & Internal Codes (Task 148).

Verifies that EVERY user-facing enum and internal machine status has a valid, non-empty,
investor-grade Vietnamese semantic presentation mapping in vietnamese_presenter.py.
"""

from portfolio.value_engine.vietnamese_presenter import (
    ARCHETYPE_VIETNAMESE,
    CLASSIFICATION_VIETNAMESE,
    DECISION_VIETNAMESE,
    DETERIORATION_VIETNAMESE,
    FINDING_TITLES,
    HARD_REJECT_REASON_VIETNAMESE,
    MARGIN_TREND_VIETNAMESE,
    Q7_CLASSIFICATION_VIETNAMESE,
    QUALITY_TIER_VIETNAMESE,
    STATUS_VIETNAMESE,
    VALUETRAP_VIETNAMESE,
    get_vietnamese_archetype,
    get_vietnamese_classification,
    get_vietnamese_decision,
    get_vietnamese_deterioration,
    get_vietnamese_finding_title,
    get_vietnamese_hard_reject_reason,
    get_vietnamese_q7_classification,
    get_vietnamese_quality_tier,
    get_vietnamese_status,
    get_vietnamese_valuetrap,
)


def test_specific_prompt_required_semantic_mappings():
    """Verify specific required mappings from prompt requirements."""
    assert get_vietnamese_finding_title("RECEIVABLES_GROW_FASTER_THAN_REVENUE") == "Khoản phải thu tăng nhanh hơn doanh thu"
    assert get_vietnamese_finding_title("PROFIT_CASH_DIVERGENCE") == "Lợi nhuận tăng nhưng dòng tiền không theo kịp"
    assert get_vietnamese_deterioration("NO_DETERIORATION") == "Chưa phát hiện xu hướng suy giảm đáng kể"
    assert get_vietnamese_deterioration("POSSIBLY_STRUCTURAL") == "Có dấu hiệu suy giảm có thể mang tính cấu trúc"
    assert get_vietnamese_decision("WAIT_FOR_MOS") == "Chờ biên an toàn"
    assert get_vietnamese_decision("REVIEW_BUSINESS") == "Cần xem xét thêm dữ liệu doanh nghiệp"
    assert get_vietnamese_classification("INSUFFICIENT_DATA") == "Chưa đủ dữ liệu để đánh giá"
    assert get_vietnamese_status("NOT_APPLICABLE") == "Không áp dụng"
    assert get_vietnamese_status("UNKNOWN") == "Chưa đủ dữ liệu"


def test_status_vietnamese_coverage():
    for code, text in STATUS_VIETNAMESE.items():
        assert text and text != code
        assert "_" not in text
        assert get_vietnamese_status(code) == text


def test_decision_vietnamese_coverage():
    for code, text in DECISION_VIETNAMESE.items():
        assert text and text != code
        assert "_" not in text
        assert get_vietnamese_decision(code) == text


def test_classification_vietnamese_coverage():
    for code, text in CLASSIFICATION_VIETNAMESE.items():
        assert text and text != code
        assert "_" not in text
        assert get_vietnamese_classification(code) == text


def test_q7_classification_vietnamese_coverage():
    for code, text in Q7_CLASSIFICATION_VIETNAMESE.items():
        assert text and text != code
        assert "_" not in text
        assert get_vietnamese_q7_classification(code) == text


def test_quality_tier_vietnamese_coverage():
    for code, text in QUALITY_TIER_VIETNAMESE.items():
        assert text and text != code
        assert "_" not in text
        assert get_vietnamese_quality_tier(code) == text


def test_hard_reject_reason_vietnamese_coverage():
    for code, text in HARD_REJECT_REASON_VIETNAMESE.items():
        assert text and text != code
        assert "_" not in text
        assert get_vietnamese_hard_reject_reason(code) == text


def test_valuetrap_vietnamese_coverage():
    for code, text in VALUETRAP_VIETNAMESE.items():
        assert text and text != code
        assert "_" not in text
        assert get_vietnamese_valuetrap(code) == text


def test_deterioration_vietnamese_coverage():
    for code, text in DETERIORATION_VIETNAMESE.items():
        assert text and text != code
        assert "_" not in text
        assert get_vietnamese_deterioration(code) == text


def test_archetype_vietnamese_coverage():
    for code, text in ARCHETYPE_VIETNAMESE.items():
        assert text and text != code
        assert "_" not in text
        assert get_vietnamese_archetype(code) == text


def test_finding_titles_coverage():
    for code, text in FINDING_TITLES.items():
        assert text and text != code
        assert "_" not in text
        assert get_vietnamese_finding_title(code) == text
