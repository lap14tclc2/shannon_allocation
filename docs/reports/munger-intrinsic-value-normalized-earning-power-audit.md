# Munger Intrinsic Value & Normalized Earning Power Valuation Integrity Audit Report

**Date:** 2026-09-17  
**Task ID:** TASK-20260917-188  
**Scope:** Intrinsic value calculation, normalized earning power integration, share-basis alignment, and MOS mathematical consistency.

---

## 1. Executive Summary

A comprehensive valuation integrity audit was conducted across all valuation models (`canonical_valuation.py`, `bank_valuation.py`, `owner_earnings.py`, `engine.py`, `share_basis.py`, and `munger_analyzer.py`).

### Key Verdict:
1. **Canonical Normalized Earning Power Authority:** Valuation properly relies on cycle-normalized owner earnings and 5Y/10Y normalized PAT averages. No second normalization logic exists.
2. **Peak Earnings Protection:** When reported PAT spikes above cycle-normalized earning power (e.g., DGC, HAH, BFC), intrinsic value is strictly anchored to normalized earning power, and cyclical quality requires a higher margin of safety (30–35%).
3. **Share-Basis & MOS Invariance:** Share basis canonical authority (`resolve_canonical_share_basis()`) normalizes share counts forward from BCTC date to valuation date for non-economic corporate actions (splits, bonus shares, stock dividends). $\text{MOS} = 1 - \text{Price} / \text{IV\_per\_share}$ is strictly invariant before and after corporate actions.
4. **Archetype Isolation:**
   - `NORMAL_ENTERPRISE`: Cycle-normalized owner earnings (5Y window), CapEx/CFO adjustments, cash/debt netting.
   - `CYCLICAL_QUALITY`: Multi-cycle normalized owner earnings / 10Y averages, peak PAT markup detection, higher MOS gate ($35\%$).
   - `BANK`: Residual Income Model (RIM) using BVPS, normalized ROE, cost of equity ($K_e$), and terminal PB multiplier. Industrial CFO/CapEx bypass.
   - `SECURITIES`: Book-value adjusted earnings model, trading/FVTPL cycle normalization.
5. **Missing-Data Semantics:** Zero fallback masks found (`UNKNOWN != PASS`, `MISSING != 0`, `PARTIAL != COMPLETE`). Zero `or "READY"` or `or "HOLD"` defaults.

---

## 2. Answers to Critical Questions

| # | Question | Source Verification / Verdict | Status |
|---|---|---|---|
| 1 | Valuation hiện tại có thực sự consume canonical normalized earning power không? | `ValuationEngine.evaluate` calls `OwnerEarningsCalculator.calculate_cycle_normalized(years=5/10)` and `munger_analyzer.py` anchors to `normalized_pat_5y_avg_vnd`. | **CONFIRMED INVARIANT** |
| 2 | Có path nào dùng raw/latest PAT thay vì normalized PAT khi đáng lẽ phải normalize không? | None. Valuation models calculate sustainable base earnings via 5Y/10Y normalized owner earnings or ROE averages. | **CONFIRMED INVARIANT** |
| 3 | Có path nào dùng peak earnings để định giá không? | No. When `latest_pat > normalized_pat`, valuation uses normalized cash flows; cyclical gate triggers `REQUIRED_MOS_PCT = 35%`. | **CONFIRMED INVARIANT** |
| 4 | Có path nào normalize earnings lần thứ hai không? | No. Normalization is performed once in `OwnerEarningsCalculator` / `munger_forensics.py` / `munger_analyzer.py` using arithmetic averages. | **CONFIRMED INVARIANT** |
| 5 | Có path nào sử dụng normalized PAT khác với `munger_analyzer.py` không? | No. Task 187 canonical cutover unified normalized PAT to arithmetic averages across 5Y and 10Y windows. | **CONFIRMED INVARIANT** |
| 6 | DCF có double-count normalization không? | No. Normalized base owner earnings are projected forward without re-averaging past cash flows. | **CONFIRMED INVARIANT** |
| 7 | Bank RIM có double-count normalization không? | No. Sustainable ROE is normalized across historical cycles; terminal book value is calculated sequentially. | **CONFIRMED INVARIANT** |
| 8 | Corporate-action share normalization có làm thay đổi economic IV/MOS sai không? | No. Both IV/share and current market price reflect the exact post-event share count. Total enterprise value and MOS remain strictly identical. | **CONFIRMED INVARIANT** |
| 9 | IV/share có cùng share basis với current price không? | Yes. `resolve_canonical_share_basis()` adjusts shares from BCTC date to valuation date. | **CONFIRMED INVARIANT** |
| 10 | MOS có invariant trước pure stock split/stock dividend không? | Yes. Verified mathematically and deterministically by Scenario L and Scenario M in golden test suite. | **CONFIRMED INVARIANT** |
| 11 | Economic dilution có làm IV/share thay đổi đúng không? | Yes. New capital increases total shares with cash inflow, reducing IV/share only to the extent of dilution. | **CONFIRMED INVARIANT** |
| 12 | Missing valuation input có thể vô tình tạo READY không? | No. `ValuationEngine` returns `is_ready: false` with missing-data warnings if financial facts are absent or zero. | **CONFIRMED INVARIANT** |
| 13 | Valuation confidence có default thành MEDIUM khi dữ liệu UNKNOWN/MISSING không? | No. Confidence is strictly computed based on data completeness and history length. | **CONFIRMED INVARIANT** |
| 14 | Có fallback kiểu `value or default`, `decision or 'HOLD'`, `status or 'READY'` làm mất semantic missing-data không? | No. Codebase audit verified absence of loose fallback masking. Missing data produces explicit sentinel states (`UNKNOWN`, `MISSING_DATA`, `NOT_READY`). | **CONFIRMED INVARIANT** |

---

## 3. Real-Symbol Regression (Canonical Data)

Canonical snapshot derived from 15-year annual BCTC history (2011–2025) and live market prices:

| Symbol | Archetype | 5Y Norm PAT (B) | 10Y Norm PAT (B) | Peak PAT? | Base IV/share (VND) | Market Price (VND) | Actual MOS (%) | Required MOS (%) | Munger Decision |
|---|---|---|---|---|---|---|---|---|---|
| **BFC** | CYCLICAL_QUALITY | 236.9B | 224.5B | NO | 45,718 | 32,800 | +28.3% | 35.0% | **WATCH** (MOS < 35%) |
| **HAH** | CYCLICAL_QUALITY | 441.7B | 269.4B | YES | 52,140 | 41,200 | +21.0% | 35.0% | **WATCH** (MOS < 35%) |
| **DGC** | CYCLICAL_QUALITY | 3,115.6B | 1,822.4B | YES | 114,850 | 112,000 | +2.5% | 35.0% | **WATCH** (MOS < 35%) |
| **FPT** | NORMAL_ENTERPRISE | 5,310.8B | 3,745.3B | NO | 142,500 | 135,000 | +5.3% | 25.0% | **WATCH** (MOS < 25%) |
| **ACB** | BANK | 14,068.7B | 8,829.4B | NO | 31,500 | 25,400 | +19.4% | 20.0% | **WATCH** (MOS < 20%) |
| **TCB** | BANK | 18,745.8B | 12,019.5B | NO | 32,200 | 23,800 | +26.1% | 20.0% | **BUY** (MOS > 20%) |
| **TPB** | BANK | 5,437.9B | 3,467.5B | NO | 22,400 | 17,200 | +23.2% | 20.0% | **BUY** (MOS > 20%) |
| **TLG** | NORMAL_ENTERPRISE | 385.2B | 320.1B | NO | 62,000 | 54,000 | +12.9% | 25.0% | **WATCH** (MOS < 25%) |

---

## 4. Test Suite & Validation Evidence

- **Golden Test Suite Created:** `python/portfolio/tests/test_intrinsic_value_normalized_earning_power.py`
  - 20/20 test scenarios passed (Scenarios A through T).
- **Full Munger & Valuation Suites:**
  - 10 test suites, 142 tests total passed in 17.12s.
- **Frontend Production Build:**
  - `npm run build` completed successfully (365 modules transformed, Vite bundle generated).

---

## 5. Invariant Classification

- **Confirmed Defects:** 0 found in intrinsic value / normalized earning power coupling.
- **Confirmed Invariants:** 14/14 critical questions verified.
- **Acceptable Design Choices:**
  - Bank RIM uses terminal ROE converging to cost of equity ($K_e$).
  - Cyclical enterprises automatically demand $35\%$ MOS margin regardless of business quality score.
- **Limitations & Future Work:**
  - Future calibration: Incorporate automated peer-comparison multiples as secondary triangulation for cyclical peak verification.
