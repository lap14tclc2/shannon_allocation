"""Vietnamese Semantic Presentation Layer for QPort (Task 140).

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
    "CLEAR": "Chưa phát hiện rủi ro đáng kể",
    "HIGH_RISK": "Rủi ro cao",
    "INFO": "Thông tin",
    "LOW": "Rủi ro thấp",
    "MEDIUM": "Rủi ro trung bình",
    "HIGH": "Rủi ro cao",
    "CRITICAL": "Rủi ro rất cao",
}


DECISION_VIETNAMESE: Dict[str, str] = {
    "BUY": "Có thể mua",
    "BUY_MORE": "Có thể mua thêm",
    "HOLD": "Tiếp tục nắm giữ",
    "HOLD_NO_NEW_CAPITAL": "Tiếp tục nắm giữ, chưa phân bổ thêm vốn",
    "WAIT_FOR_MOS": "Chờ mức giá có biên an toàn tốt hơn",
    "BUILD_RESERVE_FIRST": "Ưu tiên củng cố quỹ dự phòng trước",
    "REVIEW_BUSINESS": "Cần xem xét thêm dữ liệu doanh nghiệp",
    "AVOID": "Chưa phù hợp để đầu tư",
    "SELL_REVIEW": "Cần xem xét lại luận điểm nắm giữ",
    "SELL": "Cân nhắc thoái vốn",
}


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
        "title": "Bất biến dữ liệu thiếu",
        "explanation": "Thiếu dữ liệu tài chính không được tự ý quy đổi thành giá trị bằng không.",
    },
    "UNKNOWN_NOT_PASS": {
        "formula": "UNKNOWN != PASS",
        "title": "Bất biến nghi vấn chưa rõ",
        "explanation": "Chưa đủ dữ liệu kiểm chứng không đồng nghĩa với doanh nghiệp đạt tiêu chuẩn.",
    },
    "WATCH_NOT_FAIL": {
        "formula": "WATCH != FAIL",
        "title": "Bất biến cảnh báo theo dõi",
        "explanation": "Tín hiệu cần theo dõi không tự động coi là vi phạm nghiêm trọng để loại bỏ cổ phiếu.",
    },
    "NOT_APPLICABLE_NOT_UNKNOWN": {
        "formula": "NOT_APPLICABLE != UNKNOWN",
        "title": "Bất biến tính đặc thù mô hình",
        "explanation": "Chỉ tiêu không áp dụng cho đặc thù ngành (như Ngân hàng/Chứng khoán) khác hoàn toàn với việc thiếu dữ liệu.",
    },
}


FINDING_NARRATIVE_TEMPLATES: Dict[str, Dict[str, str]] = {
    "RECEIVABLES_GROW_FASTER_THAN_REVENUE": {
        "title": "Khoản phải thu tăng nhanh hơn doanh thu",
        "what_is_happening": "Tốc độ tăng trưởng khoản phải thu lớn hơn tốc độ tăng trưởng doanh thu thuần.",
        "why_it_matters": "Một phần doanh thu ghi nhận chưa chuyển hóa tương ứng thành tiền mặt thực tế từ khách hàng.",
        "long_term_impact": "Có thể làm tăng nguy cơ nợ xấu, nợ khó đòi hoặc phải trích lập dự phòng trong tương lai.",
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
}


def get_vietnamese_status(status_code: str) -> str:
    """Return investor-facing Vietnamese translation for internal status code."""
    if not status_code:
        return "Chưa xác định"
    return STATUS_VIETNAMESE.get(str(status_code).upper(), str(status_code))


def get_vietnamese_decision(decision_code: str) -> str:
    """Return investor-facing Vietnamese translation for internal decision code."""
    if not decision_code:
        return "Chưa xác định"
    return DECISION_VIETNAMESE.get(str(decision_code).upper(), str(decision_code))


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

    title = tmpl.get("title", code.replace("_", " ").title())
    what_happening = tmpl.get(
        "what_is_happening", f"Phát hiện chỉ tiêu {code} thuộc diện đánh giá tài chính."
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
