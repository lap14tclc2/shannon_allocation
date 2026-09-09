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
    reasons: list[str] = []
    rules: list[DecisionRuleTrigger] = []
    what_would_change: list[str] = []
    is_existing_holding = ctx.current_weight > 0 or ctx.shares_held > 0

    # Gate 1: Accounting Reliability or Data Integrity Conflict
    if ctx.accounting_reliability == "FAIL" or "ACCOUNTING_UNRELIABLE" in ctx.hard_rejects:
        decision = "SELL_REVIEW" if is_existing_holding else "AVOID"
        confidence = "HIGH"
        summary = "Báo cáo tài chính không đáng tin cậy. Tối quan trọng bảo vệ vốn."
        reasons.append("Báo cáo tài chính vi phạm tính tin cậy.")
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
        what_would_change.append("Báo cáo tài chính được kiểm toán độc lập xác nhận minh bạch.")

    # Gate 2: Solvency Failure / Solvency Risk
    elif ctx.financial_strength == "FAIL" or "SOLVENCY_RISK" in ctx.hard_rejects:
        decision = "SELL_REVIEW" if is_existing_holding else "AVOID"
        confidence = "HIGH"
        summary = "Rủi ro nợ và khả năng thanh toán nghiêm trọng."
        reasons.append("Doanh nghiệp đối mặt với rủi ro tài chính / kiệt quệ thanh khoản.")
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
        what_would_change.append("Doanh nghiệp tái cơ cấu nợ và tái lập dòng tiền kinh doanh dương.")

    # Gate 3: Personal Balance Sheet / Survival Reserve Check
    elif ctx.survival_reserve_status in ("UNSAFE", "UNSATISFACTORY", "UNKNOWN"):
        decision = "BUILD_RESERVE_FIRST"
        confidence = "HIGH"
        summary = "Doanh nghiệp hấp dẫn nhưng tài chính cá nhân chưa an toàn hoặc thiếu dữ liệu. Cần hoàn thiện dự phòng."
        reasons.append("Quỹ dự phòng an toàn cá nhân / dữ liệu tài chính chưa đạt tiêu chí an toàn.")
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
        what_would_change.append("Gia tăng tài sản thanh khoản an toàn để khôi phục quỹ dự phòng về mức SAFE.")

    # Gate 3B: Personal Balance Sheet ATTENTION
    elif ctx.survival_reserve_status == "ATTENTION":
        decision = "HOLD_NO_NEW_CAPITAL" if is_existing_holding else "BUILD_RESERVE_FIRST"
        confidence = "HIGH"
        summary = "Tài chính cá nhân ở trạng thái Cảnh Báo (ATTENTION). Cấm mở vị thế mua mới / giải ngân thêm vốn."
        reasons.append("Quỹ dự phòng cá nhân ở mức ATTENTION (cảnh báo). Cấm mua mới / mua thêm.")
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
        what_would_change.append("Tích lũy quỹ dự phòng an toàn về mức SAFE.")


    # Gate 4: Business Review Quality Failure
    elif ctx.business_review_status == "BUSINESS_FAIL":
        decision = "SELL_REVIEW" if is_existing_holding else "AVOID"
        confidence = "HIGH"
        summary = "Mô hình kinh doanh không đạt tiêu chí chất lượng tối thiểu."
        reasons.append("Chất lượng kinh doanh yếu kém hoặc xói mòn lợi thế cạnh tranh.")
        what_would_change.append("Doanh nghiệp tái lập biên lợi nhuận và lợi thế cạnh tranh bền vững.")

    # Gate 5: Value Trap High Risk
    elif ctx.value_trap_status == "HIGH_RISK":
        decision = "REVIEW_BUSINESS" if is_existing_holding else "AVOID"
        confidence = "HIGH"
        summary = "Cổ phiếu có dấu hiệu bẫy giá trị (Value Trap) do suy giảm nội tại cấu trúc."
        reasons.append("Giá rẻ nhưng lợi nhuận suy giảm cấu trúc hoặc dòng tiền phân kỳ nghiêm trọng.")
        what_would_change.append("Dòng tiền CFO phục hồi xác nhận lợi nhuận thực tế.")

    # Gate 5B: Value Trap Watch
    elif ctx.value_trap_status == "WATCH":
        decision = "REVIEW_BUSINESS" if is_existing_holding else "WAIT_FOR_MOS"
        confidence = "MEDIUM"
        summary = "Cổ phiếu thuộc danh sách theo dõi bẫy giá trị (ValueTrap WATCH). Không cho phép mở vị thế mua mới."
        reasons.append("Trạng thái bẫy giá trị ở mức WATCH (theo dõi). Mua mới bị cấm.")
        what_would_change.append("Xác nhận dòng tiền kinh doanh và đưa trạng thái bẫy giá trị về CLEAR.")

    # Gate 5C: Value Trap Insufficient Data
    elif ctx.value_trap_status == "INSUFFICIENT_DATA":
        decision = "HOLD" if is_existing_holding else "WAIT_FOR_MOS"
        confidence = "LOW"
        summary = "Dữ liệu chưa đủ để kết luận bẫy giá trị (INSUFFICIENT_DATA). Mua mới mặc định bị cấm."
        reasons.append("Thiếu dữ liệu để xác nhận Value Trap CLEAR.")
        what_would_change.append("Bổ sung dữ liệu tài chính lịch sử để hoàn thiện đánh giá Value Trap.")

    # Gate 5D: Data Readiness Blocked Gate (P0-1)
    elif (
        ctx.data_readiness.get("financial_core") == "BLOCKED"
        or ctx.data_readiness.get("valuation") == "BLOCKED"
        or ctx.data_readiness.get("personal_finance") == "BLOCKED"
        or ctx.data_readiness.get("business_review") == "BLOCKED"
        or ctx.data_readiness.get("value_trap") == "BLOCKED"
    ):
        decision = "HOLD" if is_existing_holding else "WAIT_FOR_MOS"
        confidence = "LOW"
        summary = "Dữ liệu chưa đạt trạng thái sẵn sàng (Data Readiness BLOCKED). Mua mới / mua thêm bị cấm."
        reasons.append("Trạng thái sẵn sàng dữ liệu bị khóa (BLOCKED). Mua mới bị cấm.")
        rules.append(
            DecisionRuleTrigger(
                rule_id="R-00-DATA-READINESS-BLOCKED",
                metric="data_readiness",
                value=str(ctx.data_readiness),
                threshold="READY",
                status="TRIGGERED",
                source="context_builder",
                description="Trạng thái sẵn sàng dữ liệu chưa đạt yêu cầu.",
            )
        )
        what_would_change.append("Hoàn thiện dữ liệu báo cáo tài chính và định giá để đưa readiness về READY.")

    # Gate 6: Invalid Valuation or Base IV Unavailable
    elif ctx.model_status not in ("VALID", "VERIFIED", "MODEL_VERIFIED") or ctx.base_iv is None or ctx.base_iv <= 0:
        decision = "WAIT_FOR_MOS" if not is_existing_holding else "HOLD"
        confidence = "LOW"
        summary = "Mô hình định giá chưa hoàn chỉnh hoặc chưa đủ dữ liệu giá trị nội tại."
        reasons.append("Thiếu định giá Base IV hợp lệ.")
        what_would_change.append("Cập nhật đầy đủ BCTC để tính toán định giá Base IV.")

    # Gate 7: Price above acceptable MOS Entry Value
    elif (
        ctx.current_price > 0
        and ctx.base_iv is not None
        and ctx.base_iv > 0
        and ctx.current_price > (ctx.base_iv * (1.0 - (ctx.required_mos if ctx.required_mos is not None else 15.0) / 100.0))
    ):
        decision = "WAIT_FOR_MOS"
        confidence = "HIGH" if ctx.valuation_confidence == "HIGH" else "MEDIUM"
        summary = "Doanh nghiệp tốt nhưng giá thị trường chưa tiệm cận Biên an toàn (Margin of Safety) yêu cầu."
        reasons.append(f"Giá thị trường ({ctx.current_price:,.0f}) cao hơn mức mua an toàn (Base IV: {ctx.base_iv:,.0f}).")
        what_would_change.append("Thị trường điều chỉnh về mức Biên an toàn yêu cầu hoặc IV tăng trưởng.")

    # Gate 8: Position Capacity Exceeded
    elif is_existing_holding and ctx.current_weight >= 0.35:
        decision = "HOLD_NO_NEW_CAPITAL"
        confidence = "HIGH"
        summary = "Doanh nghiệp tốt và định giá hợp lý, nhưng vị thế đã đạt ngưỡng giới hạn tỷ trọng danh mục (35%)."
        reasons.append("Tỷ trọng vị thế hiện tại đã đạt trần chính sách danh mục.")
        what_would_change.append("Tỷ trọng vị thế giảm xuống dưới 30% NAV do biến động hoặc tăng NAV.")

    # Gate 9: Fully Qualified BUY / BUY_MORE
    elif (
        ctx.business_review_status in ("BUSINESS_PASS", "PASS")
        and ctx.value_trap_status == "CLEAR"
        and ctx.survival_reserve_status == "SAFE"
        and ctx.available_long_term_capital > 0
        and ctx.data_readiness.get("financial_core", "READY") != "BLOCKED"
        and ctx.data_readiness.get("valuation", "READY") != "BLOCKED"
        and ctx.data_readiness.get("personal_finance", "READY") != "BLOCKED"
        and ctx.data_readiness.get("business_review", "READY") != "BLOCKED"
        and ctx.data_readiness.get("value_trap", "READY") != "BLOCKED"
    ):
        decision = "BUY_MORE" if is_existing_holding else "BUY"
        confidence = "HIGH" if ctx.valuation_confidence == "HIGH" else "MEDIUM"
        summary = "Doanh nghiệp chất lượng cao, Biên an toàn hấp dẫn, vốn cá nhân bền vững."
        reasons.append("Hội đủ tất cả các điều kiện chất lượng, định giá và nguồn vốn dài hạn.")
        what_would_change.append("Giá thị trường tăng vượt Base IV hoặc vị thế đạt trần tỷ trọng.")

    # Default Gate: HOLD / NO ACTION REQUIRED
    else:
        decision = "HOLD"
        confidence = "MEDIUM"
        summary = "Tài sản lành mạnh. Chưa có cơ hội mở rộng vị thế mới. Không cần hành động."
        reasons.append("Doanh nghiệp hoạt động bình thường, không có dấu hiệu suy thoái.")
        what_would_change.append("Giá cổ phiếu chiết khấu sâu hơn hoặc có biến động nội tại.")


    return DecisionEvidence(
        symbol=ctx.symbol,
        decision=decision,
        confidence=confidence,
        summary=summary,
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
