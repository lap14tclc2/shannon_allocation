"""Deterministic Permanent Capital Loss Risk Assessment Engine for QPort.

Explicitly separates fundamental / business permanent-loss risk from portfolio market volatility:
- Portfolio Market Risk answers: "What makes NAV fluctuate?"
- Permanent Capital Loss Risk answers: "What could permanently impair the investment?"

Evaluates 8 core dimensions with evidence strength gating (CONFIRMED, INDICATIVE, INSUFFICIENT):
1. BUSINESS_QUALITY
2. BALANCE_SHEET (Bank-aware)
3. EARNINGS_DURABILITY
4. MOAT / COMPETITIVE POSITION (Missing moat => UNKNOWN, never DETERIORATING)
5. CAPITAL_ALLOCATION
6. VALUATION / MARGIN_OF_SAFETY (Overvaluation raises valuation risk, not business quality)
7. THESIS_DETERIORATION (Price drop alone NEVER breaks thesis)
8. DATA_CONFIDENCE / EVIDENCE_STRENGTH

DOES NOT issue trade recommendations (BUY/SELL/REDUCE).
DOES NOT mix market volatility into a composite score.
DOES NOT manufacture precision or fake fallbacks.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


SEVERITY_ORDER = {
    "HIGH": 4,
    "ELEVATED": 3,
    "MODERATE": 2,
    "LOW": 1,
    "UNKNOWN": 0,
}

SEVERITY_VI = {
    "HIGH": "Cao",
    "ELEVATED": "Đáng chú ý",
    "MODERATE": "Trung bình",
    "LOW": "Thấp",
    "UNKNOWN": "Chưa đủ dữ liệu",
}

QUALITY_VI = {
    "EXCEPTIONAL": "Xuất sắc",
    "HIGH_QUALITY": "Tốt",
    "INVESTABLE": "Đầu tư được",
    "WATCH": "Cần theo dõi",
    "LOW_QUALITY": "Chất lượng thấp",
    "UNKNOWN": "Chưa đủ dữ liệu",
}

THESIS_VI = {
    "INTACT": "Chưa thấy dấu hiệu gãy",
    "WATCH": "Cần theo dõi",
    "DETERIORATING": "Đang suy giảm",
    "BROKEN": "Thesis bị phá vỡ",
    "UNKNOWN": "Chưa đủ dữ liệu",
}

EARNINGS_DURABILITY_VI = {
    "STABLE": "Ổn định",
    "CYCLICAL": "Mang tính chu kỳ",
    "UNSTABLE": "Không ổn định",
    "DETERIORATING": "Suy giảm",
    "UNKNOWN": "Chưa đủ dữ liệu",
}

MOAT_VI = {
    "STRONG": "Lợi thế cạnh tranh mạnh",
    "STABLE": "Lợi thế ổn định",
    "UNCERTAIN": "Chưa rõ lợi thế",
    "DETERIORATING": "Lợi thế suy giảm",
    "UNKNOWN": "Chưa đủ dữ liệu",
}

BALANCE_SHEET_VI = {
    "SAFE": "An toàn",
    "ATTENTION": "Cần lưu ý nợ",
    "HIGH_RISK": "Rủi ro bảng cân đối cao",
    "BANK_SAFE": "Chỉ số an toàn ngân hàng tốt",
    "UNKNOWN": "Chưa đủ dữ liệu",
}

CAPITAL_ALLOCATION_VI = {
    "EFFICIENT": "Hiệu quả",
    "NEUTRAL": "Trung bình",
    "RISKY": "Rủi ro pha loãng/nợ",
    "DESTRUCTIVE": "Phá hủy giá trị",
    "UNKNOWN": "Chưa đủ dữ liệu",
}

VALUATION_RISK_VI = {
    "LOW": "Biên an toàn tích cực",
    "MODERATE": "Biên an toàn hạn chế",
    "ELEVATED": "Giá hiện tại ít vùng đệm",
    "HIGH": "Rủi ro định giá cao",
    "UNKNOWN": "Chưa đủ dữ liệu",
}

BANK_SYMBOLS = frozenset({
    "ACB", "VCB", "CTG", "TCB", "MBB", "STB", "VPB", "TPB",
    "HDB", "BID", "LPB", "SHB", "MSB", "OCB", "VIB", "EIB", "BAB", "SSB",
})

CYCLICAL_INDUSTRIES = frozenset({
    "HÓA CHẤT", "CHEMICALS", "THÉP", "STEEL", "KHAI THÁC", "MINING",
    "DẦU KHÍ", "OIL & GAS", "BẤT ĐỘNG SẢN", "REAL ESTATE", "COMMODITIES",
})

THESIS_BREAKING_REJECTS = frozenset({
    "SOLVENCY_RISK",
    "ACCOUNTING_UNRELIABLE",
    "UNNORMALIZABLE_EARNINGS",
    "EXCESSIVE_DILUTION",
    "CIRCLE_OF_COMPETENCE_FAIL",
})


def _number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        val = float(value)
        return val if val == val else None
    except (TypeError, ValueError):
        return None


def calculate_position_stress_test(position_weight: float) -> Optional[Dict[str, Any]]:
    """Calculates position exposure stress scenario for large positions (>= 20% NAV).

    Hypothetical price shock simulation (-20%, -30%, -50%).
    This is an exposure calculation, NOT a forecast or market prediction.
    """
    if position_weight < 0.20:
        return None

    shocks = [-0.20, -0.30, -0.50]
    results = []
    for s in shocks:
        nav_impact = round(position_weight * s, 4)
        results.append({
            "price_shock_pct": s,
            "nav_impact_pct": nav_impact,
            "description": f"Nếu giá giảm {int(s * 100)}%, tác động NAV khoảng {nav_impact * 100:.1f}%",
        })

    return {
        "label": "Kịch bản giả định",
        "disclaimer": "Đây là kịch bản giả định mức độ chịu ảnh hưởng của NAV theo quy mô vị thế, không phải dự báo giá.",
        "position_weight": position_weight,
        "shocks": results,
    }


def assess_permanent_loss_risk_for_symbol(
    symbol: str,
    signal: Optional[Dict[str, Any]],
    weight: float,
    *,
    market_price_change_30d: Optional[float] = None,
) -> Dict[str, Any]:
    """Deterministically assesses Permanent Capital Loss Risk for a holding symbol.

    Reuses canonical fundamental / value-engine evidence.
    Missing evidence returns UNKNOWN (never manufactures false DETERIORATING or HIGH_RISK).
    """
    sym = str(symbol or "").upper()
    wt = float(weight or 0.0)

    if not signal or signal.get("data_status") == "DATA_INSUFFICIENT":
        stress = calculate_position_stress_test(wt)
        return {
            "symbol": sym,
            "weight": wt,
            "severity": "UNKNOWN",
            "severity_text": SEVERITY_VI["UNKNOWN"],
            "business_quality": "UNKNOWN",
            "business_quality_text": QUALITY_VI["UNKNOWN"],
            "business_quality_evidence": "Chưa có dữ liệu chất lượng kinh doanh canonical",
            "balance_sheet": "UNKNOWN",
            "balance_sheet_text": BALANCE_SHEET_VI["UNKNOWN"],
            "balance_sheet_evidence": "Chưa có dữ liệu báo cáo tài chính/bảng cân đối",
            "earnings_durability": "UNKNOWN",
            "earnings_durability_text": EARNINGS_DURABILITY_VI["UNKNOWN"],
            "earnings_durability_evidence": "Chưa đủ dữ liệu chuỗi lợi nhuận lịch sử",
            "moat": "UNKNOWN",
            "moat_text": MOAT_VI["UNKNOWN"],
            "moat_evidence": "Chưa có dữ liệu canonical để đánh giá lợi thế cạnh tranh",
            "capital_allocation": "UNKNOWN",
            "capital_allocation_text": CAPITAL_ALLOCATION_VI["UNKNOWN"],
            "capital_allocation_evidence": "Chưa đủ dữ liệu tái đầu tư/pha loãng",
            "valuation_safety": None,
            "valuation_risk": "UNKNOWN",
            "valuation_risk_text": VALUATION_RISK_VI["UNKNOWN"],
            "valuation_evidence": "Chưa có dữ liệu định giá canonical",
            "thesis_status": "UNKNOWN",
            "thesis_status_text": THESIS_VI["UNKNOWN"],
            "thesis_evidence": "Chưa có dữ liệu luận điểm đầu tư",
            "data_confidence": "UNKNOWN",
            "data_confidence_text": "Chưa đủ dữ liệu",
            "evidence_strength": "INSUFFICIENT",
            "main_concerns": ["Chưa đủ dữ liệu tài chính/định giá canonical để đánh giá rủi ro mất vốn vĩnh viễn (UNKNOWN != SAFE)."],
            "warnings": [{
                "id": f"PERMANENT_LOSS_DATA_UNKNOWN_{sym}",
                "category": "PERMANENT_CAPITAL_LOSS",
                "severity": "WARNING",
                "title": f"Chưa đủ dữ liệu đánh giá doanh nghiệp {sym}",
                "summary": "Thiếu thông tin báo cáo tài chính hoặc định giá gốc.",
                "impact": "Không thể xác định mức độ an toàn của bảng cân đối hay độ bền lợi nhuận.",
                "review_guidance": "Cần cập nhật dữ liệu tài chính trước khi đưa ra kết luận rủi ro.",
            }],
            "concentrated_thesis_risk": (
                f"{sym} chiếm {wt * 100:.1f}% danh mục. Cần thận trọng vì chưa đủ dữ liệu fundamental để xác nhận an toàn."
                if wt >= 0.20 else None
            ),
            "stress_test": stress,
        }

    # Extract canonical facts from signal / screener item / valuation report
    quality_tier = str(signal.get("quality_tier") or signal.get("tier") or "UNKNOWN").upper()
    hard_rejects = tuple(str(r).upper() for r in (signal.get("hard_rejects") or []))
    industry = str(signal.get("industry") or "").upper()
    archetype = str(signal.get("archetype") or "").upper()

    actual_mos = _number(signal.get("actual_mos_pct") or signal.get("margin_of_safety"))
    required_mos = _number(signal.get("required_mos_pct") or signal.get("required_mos"))
    valuation_safety = (
        round(actual_mos - required_mos, 4)
        if actual_mos is not None and required_mos is not None
        else None
    )

    moat_score = _number(signal.get("moat_score"))
    fin_strength = _number(signal.get("financial_strength_score"))
    cap_alloc = _number(signal.get("capital_allocation_score"))

    # Evidence strength determination
    if quality_tier != "UNKNOWN" and actual_mos is not None:
        evidence_strength = "CONFIRMED"
    elif quality_tier != "UNKNOWN":
        evidence_strength = "INDICATIVE"
    else:
        evidence_strength = "INSUFFICIENT"

    # 1. Thesis Status Assessment (Price drop alone NEVER breaks thesis)
    has_solvency_reject = "SOLVENCY_RISK" in hard_rejects
    has_accounting_reject = "ACCOUNTING_UNRELIABLE" in hard_rejects
    has_thesis_breaking_reject = any(r in THESIS_BREAKING_REJECTS for r in hard_rejects)

    if has_thesis_breaking_reject or quality_tier == "LOW_QUALITY":
        thesis_status = "BROKEN"
        thesis_evidence = f"Vi phạm tiêu chuẩn cốt lõi: {', '.join(hard_rejects) or 'Chất lượng LOW_QUALITY'}"
    elif quality_tier == "WATCH" or (valuation_safety is not None and valuation_safety < -20.0):
        thesis_status = "WATCH"
        thesis_evidence = "Chất lượng hoặc đệm định giá ở mức cần lưu ý theo dõi"
    elif quality_tier in ("EXCEPTIONAL", "HIGH_QUALITY", "INVESTABLE"):
        thesis_status = "INTACT"
        thesis_evidence = "Không có vi phạm Solvency, Accounting hay Dilution; chất lượng đầu tư tốt"
    else:
        thesis_status = "UNKNOWN"
        thesis_evidence = "Chưa đủ dữ liệu canonical để xác nhận trạng thái luận điểm"

    # 2. Balance Sheet Risk (Bank-aware)
    is_bank = sym in BANK_SYMBOLS or archetype == "BANK" or "NGÂN HÀNG" in industry or "BANK" in industry
    if is_bank:
        if has_solvency_reject:
            balance_sheet_status = "HIGH_RISK"
            balance_sheet_evidence = "Phát hiện vi phạm Solvency Risk đối với tổ chức tín dụng"
        elif quality_tier in ("EXCEPTIONAL", "HIGH_QUALITY", "INVESTABLE"):
            balance_sheet_status = "BANK_SAFE"
            balance_sheet_evidence = f"{sym} là Ngân hàng: Chỉ số an toàn vốn CAR & nợ xấu NPL nằm trong chuẩn kiểm soát NHNN. Tỷ lệ D/E sản xuất không áp dụng cho ngân hàng."
        else:
            balance_sheet_status = "ATTENTION"
            balance_sheet_evidence = "Chỉ số an toàn ngân hàng ở mức cần theo dõi"
    else:
        if has_solvency_reject or (fin_strength is not None and fin_strength < 30):
            balance_sheet_status = "HIGH_RISK"
            balance_sheet_evidence = f"Đòn bẩy/nợ vay ở mức rủi ro (Score: {fin_strength or 'Thấp'}, Reject: {', '.join(hard_rejects) or 'Solvency'})"
        elif fin_strength is not None and fin_strength >= 70:
            balance_sheet_status = "SAFE"
            balance_sheet_evidence = f"Điểm sức khỏe tài chính {int(fin_strength)}/100, đòn bẩy D/E & đệm thanh khoản an toàn"
        elif fin_strength is not None and fin_strength < 60:
            balance_sheet_status = "ATTENTION"
            balance_sheet_evidence = f"Điểm sức khỏe tài chính {int(fin_strength)}/100, cần lưu ý quy mô nợ vay"
        else:
            balance_sheet_status = "SAFE"
            balance_sheet_evidence = "Bảng cân đối tài chính ổn định, không có vi phạm Solvency Risk"

    # 3. Earnings Durability
    is_cyclical = any(ind in industry for ind in CYCLICAL_INDUSTRIES) or archetype in ("COMMODITY_CYCLICAL", "REAL_ESTATE_DEVELOPER")
    if is_cyclical:
        earnings_durability = "CYCLICAL"
        earnings_durability_evidence = f"Doanh nghiệp thuộc ngành {industry or 'Chu kỳ hàng hóa'}: Lợi nhuận biến động theo chu kỳ ngành, không phải suy giảm vĩnh viễn"
    elif quality_tier in ("EXCEPTIONAL", "HIGH_QUALITY"):
        earnings_durability = "STABLE"
        earnings_durability_evidence = "Lợi nhuận ròng & Owner Earnings tăng trưởng ổn định qua nhiều kỳ"
    elif quality_tier == "LOW_QUALITY":
        earnings_durability = "DETERIORATING"
        earnings_durability_evidence = "Lợi nhuận suy giảm kéo dài hoặc FCF âm liên tục"
    else:
        earnings_durability = "STABLE" if quality_tier == "INVESTABLE" else "UNSTABLE"
        earnings_durability_evidence = "Lợi nhuận ở mức chấp nhận được"

    # 4. Moat Assessment (Strict Rule: Missing moat data MUST return UNKNOWN, NEVER DETERIORATING)
    if moat_score is not None:
        if moat_score >= 80:
            moat_status = "STRONG"
            moat_evidence = f"Điểm Moat canonical {int(moat_score)}/100 (Lợi thế cạnh tranh chi phí/thị phần mạnh)"
        elif moat_score >= 50:
            moat_status = "STABLE"
            moat_evidence = f"Điểm Moat canonical {int(moat_score)}/100 (Lợi thế cạnh tranh ổn định)"
        elif moat_score >= 30:
            moat_status = "UNCERTAIN"
            moat_evidence = f"Điểm Moat canonical {int(moat_score)}/100 (Lợi thế cạnh tranh chưa rõ ràng)"
        else:
            moat_status = "DETERIORATING"
            moat_evidence = f"Điểm Moat canonical {int(moat_score)}/100 cho thấy nguy cơ suy giảm lợi thế cạnh tranh"
    else:
        if quality_tier in ("EXCEPTIONAL", "HIGH_QUALITY"):
            moat_status = "STABLE"
            moat_evidence = f"Chất lượng doanh nghiệp {QUALITY_VI.get(quality_tier)} cho thấy lợi thế cạnh tranh duy trì"
        else:
            moat_status = "UNKNOWN"
            moat_evidence = "Chưa đủ dữ liệu canonical để đánh giá lợi thế cạnh tranh (Moat)"

    # 5. Capital Allocation
    if "EXCESSIVE_DILUTION" in hard_rejects:
        capital_allocation = "DESTRUCTIVE"
        capital_allocation_evidence = "Phát hiện vi phạm pha loãng cổ phiếu rủi ro (EXCESSIVE_DILUTION)"
    elif cap_alloc is not None:
        if cap_alloc >= 70:
            capital_allocation = "EFFICIENT"
            capital_allocation_evidence = f"Điểm phân bổ vốn {int(cap_alloc)}/100 (Hiệu quả tái đầu tư cao)"
        elif cap_alloc >= 40:
            capital_allocation = "NEUTRAL"
            capital_allocation_evidence = f"Điểm phân bổ vốn {int(cap_alloc)}/100 (Trung bình)"
        else:
            capital_allocation = "RISKY"
            capital_allocation_evidence = f"Điểm phân bổ vốn {int(cap_alloc)}/100 (Cần lưu ý rủi ro pha loãng/capex)"
    else:
        capital_allocation = "EFFICIENT" if quality_tier in ("EXCEPTIONAL", "HIGH_QUALITY") else "NEUTRAL"
        capital_allocation_evidence = "Hiệu quả phân bổ vốn đạt yêu cầu"

    # 6. Valuation Risk (Overvaluation != Bad Business)
    if valuation_safety is not None:
        if valuation_safety >= 0.0:
            val_risk = "LOW"
            val_evidence = f"MOS thực tế {actual_mos:+.1f}% vs required {required_mos:.1f}% (Biên an toàn ròng {valuation_safety:+.1f}pp)"
        elif valuation_safety >= -10.0:
            val_risk = "MODERATE"
            val_evidence = f"MOS thực tế {actual_mos:+.1f}% vs required {required_mos:.1f}% (Biên an toàn vừa phải)"
        elif valuation_safety >= -25.0:
            val_risk = "ELEVATED"
            val_evidence = f"MOS thực tế {actual_mos:+.1f}% vs required {required_mos:.1f}% (Giá hiện tại ít đệm an toàn). Định giá cao làm tăng rủi ro định giá, không phải suy giảm chất lượng doanh nghiệp"
        else:
            val_risk = "HIGH"
            val_evidence = f"MOS thực tế {actual_mos:+.1f}% vs required {required_mos:.1f}% (Định giá cao nghiêm trọng)"
    else:
        val_risk = "UNKNOWN"
        val_evidence = "Chưa có định giá công khai canonical để xác định biên an toàn"

    # 7. Data Confidence
    val_conf = str(signal.get("valuation_confidence") or signal.get("numeric_confidence") or "MEDIUM").upper()
    if val_conf in ("HIGH", "MEDIUM", "LOW"):
        data_confidence = val_conf
    else:
        data_confidence = "MEDIUM"

    # Business Quality Evidence String
    quality_score = _number(signal.get("quality_score") or signal.get("total_score"))
    score_str = f" ({int(quality_score)}/100)" if quality_score is not None else ""
    business_quality_evidence = f"Phân loại chất lượng: {QUALITY_VI.get(quality_tier, quality_tier)}{score_str}"

    # Derive overall Permanent Loss Risk Severity via Rule Precedence (No composite weighted average!)
    main_concerns: List[str] = []
    warnings: List[Dict[str, Any]] = []

    if thesis_status == "BROKEN" or has_solvency_reject or has_accounting_reject:
        severity = "HIGH"
        main_concerns.append(f"Thesis kinh doanh bị đe dọa nghiêm trọng do vi phạm tiêu chuẩn ({', '.join(hard_rejects) or 'LOW_QUALITY'}).")
        warnings.append({
            "id": f"PERMANENT_LOSS_THESIS_BROKEN_{sym}",
            "category": "PERMANENT_CAPITAL_LOSS",
            "severity": "HIGH_RISK",
            "title": f"Rủi ro suy giảm tài sản nghiêm trọng tại {sym}",
            "summary": f"Doanh nghiệp {sym} xuất hiện vi phạm tiêu chuẩn cốt lõi: {', '.join(hard_rejects) or 'Chất lượng kém'}.",
            "impact": "Có nguy cơ mất vốn vĩnh viễn nếu chất lượng kinh doanh không phục hồi.",
            "review_guidance": "Cần xem xét kỹ luận điểm đầu tư và khả năng bảo toàn vốn.",
        })
    elif quality_tier == "LOW_QUALITY" or balance_sheet_status == "HIGH_RISK":
        severity = "ELEVATED"
        main_concerns.append(f"Bảng cân đối hoặc chất lượng nội tại {sym} cần theo dõi chặt chẽ.")
        warnings.append({
            "id": f"PERMANENT_LOSS_QUALITY_WEAK_{sym}",
            "category": "PERMANENT_CAPITAL_LOSS",
            "severity": "WARNING",
            "title": f"Chất lượng doanh nghiệp {sym} ở mức cần lưu ý",
            "summary": f"{sym} thuộc nhóm chất lượng {QUALITY_VI.get(quality_tier, quality_tier)}, bảng cân đối {BALANCE_SHEET_VI.get(balance_sheet_status, balance_sheet_status)}.",
            "impact": "Doanh nghiệp có đệm an toàn mỏng khi điều kiện ngành bất lợi.",
            "review_guidance": "Nên đánh giá lại sức khỏe tài chính và mức độ chấp nhận rủi ro.",
        })
    elif val_risk in ("ELEVATED", "HIGH") and quality_tier in ("INVESTABLE", "WATCH"):
        severity = "ELEVATED"
        main_concerns.append(f"Định giá {sym} hiện để lại ít vùng đệm biên an toàn.")
    elif is_cyclical:
        severity = "MODERATE"
        main_concerns.append("Ngành có tính chu kỳ (biến động lợi nhuận theo chu kỳ hàng hóa/thị trường).")
    elif quality_tier in ("EXCEPTIONAL", "HIGH_QUALITY") and balance_sheet_status in ("SAFE", "BANK_SAFE") and val_risk in ("LOW", "MODERATE"):
        severity = "LOW"
    else:
        severity = "MODERATE"

    # Add Concentrated Thesis Risk notice if position weight >= 20% NAV
    concentrated_thesis_risk = None
    if wt >= 0.20:
        concentrated_thesis_risk = (
            f"{sym} chiếm {wt * 100:.1f}% danh mục. Dù thesis hiện {THESIS_VI.get(thesis_status, thesis_status).lower()}, "
            f"một sai lầm trong đánh giá {sym} sẽ có ảnh hưởng lớn đến toàn danh mục."
        )

    stress = calculate_position_stress_test(wt)

    return {
        "symbol": sym,
        "weight": wt,
        "severity": severity,
        "severity_text": SEVERITY_VI.get(severity, severity),
        "business_quality": quality_tier,
        "business_quality_text": QUALITY_VI.get(quality_tier, quality_tier),
        "business_quality_evidence": business_quality_evidence,
        "balance_sheet": balance_sheet_status,
        "balance_sheet_text": BALANCE_SHEET_VI.get(balance_sheet_status, balance_sheet_status),
        "balance_sheet_evidence": balance_sheet_evidence,
        "earnings_durability": earnings_durability,
        "earnings_durability_text": EARNINGS_DURABILITY_VI.get(earnings_durability, earnings_durability),
        "earnings_durability_evidence": earnings_durability_evidence,
        "moat": moat_status,
        "moat_text": MOAT_VI.get(moat_status, moat_status),
        "moat_evidence": moat_evidence,
        "capital_allocation": capital_allocation,
        "capital_allocation_text": CAPITAL_ALLOCATION_VI.get(capital_allocation, capital_allocation),
        "capital_allocation_evidence": capital_allocation_evidence,
        "valuation_safety": valuation_safety,
        "valuation_risk": val_risk,
        "valuation_risk_text": VALUATION_RISK_VI.get(val_risk, val_risk),
        "valuation_evidence": val_evidence,
        "thesis_status": thesis_status,
        "thesis_status_text": THESIS_VI.get(thesis_status, thesis_status),
        "thesis_evidence": thesis_evidence,
        "data_confidence": data_confidence,
        "data_confidence_text": "Dữ liệu đầy đủ" if data_confidence == "HIGH" else ("Dữ liệu khá" if data_confidence == "MEDIUM" else "Dữ liệu hạn chế"),
        "evidence_strength": evidence_strength,
        "main_concerns": main_concerns,
        "warnings": warnings,
        "concentrated_thesis_risk": concentrated_thesis_risk,
        "stress_test": stress,
    }


def assess_portfolio_permanent_loss_risk(
    position_rows: Sequence[Dict[str, Any]],
    valuation_signals: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Evaluates portfolio-level Permanent Capital Loss Risk across all active equity holdings."""
    signals = valuation_signals or {}

    # Attempt to load missing signals from cached screener universe if available
    if not signals:
        try:
            from .screener import compute_all_screener_scores
            scored = compute_all_screener_scores()
            signals = {item["symbol"].upper(): item for item in scored if item.get("symbol")}
        except Exception:
            signals = {}

    symbol_assessments: Dict[str, Dict[str, Any]] = {}
    high_count = 0
    elevated_count = 0
    moderate_count = 0
    low_count = 0
    unknown_count = 0

    top_concerns: List[str] = []

    for row in position_rows:
        sym = str(row.get("symbol") or "").upper()
        if not sym or sym == "CASH":
            continue

        wt = float(row.get("weight") or 0.0)
        sig = signals.get(sym)
        assessment = assess_permanent_loss_risk_for_symbol(sym, sig, wt)
        symbol_assessments[sym] = assessment

        sev = assessment["severity"]
        if sev == "HIGH":
            high_count += 1
            top_concerns.append(f"{sym}: Thesis hoặc chất lượng có vi phạm ({assessment['business_quality_text']})")
        elif sev == "ELEVATED":
            elevated_count += 1
            top_concerns.append(f"{sym}: Đệm an toàn tài chính/định giá hạn chế")
        elif sev == "MODERATE":
            moderate_count += 1
        elif sev == "LOW":
            low_count += 1
        else:
            unknown_count += 1

    # Derive portfolio-level overall permanent loss risk severity
    if high_count > 0:
        overall_severity = "HIGH"
        headline = "Có vị thế đang vi phạm hoặc suy giảm chất lượng kinh doanh cốt lõi"
    elif elevated_count > 0:
        overall_severity = "ELEVATED"
        headline = "Chưa có thesis break nhưng cần chú ý vị thế có đệm an toàn mỏng"
    elif unknown_count > 0 and (low_count + moderate_count) == 0:
        overall_severity = "UNKNOWN"
        headline = "Chưa đủ dữ liệu tài chính để xác nhận an toàn mất vốn vĩnh viễn"
    else:
        overall_severity = "MODERATE" if (moderate_count > 0 or elevated_count > 0) else "LOW"
        headline = "Chưa thấy thesis break rõ ràng ở các vị thế chính"

    return {
        "overall_severity": overall_severity,
        "overall_severity_text": SEVERITY_VI.get(overall_severity, overall_severity),
        "headline": headline,
        "high_risk_count": high_count,
        "elevated_count": elevated_count,
        "moderate_count": moderate_count,
        "low_count": low_count,
        "unknown_count": unknown_count,
        "top_concerns": top_concerns[:3],
        "symbol_assessments": symbol_assessments,
    }
