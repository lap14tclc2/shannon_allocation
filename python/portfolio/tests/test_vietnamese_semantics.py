"""Unit tests for Vietnamese Semantic Presentation Layer (Task 140)."""

import pytest
from portfolio.value_engine.vietnamese_presenter import (
    COMPARISON_VIETNAMESE,
    DECISION_VIETNAMESE,
    STATUS_VIETNAMESE,
    SYSTEM_INVARIANTS_VIETNAMESE,
    enrich_finding_dict,
    generate_vietnamese_finding_narrative,
    get_vietnamese_comparison,
    get_vietnamese_decision,
    get_vietnamese_status,
)


def test_status_translations():
    assert get_vietnamese_status("PASS") == "Đạt"
    assert get_vietnamese_status("WATCH") == "Cần theo dõi"
    assert get_vietnamese_status("FAIL") == "Không đạt"
    assert get_vietnamese_status("UNKNOWN") == "Chưa đủ dữ liệu"
    assert get_vietnamese_status("NOT_APPLICABLE") == "Không áp dụng"
    assert get_vietnamese_status("CLEAR") == "Chưa phát hiện rủi ro đáng kể"
    assert get_vietnamese_status("HIGH_RISK") == "Rủi ro cao"


def test_decision_translations():
    assert get_vietnamese_decision("BUY") == "Có thể mua"
    assert get_vietnamese_decision("BUY_MORE") == "Có thể mua thêm"
    assert get_vietnamese_decision("HOLD") == "Tiếp tục nắm giữ"
    assert get_vietnamese_decision("WAIT_FOR_MOS") == "Chờ mức giá có biên an toàn tốt hơn"
    assert get_vietnamese_decision("REVIEW_BUSINESS") == "Cần xem xét thêm dữ liệu doanh nghiệp"
    assert get_vietnamese_decision("AVOID") == "Chưa phù hợp để đầu tư"
    assert get_vietnamese_decision("SELL") == "Cân nhắc thoái vốn"


def test_comparison_translations():
    assert get_vietnamese_comparison("actual_mos >= required_mos") == "Biên an toàn thực tế đạt yêu cầu tối thiểu"
    assert get_vietnamese_comparison("actual_mos < required_mos") == "Biên an toàn thực tế chưa đạt yêu cầu tối thiểu"
    assert get_vietnamese_comparison("price < base_intrinsic_value") == "Giá thị trường đang thấp hơn giá trị nội tại cơ sở"
    assert get_vietnamese_comparison("receivables_growth > revenue_growth") == "Khoản phải thu tăng nhanh hơn doanh thu"
    assert get_vietnamese_comparison("debt > cash") == "Tổng nợ vay cao hơn lượng tiền mặt và tiền gửi hiện có"


def test_system_invariants_semantics():
    assert SYSTEM_INVARIANTS_VIETNAMESE["NULL_NOT_ZERO"]["formula"] == "NULL != 0"
    assert "Thiếu dữ liệu" in SYSTEM_INVARIANTS_VIETNAMESE["NULL_NOT_ZERO"]["explanation"]

    assert SYSTEM_INVARIANTS_VIETNAMESE["UNKNOWN_NOT_PASS"]["formula"] == "UNKNOWN != PASS"
    assert "Chưa đủ dữ liệu" in SYSTEM_INVARIANTS_VIETNAMESE["UNKNOWN_NOT_PASS"]["explanation"]

    assert SYSTEM_INVARIANTS_VIETNAMESE["WATCH_NOT_FAIL"]["formula"] == "WATCH != FAIL"
    assert "cần theo dõi" in SYSTEM_INVARIANTS_VIETNAMESE["WATCH_NOT_FAIL"]["explanation"].lower()

    assert SYSTEM_INVARIANTS_VIETNAMESE["NOT_APPLICABLE_NOT_UNKNOWN"]["formula"] == "NOT_APPLICABLE != UNKNOWN"
    assert "không áp dụng" in SYSTEM_INVARIANTS_VIETNAMESE["NOT_APPLICABLE_NOT_UNKNOWN"]["explanation"].lower()


def test_finding_narrative_generator():
    narrative = generate_vietnamese_finding_narrative(
        code="RECEIVABLES_GROW_FASTER_THAN_REVENUE",
        status="WATCH",
        metrics={"receivables_cagr": 0.243, "revenue_cagr": 0.102},
        period="Giai đoạn FY2021–FY2025",
    )

    assert narrative["tieu_de"] == "Khoản phải thu tăng nhanh hơn doanh thu"
    assert "doanh thu" in narrative["dieu_gi_dang_xay_ra"].lower() or "phải thu" in narrative["dieu_gi_dang_xay_ra"].lower()
    assert narrative["xu_huong_keo_dai"] == "Giai đoạn FY2021–FY2025"
    assert narrative["muc_do_nghiem_trong"] == "Cần theo dõi"
    assert "24.3%" in narrative["du_lieu_chung_minh"] or "10.2%" in narrative["du_lieu_chung_minh"]


def test_enrich_finding_dict():
    raw_finding = {
        "code": "INVENTORY_GROW_FASTER_THAN_REVENUE",
        "category": "WORKING_CAPITAL",
        "severity": "MEDIUM",
        "confidence": "HIGH",
        "status": "WATCH",
        "start_period": 2021,
        "end_period": 2025,
        "metrics": {"inventory_cagr": 0.185, "revenue_cagr": 0.082},
    }

    enriched = enrich_finding_dict(raw_finding)
    assert enriched["status_vietnamese"] == "Cần theo dõi"
    assert "vietnamese_explanation" in enriched
    assert enriched["vietnamese_explanation"]["tieu_de"] == "Hàng tồn kho tăng nhanh hơn doanh thu"
