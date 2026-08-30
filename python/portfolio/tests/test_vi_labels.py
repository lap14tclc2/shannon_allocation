import pytest
from portfolio.value_engine.vi_labels import (
    ARCHETYPE_VI,
    QUALITY_TIER_VI,
    VAL_VERDICT_VI,
    VALUATION_MODEL_VI,
    archetype_vi,
    quality_tier_vi,
    valuation_model_vi,
    verdict_vi,
)


def test_verdict_labels_are_vietnamese():
    for code, label in VAL_VERDICT_VI.items():
        assert label != code, f"verdict label for {code} must be translated"


def test_archetype_labels_are_vietnamese():
    for code, label in ARCHETYPE_VI.items():
        assert label != code, f"archetype label for {code} must be translated"


def test_quality_tier_labels_are_vietnamese():
    for code, label in QUALITY_TIER_VI.items():
        assert label != code, f"quality tier label for {code} must be translated"


def test_valuation_model_labels_are_vietnamese():
    for code, label in VALUATION_MODEL_VI.items():
        assert label != code, f"valuation model label for {code} must be translated"


def test_helpers_fall_back_gracefully():
    assert verdict_vi("UNKNOWN_CODE") == "UNKNOWN_CODE"
    assert archetype_vi("UNKNOWN_CODE") == "UNKNOWN_CODE"
    assert quality_tier_vi("UNKNOWN_CODE") == "UNKNOWN_CODE"
    assert valuation_model_vi("UNKNOWN_CODE") == "UNKNOWN_CODE"


def test_known_codes_mapped():
    assert verdict_vi("HIGH_CONVICTION_VALUE") == "Đầu tư Giá trị Tuyệt vời"
    assert archetype_vi("TECHNOLOGY_SERVICES") == "Dịch vụ Công nghệ"
    assert quality_tier_vi("EXCEPTIONAL") == "Xuất sắc"
    assert valuation_model_vi("NORMALIZED_OWNER_EARNINGS_DCF") == "Chiết khấu Lợi nhuận Thực bình quân chu kỳ"