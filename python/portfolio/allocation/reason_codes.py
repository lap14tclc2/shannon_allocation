"""Canonical Allocation reason codes.

Business logic must never depend on localized strings. The frontend maps these
codes to Vietnamese human explanations via ``reason_code_vi``.
"""
from __future__ import annotations

# Quality
QUALITY_STRONG = "QUALITY_STRONG"
QUALITY_DETERIORATING = "QUALITY_DETERIORATING"

# Hard rejection
HARD_REJECT = "HARD_REJECT"

# Valuation
VALUATION_ATTRACTIVE = "VALUATION_ATTRACTIVE"
VALUATION_FAIR = "VALUATION_FAIR"
VALUATION_EXPENSIVE = "VALUATION_EXPENSIVE"
VALUATION_CONFIDENCE_LOW = "VALUATION_CONFIDENCE_LOW"
VALUATION_SAFETY_POSITIVE = "VALUATION_SAFETY_POSITIVE"
VALUATION_SAFETY_NEGATIVE = "VALUATION_SAFETY_NEGATIVE"

# Risk / concentration
POSITION_CONCENTRATED = "POSITION_CONCENTRATED"
RISK_CONTRIBUTION_HIGH = "RISK_CONTRIBUTION_HIGH"
CORRELATION_HIGH = "CORRELATION_HIGH"
DIVERSIFICATION_IMPROVES = "DIVERSIFICATION_IMPROVES"
DIVERSIFICATION_WORSENS = "DIVERSIFICATION_WORSENS"

# Opportunity cost
NO_SUPERIOR_REPLACEMENT = "NO_SUPERIOR_REPLACEMENT"
SUPERIOR_REPLACEMENT_AVAILABLE = "SUPERIOR_REPLACEMENT_AVAILABLE"

# Liquidity / cash
LIQUIDITY_INSUFFICIENT = "LIQUIDITY_INSUFFICIENT"
CASH_PREFERRED = "CASH_PREFERRED"

# Technical (secondary, confirmation only — never overrides fundamentals)
TECHNICAL_CONFIRMATION = "TECHNICAL_CONFIRMATION"
TECHNICAL_DETERIORATION = "TECHNICAL_DETERIORATION"

# Data
DATA_INSUFFICIENT = "DATA_INSUFFICIENT"

ALL_REASON_CODES: frozenset[str] = frozenset({
    QUALITY_STRONG,
    QUALITY_DETERIORATING,
    HARD_REJECT,
    VALUATION_ATTRACTIVE,
    VALUATION_FAIR,
    VALUATION_EXPENSIVE,
    VALUATION_CONFIDENCE_LOW,
    VALUATION_SAFETY_POSITIVE,
    VALUATION_SAFETY_NEGATIVE,
    POSITION_CONCENTRATED,
    RISK_CONTRIBUTION_HIGH,
    CORRELATION_HIGH,
    DIVERSIFICATION_IMPROVES,
    DIVERSIFICATION_WORSENS,
    NO_SUPERIOR_REPLACEMENT,
    SUPERIOR_REPLACEMENT_AVAILABLE,
    LIQUIDITY_INSUFFICIENT,
    CASH_PREFERRED,
    TECHNICAL_CONFIRMATION,
    TECHNICAL_DETERIORATION,
    DATA_INSUFFICIENT,
})

# Vietnamese human explanations used by the frontend.
REASON_CODE_VI: dict[str, str] = {
    QUALITY_STRONG: "Doanh nghiệp chất lượng cao, lợi thế cạnh tranh rõ ràng.",
    QUALITY_DETERIORATING: "Chất lượng doanh nghiệp suy giảm, cần thận trọng.",
    HARD_REJECT: "Vi phạm tiêu chí loại trừ cứng của Buffett/Munger.",
    VALUATION_ATTRACTIVE: "Mức giá có biên an toàn hấp dẫn.",
    VALUATION_FAIR: "Mức giá hợp lý, chưa đủ biên an toàn vượt trội.",
    VALUATION_EXPENSIVE: "Mức giá cao hơn giá trị hợp lý.",
    VALUATION_CONFIDENCE_LOW: "Độ tin cậy định giá thấp, thiếu bằng chứng.",
    VALUATION_SAFETY_POSITIVE: "Biên an toàn thực tế vượt mức yêu cầu.",
    VALUATION_SAFETY_NEGATIVE: "Biên an toàn thực tế thấp hơn mức yêu cầu.",
    POSITION_CONCENTRATED: "Tỷ trọng nắm giữ đang quá tập trung.",
    RISK_CONTRIBUTION_HIGH: "Mã này đóng góp rủi ro quá lớn cho danh mục.",
    CORRELATION_HIGH: "Tương quan cao với các vị thế hiện tại.",
    DIVERSIFICATION_IMPROVES: "Bổ sung giúp cải thiện đa dạng hóa danh mục.",
    DIVERSIFICATION_WORSENS: "Bổ sung làm giảm hiệu quả đa dạng hóa.",
    NO_SUPERIOR_REPLACEMENT: "Không có cơ hội thay thế tốt hơn hẳn hiện tại.",
    SUPERIOR_REPLACEMENT_AVAILABLE: "Có cơ hội thay thế tốt hơn rõ rệt.",
    LIQUIDITY_INSUFFICIENT: "Thanh khoản không đủ để giao dịch quy mô cần thiết.",
    CASH_PREFERRED: "Giữ tiền mặt là lựa chọn hợp lý hiện tại.",
    TECHNICAL_CONFIRMATION: "Xu hướng giá xác nhận quyết định cơ bản.",
    TECHNICAL_DETERIORATION: "Diễn biến giá suy yếu, chưa nên mua thêm.",
    DATA_INSUFFICIENT: "Thiếu dữ liệu, không thể kết luận đáng tin cậy.",
}


def reason_code_vi(code: str) -> str:
    """Return the Vietnamese explanation for a canonical reason code.

    Unmapped codes fall back to the raw code so the UI never shows a blank cell.
    """
    return REASON_CODE_VI.get(code, code)