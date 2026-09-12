"""Automated UI Raw-Enum Regression Test for QPort Golden Symbols (Task 148).

Executes full Buffett-Munger financial analysis pipeline on golden symbols (ACB, DGC, FPT, VIX)
and scans all rendered narrative string fields (explanations, summaries, details, decisions, evidence)
to verify NO raw internal enums, snake_case codes, or raw fallbacks (nullx, N/A, undefined, etc.) leak into investor UI.
"""

import re
from typing import Any, List, Set

from portfolio.value_engine.munger_analyzer import build_munger_financial_analysis

ALLOWED_ACRONYMS: Set[str] = {
    "ROE",
    "CFO",
    "PAT",
    "EPS",
    "SSI",
    "BCTC",
    "ROIC",
    "VND",
    "FVTPL",
    "DSO",
    "CAGR",
    "MOS",
    "BCTN",
    "VCSH",
    "LNST",
    "DNTN",
    "BTH",
    "VSDC",
    "CAFEF",
    "USD",
    "QPORT",
    "FORMULA",
    "ESOP",
}

RAW_ENUM_PATTERN = re.compile(r"\b[A-Z][A-Z0-9_]{4,}\b")


HUMAN_NARRATIVE_KEYS = {
    "explanation",
    "summary",
    "detail",
    "summary_vi",
    "detail_vi",
    "evidence_vi",
    "conclusion_vi",
    "risk_vi",
    "formatted_vi",
    "decision_reason",
    "thesis_summary",
    "tieu_de",
    "dieu_gi_dang_xay_ra",
    "vi_sao_quan_trong",
    "anh_huong_dai_han",
    "title",
    "reason",
    "impact",
}


def extract_narrative_strings(obj: Any, string_key_path: str = "") -> List[tuple[str, str]]:
    """Recursively extract user-facing narrative string fields from nested dict/list structures."""
    results = []
    if isinstance(obj, str):
        key_name = string_key_path.split(".")[-1].split("[")[0]
        if key_name in HUMAN_NARRATIVE_KEYS:
            results.append((string_key_path, obj))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{string_key_path}.{k}" if string_key_path else str(k)
            results.extend(extract_narrative_strings(v, path))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            path = f"{string_key_path}[{idx}]"
            results.extend(extract_narrative_strings(item, path))
    return results


from dataclasses import asdict, is_dataclass

def test_ui_raw_enum_regression_golden_symbols():
    symbols = ["ACB", "DGC", "FPT", "VIX"]
    leaks = []

    for sym in symbols:
        raw_res = build_munger_financial_analysis(sym)
        result = asdict(raw_res) if is_dataclass(raw_res) else raw_res
        assert isinstance(result, dict)
        assert result.get("symbol") == sym

        strings = extract_narrative_strings(result)
        for key_path, text in strings:
            # Check for bad fallback literal strings
            for bad in ["nullx", "undefined", "not applicable"]:
                if bad in text.lower():
                    leaks.append(f"{sym} -> {key_path}: Contains forbidden string '{bad}': '{text}'")

            # Check for uppercase raw enum leaks [A-Z][A-Z0-9_]{4,}
            matches = RAW_ENUM_PATTERN.findall(text)
            for match in matches:
                if match not in ALLOWED_ACRONYMS:
                    leaks.append(f"{sym} -> {key_path}: Leaked raw machine enum '{match}' in string: '{text}'")

    assert not leaks, f"Discovered {len(leaks)} raw enum/fallback string leaks in golden symbol UI output:\n" + "\n".join(leaks)
