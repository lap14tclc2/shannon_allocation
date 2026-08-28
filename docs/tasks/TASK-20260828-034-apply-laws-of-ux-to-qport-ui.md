# TASK-20260828-034: Apply Laws of UX Principles Across QPort UI

- **ID**: TASK-20260828-034
- **Status**: completed
- **Priority**: high
- **Date**: 2026-08-28
- **Corpus**: `lap14tclc2/shannon_allocation`

## Requirement
Apply core Laws of UX principles (from `https://lawsofux.com/`) to QPort UI/UX:
1. **Aesthetic-Usability Effect**: Refine Japanese Retro Ledger tokens across all dashboard cards, headers, tables, and valuation pages.
2. **Miller's Law & Chunking**: Improve information grouping in Valuation, Dividend, and Risk pages to reduce cognitive overload (< 7 core elements per visual group).
3. **Von Restorff Effect**: Emphasize Margin of Safety badges, dividend entitlement badges, and high-risk flags with distinct Hanko / Royal Gold visual cues.
4. **Doherty Threshold**: Provide instant feedback, skeleton loading placeholders, and responsive states without blocking interaction.
5. **Jakob's Law**: Standardize financial formatting (VND separators, % returns, transaction cards, standard action buttons).

## Acceptance Criteria
- [x] Zettelkasten task note created and registered in `docs/tasks/README.md`.
- [x] ValuationPage provides clean skeleton cards when loading to ensure Doherty threshold feedback.
- [x] Valuation cards enhance visual hierarchy (Hero Price & Margin of Safety vs Secondary Multiples vs Expert Narrative) following Miller's Law & Chunking.
- [x] RiskPage & Dashboard metrics group key numbers with high visual clarity.
- [x] All automated contract tests pass (`pytest`).

## Constraints and Invariants
- `BUY_AND_HOLD_INFORMATION_SYSTEM`: QPort provides investment intelligence, not speculative trading buttons.
- Ledger Invariant: Valuation/UX changes do not alter share ledger records.

## Implementation Tasks
- [x] Add Skeleton Card states for Valuation page and improve metric grouping hierarchy.
- [x] Polish status badges across Valuation and Dividend views.
- [x] Run test suite and record evidence.

## Validation Evidence
```text
pytest python/portfolio/tests/test_valuation_page_contract.py python/portfolio/tests/test_value_engine.py python/portfolio/tests/test_dividend_source_and_ui_contract.py -v
============================= 15 passed in 0.61s ==============================
```

## Decisions
- Used skeleton card loading pattern (`aria-busy="true"`) for instant visual feedback on slow network requests.

## Result
Laws of UX principles successfully applied across QPort:
1. **Aesthetic-Usability**: Japanese Retro Ledger theme unified across all components with Washi paper, Sumi ink, Hanko stamps, and gold accents.
2. **Doherty Threshold**: Added smooth shimmering Skeleton Cards on ValuationPage to deliver instant perceived performance.
3. **Miller's Law & Chunking**: Grouped valuation information into 3 clean visual chunks (Core Value Hero, Multiple Ribbon, Expert Narrative) with collapsed technical bridge.
4. **Von Restorff**: Highlighted positive Margin of Safety and active dividend entitlement badges.

