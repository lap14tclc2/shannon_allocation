"""Buffett-Munger Core Deterministic Decision Policy Engine (T08)."""

from __future__ import annotations

from typing import Any
from portfolio.policy.models import InvestmentDecisionContext
from portfolio.policy.evidence import DecisionEvidence, DecisionRuleTrigger

DECISION_STATES = (
    "BUY",
    "BUY_MORE",
    "HOLD",
    "HOLD_NO_NEW_CAPITAL",
    "WAIT_FOR_MOS",
    "BUILD_RESERVE_FIRST",
    "REVIEW_BUSINESS",
    "AVOID",
    "SELL_REVIEW",
    "SELL",
)


def evaluate_decision(ctx: InvestmentDecisionContext) -> DecisionEvidence:
    """Evaluate canonical InvestmentDecisionContext through strict Buffett-Munger precedence rules."""
    is_existing_holding = ctx.current_weight > 0 or ctx.shares_held > 0

    blocking_reasons: list[str] = []
    rules: list[DecisionRuleTrigger] = []
    reasons: list[str] = []
    what_would_change: list[str] = []

    # -------------------------------------------------------------------------
    # 1. GATE 1: Hard Accounting Reliability Failure
    # -------------------------------------------------------------------------
    if ctx.accounting_reliability == "FAIL" or "ACCOUNTING_UNRELIABLE" in ctx.hard_rejects:
        blocking_reasons.append("ACCOUNTING_FAILURE")
        rules.append(
            DecisionRuleTrigger(
                rule_id="R-02-ACCOUNTING-RELIABILITY",
                metric="accounting_reliability",
                value=ctx.accounting_reliability,
                threshold="PASS",
                status="TRIGGERED",
                source="business_review",
                description="Báo cáo tài chính không đạt chuẩn tin cậy.",
            )
        )

    # -------------------------------------------------------------------------
    # 2. GATE 2: Solvency Failure / Solvency Risk
    # -------------------------------------------------------------------------
    if ctx.financial_strength == "FAIL" or "SOLVENCY_RISK" in ctx.hard_rejects:
        blocking_reasons.append("SOLVENCY_FAILURE")
        rules.append(
            DecisionRuleTrigger(
                rule_id="R-03-SOLVENCY-RISK",
                metric="financial_strength",
                value=ctx.financial_strength,
                threshold="PASS/WATCH",
                status="TRIGGERED",
                source="financial_data",
                description="Khả năng thanh toán nợ không đạt.",
            )
        )

    # -------------------------------------------------------------------------
    # 3. GATE 3: Structural Business Deterioration / Moat Destruction
    # -------------------------------------------------------------------------
    if (
        ctx.business_review_status in ("BUSINESS_FAIL", "FAIL")
        or ctx.moat_assessment == "FAIL"
        or "MOAT_DESTRUCTION" in ctx.hard_rejects
    ):
        blocking_reasons.append("STRUCTURAL_DETERIORATION")
        rules.append(
            DecisionRuleTrigger(
                rule_id="R-04-BUSINESS-MOAT-FAILURE",
                metric="moat_assessment",
                value=ctx.moat_assessment,
                threshold="PASS/WATCH",
                status="TRIGGERED",
                source="business_review",
                description="Doanh nghiệp hoặc lợi thế cạnh tranh thất bại.",
            )
        )

    # -------------------------------------------------------------------------
    # 4. GATE 4: Value Trap High Risk
    # -------------------------------------------------------------------------
    if ctx.value_trap_status == "HIGH_RISK":
        blocking_reasons.append("VALUE_TRAP_HIGH_RISK")
        rules.append(
            DecisionRuleTrigger(
                rule_id="R-06-VALUE-TRAP-HIGH-RISK",
                metric="value_trap_status",
                value=ctx.value_trap_status,
                threshold="CLEAR",
                status="TRIGGERED",
                source="value_trap",
                description="Cổ phiếu bị bẫy giá trị mức nguy hiểm HIGH_RISK.",
            )
        )

    # -------------------------------------------------------------------------
    # 5. GATE 5: Business Evidence Readiness (Unresolved Qualitative / Business Review)
    # -------------------------------------------------------------------------
    if ctx.business_review_status not in ("BUSINESS_PASS", "PASS"):
        blocking_reasons.append("BUSINESS_REVIEW_INCOMPLETE")
        if ctx.circle_of_competence in ("UNKNOWN", None):
            blocking_reasons.append("UNDERSTANDABILITY_UNKNOWN")
            blocking_reasons.append("CIRCLE_OF_COMPETENCE_UNKNOWN")
        if ctx.moat_assessment in ("UNKNOWN", None):
            blocking_reasons.append("MOAT_UNKNOWN")
        if ctx.management_integrity in ("UNKNOWN", None) or ctx.capital_allocation_quality in ("UNKNOWN", None):
            blocking_reasons.append("MANAGEMENT_EVIDENCE_UNKNOWN")
        if ctx.accounting_qualitative_reliability in ("UNKNOWN", None):
            blocking_reasons.append("ACCOUNTING_RELIABILITY_UNKNOWN")

        rules.append(
            DecisionRuleTrigger(
                rule_id="R-05-BUSINESS-REVIEW-INCOMPLETE",
                metric="business_review_status",
                value=ctx.business_review_status,
                threshold="BUSINESS_PASS",
                status="TRIGGERED",
                source="business_review",
                description="Chưa đủ bằng chứng định tính về doanh nghiệp.",
            )
        )

    # -------------------------------------------------------------------------
    # 6. GATE 6: Value Trap Insufficient Data / Watch
    # -------------------------------------------------------------------------
    if ctx.value_trap_status in ("INSUFFICIENT_DATA", "WATCH", None) or ctx.data_readiness.get("value_trap") == "BLOCKED":
        blocking_reasons.append("VALUE_TRAP_INSUFFICIENT")
        rules.append(
            DecisionRuleTrigger(
                rule_id="R-06B-VALUE-TRAP-INSUFFICIENT",
                metric="value_trap_status",
                value=ctx.value_trap_status,
                threshold="CLEAR",
                status="TRIGGERED",
                source="value_trap",
                description="Dữ liệu bẫy giá trị chưa đầy đủ hoặc thuộc WATCH.",
            )
        )

    # -------------------------------------------------------------------------
    # 7. GATE 7: Valuation Readiness & Base IV Availability
    # -------------------------------------------------------------------------
    has_valid_valuation = (
        ctx.model_status in ("VALID", "VERIFIED", "MODEL_VERIFIED")
        or (ctx.base_iv is not None and ctx.base_iv > 0)
        or (ctx.actual_mos is not None and ctx.actual_mos > 0)
    )
    if (
        not has_valid_valuation
        or ctx.data_readiness.get("valuation") == "BLOCKED"
        or ctx.data_readiness.get("financial_core") == "BLOCKED"
    ):
        blocking_reasons.append("VALUATION_UNAVAILABLE")
        rules.append(
            DecisionRuleTrigger(
                rule_id="R-00-DATA-READINESS-BLOCKED",
                metric="model_status",
                value=ctx.model_status,
                threshold="VALID",
                status="TRIGGERED",
                source="valuation",
                description="Mô hình định giá hoặc dữ liệu tài chính chưa sẵn sàng.",
            )
        )

    # -------------------------------------------------------------------------
    # 8. GATE 8: Margin of Safety (MOS) Check
    # -------------------------------------------------------------------------
    req_mos = ctx.required_mos if (ctx.required_mos is not None and ctx.required_mos > 0) else 15.0
    mos_price = (ctx.base_iv * (1.0 - req_mos / 100.0)) if (ctx.base_iv and ctx.base_iv > 0) else None

    mos_insufficient = False
    if ctx.current_price > 0 and mos_price is not None:
        if ctx.current_price > mos_price:
            mos_insufficient = True
    elif ctx.actual_mos is not None and ctx.actual_mos < req_mos:
        mos_insufficient = True

    if mos_insufficient:
        blocking_reasons.append("MOS_INSUFFICIENT")
        rules.append(
            DecisionRuleTrigger(
                rule_id="R-07-MOS-INSUFFICIENT",
                metric="current_price",
                value=ctx.current_price,
                threshold=mos_price if mos_price is not None else req_mos,
                status="TRIGGERED",
                source="valuation",
                description="Giá thị trường chưa đạt mức Biên an toàn (MOS) yêu cầu.",
            )
        )

    # -------------------------------------------------------------------------
    # 9. GATE 9: Personal Balance Sheet (PBS) Check
    # -------------------------------------------------------------------------
    if ctx.survival_reserve_status in ("UNCONFIGURED", "UNKNOWN"):
        blocking_reasons.append("PERSONAL_BALANCE_SHEET_UNKNOWN")
        rules.append(
            DecisionRuleTrigger(
                rule_id="R-01-SURVIVAL-RESERVE-UNKNOWN",
                metric="survival_reserve_status",
                value=ctx.survival_reserve_status,
                threshold="SAFE",
                status="TRIGGERED",
                source="personal_finance",
                description="Chưa cấu hình Bảng Cân Đối Cá Nhân.",
            )
        )
    elif ctx.survival_reserve_status in ("UNSAFE", "UNSATISFACTORY") or (ctx.available_long_term_capital <= 0 and not is_existing_holding):
        blocking_reasons.append("SURVIVAL_RESERVE_INSUFFICIENT")
        rules.append(
            DecisionRuleTrigger(
                rule_id="R-01-SURVIVAL-RESERVE",
                metric="survival_reserve_status",
                value=ctx.survival_reserve_status,
                threshold="SAFE",
                status="TRIGGERED",
                source="personal_finance",
                description="Trạng thái quỹ dự phòng cá nhân không an toàn.",
            )
        )
    elif ctx.survival_reserve_status == "ATTENTION":
        blocking_reasons.append("SURVIVAL_RESERVE_INSUFFICIENT")
        rules.append(
            DecisionRuleTrigger(
                rule_id="R-01B-SURVIVAL-RESERVE-ATTENTION",
                metric="survival_reserve_status",
                value="ATTENTION",
                threshold="SAFE",
                status="TRIGGERED",
                source="personal_finance",
                description="Trạng thái quỹ dự phòng cá nhân ở mức ATTENTION.",
            )
        )

    # -------------------------------------------------------------------------
    # 10. GATE 10: Position Capacity Check
    # -------------------------------------------------------------------------
    if is_existing_holding and ctx.current_weight >= 0.35:
        blocking_reasons.append("POSITION_CAP_REACHED")
        rules.append(
            DecisionRuleTrigger(
                rule_id="R-08-POSITION-CAP",
                metric="current_weight",
                value=ctx.current_weight,
                threshold=0.35,
                status="TRIGGERED",
                source="position_state",
                description="Vị thế vượt ngưỡng tỷ trọng 35% danh mục.",
            )
        )

    # Deduplicate blocking reasons maintaining insertion order
    blocking_reasons = list(dict.fromkeys(blocking_reasons))

    # -------------------------------------------------------------------------
    # DETERMINISTIC WATERFALL PRECEDENCE EVALUATION
    # -------------------------------------------------------------------------
    if "ACCOUNTING_FAILURE" in blocking_reasons:
        primary_reason = "ACCOUNTING_FAILURE"
        decision = "SELL_REVIEW" if is_existing_holding else "AVOID"
        confidence = "HIGH"
        summary = "Báo cáo tài chính vi phạm tính tin cậy. Tối quan trọng bảo vệ vốn."
        reasons.append("Báo cáo tài chính vi phạm tính tin cậy.")
        what_would_change.append("Báo cáo tài chính được kiểm toán độc lập xác nhận minh bạch.")

    elif "SOLVENCY_FAILURE" in blocking_reasons:
        primary_reason = "SOLVENCY_FAILURE"
        decision = "SELL_REVIEW" if is_existing_holding else "AVOID"
        confidence = "HIGH"
        summary = "Rủi ro nợ và khả năng thanh toán nghiêm trọng."
        reasons.append("Doanh nghiệp đối mặt với rủi ro tài chính / kiệt quệ thanh khoản.")
        what_would_change.append("Doanh nghiệp tái cơ cấu nợ và tái lập dòng tiền kinh doanh dương.")

    elif "STRUCTURAL_DETERIORATION" in blocking_reasons:
        primary_reason = "STRUCTURAL_DETERIORATION"
        decision = "SELL_REVIEW" if is_existing_holding else "AVOID"
        confidence = "HIGH"
        summary = "Mô hình kinh doanh không đạt tiêu chí chất lượng tối thiểu hoặc suy giảm xói mòn lợi thế cạnh tranh."
        reasons.append("Chất lượng kinh doanh yếu kém hoặc xói mòn lợi thế cạnh tranh.")
        what_would_change.append("Doanh nghiệp tái lập biên lợi nhuận và lợi thế cạnh tranh bền vững.")

    elif "VALUE_TRAP_HIGH_RISK" in blocking_reasons:
        primary_reason = "VALUE_TRAP_HIGH_RISK"
        decision = "SELL_REVIEW" if is_existing_holding else "AVOID"
        confidence = "HIGH"
        summary = "Cổ phiếu có dấu hiệu bẫy giá trị (Value Trap) do suy giảm nội tại cấu trúc."
        reasons.append("Giá rẻ nhưng lợi nhuận suy giảm cấu trúc hoặc dòng tiền phân kỳ nghiêm trọng.")
        what_would_change.append("Dòng tiền CFO phục hồi xác nhận lợi nhuận thực tế.")

    elif "BUSINESS_REVIEW_INCOMPLETE" in blocking_reasons:
        primary_reason = "BUSINESS_REVIEW_INCOMPLETE"
        decision = "REVIEW_BUSINESS"
        confidence = "LOW"
        summary = "Chưa đủ bằng chứng định tính về doanh nghiệp. Cần nghiên cứu doanh nghiệp trước khi phân bổ vốn."
        reasons.append("Thông tin định tính hoặc năng lực hiểu biết doanh nghiệp chưa hoàn thiện.")
        what_would_change.append("Bổ sung đầy đủ bằng chứng định tính (Vòng tròn năng lực, Moat, Ban lãnh đạo).")

    elif "VALUE_TRAP_INSUFFICIENT" in blocking_reasons:
        primary_reason = "VALUE_TRAP_INSUFFICIENT"
        decision = "REVIEW_BUSINESS" if is_existing_holding else "REVIEW_BUSINESS"
        confidence = "LOW"
        summary = "Dữ liệu bẫy giá trị ở trạng thái INSUFFICIENT_DATA hoặc WATCH. Cần hoàn thiện đánh giá."
        reasons.append("Chưa đủ bằng chứng xác nhận Value Trap CLEAR.")
        what_would_change.append("Bổ sung dữ liệu tài chính lịch sử để hoàn thiện đánh giá Value Trap.")

    elif "VALUATION_UNAVAILABLE" in blocking_reasons:
        primary_reason = "VALUATION_UNAVAILABLE"
        decision = "HOLD" if is_existing_holding else "WAIT_FOR_MOS"
        confidence = "LOW"
        summary = "Mô hình định giá chưa hoàn chỉnh hoặc chưa đủ dữ liệu giá trị nội tại."
        reasons.append("Thiếu định giá Base IV hợp lệ.")
        what_would_change.append("Cập nhật đầy đủ BCTC để tính toán định giá Base IV.")

    elif "MOS_INSUFFICIENT" in blocking_reasons:
        primary_reason = "MOS_INSUFFICIENT"
        decision = "HOLD" if is_existing_holding else "WAIT_FOR_MOS"
        confidence = "HIGH" if ctx.valuation_confidence == "HIGH" else "MEDIUM"
        formatted_mos_price = f"{mos_price:,.0f}" if mos_price is not None else "N/A"
        summary = "Doanh nghiệp tốt nhưng giá thị trường chưa tiệm cận Biên an toàn (Margin of Safety) yêu cầu."
        reasons.append(f"Giá thị trường ({ctx.current_price:,.0f}) cao hơn mức mua an toàn (MOS: {formatted_mos_price}).")
        what_would_change.append("Thị trường điều chỉnh về mức Biên an toàn yêu cầu hoặc IV tăng trưởng.")

    elif "PERSONAL_BALANCE_SHEET_UNKNOWN" in blocking_reasons:
        primary_reason = "PERSONAL_BALANCE_SHEET_UNKNOWN"
        decision = "BUILD_RESERVE_FIRST"
        confidence = "HIGH"
        summary = "Chưa cấu hình Bảng Cân Đối Cá Nhân. Cần thiết lập dự phòng tài chính trước khi mua."
        reasons.append("Thiếu cấu hình Bảng Cân Đối Cá Nhân.")
        what_would_change.append("Cấu hình Bảng Cân Đối Cá Nhân và đạt trạng thái dự phòng SAFE.")

    elif "SURVIVAL_RESERVE_INSUFFICIENT" in blocking_reasons:
        primary_reason = "SURVIVAL_RESERVE_INSUFFICIENT"
        decision = "HOLD_NO_NEW_CAPITAL" if (is_existing_holding and ctx.survival_reserve_status == "ATTENTION") else "BUILD_RESERVE_FIRST"
        confidence = "HIGH"
        summary = "Tài chính cá nhân ở trạng thái chưa đạt SAFE. Cấm mở vị thế mua mới."
        reasons.append("Quỹ dự phòng an toàn cá nhân / nguồn vốn dài hạn chưa đạt tiêu chuẩn.")
        what_would_change.append("Tích lũy tài sản thanh khoản an toàn để khôi phục quỹ dự phòng về mức SAFE.")

    elif "POSITION_CAP_REACHED" in blocking_reasons:
        primary_reason = "POSITION_CAP_REACHED"
        decision = "HOLD_NO_NEW_CAPITAL"
        confidence = "HIGH"
        summary = "Doanh nghiệp tốt và định giá hợp lý, nhưng vị thế đã đạt ngưỡng giới hạn tỷ trọng danh mục (35%)."
        reasons.append("Tỷ trọng vị thế hiện tại đã đạt trần chính sách danh mục.")
        what_would_change.append("Tỷ trọng vị thế giảm xuống dưới 30% NAV do biến động hoặc tăng NAV.")

    else:
        primary_reason = "ALL_CRITERIA_SATISFIED"
        decision = "BUY_MORE" if is_existing_holding else "BUY"
        confidence = "HIGH" if ctx.valuation_confidence == "HIGH" else "MEDIUM"
        summary = "Doanh nghiệp chất lượng cao, Biên an toàn hấp dẫn, nguồn vốn cá nhân bền vững."
        reasons.append("Hội đủ tất cả các điều kiện chất lượng, định giá và nguồn vốn dài hạn.")
        what_would_change.append("Giá thị trường tăng vượt Base IV hoặc vị thế đạt trần tỷ trọng.")

    if not reasons and blocking_reasons:
        reasons.extend(blocking_reasons)

    return DecisionEvidence(
        symbol=ctx.symbol,
        decision=decision,
        confidence=confidence,
        summary=summary,
        primary_reason=primary_reason,
        blocking_reasons=blocking_reasons,
        reasons=reasons,
        facts=[
            {"metric": "current_price", "value": ctx.current_price},
            {"metric": "base_iv", "value": ctx.base_iv},
            {"metric": "bear_iv", "value": ctx.bear_iv},
            {"metric": "quality_tier", "value": ctx.quality_tier},
            {"metric": "available_capital", "value": ctx.available_long_term_capital},
        ],
        rules_triggered=rules,
        warnings=ctx.warnings,
        missing_data=ctx.missing_data,
        what_changed=[],
        what_would_change_decision=what_would_change,
    )
