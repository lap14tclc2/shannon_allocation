"""Vietnamese Semantic Presentation Layer for QPort (Task 140, Task 145).

Separates machine calculation semantics from investor-facing Vietnamese explanations.

Retains raw mathematical precision, thresholds, operators, and evidence for audit/tests/debugging,
while providing natural Vietnamese financial narratives for investors.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


STATUS_VIETNAMESE: Dict[str, str] = {
    "PASS": "Đạt",
    "GOOD": "Tốt",
    "WATCH": "Cần theo dõi",
    "FAIL": "Không đạt",
    "UNKNOWN": "Chưa đủ dữ liệu",
    "NOT_APPLICABLE": "Không áp dụng",
    "MISSING": "Thiếu dữ liệu",
    "CLEAR": "Chưa phát hiện rủi ro đáng kể",
    "HIGH_RISK": "Rủi ro cao",
    "INFO": "Thông tin",
    "LOW": "Rủi ro thấp",
    "MEDIUM": "Rủi ro trung bình",
    "HIGH": "Rủi ro cao",
    "CRITICAL": "Rủi ro rất cao",
    "READY": "Sẵn sàng",
    "PARTIAL": "Khả thi một phần",
    "INSUFFICIENT": "Chưa đủ dữ liệu",
    "RESILIENT": "Khả năng chống chịu tốt",
    "VULNERABLE": "Dễ bị tổn thương",
    "EXTREME": "Cực đoan",
}


DECISION_VIETNAMESE: Dict[str, str] = {
    "BUY": "Có thể mua",
    "BUY_MORE": "Có thể mua thêm",
    "BUY_UNDER_MOS": "Đạt chuẩn mua tích sản",
    "CONDITIONAL_BUY": "Có thể mua có điều kiện / Cần theo dõi",
    "BUY_WATCH": "Có thể mua có điều kiện / Cần theo dõi",
    "WAIT_FOR_QUALITY_CONFIRMATION": "Chờ xác nhận chất lượng tài chính",
    "HOLD": "Tiếp tục nắm giữ",
    "HOLD_NO_NEW_CAPITAL": "Tiếp tục nắm giữ, chưa phân bổ thêm vốn",
    "WAIT_FOR_MOS": "Chờ biên an toàn",
    "BUILD_RESERVE_FIRST": "Ưu tiên củng cố quỹ dự phòng trước",
    "REVIEW_BUSINESS": "Cần xem xét thêm dữ liệu doanh nghiệp",
    "BUSINESS_REVIEW_INCOMPLETE": "Đánh giá doanh nghiệp chưa hoàn tất",
    "AVOID": "Chưa phù hợp để đầu tư",
    "DO_NOT_BUY": "Không mua",
    "SELL_REVIEW": "Cần xem xét lại luận điểm nắm giữ",
    "SELL": "Cân nhắc thoái vốn",
    "REDUCE": "Cân nhắc giảm tỷ trọng",
    "KEEP_CASH": "Ưu tiên giữ tiền mặt",
}


LIQUIDITY_VIETNAMESE: Dict[str, str] = {
    "LIQUIDITY_STRONG": "Thanh khoản tốt",
    "LIQUIDITY_ACCEPTABLE": "Thanh khoản đủ",
    "LIQUIDITY_WEAK": "Thanh khoản thấp",
    "LIQUIDITY_INSUFFICIENT_DATA": "Chưa đủ dữ liệu thanh khoản",
}


def get_vietnamese_liquidity(code: Optional[str]) -> str:
    if not code:
        return "Chưa đủ dữ liệu thanh khoản"
    clean = str(code).strip().upper()
    return LIQUIDITY_VIETNAMESE.get(clean, LIQUIDITY_VIETNAMESE.get(f"LIQUIDITY_{clean}", "Chưa đủ dữ liệu thanh khoản"))


COMPARISON_VIETNAMESE: Dict[str, str] = {
    "actual_mos >= required_mos": "Biên an toàn thực tế đạt yêu cầu tối thiểu",
    "actual_mos < required_mos": "Biên an toàn thực tế chưa đạt yêu cầu tối thiểu",
    "price < base_intrinsic_value": "Giá thị trường đang thấp hơn giá trị nội tại cơ sở",
    "price >= base_intrinsic_value": "Giá thị trường đang cao hơn hoặc bằng giá trị nội tại cơ sở",
    "receivables_growth > revenue_growth": "Khoản phải thu tăng nhanh hơn doanh thu",
    "receivables_growth <= revenue_growth": "Khoản phải thu tăng trưởng tương đương hoặc chậm hơn doanh thu",
    "inventory_growth > revenue_growth": "Hàng tồn kho tăng nhanh hơn doanh thu",
    "inventory_growth <= revenue_growth": "Hàng tồn kho tăng trưởng kiểm soát tốt so với doanh thu",
    "debt > cash": "Tổng nợ vay cao hơn lượng tiền mặt và tiền gửi hiện có",
    "debt <= cash": "Lượng tiền mặt duy trì cao hơn tổng nợ vay",
    "cfo < pat": "Dòng tiền kinh doanh nhỏ hơn lợi nhuận sau thuế",
    "cfo >= pat": "Lợi nhuận sau thuế có dòng tiền kinh doanh bảo chứng mạnh mẽ",
    "normalized_earnings_trend < 0": "Sức kiếm tiền bình thường hóa đang có dấu hiệu suy giảm",
    "normalized_earnings_trend >= 0": "Sức kiếm tiền bình thường hóa duy trì tăng trưởng ổn định",
}


SYSTEM_INVARIANTS_VIETNAMESE: Dict[str, Dict[str, str]] = {
    "NULL_NOT_ZERO": {
        "formula": "NULL != 0",
        "explanation": "Thiếu dữ liệu (NULL) khác với giá trị 0 thực tế.",
    },
    "UNKNOWN_NOT_PASS": {
        "formula": "UNKNOWN != PASS",
        "explanation": "Chưa đủ dữ liệu không thể mặc định coi là Đạt.",
    },
    "WATCH_NOT_FAIL": {
        "formula": "WATCH != FAIL",
        "explanation": "Chỉ tiêu thuộc diện cần theo dõi chưa mặc định là Không đạt.",
    },
    "NOT_APPLICABLE_NOT_UNKNOWN": {
        "formula": "NOT_APPLICABLE != UNKNOWN",
        "explanation": "Chỉ tiêu không áp dụng cho mô hình đặc thù khác với thiếu dữ liệu.",
    },
}



CLASSIFICATION_VIETNAMESE: Dict[str, str] = {
    "COMPOUNDER": "Doanh nghiệp tích lũy giá trị dài hạn",
    "POTENTIAL_COMPOUNDER": "Doanh nghiệp có tiềm năng tăng trưởng giá trị dài hạn",
    "AVERAGE_BUSINESS": "Doanh nghiệp có chất lượng trung bình",
    "CYCLICAL_QUALITY": "Doanh nghiệp chất lượng mang tính chu kỳ",
    "WEAK_BUSINESS": "Chất lượng doanh nghiệp còn yếu",
    "DETERIORATING_BUSINESS": "Nền tảng kinh doanh đang suy yếu",
    "INSUFFICIENT_DATA": "Chưa đủ dữ liệu để đánh giá",
}

Q7_CLASSIFICATION_VIETNAMESE: Dict[str, str] = {
    "POSSIBLE_VALUE_TRAP": "Có dấu hiệu bẫy giá trị",
    "CHEAP_BUT_DETERIORATING": "Giá rẻ nhưng chất lượng đang suy giảm",
    "VALUE_WITH_SAFETY": "Cơ hội giá trị có biên an toàn",
    "QUALITY_BUT_EXPENSIVE": "Doanh nghiệp tốt nhưng giá chưa đủ hấp dẫn",
    "INSUFFICIENT_EVIDENCE": "Chưa đủ bằng chứng để phân loại",
}

QUALITY_TIER_VIETNAMESE: Dict[str, str] = {
    "EXCEPTIONAL": "Xuất sắc",
    "HIGH_QUALITY": "Chất lượng cao",
    "INVESTABLE": "Đạt chuẩn đầu tư",
    "WATCH": "Cần theo dõi",
    "LOW_QUALITY": "Chất lượng thấp",
}

HARD_REJECT_REASON_VIETNAMESE: Dict[str, str] = {
    "CIRCLE_OF_COMPETENCE_FAIL": "Vượt quá năng lực hiểu biết",
    "DATA_INSUFFICIENT": "Chưa đủ dữ liệu lịch sử",
    "ACCOUNTING_UNRELIABLE": "Dữ liệu kế toán không tin cậy",
    "SOLVENCY_RISK": "Rủi ro khả năng thanh toán",
    "UNNORMALIZABLE_EARNINGS": "Lợi nhuận không thể bình thường hóa",
    "EXCESSIVE_DILUTION": "Pha loãng cổ phiếu quá mức",
}

VALUETRAP_VIETNAMESE: Dict[str, str] = {
    "CLEAR": "Chưa phát hiện dấu hiệu bẫy giá trị đáng kể",
    "WATCH": "Có dấu hiệu cần theo dõi",
    "HIGH_RISK": "Nguy cơ bẫy giá trị cao",
    "INSUFFICIENT_DATA": "Chưa đủ dữ liệu để đánh giá",
    "UNPROTECTED": "Kịch bản thận trọng chưa được bảo vệ",
}

DETERIORATION_VIETNAMESE: Dict[str, str] = {
    "NO_DETERIORATION": "Chưa phát hiện xu hướng suy giảm đáng kể",
    "LIKELY_CYCLICAL": "Suy giảm có khả năng mang tính chu kỳ",
    "POSSIBLY_CYCLICAL": "Có dấu hiệu suy giảm mang tính chu kỳ",
    "POSSIBLY_STRUCTURAL": "Có dấu hiệu suy giảm có thể mang tính cấu trúc",
    "STRUCTURAL": "Đã phát hiện suy giảm mang tính cấu trúc",
    "UNKNOWN": "Chưa đủ dữ liệu để xác định",
    "NEUTRAL": "Trung tính",
}

ARCHETYPE_VIETNAMESE: Dict[str, str] = {
    "NORMAL_ENTERPRISE": "Doanh nghiệp sản xuất / thương mại thông thường",
    "BANK": "Ngân hàng thương mại",
    "SECURITIES": "Công ty chứng khoán",
    "REAL_ESTATE": "Bất động sản",
    "INSURANCE": "Bảo hiểm",
    "HOLDING": "Công ty quản lý / đầu tư vốn",
    "CYCLICAL": "Doanh nghiệp mang tính chu kỳ",
}

MARGIN_TREND_VIETNAMESE: Dict[str, str] = {
    "EXPANDING": "Đang mở rộng",
    "STABLE": "Ổn định",
    "DECLINING": "Đang thu hẹp",
    "NOT_APPLICABLE": "Không áp dụng",
}

METRIC_NAMES_VIETNAMESE: Dict[str, str] = {
    "revenue_growth": "Tăng trưởng doanh thu",
    "revenue_cagr": "Tăng trưởng doanh thu thuần",
    "net_profit_cagr": "Tăng trưởng lợi nhuận sau thuế",
    "median_roe": "ROE trung vị",
    "margin_trend": "Xu hướng biên lợi nhuận",
    "pat_volatility": "Mức ổn định của lợi nhuận",
    "profit_volatility": "Mức ổn định của lợi nhuận",
    "avg_cfo_pat": "Khả năng chuyển lợi nhuận thành dòng tiền",
    "latest_debt_equity": "Mức nợ so với vốn chủ sở hữu",
    "debt_equity_ratio": "Mức nợ so với vốn chủ sở hữu",
    "annual_share_growth": "Tăng trưởng số lượng cổ phiếu",
    "share_cagr": "Tăng trưởng số lượng cổ phiếu",
    "dilution": "Mức pha loãng cổ phiếu",
    "accounting_consistency": "Tính nhất quán của báo cáo tài chính",
    "forensics": "Kiểm tra dấu hiệu bất thường",
}


FINDING_TITLES: Dict[str, str] = {
    "RECEIVABLES_GROW_FASTER_THAN_REVENUE": "Khoản phải thu tăng nhanh hơn doanh thu",
    "PROFIT_CASH_DIVERGENCE": "Lợi nhuận tăng nhưng dòng tiền không theo kịp",
    "WEAK_CASH_CONVERSION": "Dòng tiền kinh doanh chưa tương ứng với lợi nhuận",
    "INVENTORY_BUILDUP": "Hàng tồn kho gia tăng bất thường",
    "INVENTORY_GROWTH_EXCEEDS_SALES": "Hàng tồn kho tăng nhanh hơn doanh thu",
    "INVENTORY_GROW_FASTER_THAN_REVENUE": "Hàng tồn kho tăng nhanh hơn doanh thu",
    "DEBT_FUNDED_LOW_QUALITY_GROWTH": "Tăng trưởng phụ thuộc nhiều vào nợ vay",
    "EXCESSIVE_DEBT_LEVERAGE": "Đòn bẩy tài chính ở mức cao",
    "UNSTABLE_EARNINGS_HISTORY": "Biến động lợi nhuận bất ổn qua các năm",
    "WEAK_PROFITABILITY_ROE": "Tỷ suất sinh lời trên vốn chủ sở hữu (ROE) khiêm tốn",
    "PER_SHARE_VALUE_DILUTION": "Lợi nhuận trên mỗi cổ phiếu (EPS) bị pha loãng",
    "ACCOUNTING_IDENTITY_DISCREPANCY": "Lệch dữ liệu phương trình kế toán",
    "WEAK_BANK_ROE": "ROE ngân hàng ở mức thấp so với tiêu chuẩn",
    "LOW_BANK_CAPITAL_ADEQUACY": "Tỷ lệ an toàn vốn chủ sở hữu ngân hàng mỏng",
    "WEAK_SECURITIES_ROE": "ROE công ty chứng khoán ở mức thấp",
    "TRADING_INCOME_DEPENDENCE": "Phụ thuộc lớn vào hoạt động tự doanh / FVTPL",
    "SECURITIES_HIGH_LEVERAGE": "Đòn bẩy công ty chứng khoán ở mức cao",
}


FINDING_NARRATIVE_TEMPLATES: Dict[str, Dict[str, str]] = {
    "RECEIVABLES_GROW_FASTER_THAN_REVENUE": {
        "title": "Khoản phải thu tăng nhanh hơn doanh thu",
        "what_is_happening": "Khoản phải thu từ khách hàng đang tăng nhanh hơn doanh thu.",
        "why_it_matters": "Một phần doanh thu ghi nhận chưa chuyển hóa tương ứng thành tiền mặt thực tế từ khách hàng.",
        "long_term_impact": "Có thể làm gia tăng thời gian thu tiền (DSO), gây chôn vốn lưu động hoặc đọng vốn kém hiệu quả.",
    },
    "PROFIT_CASH_DIVERGENCE": {
        "title": "Lợi nhuận tăng nhưng dòng tiền không theo kịp",
        "what_is_happening": "Dòng tiền từ hoạt động kinh doanh (CFO) không tăng tương ứng với đà tăng lợi nhuận sau thuế.",
        "why_it_matters": "Lợi nhuận báo cáo tăng nhưng tiền mặt đọng ở tài sản lưu động hoặc phải thu.",
        "long_term_impact": "Nguy cơ trích lập dự phòng hoặc suy giảm chất lượng lợi nhuận trong tương lai.",
    },
    "INVENTORY_BUILDUP": {
        "title": "Hàng tồn kho gia tăng bất thường",
        "what_is_happening": "Tồn kho tích lũy tăng cao so với quy mô kinh doanh.",
        "why_it_matters": "Gây chôn vốn và gia tăng chi phí quản lý hàng tồn kho.",
        "long_term_impact": "Rủi ro giảm giá trị tồn kho khi nhu cầu thị trường chậm lại.",
    },
    "INVENTORY_GROWTH_EXCEEDS_SALES": {
        "title": "Hàng tồn kho tăng nhanh hơn doanh thu",
        "what_is_happening": "Tốc độ tăng trưởng hàng tồn kho vượt tốc độ tăng doanh thu.",
        "why_it_matters": "Tồn kho ứ đọng làm chôn vốn lưu động và tăng chi phí lưu kho, bảo quản.",
        "long_term_impact": "Nguy cơ giảm giá trị hàng tồn kho và phải trích lập giảm giá tồn kho khi thị trường biến động.",
    },
    "INVENTORY_GROW_FASTER_THAN_REVENUE": {
        "title": "Hàng tồn kho tăng nhanh hơn doanh thu",
        "what_is_happening": "Tốc độ tăng trưởng hàng tồn kho vượt tốc độ tăng doanh thu.",
        "why_it_matters": "Tồn kho ứ đọng làm chôn vốn lưu động và tăng chi phí lưu kho, bảo quản.",
        "long_term_impact": "Nguy cơ giảm giá trị hàng tồn kho và phải trích lập giảm giá tồn kho khi thị trường biến động.",
    },
    "WEAK_CASH_CONVERSION": {
        "title": "Dòng tiền kinh doanh chưa tương ứng với lợi nhuận",
        "what_is_happening": "Dòng tiền từ hoạt động kinh doanh (CFO) duy trì ở mức thấp hơn lợi nhuận sau thuế (PAT) kéo dài.",
        "why_it_matters": "Lợi nhuận báo cáo chưa đi kèm với dòng tiền mặt thu về thực tế.",
        "long_term_impact": "Chất lượng lợi nhuận kém, buộc doanh nghiệp phải dùng nợ vay để duy trì hoạt động.",
    },
    "DEBT_FUNDED_LOW_QUALITY_GROWTH": {
        "title": "Tăng trưởng phụ thuộc nhiều vào nợ vay",
        "what_is_happening": "Nợ vay tăng nhanh để tài trợ tài sản nhưng không đem lại hiệu quả lợi nhuận tương ứng.",
        "why_it_matters": "Hiệu suất sinh lời trên tài sản (ROIC) bị bào mòn bởi chi phí lãi vay.",
        "long_term_impact": "Doanh nghiệp dễ gặp áp lực thanh khoản khi chu kỳ kinh doanh suy thoái.",
    },
    "EXCESSIVE_DEBT_LEVERAGE": {
        "title": "Đòn bẩy tài chính ở mức cao",
        "what_is_happening": "Tỷ lệ tổng nợ vay trên vốn chủ sở hữu vượt ngưỡng an toàn.",
        "why_it_matters": "Áp lực trả gốc và lãi vay làm tăng rủi ro tài chính cho cổ đông.",
        "long_term_impact": "Thu hẹp dư địa mở rộng kinh doanh và làm tăng yêu cầu Biên an toàn (MOS).",
    },
    "UNSTABLE_EARNINGS_HISTORY": {
        "title": "Biến động lợi nhuận bất ổn qua các năm",
        "what_is_happening": "Lợi nhuận sau thuế trồi sụt mạnh hoặc trập trùng theo chu kỳ ngắn.",
        "why_it_matters": "Khó dự phóng sức kiếm tiền bền vững và dòng tiền chủ sở hữu (Owner Earnings).",
        "long_term_impact": "Cần áp dụng mức chiết khấu định giá lớn hơn và thận trọng với giả định tăng trưởng.",
    },
    "WEAK_PROFITABILITY_ROE": {
        "title": "Tỷ suất sinh lời trên vốn chủ sở hữu (ROE) khiêm tốn",
        "what_is_happening": "Tỷ suất ROE trung bình nhiều năm thấp hơn mức kỳ vọng tối thiểu.",
        "why_it_matters": "Vốn giữ lại tái đầu tư tạo ra giá trị gia tăng thấp cho cổ đông.",
        "long_term_impact": "Không đạt tiêu chuẩn doanh nghiệp tăng trưởng hợp nhất (Compounder).",
    },
    "PER_SHARE_VALUE_DILUTION": {
        "title": "Lợi nhuận trên mỗi cổ phiếu (EPS) bị pha loãng",
        "what_is_happening": "Tốc độ tăng tổng lợi nhuận chậm hơn tốc độ tăng số lượng cổ phiếu phát hành.",
        "why_it_matters": "Việc phát hành thêm cổ phiếu làm suy giảm lợi ích kinh tế của cổ đông hiện hữu.",
        "long_term_impact": "Tăng trưởng tổng tài sản không đồng nghĩa với gia tăng giá trị cho từng cổ phiếu.",
    },
    "ACCOUNTING_IDENTITY_DISCREPANCY": {
        "title": "Lệch dữ liệu phương trình kế toán",
        "what_is_happening": "Phát hiện chênh lệch giữa Tổng tài sản và Tổng Nợ + Vốn chủ sở hữu trên BCTC.",
        "why_it_matters": "Dữ liệu kế toán thô cần được kiểm tra đối soát nguồn trước khi sử dụng.",
        "long_term_impact": "Yêu cầu rà soát mapping dữ liệu SSI để đảm bảo tính chính xác.",
    },
    "WEAK_BANK_ROE": {
        "title": "ROE ngân hàng ở mức thấp so với tiêu chuẩn",
        "what_is_happening": "Tỷ suất lợi nhuận trên vốn chủ sở hữu (ROE) của ngân hàng chưa đạt ngưỡng khuyến nghị.",
        "why_it_matters": "Khả năng tự tích lũy vốn rủi ro của ngân hàng bị hạn chế.",
        "long_term_impact": "Ngân hàng có thể phải phát hành thêm cổ phiếu để đáp ứng chuẩn an toàn vốn Basel.",
    },
    "LOW_BANK_CAPITAL_ADEQUACY": {
        "title": "Tỷ lệ an toàn vốn chủ sở hữu ngân hàng mỏng",
        "what_is_happening": "Tỷ lệ Vốn chủ sở hữu / Tổng tài sản ở mức thấp so với trung bình ngành.",
        "why_it_matters": "Đòn bẩy tài sản cao làm giảm đệm chống đỡ khi nợ xấu gia tăng.",
        "long_term_impact": "Cần thận trọng đánh giá tỷ lệ nợ xấu nhóm 3–5 và trích lập dự phòng rủi ro tín dụng.",
    },
    "WEAK_SECURITIES_ROE": {
        "title": "ROE công ty chứng khoán ở mức thấp",
        "what_is_happening": "Hiệu quả sử dụng vốn của công ty chứng khoán chưa tối ưu.",
        "why_it_matters": "Nguồn vốn cho vay cho vay ký quỹ (margin) hoặc tự doanh đạt lợi suất thấp.",
        "long_term_impact": "Cạnh tranh hạ phí môi giới (zero-fee) bào mòn biên lợi nhuận.",
    },
    "TRADING_INCOME_DEPENDENCE": {
        "title": "Phụ thuộc lớn vào hoạt động tự doanh / FVTPL",
        "what_is_happening": "Lợi nhuận ròng biến động phụ thuộc phần lớn vào danh mục tài sản tự doanh (FVTPL).",
        "why_it_matters": "Lợi nhuận không đến từ phí dịch vụ môi giới cố định mà biến động theo thị trường.",
        "long_term_impact": "Độ bền lợi nhuận kém ổn định, biến động mạnh khi thị trường chứng khoán điều chỉnh.",
    },
    "SECURITIES_HIGH_LEVERAGE": {
        "title": "Đòn bẩy công ty chứng khoán ở mức cao",
        "what_is_happening": "Tỷ lệ nợ vay / vốn chủ sở hữu của công ty chứng khoán tăng nhanh.",
        "why_it_matters": "Nguồn vốn vay ngân hàng để tài trợ margin hoặc tự doanh tạo chi phí tài chính.",
        "long_term_impact": "Nguy cơ rủi ro thanh khoản khi thanh khoản thị trường sụt giảm.",
    },
}


def get_vietnamese_finding_title(code: str) -> str:
    """Return investor-facing Vietnamese title for a finding code."""
    if not code:
        return "Chưa xác định"
    c_upper = str(code).upper().strip()
    if c_upper in FINDING_TITLES:
        return FINDING_TITLES[c_upper]
    # Safe fallback formatting
    return c_upper.lower().replace("_", " ").title()


def get_vietnamese_q7_classification(code: str) -> str:
    """Return investor-facing Vietnamese translation for Q7 opportunity classification."""
    if not code:
        return "Chưa xác định"
    c_upper = str(code).upper().strip()
    return Q7_CLASSIFICATION_VIETNAMESE.get(c_upper, c_upper.lower().replace("_", " "))


def get_vietnamese_quality_tier(code: str) -> str:
    """Return investor-facing Vietnamese translation for Business Quality Tier."""
    if not code:
        return "Chưa xác định"
    c_upper = str(code).upper().strip()
    return QUALITY_TIER_VIETNAMESE.get(c_upper, c_upper.lower().replace("_", " "))


def get_vietnamese_hard_reject_reason(code: str) -> str:
    """Return investor-facing Vietnamese translation for Hard Reject Reason."""
    if not code:
        return "Chưa xác định"
    c_upper = str(code).upper().strip()
    return HARD_REJECT_REASON_VIETNAMESE.get(c_upper, c_upper.lower().replace("_", " "))


def get_vietnamese_classification(code: str) -> str:
    """Return investor-facing Vietnamese translation for compounder classification."""
    if not code:
        return "Chưa xác định"
    c_upper = str(code).upper().strip()
    return CLASSIFICATION_VIETNAMESE.get(c_upper, c_upper.lower().replace("_", " "))


def get_vietnamese_valuetrap(code: str) -> str:
    """Return investor-facing Vietnamese translation for ValueTrap assessment status."""
    if not code:
        return "Chưa xác định"
    c_upper = str(code).upper().strip()
    return VALUETRAP_VIETNAMESE.get(c_upper, c_upper.lower().replace("_", " "))


def get_vietnamese_deterioration(code: str) -> str:
    """Return investor-facing Vietnamese translation for deterioration classification."""
    if not code:
        return "Chưa xác định"
    c_upper = str(code).upper().strip()
    return DETERIORATION_VIETNAMESE.get(c_upper, c_upper.lower().replace("_", " "))


def get_vietnamese_archetype(code: str) -> str:
    """Return investor-facing Vietnamese translation for economic archetype."""
    if not code:
        return "Chưa xác định"
    c_upper = str(code).upper().strip()
    return ARCHETYPE_VIETNAMESE.get(c_upper, c_upper.lower().replace("_", " "))


def get_vietnamese_status(status_code: str) -> str:
    """Return investor-facing Vietnamese translation for internal status code."""
    if not status_code:
        return "Chưa xác định"
    s_upper = str(status_code).upper().strip()
    return STATUS_VIETNAMESE.get(s_upper, s_upper.lower().replace("_", " "))


def get_vietnamese_decision(decision_code: str) -> str:
    """Return investor-facing Vietnamese translation for internal decision code."""
    if not decision_code:
        return "Chưa xác định"
    d_upper = str(decision_code).upper().strip()
    return DECISION_VIETNAMESE.get(d_upper, d_upper.lower().replace("_", " "))


def get_vietnamese_comparison(comparison_expr: str) -> str:
    """Return investor-facing Vietnamese translation for mathematical comparison expression."""
    if not comparison_expr:
        return ""
    norm = str(comparison_expr).strip()
    if norm in COMPARISON_VIETNAMESE:
        return COMPARISON_VIETNAMESE[norm]
    # Fallback readable conversion
    return (
        norm.replace(">=", " đạt hoặc vượt ")
        .replace("<=", " nhỏ hơn hoặc bằng ")
        .replace(">", " lớn hơn ")
        .replace("<", " nhỏ hơn ")
        .replace("==", " bằng ")
        .replace("!=", " khác ")
        .replace("_", " ")
    )


def format_metric_presentation(
    val: Any,
    metric_code: str,
    archetype: str = "NORMAL_ENTERPRISE",
) -> Dict[str, Any]:
    """Format metric value into a structured diagnostic object with value, status, reason, and formatted_vi."""
    import math

    m_code = str(metric_code).lower().strip()
    arch = str(archetype).upper().strip()

    if m_code in ("latest_debt_equity", "debt_equity_ratio"):
        if arch == "BANK":
            return {
                "value": None,
                "status": "NOT_APPLICABLE",
                "reason": "BANK_DEBT_NOT_APPLICABLE",
                "formatted_vi": "Không áp dụng cho ngân hàng thương mại",
            }
        elif arch == "SECURITIES":
            if val is not None and isinstance(val, (int, float)) and not math.isnan(val):
                return {
                    "value": float(val),
                    "status": "VALUE",
                    "reason": "CALCULATED_FROM_FINANCIALS",
                    "formatted_vi": f"{float(val):.2f}x (Nợ / Vốn chủ)",
                }
            return {
                "value": None,
                "status": "NOT_APPLICABLE",
                "reason": "SECURITIES_LEVERAGE_NOT_STANDARD",
                "formatted_vi": "Thương lượng đòn bẩy tự doanh / Margin",
            }
        else:
            if val is not None and isinstance(val, (int, float)) and not math.isnan(val):
                return {
                    "value": float(val),
                    "status": "VALUE",
                    "reason": "CALCULATED_FROM_FINANCIALS",
                    "formatted_vi": f"{float(val):.2f}x",
                }
            return {
                "value": None,
                "status": "INSUFFICIENT_DATA",
                "reason": "DEBT_OR_EQUITY_MISSING",
                "formatted_vi": "Chưa đủ dữ liệu nợ và vốn chủ sở hữu",
            }

    if "cagr" in m_code or "growth" in m_code or "roe" in m_code or "roic" in m_code or "margin" in m_code:
        if val is not None and isinstance(val, (int, float)) and not math.isnan(val):
            f_val = float(val)
            sign = "+" if f_val > 0 else ""
            formatted = f"{sign}{f_val * 100:.1f}%" if abs(f_val) <= 5.0 else f"{sign}{f_val:.1f}%"
            return {
                "value": f_val,
                "status": "VALUE",
                "reason": "CALCULATED_FROM_SERIES",
                "formatted_vi": formatted,
            }
        return {
            "value": None,
            "status": "INSUFFICIENT_DATA",
            "reason": "HISTORICAL_SERIES_TOO_SHORT",
            "formatted_vi": "Chưa đủ dữ liệu lịch sử",
        }

    if "cfo_pat" in m_code:
        if val is not None and isinstance(val, (int, float)) and not math.isnan(val):
            return {
                "value": float(val),
                "status": "VALUE",
                "reason": "CALCULATED_FROM_CFO_AND_PAT",
                "formatted_vi": f"{float(val):.2f}x",
            }
        return {
            "value": None,
            "status": "INSUFFICIENT_DATA",
            "reason": "CFO_OR_PAT_MISSING",
            "formatted_vi": "Chưa đủ dữ liệu dòng tiền hoạt động",
        }

    if "volatility" in m_code:
        if val is not None and isinstance(val, (int, float)) and not math.isnan(val):
            return {
                "value": float(val),
                "status": "VALUE",
                "reason": "CALCULATED_SD_OVER_MEAN",
                "formatted_vi": f"{float(val) * 100:.1f}%",
            }
        return {
            "value": None,
            "status": "INSUFFICIENT_DATA",
            "reason": "PAT_SERIES_LESS_THAN_3_YEARS",
            "formatted_vi": "Chưa đủ dữ liệu chuỗi lợi nhuận",
        }

    if val is not None:
        return {
            "value": val,
            "status": "VALUE",
            "reason": "EXPLICIT_VALUE",
            "formatted_vi": str(val),
        }

    return {
        "value": None,
        "status": "INSUFFICIENT_DATA",
        "reason": "DATA_MISSING",
        "formatted_vi": "Chưa đủ dữ liệu",
    }


def generate_vietnamese_finding_narrative(
    code: str,
    status: str = "WATCH",
    metrics: Optional[Dict[str, Any]] = None,
    period: str = "",
    archetype: str = "NORMAL_ENTERPRISE",
) -> Dict[str, str]:
    """Generate 6-part investor Vietnamese narrative for a financial finding."""
    metrics = metrics or {}
    tmpl = FINDING_NARRATIVE_TEMPLATES.get(code, {})

    title = tmpl.get("title", get_vietnamese_finding_title(code))
    what_happening = tmpl.get(
        "what_is_happening", f"Phát hiện chỉ tiêu {title} thuộc diện đánh giá tài chính."
    )
    why_matters = tmpl.get(
        "why_it_matters", "Chỉ tiêu này ảnh hưởng trực tiếp đến chất lượng tài sản và dòng tiền."
    )
    long_impact = tmpl.get(
        "long_term_impact", "Cần xem xét kĩ trong mô hình định giá và xác định Biên an toàn (MOS)."
    )

    duration = period if period else "Theo dõi lịch sử tài chính nhiều năm (FY)"
    severity_desc = get_vietnamese_status(status)

    # Format evidence summary from metrics
    evidence_parts = []
    for k, v in metrics.items():
        if isinstance(v, float):
            if "cagr" in k.lower() or "ratio" in k.lower() or "pct" in k.lower() or "roe" in k.lower():
                evidence_parts.append(f"{k.replace('_', ' ').title()}: {v * 100:.1f}%" if abs(v) <= 5.0 else f"{k.replace('_', ' ').title()}: {v:.1f}%")
            else:
                evidence_parts.append(f"{k.replace('_', ' ').title()}: {v:,.0f}")
        elif v is not None:
            evidence_parts.append(f"{k.replace('_', ' ').title()}: {v}")

    evidence_summary = ", ".join(evidence_parts) if evidence_parts else "Dữ liệu BCTC chuẩn hóa SSI"

    return {
        "tieu_de": title,
        "dieu_gi_dang_xay_ra": what_happening,
        "xu_huong_keo_dai": duration,
        "vi_sao_quan_trong": why_matters,
        "muc_do_nghiem_trong": severity_desc,
        "du_lieu_chung_minh": evidence_summary,
        "anh_huong_dai_han": long_impact,
    }


def enrich_finding_dict(finding_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich a finding dictionary with structured Vietnamese presentation fields."""
    code = finding_dict.get("code", "")
    status = finding_dict.get("status", "WATCH")
    metrics = finding_dict.get("metrics", {})
    start_p = finding_dict.get("start_period")
    end_p = finding_dict.get("end_period")

    period_str = ""
    if start_p and end_p:
        period_str = f"Giai đoạn FY{start_p}–FY{end_p}"
    elif end_p:
        period_str = f"Năm FY{end_p}"

    narrative = generate_vietnamese_finding_narrative(
        code=code,
        status=status,
        metrics=metrics,
        period=period_str,
        archetype=finding_dict.get("archetype", "NORMAL_ENTERPRISE"),
    )

    result = dict(finding_dict)
    result["status_vietnamese"] = get_vietnamese_status(status)
    result["vietnamese_explanation"] = narrative
    return result
