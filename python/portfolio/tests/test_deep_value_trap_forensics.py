import re
import pytest
from portfolio.value_engine.value_trap import evaluate_value_trap


FORBIDDEN_PATTERNS = [
    re.compile(r"\b[A-Z][A-Z0-9_]{5,}\b"),  # Raw internal uppercase enums
    re.compile(r"nullx", re.IGNORECASE),
    re.compile(r"undefined", re.IGNORECASE),
]

ALLOWED_ACRONYMS = {
    "CAGR", "ROE", "ROIC", "ROA", "CFO", "FCF", "PAT", "PBT", "EBIT", "EBITDA",
    "EPS", "DSO", "DIO", "DPO", "CCC", "MOS", "VND", "SSI", "FPT", "DGC", "ACB",
    "VIX", "BCTC", "LNST", "LNTT", "LNHĐ", "VCSH", "GTSB", "CTCK", "NHTM", "SBV",
}


def _check_no_enum_leaks(data, path=""):
    leaks = []
    if isinstance(data, dict):
        for k, v in data.items():
            leaks.extend(_check_no_enum_leaks(v, f"{path}.{k}"))
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            leaks.extend(_check_no_enum_leaks(item, f"{path}[{idx}]"))
    elif isinstance(data, str):
        # Check forbidden patterns in human-facing text
        if any(token in path.lower() for token in ["_vi", "narrative", "explanation", "conclusion", "reason", "evidence", "impact"]):
            for match in FORBIDDEN_PATTERNS[0].findall(data):
                if match not in ALLOWED_ACRONYMS and not re.match(r"^FY\d{4}$", match):
                    leaks.append(f"{path}: Leaked raw enum '{match}' in string: '{data}'")
            for pat in FORBIDDEN_PATTERNS[1:]:
                if pat.search(data):
                    leaks.append(f"{path}: Contains forbidden phrase in string: '{data}'")
    return leaks


def test_golden_symbols_deep_value_trap_forensics():
    """Verify deep value trap forensics across golden tickers FPT, DGC, ACB, VIX."""
    symbols = ["FPT", "DGC", "ACB", "VIX"]

    for sym in symbols:
        res = evaluate_value_trap(sym)
        d = res.to_dict()

        # 1. Mandatory 14-item scorecard
        scorecard = d.get("scorecard", [])
        assert len(scorecard) == 14, f"{sym} scorecard must have exactly 14 items, got {len(scorecard)}"
        for item in scorecard:
            assert item.get("index") in range(1, 15)
            assert item.get("name_vi"), f"{sym} scorecard item missing name_vi"
            assert item.get("status_vi"), f"{sym} scorecard item missing status_vi"
            assert item.get("severity_vi"), f"{sym} scorecard item missing severity_vi"
            assert item.get("period_vi"), f"{sym} scorecard item missing period_vi"
            assert item.get("evidence_vi"), f"{sym} scorecard item missing evidence_vi"

        # 2. Munger Action
        action = d.get("munger_action", {})
        assert action.get("action_code") in ("BUY_WITH_MOS", "WAIT_FOR_IMPROVEMENT", "STUDY_FURTHER", "AVOID", "HOLD")
        assert action.get("action_vi")
        assert action.get("munger_rationale_vi")

        # 3. Counter-Evidence
        assert isinstance(d.get("counter_evidence"), list)

        # 4. Zero Enum Leaks in text
        leaks = _check_no_enum_leaks(d, sym)
        assert not leaks, f"Discovered {len(leaks)} enum leaks in {sym}:\n" + "\n".join(leaks)


def test_distressed_value_trap_structural_deterioration():
    """Verify high-risk detection on a simulated distressed structural value trap."""
    history = [
        {"fiscal_year": 2021, "revenue": 1000.0, "net_profit": 150.0, "cfo": 120.0, "receivables": 100.0, "inventory": 100.0, "debt": 200.0, "equity": 500.0, "roe": 30.0},
        {"fiscal_year": 2022, "revenue": 900.0, "net_profit": 100.0, "cfo": 30.0, "receivables": 180.0, "inventory": 160.0, "debt": 400.0, "equity": 520.0, "roe": 19.2},
        {"fiscal_year": 2023, "revenue": 750.0, "net_profit": 40.0, "cfo": -50.0, "receivables": 250.0, "inventory": 220.0, "debt": 650.0, "equity": 480.0, "roe": 8.3},
        {"fiscal_year": 2024, "revenue": 600.0, "net_profit": -30.0, "cfo": -100.0, "receivables": 320.0, "inventory": 280.0, "debt": 900.0, "equity": 380.0, "roe": -7.9},
        {"fiscal_year": 2025, "revenue": 500.0, "net_profit": -60.0, "cfo": -150.0, "receivables": 380.0, "inventory": 310.0, "debt": 1100.0, "equity": 280.0, "roe": -21.4},
    ]

    val_rep = {
        "current_price": 15000.0,
        "bear_iv": 8000.0,
        "base_iv": 20000.0,
        "value_investor_pillars": {
            "financial_fortress": {"status": "DANGER"},
            "earnings_quality": {"status": "FAIL"},
            "capital_allocation": {"status": "FAIL", "dilution_classification": "DESTRUCTIVE_DILUTION"},
        },
        "financial_history": history,
    }

    res = evaluate_value_trap("DISTRESSED_CO", valuation_report=val_rep, financial_history=history)
    d = res.to_dict()

    assert d["status"] == "HIGH_RISK"
    assert d["deterioration_classification"] == "STRUCTURAL_EVIDENCE"
    assert d["earnings_quality"] == "FAIL"
    assert d["cash_conversion_status"] == "DIVERGENT"
    assert d["dilution_status"] == "DESTRUCTIVE"
    assert d["munger_action"]["action_code"] == "AVOID"
    assert "Tránh" in d["munger_action"]["action_vi"]

    # Must generate structured evidence matrix and top risks
    assert len(d["evidence_matrix"]) >= 1
    assert len(d["top_risks"]) >= 1


def test_cyclical_deterioration_with_counter_evidence():
    """Verify cyclical downswing with strong fortress is classified as LIKELY_CYCLICAL or WATCH."""
    history = [
        {"fiscal_year": 2021, "revenue": 1000.0, "net_profit": 300.0, "cfo": 320.0, "receivables": 50.0, "inventory": 80.0, "debt": 50.0, "cash": 500.0, "equity": 1000.0, "roe": 30.0},
        {"fiscal_year": 2022, "revenue": 1200.0, "net_profit": 380.0, "cfo": 400.0, "receivables": 60.0, "inventory": 90.0, "debt": 40.0, "cash": 700.0, "equity": 1300.0, "roe": 29.2},
        {"fiscal_year": 2023, "revenue": 1100.0, "net_profit": 200.0, "cfo": 180.0, "receivables": 65.0, "inventory": 95.0, "debt": 30.0, "cash": 800.0, "equity": 1450.0, "roe": 13.8},
        {"fiscal_year": 2024, "revenue": 950.0, "net_profit": 150.0, "cfo": 140.0, "receivables": 70.0, "inventory": 100.0, "debt": 20.0, "cash": 900.0, "equity": 1550.0, "roe": 9.7},
        {"fiscal_year": 2025, "revenue": 1150.0, "net_profit": 280.0, "cfo": 310.0, "receivables": 72.0, "inventory": 105.0, "debt": 10.0, "cash": 1100.0, "equity": 1780.0, "roe": 15.7},
    ]

    val_rep = {
        "current_price": 25000.0,
        "bear_iv": 22000.0,
        "base_iv": 35000.0,
        "value_investor_pillars": {
            "financial_fortress": {"status": "FORTRESS"},
            "earnings_quality": {"status": "GOOD", "avg_cash_conversion_5y": 1.05},
            "capital_allocation": {"status": "EXCELLENT", "dilution_classification": "STABLE"},
        },
        "financial_history": history,
    }

    res = evaluate_value_trap("CYCLICAL_LEADER", valuation_report=val_rep, financial_history=history)
    d = res.to_dict()

    assert d["status"] in ("CLEAR", "WATCH")
    assert d["deterioration_classification"] in ("NO_DETERIORATION", "LIKELY_CYCLICAL")
    assert any("tiền mặt" in c.lower() for c in d["counter_evidence"])


def test_bank_and_securities_archetype_isolation():
    """Verify banks and securities are not penalized with inapplicable working capital / inventory checks."""
    for sym in ["ACB", "VIX"]:
        res = evaluate_value_trap(sym)
        d = res.to_dict()

        scorecard = d["scorecard"]
        cash_conv_item = next(item for item in scorecard if item["category"] == "CASH_CONVERSION")
        wc_item = next(item for item in scorecard if item["category"] == "WORKING_CAPITAL")
        rec_item = next(item for item in scorecard if item["category"] == "RECEIVABLES")
        inv_item = next(item for item in scorecard if item["category"] == "INVENTORY")

        assert cash_conv_item["status_code"] == "NOT_APPLICABLE"
        assert wc_item["status_code"] == "NOT_APPLICABLE"
        assert rec_item["status_code"] == "NOT_APPLICABLE"
        assert inv_item["status_code"] == "NOT_APPLICABLE"

        assert cash_conv_item["status_vi"] == "Không áp dụng"
        assert wc_item["status_vi"] == "Không áp dụng"
        assert rec_item["status_vi"] == "Không áp dụng"
        assert inv_item["status_vi"] == "Không áp dụng"
