# TASK-20260907-105: Clarify Allocation Position-Band and Existing-Holding Target Semantics

---
id: TASK-20260907-105
title: Clarify Allocation Position-Band and Existing-Holding Target Semantics
status: completed
priority: high
date: 2026-09-07
---

## Requirement

Correct the allocation semantic ambiguity where conviction/sizing bands (3–5%, 7–12%, 12–18%) for building or opening new positions were displayed as target weights for existing holdings.

Separate four core concepts across backend models, API contracts, frontend UI, labels, and tests:
1. `CURRENT_WEIGHT` ("Tỷ trọng hiện tại"): Portfolio share currently held.
2. `ACTION` ("Khuyến nghị"): BUY_MORE | HOLD | REDUCE | SELL | WATCH | KEEP_CASH.
3. `POST_ACTION_WEIGHT` ("Tỷ trọng sau đề xuất"): Actionable target weight if recommendation is followed.
4. `NEW_POSITION_GUIDANCE` ("Mức vốn gợi ý khi mở vị thế mới"): Background sizing reference for opening/building a new position under current conditions.

## Context

Current Allocation UI displayed rows like:
ACB | Current weight: 38.2% | Recommendation: HOLD | Range: 3–5%

Users naturally interpreted "3–5%" as "QPort wants me to sell ACB down to 3–5% while recommending HOLD", creating a major semantic contradiction. Conviction bands are initial position-building guidance, NOT forced rebalance targets for existing holdings.

## Acceptance Criteria

- [x] Backend models and API response explicitly include `post_action_target_weight` and `new_position_guidance`.
- [x] For `action == HOLD`, `post_action_target_weight` equals `current_weight` (or null if non-actionable), NOT the new position band.
- [x] For `action == REDUCE`, `post_action_target_weight < current_weight`.
- [x] For `action == BUY_MORE`, `post_action_target_weight > current_weight`.
- [x] For `action == SELL`, `post_action_target_weight == 0.0`.
- [x] Frontend main table headers changed from "Khoảng mục tiêu" to "Tỷ trọng sau đề xuất".
- [x] Labels "Khoảng mục tiêu", "Tỷ trọng mục tiêu", "Mức nên giữ" are strictly removed from conviction band displays.
- [x] Conviction bands in detail view labeled as "Mức vốn gợi ý khi mở vị thế mới" with clarifying helper text.
- [x] Mobile holding cards show current weight, action, and post-action weight prominently, moving new-position guidance to expandable details.
- [x] Tooltips added for "Tỷ trọng hiện tại", "Tỷ trọng sau đề xuất", and "Mức vốn gợi ý khi mở vị thế mới".
- [x] Comprehensive unit, integration, contract, and UI tests pass.

## Constraints and Invariants

1. HOLD must not imply a different actionable target from current weight (`post_action_target_weight == current_weight`).
2. REDUCE `post_action_target_weight < current_weight`.
3. BUY_MORE `post_action_target_weight > current_weight`.
4. SELL `post_action_target_weight == 0.0`.
5. New-position guidance must not be labeled as target weight.
6. New-position guidance must not drive UI action wording directly.
7. Existing holding recommendation and new-position guidance remain separate concepts.
8. If UI shows HOLD, it must not visually imply "sell down to 3–5%".
9. If existing holding is supposed to move to the new-position band, action must explicitly be REDUCE.
10. No ledger mutation.

## Implementation Tasks

- [x] Update `python/portfolio/allocation/models.py` (`AllocationDecision`, `SizingResult`, `PortfolioAllocationReport`) to add `post_action_target_weight` and `new_position_guidance`.
- [x] Update `python/portfolio/allocation/opportunity.py` and `service.py` to enforce `post_action_target_weight` semantics for `HOLD`, `REDUCE`, `SELL`, and `BUY_MORE`.
- [x] Update `python/portfolio/allocation/execution_planner.py` to compute `post_action_target_weight` cleanly.
- [x] Update `frontend/src/lib/allocationLabels.js` with new Vietnamese labels and tooltips.
- [x] Overhaul `frontend/src/pages/AllocationPage.jsx` (main table columns, mobile cards, detail view, tooltips).
- [x] Add backend unit/contract tests verifying semantic invariants in `python/portfolio/tests/test_allocation_semantic_invariants.py`.
- [x] Verify `npm run build` and python tests.

## Related Notes

- `AGENTS.md` - System Invariants & Task-first workflow.
- `docs/QPORT_BUFFETT_THORP_SYSTEM_PLAN.md`
- `docs/QPORT_BUFFETT_THORP_IMPLEMENTATION.md`
- `TASK-20260906-095-buffett-thorp-allocation.md`

## Validation Evidence

```powershell
$env:PYTHONPATH="python"; python -m pytest python/portfolio/tests/test_allocation_semantic_invariants.py python/portfolio/tests/test_allocation_domain.py python/portfolio/tests/test_allocation_eligibility.py python/portfolio/tests/test_allocation_sizing.py python/portfolio/tests/test_allocation_opportunity.py python/portfolio/tests/test_allocation_candidate_tiers.py python/portfolio/tests/test_allocation_execution_planner.py python/portfolio/tests/test_allocation_service.py python/portfolio/tests/test_allocation_architecture.py
# Output: 133 passed in 1.15s

npm run build (in frontend/)
# Output: vite v6.4.3 building for production... built in 1.23s
```

## Decisions

- Retained `target_min`, `target_mid`, `target_max` on `AllocationDecision` for backward compatibility where `target_mid` holds `post_action_target_weight`, while adding explicit `post_action_target_weight` and `new_position_guidance` dict/model to guarantee clean public API contracts.

## Result

- 133 allocation backend unit/contract tests passed.
- Frontend production build succeeded without warnings.
- Position sizing bands and existing-holding targets are explicitly separated across backend and frontend.

