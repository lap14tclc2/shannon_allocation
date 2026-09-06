# TASK-20260906-104: Expand Allocation Candidate Discovery into Buy-Ready, Watchlist, and Rejected Tiers

- **Status**: completed
- **Priority**: high
- **Date**: 2026-09-06
- **Author**: Antigravity AI

---

## ## Requirement

Separate Allocation candidate discovery into three explicit, deterministic tiers:
1. **`BUY_READY`**: Candidates passing ALL strict actionability gates (security, liquidity $\ge 10\text{B}$, quality tier, no hard rejects, public valuation, valuation safety $\ge 0\text{pp}$, portfolio fit GOOD/MODERATE, risk data, funding, feasible execution plan). Only `BUY_READY` candidates receive `BUY_MORE` recommendations, share quantities, and VND trade values.
2. **`WATCHLIST` / `NEAR_QUALIFIED`**: Fundamentally interesting candidates passing basic security & quality constraints but failing one or more non-destructive gates (valuation safety slightly negative, MOS near threshold, low valuation confidence, weak portfolio fit, sector concentration, or liquidity below BUY threshold but $\ge 3\text{B VND/day}$). `WATCHLIST` candidates DO NOT receive `BUY_MORE` actions or share quantities.
3. **`REJECTED`**: Candidates failing destructive/non-negotiable constraints (solvency risk, accounting unreliability, confirmed destructive dilution, `LOW_QUALITY`, unsupported security, severe data integrity failure). Hidden or collapsed by default on Allocation UI.

**Constraints**:
- BUY standards must NOT be weakened.
- NO weighted score (no composite candidate score $w_1 \cdot Q + w_2 \cdot V + w_3 \cdot F$). Gate-based classification only.
- Expected Alpha and Kelly remain disabled.

---

## ## Context

Currently, the Allocation engine filters all candidate items through a single strict gate. Stocks failing even slightly on MOS or portfolio fit get dropped entirely into diagnostics, showing only ~2-5 visible suggestions. By decoupling candidate research discovery from portfolio action execution, QPort can show near-qualified research opportunities without lowering strict BUY criteria.

---

## ## Acceptance Criteria

- [x] **Candidate Classification Function**: Implement gate-based `classify_candidate()` returning `BUY_READY`, `WATCHLIST`, or `REJECTED`, attached `gate_evidence`, `failed_gates`, `watch_reasons`, and optional `max_qualifying_price`.
- [x] **BUY_READY Tier**: Requires passing security, liquidity ($\ge 10\text{B}$), quality, no hard rejects, public valuation, valuation safety ($\ge 0\text{pp}$), portfolio fit (GOOD/MODERATE), risk data, funding, and feasible execution plan.
- [x] **WATCHLIST Tier**: Requires passing security, no destructive hard rejects, non-`LOW_QUALITY`, liquidity $\ge 3\text{B VND/day}$ (configurable research threshold). Attaches explicit watch reasons (`WATCH_VALUATION_TOO_EXPENSIVE`, `WATCH_MOS_NEAR_THRESHOLD`, `WATCH_PORTFOLIO_FIT_WEAK`, `WATCH_SECTOR_CONCENTRATION`, `WATCH_LOW_VALUATION_CONFIDENCE`, `WATCH_DATA_INCOMPLETE`, `WATCH_LIQUIDITY_BELOW_BUY_THRESHOLD`).
- [x] **Price-to-Qualify Math**: For WATCHLIST candidates failing ONLY valuation safety, compute informational `max_buy_price = intrinsic_value * (1 - required_mos_pct / 100)`.
- [x] **REJECTED Tier**: Captures destructive thesis breaks (`SOLVENCY_RISK`, `ACCOUNTING_UNRELIABLE`, etc.), `LOW_QUALITY`, unsupported security types, liquidity $< 3\text{B}$.
- [x] **Tier Counts**: Expose `buy_ready_count`, `watchlist_count`, `rejected_count`, `universe_count` in `PortfolioAllocationReport`.
- [x] **Deterministic Ordering Policy**: Order within tiers deterministically without weighted scores (BUY_READY: safety desc, quality desc, fit desc, liquidity desc; WATCHLIST: fewest failed gates asc, quality desc, safety proximity, fit, liquidity).
- [x] **Frontend UI Overhaul**: Render 3 explicit sections on `/allocation`: BUY_READY candidates, WATCHLIST candidates (with "missing" reasons and max buy price), and REJECTED candidates (collapsed by default).
- [x] **Tests & Verification**: Add backend tests covering all 26 specified edge cases and run `npm run build`.

---

## ## Constraints and Invariants

- "BUY standards were not weakened."
- "More stocks are visible for research because discovery is now separated from action eligibility."
- Maintain advisory-only contract (no auto-execution, no ledger mutation).
- Expected Alpha and Kelly remain disabled.

---

## ## Implementation Tasks

- [x] Add new reason codes and Vietnamese labels in `reason_codes.py` and `allocationLabels.js`.
- [x] Update data models in `models.py` (`CandidateOpportunity`, `PortfolioAllocationReport`).
- [x] Refactor candidate discovery & classification in `candidate_service.py`, `opportunity.py`, and `service.py`.
- [x] Implement `max_qualifying_price` calculation for WATCHLIST candidates failing valuation safety.
- [x] Update `/allocation` UI in `AllocationPage.jsx` to show 3 candidate tiers (BUY_READY, WATCHLIST, REJECTED collapsed).
- [x] Add comprehensive test suite covering near-qualified candidate semantics and tier separation.
- [x] Execute `pytest` and `npm run build` to verify clean build and passing tests.

---

## ## Related Notes

- [AGENTS.md](file:///c:/workspace/shannon_allocation/AGENTS.md)
- [TASK-20260906-101](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260906-101-executable-share-quantity-plans-and-explainable-candidate-selection.md)
- [TASK-20260906-102](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260906-102-add-vnd-amount-and-share-quantity-to-allocation.md)
- [TASK-20260906-103](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260906-103-frontend-css-typography-aesthetic-responsive-overhaul.md)

---

## ## Validation Evidence

```powershell
$env:PYTHONPATH="python"; .venv\Scripts\pytest.exe python/portfolio/tests/test_allocation_candidate_tiers.py python/portfolio/tests/test_allocation_service.py python/portfolio/tests/test_allocation_opportunity.py
# Output: 75 passed in 0.74s

npm run build (in frontend/)
# Output: built in 1.38s (dist/index.html, dist/assets/index-BvTst0Zm.css, dist/assets/index-3Ip-PXXD.js)
```

---

## ## Decisions

- Use explicit gate evaluation instead of a composite weighted score to ensure complete determinism and auditability.
- Provide configurable liquidity thresholds (`min_buy_liquidity = 10.0B`, `min_research_liquidity = 3.0B`) and valuation safety thresholds (`min_valuation_safety = 0.0pp`, `near_qualified_safety_threshold = -10.0pp`).

---

## ## Result

Candidate discovery has been expanded into 3 explicit, gate-based deterministic tiers (`BUY_READY`, `WATCHLIST`, `REJECTED`). BUY standards were NOT weakened. Discovery is now decoupled from action eligibility, allowing research candidates to remain visible with clear missing gate explanations and max qualifying prices. All 75 allocation unit tests and Vite frontend build pass 100%.
