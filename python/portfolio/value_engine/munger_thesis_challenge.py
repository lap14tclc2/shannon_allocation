"""Automated Munger Investment Thesis Challenge Engine (Task 141).

Provides deterministic evidence-first thesis challenge across 8 core investment questions.
Actively searches for evidence that could invalidate QPort's investment conclusion
instead of only presenting supporting evidence.

Rules depend on financial facts, history, archetype, valuation, and evidence — NOT ticker identity.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .vietnamese_presenter import (
    MARGIN_TREND_VIETNAMESE,
    get_vietnamese_archetype,
    get_vietnamese_decision,
    get_vietnamese_finding_title,
    get_vietnamese_q7_classification,
    get_vietnamese_status,
    get_vietnamese_valuetrap,
)


class ThesisChallengeAnswerStatus(str):
    RESILIENT = "RESILIENT"
    WATCH = "WATCH"
    VULNERABLE = "VULNERABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    NOT_APPLICABLE = "NOT_APPLICABLE"


STATUS_VIETNAMESE_MAP = {
    "RESILIENT": "Có khả năng chống chịu",
    "WATCH": "Cần theo dõi",
    "VULNERABLE": "Dễ tổn thương",
    "INSUFFICIENT_DATA": "Chưa đủ dữ liệu",
    "NOT_APPLICABLE": "Không áp dụng",
}


@dataclass
class ThesisChallengeQuestion:
    question_id: str
    question_number: int
    title_vi: str
    answer_status: str  # RESILIENT, WATCH, VULNERABLE, INSUFFICIENT_DATA, NOT_APPLICABLE
    answer_status_vi: str
    summary_vi: str
    detail_vi: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    evidence_fact_ids: List[str] = field(default_factory=list)
    limitations: str = ""
    confidence: str = "HIGH"
    conclusion_vi: str = ""
    evidence_vi: str = ""
    risk_vi: str = ""
    severity_vi: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InvestmentThesisChallenge:
    symbol: str
    archetype: str
    analysis_date: str
    status: str  # CLEAR, WATCH, HIGH_RISK, INSUFFICIENT_DATA
    confidence: str
    thesis_summary: str
    primary_risks: List[str] = field(default_factory=list)
    questions: List[ThesisChallengeQuestion] = field(default_factory=list)
    stress_tests: Dict[str, Any] = field(default_factory=dict)
    invalidation_criteria: List[Dict[str, Any]] = field(default_factory=list)
    decision_contradiction: bool = False
    contradiction_details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["questions"] = [q.to_dict() if hasattr(q, "to_dict") else q for q in self.questions]
        return d


def run_thesis_challenge_analysis(
    munger_analysis: Dict[str, Any],
    valuation_data: Optional[Dict[str, Any]] = None,
    personal_balance_sheet: Optional[Dict[str, Any]] = None,
) -> InvestmentThesisChallenge:
    """Run deterministic 8-question thesis challenge against Munger financial analysis."""
    symbol = munger_analysis.get("symbol", "UNKNOWN")
    archetype = munger_analysis.get("archetype", "NORMAL_ENTERPRISE")
    readiness = munger_analysis.get("data_readiness", "READY")
    all_findings = munger_analysis.get("all_findings", [])
    hard_failures = munger_analysis.get("hard_financial_failures", [])
    warnings = munger_analysis.get("financial_warnings", [])
    value_trap = munger_analysis.get("value_trap_assessment", {})
    norm_power = munger_analysis.get("normalized_earning_power", {})
    quality = munger_analysis.get("overall_financial_quality", {})
    decision = munger_analysis.get("long_term_decision", {})
    val = valuation_data or munger_analysis.get("valuation", {})

    core_decision_state = decision.get("state", "WAIT_FOR_MOS")
    base_iv = val.get("base_iv")
    current_price = val.get("current_price")
    actual_mos = val.get("actual_mos_pct")
    required_mos = val.get("required_mos_pct") or 25.0

    questions: List[ThesisChallengeQuestion] = []
    primary_risks: List[str] = []

    # -------------------------------------------------------------------------
    # Q1: Tại sao luận điểm đầu tư này có thể sai?
    # -------------------------------------------------------------------------
    q1_risks = []
    if hard_failures:
        q1_risks.extend([f"Thất bại nghiêm trọng BCTC: {get_vietnamese_finding_title(f)}" for f in hard_failures])
    if value_trap.get("status") == "HIGH_RISK":
        q1_risks.append("Bẫy giá trị nguy cơ cao do suy giảm cấu trúc")

    for f in all_findings:
        if isinstance(f, dict) and f.get("severity") in ("HIGH", "CRITICAL"):
            code = f.get("code", "")
            if code not in q1_risks:
                q1_risks.append(f.get("vietnamese_explanation", {}).get("tieu_de") or code)

    if q1_risks:
        primary_risks.extend(q1_risks[:3])
        q1_status = ThesisChallengeAnswerStatus.VULNERABLE if hard_failures or value_trap.get("status") == "HIGH_RISK" else ThesisChallengeAnswerStatus.WATCH
        q1_summary = f"Rủi ro chính của luận điểm hiện tại nằm ở: {'; '.join(q1_risks[:2])}."
        q1_detail = (
            "Hệ thống đã phân tích toàn bộ 12 chiều BCTC và phát hiện các yếu tố rủi ro tiềm ẩn trên. "
            "Nhà đầu tư cần theo dõi sát các chỉ tiêu này trước khi đưa ra quyết định phân bổ vốn."
        )
    elif warnings:
        q1_status = ThesisChallengeAnswerStatus.WATCH
        q1_summary = "Luận điểm duy trì ổn định, tuy nhiên phát hiện một số cảnh báo cấp độ theo dõi nhẹ (Warnings)."
        q1_detail = f"Các cảnh báo lưu ý: {', '.join(get_vietnamese_finding_title(w) for w in warnings[:3])}."
    else:
        q1_status = ThesisChallengeAnswerStatus.RESILIENT
        q1_summary = "Không phát hiện rủi ro tài chính nghiêm trọng nào đe dọa luận điểm đầu tư cơ sở."
        q1_detail = "Doanh nghiệp đạt tiêu chuẩn trên các chiều phân tích BCTC chính."

    questions.append(
        ThesisChallengeQuestion(
            question_id="Q1_WHY_THESIS_COULD_BE_WRONG",
            question_number=1,
            title_vi="Tại sao luận điểm đầu tư này có thể sai?",
            answer_status=q1_status,
            answer_status_vi=STATUS_VIETNAMESE_MAP[q1_status],
            summary_vi=q1_summary,
            detail_vi=q1_detail,
            metrics={"hard_failures_count": len(hard_failures), "warnings_count": len(warnings)},
            limitations="Phân tích rủi ro dựa trên dữ liệu BCTC lịch sử; không dự đoán biến động kinh tế vĩ mô bất ngờ.",
            conclusion_vi=q1_summary,
            evidence_vi=f"BCTC phát hiện {len(hard_failures)} thất bại nghiêm trọng và {len(warnings)} cảnh báo. Danh sách rủi ro: {', '.join(q1_risks)}" if q1_risks else "BCTC đạt tiêu chuẩn trên các chiều phân tích chính.",
            risk_vi=", ".join(q1_risks[:3]) if q1_risks else "Rủi ro biến động chung của thị trường.",
            severity_vi=STATUS_VIETNAMESE_MAP.get(q1_status, q1_status),
        )
    )

    # -------------------------------------------------------------------------
    # Q2: Điều gì có thể làm suy yếu lợi thế kinh tế?
    # -------------------------------------------------------------------------
    prof_analysis = munger_analysis.get("profitability_analysis", {})
    prof_metrics = prof_analysis.get("metrics", {}) if isinstance(prof_analysis, dict) else {}
    med_roe = prof_metrics.get("median_roe")
    margin_trend = prof_metrics.get("margin_trend")

    if med_roe is not None and med_roe >= 0.15 and margin_trend != "DETERIORATING":
        q2_status = ThesisChallengeAnswerStatus.RESILIENT
        q2_summary = f"ROIC/ROE trung vị duy trì mức cao ({(med_roe*100):.1f}%), chưa có dấu hiệu suy yếu lợi thế kinh tế."
        q2_detail = "Xu hướng biên lợi nhuận và hiệu quả sử dụng vốn cho thấy năng lực cạnh tranh duy trì tốt."
    elif margin_trend == "DETERIORATING" or (med_roe is not None and med_roe < 0.10):
        q2_status = ThesisChallengeAnswerStatus.VULNERABLE
        q2_summary = "Biên lợi nhuận hoặc ROE đang suy giảm kéo dài, là bằng chứng định lượng cho thấy lợi thế kinh tế có thể đang yếu đi."
        q2_detail = "Hiệu suất sinh lời trên vốn có dấu hiệu đi xuống qua các chu kỳ tài chính."
    else:
        q2_status = ThesisChallengeAnswerStatus.WATCH
        q2_summary = "Lợi thế kinh tế ở mức trung bình, cần tiếp tục theo dõi biến động biên lợi nhuận."
        q2_detail = "Biên lợi nhuận và tỷ suất sinh lời ổn định nhưng không quá nổi bật."

    questions.append(
        ThesisChallengeQuestion(
            question_id="Q2_ECONOMIC_ADVANTAGE_WEAKENING",
            question_number=2,
            title_vi="Điều gì có thể làm suy yếu lợi thế kinh tế của doanh nghiệp?",
            answer_status=q2_status,
            answer_status_vi=STATUS_VIETNAMESE_MAP[q2_status],
            summary_vi=q2_summary,
            detail_vi=q2_detail,
            metrics={"median_roe": med_roe, "margin_trend": margin_trend},
            limitations="BCTC không thể chứng minh trực tiếp lợi thế cạnh tranh định tính (như thương hiệu hay giấy phép). Kết luận dựa trên xu hướng ROIC và biên lợi nhuận lịch sử.",
            conclusion_vi=q2_summary,
            evidence_vi=f"ROE trung vị: {(med_roe*100):.1f}%, Xu hướng biên lợi nhuận: {MARGIN_TREND_VIETNAMESE.get(margin_trend, 'Ổn định')}." if med_roe is not None else "Chưa đủ dữ liệu ROE trung vị.",
            risk_vi="Cạnh tranh ngành làm thu hẹp biên lợi nhuận hoặc sụt giảm tỷ suất sinh lời trên vốn.",
            severity_vi=STATUS_VIETNAMESE_MAP.get(q2_status, q2_status),
        )
    )

    # -------------------------------------------------------------------------
    # Q3: Kịch bản suy giảm lợi nhuận bình thường (-30% & -50%)
    # -------------------------------------------------------------------------
    reported_latest = norm_power.get("reported_latest")
    norm_5y = norm_power.get("normalized_5y")

    stress_q3 = {}
    if base_iv is not None and current_price is not None and current_price > 0 and base_iv > 0:
        # Earnings Stress Test: Tái tính toán giá trị nội tại từ sức kiếm tiền bình thường hóa sau khi giảm 30% / 50%
        iv_30 = round(base_iv * 0.70, 0)
        mos_30 = round(((iv_30 - current_price) / iv_30) * 100, 1)

        iv_50 = round(base_iv * 0.50, 0)
        mos_50 = round(((iv_50 - current_price) / iv_50) * 100, 1)

        status_mos_30 = "Vẫn đạt ngưỡng MOS" if mos_30 >= required_mos else ("Biên an toàn dương nhưng dưới ngưỡng yêu cầu" if mos_30 >= 0 else "Không còn đạt ngưỡng MOS")

        stress_q3 = {
            "scenario": "OWNER_EARNINGS_HAIRCUT_30",
            "baseline": "NORMALIZED_EARNING_POWER",
            "assumption": "Sức kiếm tiền bình thường hóa suy giảm 30% kéo dài",
            "calculation_method": "Tái tính toán định giá từ sức kiếm tiền bình thường hóa sau khi giảm 30% / 50%",
            "minus_30_iv": iv_30,
            "minus_30_mos": mos_30,
            "minus_50_iv": iv_50,
            "minus_50_mos": mos_50,
            "required_mos": required_mos,
            "status_mos": status_mos_30,
        }

        if mos_30 >= required_mos:
            q3_status = ThesisChallengeAnswerStatus.RESILIENT
        elif mos_30 >= 0:
            q3_status = ThesisChallengeAnswerStatus.WATCH
        else:
            q3_status = ThesisChallengeAnswerStatus.VULNERABLE

        q3_summary = f"Kịch bản lợi nhuận chuẩn hóa giảm 30% làm IV giảm xuống {iv_30:,.0f} đ; với giá thị trường hiện tại ({current_price:,.0f} đ), MOS còn {mos_30:.1f}% so với yêu cầu {required_mos:.1f}% ({status_mos_30})."
        q3_detail = (
            f"Kịch bản Sức kiếm tiền (Earning Power) -30%: Giá trị nội tại điều chỉnh = {iv_30:,.0f} đ, MOS = {mos_30:.1f}%. "
            f"Kịch bản Sức kiếm tiền -50%: Giá trị nội tại điều chỉnh = {iv_50:,.0f} đ, MOS = {mos_50:.1f}%."
        )
    else:
        q3_status = ThesisChallengeAnswerStatus.INSUFFICIENT_DATA
        q3_summary = "Chưa đủ dữ liệu định giá hoặc giá thị trường để tính toán kịch bản suy giảm lợi nhuận."
        q3_detail = f"Cần định giá sẵn sàng ({STATUS_VIETNAMESE_MAP.get(readiness, 'Sẵn sàng')}) để thực hiện tính toán stress test lợi nhuận."

    q3_evidence_str = (
        f"Kịch bản LN -30%: IV = {stress_q3.get('minus_30_iv', 0):,.0f} đ (MOS {stress_q3.get('minus_30_mos', 0):.1f}%). "
        f"Kịch bản LN -50%: IV = {stress_q3.get('minus_50_iv', 0):,.0f} đ (MOS {stress_q3.get('minus_50_mos', 0):.1f}%)."
    ) if stress_q3 else "Chưa đủ dữ liệu BCTC định giá."

    questions.append(
        ThesisChallengeQuestion(
            question_id="Q3_NORMALIZED_EARNINGS_STRESS",
            question_number=3,
            title_vi="Chuyện gì xảy ra nếu lợi nhuận bình thường giảm 30–50%?",
            answer_status=q3_status,
            answer_status_vi=STATUS_VIETNAMESE_MAP[q3_status],
            summary_vi=q3_summary,
            detail_vi=q3_detail,
            metrics=stress_q3,
            limitations="Tính toán giả định mức sụt giảm sức kiếm tiền kéo dài tác động tỷ lệ thuận lên giá trị nội tại cơ sở (Owner Earnings Haircut).",
            conclusion_vi=q3_summary,
            evidence_vi=q3_evidence_str,
            risk_vi="Sụt giảm lợi nhuận làm suy giảm giá trị nội tại, khiên bảo vệ Biên an toàn không còn đầy đủ.",
            severity_vi=STATUS_VIETNAMESE_MAP.get(q3_status, q3_status),
        )
    )

    # -------------------------------------------------------------------------
    # Q4: Kịch bản giá trị nội tại bị ước tính cao 30% (Valuation Model Error)
    # -------------------------------------------------------------------------
    stress_q4 = {}
    if base_iv is not None and current_price is not None and base_iv > 0:
        haircut_iv = round(base_iv * 0.70, 0)
        stressed_mos = round(((haircut_iv - current_price) / haircut_iv) * 100, 1)
        status_mos_40 = "Vẫn đạt ngưỡng MOS" if stressed_mos >= required_mos else ("Biên an toàn dương nhưng dưới ngưỡng yêu cầu" if stressed_mos >= 0 else "Không còn đạt ngưỡng MOS")

        stress_q4 = {
            "scenario": "VALUATION_MODEL_MARGIN_ERROR_30",
            "baseline": "CANONICAL_INTRINSIC_VALUE",
            "assumption": "Sai số mô hình định giá ước tính quá cao 30%",
            "calculation_method": "Chiết khấu trực tiếp 30% trên Giá trị nội tại cơ sở (Base IV)",
            "base_iv": base_iv,
            "haircut_pct": 30.0,
            "haircut_iv": haircut_iv,
            "current_price": current_price,
            "stressed_mos": stressed_mos,
            "required_mos": required_mos,
            "status_mos": status_mos_40,
        }

        if stressed_mos >= required_mos:
            q4_status = ThesisChallengeAnswerStatus.RESILIENT
        elif stressed_mos >= 0:
            q4_status = ThesisChallengeAnswerStatus.WATCH
        else:
            q4_status = ThesisChallengeAnswerStatus.VULNERABLE

        q4_summary = f"Kịch bản giá trị nội tại bị ước tính cao 30% làm IV điều chỉnh còn {haircut_iv:,.0f} đ; với giá thị trường hiện tại ({current_price:,.0f} đ), MOS còn {stressed_mos:.1f}% so với yêu cầu {required_mos:.1f}% ({status_mos_40})."
        q4_detail = (
            f"Giá trị nội tại cơ sở = {base_iv:,.0f} đ/cp. Sau khi áp dụng mức chiết khấu sai số mô hình 30%, "
            f"IV còn {haircut_iv:,.0f} đ/cp. Biên an toàn tương ứng với giá hiện tại là {stressed_mos:.1f}%."
        )
    else:
        q4_status = ThesisChallengeAnswerStatus.INSUFFICIENT_DATA
        q4_summary = "Chưa đủ dữ liệu định giá chuẩn để kiểm tra rủi ro sai số mô hình."
        q4_detail = "Yêu cầu dữ liệu định giá cơ sở sẵn sàng."

    q4_evidence_str = (
        f"IV cơ sở = {base_iv:,.0f} đ, IV sau haircut 30% = {stress_q4.get('haircut_iv', 0):,.0f} đ, "
        f"MOS điều chỉnh = {stress_q4.get('stressed_mos', 0):.1f}% vs MOS yêu cầu {required_mos:.1f}%."
    ) if stress_q4 else "Chưa đủ dữ liệu định giá cơ sở."

    questions.append(
        ThesisChallengeQuestion(
            question_id="Q4_VALUATION_MODEL_ERROR",
            question_number=4,
            title_vi="Nếu giá trị nội tại đang bị ước tính cao hơn thực tế 30% thì sao?",
            answer_status=q4_status,
            answer_status_vi=STATUS_VIETNAMESE_MAP[q4_status],
            summary_vi=q4_summary,
            detail_vi=q4_detail,
            metrics=stress_q4,
            limitations="Sử dụng duy nhất một thẩm quyền Biên an toàn chuẩn (Canonical MOS Authority).",
            conclusion_vi=q4_summary,
            evidence_vi=q4_evidence_str,
            risk_vi="Rủi ro sai số mô hình định giá khiến nhà đầu tư trả mức giá quá cao cho doanh nghiệp.",
            severity_vi=STATUS_VIETNAMESE_MAP.get(q4_status, q4_status),
        )
    )

    # -------------------------------------------------------------------------
    # Q5: Giá cổ phiếu giảm thêm 50% - Khả năng tiếp tục nắm giữ của nhà đầu tư
    # -------------------------------------------------------------------------
    pbs = personal_balance_sheet or {}
    if pbs and pbs.get("safe_liquid_assets") is not None:
        burn_rate = pbs.get("monthly_burn_rate", 1.0)
        reserve_months = pbs.get("survival_months") or (pbs.get("safe_liquid_assets", 0) / max(1.0, burn_rate))
        margin_debt = pbs.get("margin_debt", 0)

        if reserve_months >= 12 and margin_debt == 0:
            q5_status = ThesisChallengeAnswerStatus.RESILIENT
            q5_summary = f"Quỹ dự phòng cá nhân đảm bảo {reserve_months:.0f} tháng chi tiêu và không có nợ vay margin. Giá cổ phiếu giảm 50% không gây áp lực bán cưỡng bố."
        else:
            q5_status = ThesisChallengeAnswerStatus.WATCH
            q5_summary = "Dự phòng tài chính cá nhân ở mức trung bình hoặc có sử dụng margin. Cần cẩn trọng áp lực tâm lý khi giá sụt giảm sâu."
        q5_detail = f"Thời gian dự phòng: {reserve_months:.1f} tháng. Nợ margin: {margin_debt:,.0f} đ."
    else:
        q5_status = ThesisChallengeAnswerStatus.INSUFFICIENT_DATA
        q5_summary = "Chưa đủ dữ liệu tài chính cá nhân để đánh giá khả năng tiếp tục nắm giữ trong kịch bản giá giảm 50%."
        q5_detail = "Hệ thống không yêu cầu nhà đầu tư tự điền thủ công. Kết quả tự động ghi nhận chưa đủ dữ liệu."

    questions.append(
        ThesisChallengeQuestion(
            question_id="Q5_SURVIVE_PRICE_DECLINE",
            question_number=5,
            title_vi="Nếu giá cổ phiếu giảm thêm 50%, nhà đầu tư có khả năng tiếp tục nắm giữ không?",
            answer_status=q5_status,
            answer_status_vi=STATUS_VIETNAMESE_MAP[q5_status],
            summary_vi=q5_summary,
            detail_vi=q5_detail,
            metrics={"pbs_available": bool(pbs)},
            limitations="Biến động giá cổ phiếu -50% không tự động coi là suy giảm bản chất doanh nghiệp. Đánh giá tập trung vào khả năng tránh bị bán giải chấp/cưỡng bố.",
            conclusion_vi=q5_summary,
            evidence_vi=q5_detail,
            risk_vi="Áp lực tâm lý từ biến động giá sụt giảm sâu hoặc rủi ro bán giải chấp nợ margin.",
            severity_vi=STATUS_VIETNAMESE_MAP.get(q5_status, q5_status),
        )
    )

    # -------------------------------------------------------------------------
    # Q6: Thị trường đóng cửa 5 năm
    # -------------------------------------------------------------------------
    debt_liquidity = munger_analysis.get("debt_liquidity", {})
    debt_metrics = debt_liquidity.get("metrics", {}) if isinstance(debt_liquidity, dict) else {}
    debt_eq = debt_metrics.get("latest_debt_equity", 0.0)

    if (
        not hard_failures
        and value_trap.get("status") != "HIGH_RISK"
        and (debt_eq is None or debt_eq <= 1.0)
        and readiness == "READY"
    ):
        q6_status = ThesisChallengeAnswerStatus.RESILIENT
        q6_summary = "Xét riêng nền tảng tài chính, doanh nghiệp hiện có sức khỏe bảng cân đối và sức kiếm tiền đủ ổn định để hỗ trợ luận điểm sở hữu dài hạn."
        q6_detail = "Đòn bẩy tài chính thấp, không có rủi ro suy giảm cấu trúc nghiêm trọng."
    elif (debt_eq is not None and debt_eq > 1.5) or value_trap.get("status") in ("WATCH", "HIGH_RISK"):
        q6_status = ThesisChallengeAnswerStatus.WATCH
        q6_summary = "Nền tảng tài chính có một số điểm cần theo dõi (nợ vay hoặc biến động lợi nhuận), cần cẩn trọng nếu không có thanh khoản thị trường."
        q6_detail = "Áp lực nợ hoặc tính chu kỳ đòi hỏi doanh nghiệp phải quản trị dòng tiền chặt chẽ."
    else:
        q6_status = ThesisChallengeAnswerStatus.VULNERABLE
        q6_summary = "Nền tảng tài chính yếu hoặc rủi ro bẫy giá trị cao, không phù hợp để nắm giữ nếu thị trường đóng cửa."
        q6_detail = "Phát hiện rủi ro cấu trúc tài chính."

    questions.append(
        ThesisChallengeQuestion(
            question_id="Q6_FIVE_YEAR_MARKET_CLOSURE",
            question_number=6,
            title_vi="Nếu không thể giao dịch trong 5 năm, nền tảng tài chính có đủ sức để tiếp tục nắm giữ?",
            answer_status=q6_status,
            answer_status_vi=STATUS_VIETNAMESE_MAP[q6_status],
            summary_vi=q6_summary,
            detail_vi=q6_detail,
            metrics={"debt_to_equity": debt_eq},
            limitations="Xét riêng nền tảng tài chính BCTC; không dự đoán biến động giá cổ phiếu trên thị trường.",
            conclusion_vi=q6_summary,
            evidence_vi=f"Tỷ lệ Nợ/VCSH = {debt_eq:.2f}x. Trạng thái Bẫy giá trị: {get_vietnamese_valuetrap(value_trap.get('status', 'CLEAR'))}." if debt_eq is not None else f"Tỷ lệ Nợ/VCSH chưa đủ dữ liệu. Trạng thái Bẫy giá trị: {get_vietnamese_valuetrap(value_trap.get('status', 'CLEAR'))}.",
            risk_vi="Gánh nặng nghĩa vụ nợ vay tài chính khi không có cơ hội giao dịch thanh khoản ngắn hạn.",
            severity_vi=STATUS_VIETNAMESE_MAP.get(q6_status, q6_status),
        )
    )

    # -------------------------------------------------------------------------
    # Q7: Cơ hội giá trị hay giá giảm (Value vs Falling Knife)
    # -------------------------------------------------------------------------
    mos_gate = val.get("mos_gate", "UNKNOWN")
    vt_status = value_trap.get("status", "CLEAR")
    compounder_class = munger_analysis.get("compounder_classification", "AVERAGE_BUSINESS")

    if hard_failures or vt_status == "HIGH_RISK":
        q7_class = "POSSIBLE_VALUE_TRAP"
        q7_status = ThesisChallengeAnswerStatus.VULNERABLE
        q7_summary = "Có dấu hiệu bẫy giá trị (Value Trap). Giá cổ phiếu giảm phản ánh sự suy yếu thực sự của nền tảng kinh doanh."
    elif vt_status == "WATCH" or compounder_class == "WEAK_BUSINESS":
        q7_class = "CHEAP_BUT_DETERIORATING"
        q7_status = ThesisChallengeAnswerStatus.WATCH
        q7_summary = "Giá giảm nhưng nền tảng kinh doanh đang có dấu hiệu suy yếu. Cần phân biệt kỹ giữa giá rẻ và cơ hội giá trị."
    elif mos_gate == "PASS" and not hard_failures:
        q7_class = "VALUE_WITH_SAFETY"
        q7_status = ThesisChallengeAnswerStatus.RESILIENT
        q7_summary = "Cơ hội giá trị có biên an toàn: Doanh nghiệp đạt chuẩn chất lượng BCTC và mức giá hiện tại đạt Biên an toàn yêu cầu."
    elif mos_gate == "FAIL":
        q7_class = "QUALITY_BUT_EXPENSIVE"
        q7_status = ThesisChallengeAnswerStatus.WATCH
        q7_summary = "Doanh nghiệp có chất lượng tài chính tốt nhưng mức giá hiện tại chưa đủ hấp dẫn (chưa đạt Biên an toàn)."
    else:
        q7_class = "INSUFFICIENT_EVIDENCE"
        q7_status = ThesisChallengeAnswerStatus.INSUFFICIENT_DATA
        q7_summary = "Chưa đủ bằng chứng định giá để phân loại cơ hội giá trị."

    q7_detail = f"Phân loại cơ hội: {get_vietnamese_q7_classification(q7_class)}. Biên an toàn thực tế: {actual_mos if actual_mos is not None else 'Chưa đủ dữ liệu'}% vs Yêu cầu: {required_mos}%."

    questions.append(
        ThesisChallengeQuestion(
            question_id="Q7_VALUE_OR_FALLING_KNIFE",
            question_number=7,
            title_vi="Đây là cơ hội giá trị hay chỉ là giá cổ phiếu giảm?",
            answer_status=q7_status,
            answer_status_vi=STATUS_VIETNAMESE_MAP[q7_status],
            summary_vi=q7_summary,
            detail_vi=q7_detail,
            metrics={"classification": q7_class, "actual_mos": actual_mos, "required_mos": required_mos},
            limitations="Quy tắc bất biến: Giá cổ phiếu giảm đơn thuần TUYỆT ĐỐI KHÔNG tự động coi là cơ hội giá trị.",
            conclusion_vi=q7_summary,
            evidence_vi=q7_detail,
            risk_vi="Nhầm lẫn giữa cổ phiếu giá rẻ do suy yếu cấu trúc kinh doanh và cổ phiếu dưới giá trị có Biên an toàn.",
            severity_vi=STATUS_VIETNAMESE_MAP.get(q7_status, q7_status),
        )
    )

    # -------------------------------------------------------------------------
    # Q8: Bằng chứng thực tế nào sẽ chứng minh luận điểm hiện tại sai?
    # -------------------------------------------------------------------------
    invalidation_criteria = []
    if archetype == "BANK":
        invalidation_criteria = [
            {
                "metric": "ROE Ngân hàng",
                "trigger": "< 12.0% liên tiếp 2 năm",
                "reason": "Suy giảm hiệu suất sinh lời trên vốn chủ sở hữu ngân hàng.",
            },
            {
                "metric": "Tăng trưởng Vốn chủ sở hữu",
                "trigger": "< 8.0%/năm",
                "reason": "Tốc độ tích lũy vốn không đủ hỗ trợ mở rộng quy mô tín dụng.",
            },
            {
                "metric": "Rủi ro nợ xấu & Trích lập",
                "trigger": "Tỷ lệ nợ xấu tăng đột biến > 3.0%",
                "reason": "Phản ánh chất lượng tài sản ngân hàng suy giảm nghiêm trọng.",
            },
        ]
    elif archetype == "SECURITIES":
        invalidation_criteria = [
            {
                "metric": "ROE Công ty chứng khoán",
                "trigger": "< 8.0% liên tiếp 2 năm",
                "reason": "Suy giảm hiệu quả mảng môi giới và tự doanh.",
            },
            {
                "metric": "Tỷ lệ Đòn bẩy (Nợ/VCSH)",
                "trigger": "> 2.5x kèm chi phí lãi vay tăng mạnh",
                "reason": "Đòn bẩy tài chính quá cao gây áp lực chi phí vốn.",
            },
            {
                "metric": "Biến động Danh mục FVTPL",
                "trigger": "Lỗ tự doanh ròng kéo dài 2 năm",
                "reason": "Rủi ro thị trường ảnh hưởng trực tiếp đến LNST.",
            },
        ]
    else:  # NORMAL_ENTERPRISE
        invalidation_criteria = [
            {
                "metric": "Hiệu suất Sinh lời ROIC / ROE",
                "trigger": "ROE < 10.0% hoặc ROIC < 8.0% kéo dài 2 năm",
                "reason": "Suy giảm năng lực tạo giá trị từ vốn đầu tư.",
            },
            {
                "metric": "Chuyển hóa Dòng tiền (CFO/PAT)",
                "trigger": "< 0.6x liên tiếp 2 năm",
                "reason": "Lợi nhuận báo cáo không đi kèm với dòng tiền mặt thu về.",
            },
            {
                "metric": "Tăng trưởng Khoản phải thu vs Doanh thu",
                "trigger": "CAGR Phải thu vượt CAGR Doanh thu > 15% trong 3 năm",
                "reason": "Rủi ro đọng vốn và nợ xấu từ khách hàng.",
            },
            {
                "metric": "Nợ vay & Đòn bẩy",
                "trigger": "Nợ/VCSH > 1.5x trong khi LNST suy giảm",
                "reason": "Gia tăng áp lực gánh nặng chi phí lãi vay.",
            },
            {
                "metric": "Pha loãng cổ phiếu (EPS)",
                "trigger": "Tốc độ tăng số cổ phiếu vượt tốc độ tăng LNST > 5%",
                "reason": "Xâm phạm lợi ích kinh tế của cổ đông hiện hữu.",
            },
        ]

    q8_summary = f"Đã thiết lập {len(invalidation_criteria)} ngưỡng theo dõi của QPort để kiểm tra và bác bỏ luận điểm đầu tư."
    q8_detail = f"Nếu các sự kiện tài chính trên vượt ngưỡng theo dõi của QPort trong các kỳ BCTC tiếp theo, hệ thống sẽ tự động hạ cấp đánh giá và khuyến nghị {get_vietnamese_decision('AVOID')}."
    q8_evidence_str = "; ".join([f"{c['metric']}: {c['trigger']}" for c in invalidation_criteria])

    questions.append(
        ThesisChallengeQuestion(
            question_id="Q8_MEASURABLE_INVALIDATION_CRITERIA",
            question_number=8,
            title_vi="Bằng chứng thực tế nào sẽ chứng minh luận điểm hiện tại sai?",
            answer_status=ThesisChallengeAnswerStatus.RESILIENT,
            answer_status_vi=STATUS_VIETNAMESE_MAP[ThesisChallengeAnswerStatus.RESILIENT],
            summary_vi=q8_summary,
            detail_vi=q8_detail,
            metrics={"criteria_count": len(invalidation_criteria)},
            limitations="Các tiêu chí bác bỏ được theo dõi tự động qua các kỳ BCTC năm (FY) tiếp theo.",
            conclusion_vi=q8_summary,
            evidence_vi=q8_evidence_str,
            risk_vi="Doanh nghiệp chạm ngưỡng suy thoái định lượng nhưng nhà đầu tư trì hoãn thoái vốn.",
            severity_vi=STATUS_VIETNAMESE_MAP.get(ThesisChallengeAnswerStatus.RESILIENT, "Có khả năng chống chịu"),
        )
    )

    # -------------------------------------------------------------------------
    # Decision Contradiction Check (System Invariant)
    # -------------------------------------------------------------------------
    decision_contradiction = False
    contradiction_details = ""
    vulnerable_q_count = sum(1 for q in questions if q.answer_status == ThesisChallengeAnswerStatus.VULNERABLE)

    if core_decision_state == "BUY" and (vulnerable_q_count > 0 or vt_status == "HIGH_RISK"):
        decision_contradiction = True
        contradiction_details = "Mẫu thuẫn hệ thống: QPort đưa ra quyết định BUY nhưng kịch bản Phản biện phát hiện rủi ro cao (Decision Contradiction)."

    overall_status = "CLEAR"
    if hard_failures or vulnerable_q_count >= 2:
        overall_status = "HIGH_RISK"
    elif warnings or vulnerable_q_count == 1:
        overall_status = "WATCH"

    thesis_summary = (
        f"Kết quả Phản biện luận điểm cho {symbol} ({get_vietnamese_archetype(archetype)}): "
        f"{len([q for q in questions if q.answer_status == 'RESILIENT'])}/8 câu hỏi đạt trạng thái chống chịu tốt."
    )

    return InvestmentThesisChallenge(
        symbol=symbol,
        archetype=archetype,
        analysis_date=datetime.now().strftime("%Y-%m-%d"),
        status=overall_status,
        confidence=munger_analysis.get("overall_confidence", "MEDIUM"),
        thesis_summary=thesis_summary,
        primary_risks=primary_risks,
        questions=questions,
        stress_tests={"q3_stress": stress_q3, "q4_stress": stress_q4},
        invalidation_criteria=invalidation_criteria,
        decision_contradiction=decision_contradiction,
        contradiction_details=contradiction_details,
    )
