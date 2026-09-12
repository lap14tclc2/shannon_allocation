---
id: TASK-20260912-149
title: Fix validation gate classification bugs (cycle/unit/excluded_years)
status: completed
created: 2026-09-12
---

## Requirement
4 tests in `test_value_engine_validation.py` failing:
1. `CYCLICAL_EXTREME` classified as `SUSPICIOUS_ISOLATED` for DGC 2021/2022
2. `valuation_handling.use` returns `KEEP_WITH_WARNING` instead of `INCLUDE` for CYCLICAL_EXTREME
3. `normalization_window.excluded_years` is list of dicts `[{year, reason}]` instead of list of ints
4. `UNIT_MAPPING_ERROR_CANDIDATE` has `block=False` instead of `True`

## Context
- `validation_gate._classify_year` receives `cycle_years` list but NEVER uses it in decision tree
- For DGC 2021: `P=1.0` (post-regime is persistently high 2021-2023), so `CY = A*C*M*(1-P) = 0`
- Without CY, falls through to `SUSPICIOUS_ISOLATED` fallback
- Fix: insert `year in cycle_years` check BEFORE R>=0.15 STRUCTURAL_BREAK_CANDIDATE branch
- `block=False` for unit_error_year is plain wrong; unit errors must block model
- `excluded_years` dict shape was API design error; tests contract requires int list

## Acceptance Criteria
- [x] `test_gate_detects_dgc_structural_break_and_cycle_extremes` passes
- [x] `test_gate_valuation_handling_use_policies` passes
- [x] `test_normalization_window_evidence_in_report` passes
- [x] `test_gate_unit_jump_is_unit_mapping_error` passes

## Implementation Tasks
- [x] `validation_gate.py`: insert `year in set(cycle_years)` → CYCLICAL_EXTREME before R>=0.15
- [x] `validation_gate.py`: `block = True` for unit_error_year branch
- [x] `engine.py`: `excluded_years` → list of ints

## Validation Evidence
```
pytest python/portfolio/tests/test_value_engine_validation.py -o pythonpath=python
11 passed in 0.67s
```
All 4 originally-failing assertions now pass. No regressions in adjacent tests.

## Result
Fixed 3 root causes across 2 files. 4 tests green.
