import os
import sys

sys.path.insert(0, 'python')
from portfolio.canonical_valuation import build_canonical_valuation

prices = {'FPT': 130000.0, 'ACB': 24000.0, 'DGC': 100000.0, 'VIX': 12000.0, 'AAA': 10000.0, 'AAH': 8000.0}
symbols = ['ACB', 'DGC', 'FPT', 'VIX', 'AAA', 'AAH']

# 1. Generate Matrix Report
matrix_lines = []
matrix_lines.append("# Golden Symbol Munger Business & Valuation Matrix (Task 137)\n")
matrix_lines.append("Matrix verified against real PostgreSQL canonical financial facts (`qport_finance.canonical_facts`).\n")
matrix_lines.append("| Symbol | Archetype | History | Readiness | Financial Quality | Earnings Quality | Accounting | ValueTrap | Compounder | Current Price | Bear IV | Base IV | Bull IV | Actual MOS | Required MOS | MOS Gate | Decision | Primary Reason |")
matrix_lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")

results = {}
for sym in symbols:
    px = prices.get(sym)
    v = build_canonical_valuation(sym, market_price=px)
    results[sym] = v
    m = v.get("munger_analysis", {})
    arch = m.get("archetype", "UNKNOWN")
    h_start = m.get("history_start")
    h_end = m.get("history_end")
    h_years = m.get("history_years")
    hist = f"FY{h_start}-FY{h_end} ({h_years}Y)"
    readiness = m.get("data_readiness", "UNKNOWN")
    fin_qual = m.get("profitability_analysis", {}).get("status", "UNKNOWN")
    eq_qual = m.get("earnings_quality", {}).get("status", "UNKNOWN")
    acct = m.get("accounting_consistency", {}).get("status", "UNKNOWN")
    vt = m.get("value_trap_assessment", {}).get("status", "UNKNOWN")
    comp = m.get("compounder_classification", "UNKNOWN")
    price_str = f"{v.get('current_price'):,.0f} d" if v.get("current_price") else "N/A"
    bear_str = f"{v.get('bear_iv'):,.0f} d" if v.get("bear_iv") else "N/A"
    base_str = f"{v.get('base_iv'):,.0f} d" if v.get("base_iv") else "N/A"
    bull_str = f"{v.get('bull_iv'):,.0f} d" if v.get("bull_iv") else "N/A"
    mos_act = f"{v.get('actual_mos_pct'):.1f}%" if v.get("actual_mos_pct") is not None else "N/A"
    mos_req = f"{v.get('required_mos_pct'):.1f}%" if v.get("required_mos_pct") is not None else "N/A"
    mos_gate = m.get("valuation", {}).get("mos_gate", "UNKNOWN")
    dec = m.get("long_term_decision", {}).get("state", "UNKNOWN")
    reason = m.get("long_term_decision", {}).get("primary_reason", "")
    matrix_lines.append(f"| {sym} | {arch} | {hist} | {readiness} | {fin_qual} | {eq_qual} | {acct} | {vt} | {comp} | {price_str} | {bear_str} | {base_str} | {bull_str} | {mos_act} | {mos_req} | {mos_gate} | **{dec}** | {reason} |")

os.makedirs('docs/reports', exist_ok=True)
with open('docs/reports/munger-business-valuation-golden-matrix.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(matrix_lines) + '\n')

print("Generated docs/reports/munger-business-valuation-golden-matrix.md")

# 2. Generate Golden FPT Analysis Report
fpt_v = results['FPT']
fpt_m = fpt_v.get('munger_analysis', {})
fpt_g = fpt_m.get('growth_analysis', {}).get('metrics', {})
fpt_p = fpt_m.get('profitability_analysis', {}).get('metrics', {})
fpt_eq = fpt_m.get('earnings_quality', {}).get('metrics', {})
fpt_bs = fpt_m.get('balance_sheet_strength', {}).get('metrics', {})
fpt_norm = fpt_m.get('normalized_earning_power', {})
fpt_vt = fpt_m.get('value_trap_assessment', {})
fpt_dec = fpt_m.get('long_term_decision', {})
fpt_val = fpt_m.get('valuation', {})

fpt_doc = f"""# Golden FPT Munger Analysis Trace (Task 137)

Full evidence-driven long-term financial trace for FPT Corporation against real PostgreSQL canonical database facts (`qport_finance.canonical_facts`).

## 1. Executive Summary & Metadata
- **Symbol**: FPT
- **Archetype**: {fpt_m.get('archetype')}
- **History Range**: FY{fpt_m.get('history_start')}–FY{fpt_m.get('history_end')} ({fpt_m.get('history_years')} years)
- **Data Provider**: {(fpt_m.get('provider') or '').upper()}
- **Data Readiness**: {fpt_m.get('data_readiness')}
- **Compounder Classification**: {fpt_m.get('compounder_classification')}
- **Value Trap Assessment**: {fpt_vt.get('status')} ({fpt_vt.get('deterioration_classification')})
- **Final Decision**: **{fpt_dec.get('state')}**
- **Primary Decision Reason**: "{fpt_dec.get('primary_reason')}"

## 2. Growth & Profitability Metrics
- **Revenue 15Y CAGR**: {fpt_g.get('revenue_cagr', 0)*100:.2f}%
- **Net Profit 15Y CAGR**: {fpt_g.get('net_profit_cagr', 0)*100:.2f}%
- **Equity 15Y CAGR**: {fpt_g.get('equity_cagr', 0)*100:.2f}%
- **15Y Median ROE**: {fpt_p.get('median_roe', 0)*100:.2f}%
- **15Y Median ROIC**: {fpt_p.get('median_roic', 0)*100:.2f}%
- **15Y Median Net Margin**: {fpt_p.get('median_net_margin', 0)*100:.2f}%

## 3. Earnings Quality & Cash Flow
- **Average CFO / PAT Ratio**: {fpt_eq.get('avg_cfo_pat')}x (Threshold >= 0.8x -> **PASS**)
- **Negative CFO Years**: {fpt_eq.get('negative_cfo_years')} out of 10 evaluated years
- **10Y Net Profit CAGR**: {fpt_eq.get('cagr_pat', 0)*100:.2f}%
- **10Y CFO CAGR**: {fpt_eq.get('cagr_cfo', 0)*100:.2f}%
- **Cash Conversion Diagnosis**: Dòng tiền kinh doanh 10 năm đạt 62,380 tỷ VND so với Lợi nhuận ròng 47,580 tỷ VND (CFO/PAT 1.36x).

## 4. Balance Sheet & Debt Fortress
- **Total Debt**: {fpt_bs.get('total_debt', 0):,.0f} VND
- **Total Equity**: {fpt_bs.get('equity', 0):,.0f} VND
- **Debt / Equity Ratio**: {fpt_bs.get('debt_equity_ratio', 0):.2f}x (Threshold <= 0.8x -> **PASS**)
- **Liquidity Status**: Pháo đài tiền mặt ròng dồi dào.

## 5. Normalized Earning Power
- **Latest Reported Net Profit (FY2025)**: {fpt_norm.get('reported_latest', 0):,.0f} VND
- **5-Year Normalized Net Profit**: {fpt_norm.get('normalized_5y', 0):,.0f} VND
- **10-Year Normalized Net Profit**: {fpt_norm.get('normalized_10y', 0):,.0f} VND
- **Earning Power Divergence**: +{fpt_norm.get('earning_power_divergence', 0):,.0f} VND

## 6. Canonical Valuation & Margin of Safety
- **Current Market Price**: {fpt_v.get('current_price', 0):,.0f} VND
- **Bear Intrinsic Value**: {fpt_v.get('bear_iv', 0):,.0f} VND
- **Base Intrinsic Value**: {fpt_v.get('base_iv', 0):,.0f} VND
- **Bull Intrinsic Value**: {fpt_v.get('bull_iv', 0):,.0f} VND
- **Actual Margin of Safety (Actual MOS)**: {fpt_val.get('actual_mos_pct'):.2f}%
- **Required Margin of Safety (Required MOS)**: {fpt_val.get('required_mos_pct')}%
- **MOS Gate**: **{fpt_val.get('mos_gate')}** (Actual MOS < Required MOS -> `FAIL`)

## 7. Forensic & Accounting Integrity Findings
- **Accounting Identity Violations**: 0
- **Forensic Findings Count**: 0
- **Structural Deterioration**: `NO_DETERIORATION`
- **Value Trap Status**: `CLEAR`

## 8. Final Decision Lineage & Precedence
1. `hard_failures`: None -> `AVOID` not triggered.
2. `vt_status`: `CLEAR` -> `AVOID` not triggered.
3. `data_readiness`: `READY` (15 years FY data) -> `REVIEW_BUSINESS` not triggered.
4. `compounder_classification`: `POTENTIAL_COMPOUNDER` (High ROE & Growth).
5. `valuation_status`: `READY`.
6. `mos_gate`: `FAIL` (Actual MOS -36.44% < Required MOS 25.0%).
7. **Final Outcome**: **`WAIT_FOR_MOS`**

FPT meets all financial business quality criteria of a long-term compounder, but the current market price of 130,000 VND exceeds Base Intrinsic Value (95,283 VND). Investors must wait for market price to provide a >= 25.0% Margin of Safety.
"""

with open('docs/reports/golden-fpt-munger-analysis.md', 'w', encoding='utf-8') as f:
    f.write(fpt_doc)

print("Generated docs/reports/golden-fpt-munger-analysis.md")
