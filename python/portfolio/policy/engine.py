"""Buffett-Munger Core Deterministic Decision Policy Engine (Task 136, Task 154).

Strict BCTC-Only 16-Gate Decision Precedence Engine:
- Sole source of financial evidence: Canonical SSI Annual Financial Statements in PostgreSQL.
- Qualitative UNKNOWN (Circle of competence, qualitative moat, management integrity) MUST NOT block financial decisions.
- Margin of Safety (MOS) is a PRICE condition, Financial Quality is a BUSINESS condition.
- A high MOS alone CANNOT override financial red flags or create false BUY decisions.
"""

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
    """Evaluate canonical InvestmentDecisionContext through strict 16-gate Buffett-Munger precedence rules."""
    is_existing_holding = ctx.current_weight > 0 or ctx.shares_held > 0

    blocking_reasons: list[str] = []
    rules: list[DecisionRuleTrigger] = []
    reasons: list[str] = []
    what_would_change: list[str] = []

    # -------------------------------------------------------------------------
    # GATE 1: Hard Accounting Reliability Failure
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
                description="Báo cáo tài chính không đạt chuẩn tin cậy kế toán.",
            )
        )

    # -------------------------------------------------------------------------
    # GATE 2: Solvency Failure / Solvency Risk
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
                description="Khả năng thanh toán nợ và an toàn tài chính không đạt.",
            )
        )

    # -------------------------------------------------------------------------
    # GATE 3: Structural Business Deterioration / Moat Destruction
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
                description="Doanh nghiệp hoặc lợi thế cạnh tranh bị suy thoái cấu trúc.",
            )
        )

    # -------------------------------------------------------------------------
    # GATE 4: Value Trap High Risk
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
                description="Cổ phiếu bị bẫy giá trị mức nguy hiểm cao (HIGH_RISK).",
            )
        )

    # -------------------------------------------------------------------------
    # GATE 5: Financial Core Data Readiness
    # Note: Qualitative UNKNOWN (Circle of competence, qualitative moat, management)
    # MUST NOT block the financial decision pipeline.
    # -------------------------------------------------------------------------
    has_financial_core_gap = (
        ctx.data_readiness.get("financial_core") in ("BLOCKED", "INSUFFICIENT")
        or ctx.data_readiness.get("history") == "INSUFFICIENT"
    )
    if has_financial_core_gap:
        blocking_reasons.append("BUSINESS_REVIEW_INCOMPLETE")
        rules.append(
            DecisionRuleTrigger(
                rule_id="R-05-BUSINESS-REVIEW-INCOMPLETE",
                metric="data_readiness",
                value=str(ctx.data_readiness),
                threshold="READY/PARTIAL",
                status="TRIGGERED",
                source="financial_data",
                description="Chưa đủ dữ liệu tài chính BCTC lịch sử để hoàn tất phân tích.",
            )
        )

    # -------------------------------------------------------------------------
    # GATE 6: Valuation Readiness & Base IV Availability
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
    # GATE 7: Forensic Red Flags & Quality Mismatch (Anti-False BUY Gate)
    # If there are quality warnings (CFO/PAT divergence, persistent receivables, high volatility)
    # A high MOS CANNOT automatically trigger BUY!
    # -------------------------------------------------------------------------
    has_forensic_cfo_warning = any(
        "CFO" in w or "CASH_CONVERSION" in w or "DIVERGENCE" in w or "RECEIVABLES" in w or "IDENTITY" in w
        for w in ctx.warnings
    )
    has_quality_hesitation = (
        has_forensic_cfo_warning
        or ctx.value_trap_status == "WATCH"
        or ctx.quality_tier in ("TIER_3", "TIER_4", "WEAK", "WEAK_BUSINESS", "AVERAGE_BUSINESS")
    )

    # -------------------------------------------------------------------------
    # GATE 8: Margin of Safety (MOS) Check
    # -------------------------------------------------------------------------
    req_mos = ctx.required_mos if (ctx.required_mos is not None and ctx.required_mos > 0) else 20.0
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
    elif has_quality_hesitation and not is_existing_holding:
        # MOS passes, but quality has red flags/warnings -> Do NOT auto BUY
        blocking_reasons.append("FINANCIAL_QUALITY_HESITATION")
        rules.append(
            DecisionRuleTrigger(
                rule_id="R-07B-QUALITY-HESITATION",
                metric="warnings",
                value=str(ctx.warnings),
                threshold="CLEAR",
                status="TRIGGERED",
                source="forensics",
                description="Biên an toàn đạt nhưng chất lượng dòng tiền/BCTC có dấu hiệu cần thận trọng.",
            )
        )

    # -------------------------------------------------------------------------
    # GATE 9: Personal Balance Sheet (PBS) Check
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
    # GATE 10: Position Capacity Check
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
        summary = "Báo cáo tài chính vi phạm tính tin cậy kế toán. Tối quan trọng bảo vệ vốn."
        reasons.append("Báo cáo tài chính vi phạm tính tin cậy kế toán.")
        what_would_change.append("Báo cáo tài chính được kiểm toán độc lập xác nhận minh bạch.")

    elif "SOLVENCY_FAILURE" in blocking_reasons:
        primary_reason = "SOLVENCY_FAILURE"
        decision = "SELL_REVIEW" if is_existing_holding else "AVOID"
        confidence = "HIGH"
        summary = "Rủi ro nợ vay và khả năng thanh toán nghiêm trọng."
        reasons.append("Doanh nghiệp đối mặt với rủi ro tài chính / kiệt quệ thanh khoản.")
        what_would_change.append("Doanh nghiệp tái cơ cấu nợ và tái lập dòng tiền kinh doanh dương.")

    elif "STRUCTURAL_DETERIORATION" in blocking_reasons:
        primary_reason = "STRUCTURAL_DETERIORATION"
        decision = "SELL_REVIEW" if is_existing_holding else "AVOID"
        confidence = "HIGH"
        summary = "Mô hình kinh doanh suy giảm cấu trúc hoặc xói mòn lợi thế cạnh tranh kéo dài."
        reasons.append("Chất lượng kinh doanh yếu kém hoặc xói mòn lợi thế cạnh tranh.")
        what_would_change.append("Doanh nghiệp tái lập biên lợi nhuận và sức kiếm tiền bền vững.")

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
        summary = "Chưa đủ dữ liệu tài chính BCTC lịch sử để hoàn thành đánh giá toàn diện."
        reasons.append("Dữ liệu tài chính lịch sử dưới 3-5 năm.")
        what_would_change.append("Bổ sung dữ liệu BCTC các năm tiếp theo.")

    elif "VALUATION_UNAVAILABLE" in blocking_reasons:
        primary_reason = "VALUATION_UNAVAILABLE"
        decision = "HOLD" if is_existing_holding else "WAIT_FOR_MOS"
        confidence = "LOW"
        summary = "Mô hình định giá chưa hoàn chỉnh hoặc chưa đủ dữ liệu giá trị nội tại."
        reasons.append("Thiếu định giá Base IV hợp lệ.")
        what_would_change.append("Cập nhật đầy đủ BCTC để tính toán định giá Base IV.")

    elif "FINANCIAL_QUALITY_HESITATION" in blocking_reasons:
        primary_reason = "FINANCIAL_QUALITY_HESITATION"
        decision = "HOLD" if is_existing_holding else "WAIT_FOR_MOS"
        confidence = "HIGH" if ctx.valuation_confidence == "HIGH" else "MEDIUM"
        summary = "Biên an toàn số học hấp dẫn nhưng chất lượng dòng tiền/BCTC có dấu hiệu cần thận trọng."
        reasons.append("Mặc dù MOS đạt yêu cầu, nhưng phát hiện phân kỳ dòng tiền hoặc biến động lợi nhuận lớn.")
        what_would_change.append("Dòng tiền kinh doanh xác nhận ổn định qua 2 kỳ BCTC liên tiếp.")

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
