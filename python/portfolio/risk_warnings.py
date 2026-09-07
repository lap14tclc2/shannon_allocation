"""Deterministic Portfolio Risk Warning and Interpretation Engine.

Transforms canonical quantitative risk outputs into advisory risk warnings,
impact assessments, and review guidance for retail long-term investors.

DOES NOT recommend capital allocation actions or trade orders.
DOES NOT mutate ledger or portfolio state.
DOES NOT use LLM or non-deterministic AI logic.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


SEVERITY_ORDER = {
    "HIGH_RISK": 4,
    "WARNING": 3,
    "ATTENTION": 2,
    "NORMAL": 1,
}

SEVERITY_VIETNAMESE = {
    "HIGH_RISK": "Nguy cơ cao",
    "WARNING": "Cảnh báo",
    "ATTENTION": "Cần chú ý",
    "NORMAL": "Bình thường",
}


def _format_pct(val: Optional[float], decimals: int = 1) -> str:
    if val is None:
        return "N/A"
    return f"{val * 100:.{decimals}f}%"


def generate_risk_warnings(
    risk_data: Dict[str, Any],
    position_rows: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Generates a list of deterministic risk warnings and an overall summary.

    Reuses canonical outputs from `portfolio_risk()`. Does NOT recompute math.
    """
    warnings: List[Dict[str, Any]] = []
    rows = position_rows or []

    # Extract canonical metrics safely
    status = risk_data.get("status", "VALID")
    quality = risk_data.get("quality") or {}
    missing_symbols = quality.get("missing_symbols") or []
    coverage_weight = float(quality.get("coverage_weight") or 0.0)
    coverage_status = risk_data.get("risk_coverage_status", "COMPLETE")
    eligible_nav_weight = float(risk_data.get("risk_eligible_nav_weight") or 0.0)
    eligible_count = int(risk_data.get("risk_eligible_count") or 0)
    total_symbols = int(risk_data.get("risk_total_symbols") or len(rows))

    max_pos_weight = float(risk_data.get("max_position_weight") or 0.0)
    largest_pos_symbol = risk_data.get("largest_position_symbol")
    n_positions = int(risk_data.get("n_positions") or 0)
    effective_positions = risk_data.get("effective_positions")
    hhi = risk_data.get("hhi")

    risk_contribs = risk_data.get("risk_contributions") or {}
    largest_risk_symbol = risk_data.get("largest_risk_symbol")
    largest_risk_contrib = risk_data.get("largest_risk_contribution")
    equal_risk = risk_data.get("equal_risk_contribution")

    vol63 = risk_data.get("volatility_63")
    vol252 = risk_data.get("volatility_252")
    vol_ratio = risk_data.get("volatility_ratio")

    var_95 = risk_data.get("daily_var_95")
    cvar_95 = risk_data.get("daily_cvar_95")
    max_daily_loss = risk_data.get("max_daily_loss")
    max_daily_loss_date = risk_data.get("max_daily_loss_date")

    corr_matrix = risk_data.get("correlation_matrix") or {}
    avg_corr = risk_data.get("average_correlation")
    max_corr = risk_data.get("max_correlation")
    symbol_metrics = risk_data.get("symbol_metrics") or {}

    # Category 1: DATA QUALITY
    if status == "UNAVAILABLE" or coverage_status == "INSUFFICIENT":
        warnings.append({
            "id": "RISK_DATA_QUALITY_UNAVAILABLE",
            "category": "DATA_QUALITY",
            "severity": "HIGH_RISK",
            "title": "Chưa đủ dữ liệu để đánh giá rủi ro toàn danh mục",
            "summary": f"Chỉ {eligible_count}/{total_symbols} cổ phiếu ({_format_pct(eligible_nav_weight)} NAV) có đủ dữ liệu 40+ phiên giá.",
            "metric_name": "coverage_status",
            "metric_value": coverage_status,
            "threshold": "COMPLETE",
            "affected_symbols": missing_symbols,
            "evidence": {"status": status, "missing_symbols": missing_symbols, "coverage_weight": coverage_weight, "eligible_nav_weight": eligible_nav_weight},
            "impact": f"Các mã chưa đủ dữ liệu ({', '.join(missing_symbols)}) không thể tính ma trận rủi ro và tương quan. Dữ liệu chưa rõ không có nghĩa là an toàn (UNKNOWN != SAFE).",
            "review_guidance": "QPort chưa đưa ra kết luận biến động toàn danh mục. Cần cập nhật thêm lịch sử giá cho các mã thiếu.",
            "reason_codes": ["DATA_QUALITY_INSUFFICIENT"],
        })
    elif status == "PARTIAL" or len(missing_symbols) > 0:
        warnings.append({
            "id": "RISK_DATA_QUALITY_PARTIAL",
            "category": "DATA_QUALITY",
            "severity": "WARNING",
            "title": "Phân tích rủi ro chưa đầy đủ dữ liệu toàn danh mục",
            "summary": f"Có {len(missing_symbols)} mã thiếu lịch sử giá: {', '.join(missing_symbols)}.",
            "metric_name": "missing_symbols",
            "metric_value": len(missing_symbols),
            "threshold": 0,
            "affected_symbols": missing_symbols,
            "evidence": {"missing_symbols": missing_symbols, "coverage_weight": coverage_weight, "eligible_nav_weight": eligible_nav_weight},
            "impact": f"Tỷ lệ dữ liệu hiện đạt {_format_pct(eligible_nav_weight)} NAV. Dữ liệu chưa có không có nghĩa là an toàn (UNKNOWN != SAFE).",
            "review_guidance": "Nên cập nhật thêm lịch sử giá cho các mã bị thiếu để có bức tranh rủi ro đầy đủ hơn.",
            "reason_codes": ["DATA_QUALITY_PARTIAL"],
        })

    # Category 2 & 3: CONCENTRATION & RISK CONTRIBUTION (Grouped per symbol to avoid duplicates)
    symbol_concentrations: Dict[str, Dict[str, Any]] = {}
    for p in rows:
        sym = str(p.get("symbol") or "").upper()
        if not sym or sym == "CASH":
            continue
        weight = float(p.get("weight") or 0.0)
        rc = float(risk_contribs.get(sym) or 0.0)
        if weight >= 0.20 or rc >= 0.35:
            symbol_concentrations[sym] = {"weight": weight, "risk_contribution": rc}

    for sym, data in symbol_concentrations.items():
        w = data["weight"]
        rc = data["risk_contribution"]

        if w >= 0.40 or rc >= 0.45:
            sev = "HIGH_RISK"
        elif w >= 0.30 or rc >= 0.38:
            sev = "WARNING"
        else:
            sev = "ATTENTION"

        title = f"Rủi ro biến động đang tập trung vào {sym}" if (rc > w * 1.15) else f"Tỷ trọng lớn ở vị thế {sym}"
        summary = f"{sym} chiếm {_format_pct(w)} NAV và đóng góp {_format_pct(rc)} tổng biến động danh mục."
        if coverage_status != "COMPLETE":
            impact = f"Trong phần danh mục có đủ dữ liệu ({_format_pct(eligible_nav_weight)} NAV), {sym} chiếm {_format_pct(rc)} đóng góp biến động đo lường được. Con số này không đại diện cho 100% rủi ro toàn danh mục."
        else:
            impact = f"{sym} đang tạo ra khoảng {_format_pct(rc)} biến động tổng thể của danh mục. NAV có thể biến động mạnh nếu giá {sym} thay đổi đáng kể. Đây là rủi ro biến động giá, không phải kết luận về chất lượng doanh nghiệp {sym}."
        review_guidance = f"Nên kiểm tra tỷ trọng {sym}, tương quan với các mã khác và tham khảo kịch bản giả định sụt giảm giá."

        warnings.append({
            "id": f"RISK_CONCENTRATION_{sym}",
            "category": "POSITION_CONCENTRATION",
            "severity": sev,
            "title": title,
            "summary": summary,
            "metric_name": "risk_contribution" if rc > w else "equity_weight",
            "metric_value": max(w, rc),
            "threshold": 0.30 if sev in ("WARNING", "HIGH_RISK") else 0.20,
            "affected_symbols": [sym],
            "evidence": {"equity_weight": w, "risk_contribution": rc},
            "impact": impact,
            "review_guidance": review_guidance,
            "reason_codes": ["POSITION_CONCENTRATION_BREACH" if w >= 0.20 else "RISK_CONTRIBUTION_BREACH"],
        })

    # Category 4: CORRELATION CLUSTER
    high_corr_pairs: List[tuple[str, str, float]] = []
    cluster_symbols: set[str] = set()
    if corr_matrix:
        sym_list = list(corr_matrix.keys())
        for i in range(len(sym_list)):
            for j in range(i + 1, len(sym_list)):
                s1, s2 = sym_list[i], sym_list[j]
                val = corr_matrix[s1].get(s2)
                if val is not None and val >= 0.70:
                    high_corr_pairs.append((s1, s2, float(val)))
                    cluster_symbols.add(s1)
                    cluster_symbols.add(s2)

    if cluster_symbols:
        sorted_cluster = sorted(cluster_symbols)
        max_pair_val = max(p[2] for p in high_corr_pairs)
        sev = "WARNING" if (len(sorted_cluster) >= 3 or max_pair_val >= 0.80) else "ATTENTION"
        warnings.append({
            "id": "RISK_CORRELATION_CLUSTER",
            "category": "CORRELATION_CLUSTER",
            "severity": sev,
            "title": f"Cụm vị thế có tương quan cao ({', '.join(sorted_cluster)})",
            "summary": f"Các mã {', '.join(sorted_cluster)} thường biến động cùng chiều (tương quan cao nhất {max_pair_val:.2f}).",
            "metric_name": "max_correlation",
            "metric_value": max_pair_val,
            "threshold": 0.70,
            "affected_symbols": sorted_cluster,
            "evidence": {"cluster_symbols": sorted_cluster, "max_correlation": max_pair_val, "pair_count": len(high_corr_pairs)},
            "impact": "Khi thị trường biến động xấu, các mã này có xu hướng sụt giảm cùng lúc, làm giảm hiệu quả đa dạng hóa.",
            "review_guidance": "Nên kiểm tra tỷ trọng tổng của cụm này, sector exposure và số vị thế hiệu dụng.",
            "reason_codes": ["CORRELATION_CLUSTER_DETECTED"],
        })

    # Category 5: LOW EFFECTIVE DIVERSIFICATION
    if n_positions >= 3 and effective_positions is not None:
        eff_pos = float(effective_positions)
        if eff_pos < min(3.5, n_positions * 0.6) or (hhi and hhi > 0.25):
            sev = "WARNING" if eff_pos < 3.0 else "ATTENTION"
            warnings.append({
                "id": "RISK_DIVERSIFICATION_LOW",
                "category": "DIVERSIFICATION",
                "severity": sev,
                "title": "Chưa đa dạng hóa thực tế như số lượng mã",
                "summary": f"Bạn đang nắm {n_positions} cổ phiếu, nhưng mức độ tập trung thực tế chỉ tương đương khoảng {eff_pos:.1f} vị thế độc lập.",
                "metric_name": "effective_positions",
                "metric_value": eff_pos,
                "threshold": min(3.5, n_positions * 0.6),
                "affected_symbols": [largest_pos_symbol] if largest_pos_symbol else [],
                "evidence": {"n_positions": n_positions, "effective_positions": eff_pos, "hhi": hhi},
                "impact": "Mức tập trung tỷ trọng hoặc sự biến động cùng chiều khiến tác động giảm thiểu rủi ro của việc chia nhỏ danh mục bị hạn chế.",
                "review_guidance": "Kiểm tra lại số vị thế hiệu dụng, cụm tương quan và phân bổ vốn giữa các nhóm tài sản.",
                "reason_codes": ["EFFECTIVE_POSITIONS_LOW"],
            })

    # Category 6: PORTFOLIO VOLATILITY
    if vol63 is not None and vol252 is not None and vol252 > 0:
        ratio = float(vol_ratio or (vol63 / vol252))
        if ratio >= 1.25 and vol63 >= 0.18:
            sev = "WARNING" if ratio >= 1.40 else "ATTENTION"
            warnings.append({
                "id": "RISK_VOLATILITY_SPIKE",
                "category": "VOLATILITY",
                "severity": sev,
                "title": "Biến động ngắn hạn đang cao hơn nền 1 năm",
                "summary": f"Biến động 3 tháng gần đây ({_format_pct(vol63)}) cao hơn nền 1 năm ({_format_pct(vol252)}) khoảng {_format_pct(ratio - 1.0)}.",
                "metric_name": "volatility_ratio",
                "metric_value": ratio,
                "threshold": 1.25,
                "affected_symbols": [],
                "evidence": {"volatility_63": vol63, "volatility_252": vol252, "ratio": ratio},
                "impact": "Danh mục đang ở giai đoạn rung lắc mạnh hơn lịch sử trung bình.",
                "review_guidance": "Xem xét rủi ro sụt giảm ngắn hạn (VaR) và mã đóng góp rủi ro chính.",
                "reason_codes": ["PORTFOLIO_VOLATILITY_SPIKE"],
            })

    # Category 7: TAIL RISK (VaR / CVaR)
    if var_95 is not None and cvar_95 is not None:
        abs_var = abs(float(var_95))
        abs_cvar = abs(float(cvar_95))
        if abs_var >= 0.02:
            sev = "WARNING" if abs_var >= 0.035 else "ATTENTION"
            warnings.append({
                "id": "RISK_TAIL_VAR_CVAR",
                "category": "TAIL_RISK",
                "severity": sev,
                "title": "Rủi ro sụt giảm trong ngày (VaR / CVaR)",
                "summary": f"VaR 95%: {_format_pct(abs_var)}/ngày | CVaR 95%: {_format_pct(abs_cvar)}/ngày.",
                "metric_name": "daily_var_95",
                "metric_value": abs_var,
                "threshold": 0.02,
                "affected_symbols": [],
                "evidence": {"daily_var_95": var_95, "daily_cvar_95": cvar_95},
                "impact": f"Theo dữ liệu lịch sử đang dùng, khoảng 5% số ngày xấu nhất có thể có mức lỗ vượt {_format_pct(abs_var)}; trong nhóm ngày đó, mức lỗ trung bình khoảng {_format_pct(abs_cvar)}.",
                "review_guidance": "Đây là thống kê mô hình lịch sử, không phải mức lỗ tối đa có thể xảy ra. Trong các kịch bản thị trường đặc biệt xấu, sụt giảm thực tế có thể lớn hơn.",
                "reason_codes": ["VAR_TAIL_RISK_OBSERVED"],
            })

    # Category 8: WORST HISTORICAL DAY
    if max_daily_loss is not None:
        abs_worst = abs(float(max_daily_loss))
        if abs_worst >= 0.04:
            warnings.append({
                "id": "RISK_WORST_DAY_OBSERVED",
                "category": "WORST_DAY",
                "severity": "ATTENTION",
                "title": "Từng có phiên sụt giảm mạnh trong lịch sử",
                "summary": f"Danh mục từng có phiên giảm {_format_pct(abs_worst)} vào ngày {max_daily_loss_date or 'trước đó'}.",
                "metric_name": "max_daily_loss",
                "metric_value": abs_worst,
                "threshold": 0.04,
                "affected_symbols": [],
                "evidence": {"max_daily_loss": max_daily_loss, "max_daily_loss_date": max_daily_loss_date},
                "impact": "Tổn thất thực tế trong một phiên giao dịch có thể lớn hơn mức VaR ước tính trung bình.",
                "review_guidance": "Cần chuẩn bị tâm lý và khả năng tài chính cho các phiên rung lắc mạnh tương tự.",
                "reason_codes": ["WORST_DAILY_LOSS_OBSERVED"],
            })

    # Category 9: SECTOR CONCENTRATION
    sector_weights: Dict[str, float] = {}
    sector_symbols: Dict[str, List[str]] = {}
    for p in rows:
        sym = str(p.get("symbol") or "").upper()
        sec = str(p.get("sector") or p.get("industry") or "").strip()
        if sym and sym != "CASH" and sec:
            w = float(p.get("weight") or 0.0)
            sector_weights[sec] = sector_weights.get(sec, 0.0) + w
            sector_symbols.setdefault(sec, []).append(sym)

    for sec, w in sector_weights.items():
        if w >= 0.40:
            syms = sector_symbols.get(sec, [])
            sev = "WARNING" if w >= 0.50 else "ATTENTION"
            warnings.append({
                "id": f"RISK_SECTOR_{sec.upper().replace(' ', '_')}",
                "category": "SECTOR_CONCENTRATION",
                "severity": sev,
                "title": f"Cảnh báo tập trung ngành ({sec})",
                "summary": f"Hơn {_format_pct(w)} NAV nằm trong ngành {sec} ({', '.join(syms)}).",
                "metric_name": "sector_weight",
                "metric_value": w,
                "threshold": 0.40,
                "affected_symbols": syms,
                "evidence": {"sector": sec, "weight": w, "symbols": syms},
                "impact": "Nhiều mã khác nhau không đồng nghĩa với đa dạng hóa nếu các mã đó cùng chịu rủi ro chung của một ngành.",
                "review_guidance": "Nên xem thêm tương quan và sự đóng góp rủi ro của các cổ phiếu cùng ngành.",
                "reason_codes": ["SECTOR_CONCENTRATION_BREACH"],
            })

    # Category 10: CASH CONCENTRATION (Informational)
    cash_row = next((p for p in rows if str(p.get("symbol") or "").upper() == "CASH"), None)
    if cash_row:
        cash_weight = float(cash_row.get("weight") or 0.0)
        if cash_weight >= 0.30:
            warnings.append({
                "id": "RISK_CASH_HIGH",
                "category": "CASH_CONCENTRATION",
                "severity": "NORMAL",
                "title": "Tỷ trọng tiền mặt lớn",
                "summary": f"{_format_pct(cash_weight)} danh mục đang ở tiền mặt.",
                "metric_name": "cash_weight",
                "metric_value": cash_weight,
                "threshold": 0.30,
                "affected_symbols": ["CASH"],
                "evidence": {"cash_weight": cash_weight},
                "impact": "Giữ nhiều tiền mặt giúp giảm rung lắc tổng thể nhưng cũng làm giảm mức độ tham gia vào thị trường.",
                "review_guidance": "Có thể tham khảo trang Phân bổ vốn để xem cơ hội đầu tư phù hợp khi muốn giải ngân.",
                "reason_codes": ["CASH_CONCENTRATION_INFORMATIONAL"],
            })

    # Sort warnings deterministically by severity rank and category priority
    warnings.sort(key=lambda w: (
        -SEVERITY_ORDER.get(w["severity"], 0),
        w["id"]
    ))

    # Compute overall summary
    highest_sev = "NORMAL"
    for w in warnings:
        if SEVERITY_ORDER.get(w["severity"], 0) > SEVERITY_ORDER.get(highest_sev, 0):
            highest_sev = w["severity"]

    high_risk_count = sum(1 for w in warnings if w["severity"] == "HIGH_RISK")
    warning_count = sum(1 for w in warnings if w["severity"] == "WARNING")

    if highest_sev == "HIGH_RISK":
        headline = "Danh mục có yếu tố rủi ro cao cần chú ý kỹ"
    elif highest_sev == "WARNING":
        headline = "Cần chú ý các điểm rủi ro tập trung"
    elif highest_sev == "ATTENTION":
        headline = "Có một số điểm biến động cần theo dõi"
    else:
        headline = "Chưa có cảnh báo rủi ro đáng kể"

    top_concerns = [w["title"] for w in warnings if w["severity"] in ("HIGH_RISK", "WARNING")][:3]
    if not top_concerns and warnings:
        top_concerns = [w["title"] for w in warnings[:3]]

    risk_summary = {
        "overall_severity": highest_sev,
        "overall_severity_text": SEVERITY_VIETNAMESE.get(highest_sev, highest_sev),
        "headline": headline,
        "total_warning_count": len(warnings),
        "high_risk_count": high_risk_count,
        "warning_count": warning_count,
        "top_concerns": top_concerns,
    }

    return {
        "summary": risk_summary,
        "warnings": warnings,
    }
