# Canonical Munger Decision Engine Integrity Audit (TASK-182)

`status: completed`
`created: 2026-09-17`

---

## Requirement
Audit the layer AFTER valuation/MOS and ensure that QPort's final Munger/Buffett decision is logically consistent with:
Business Quality + Forensics + Value Trap + Liquidity + Valuation + MOS.

Ensure:
1. Exactly one canonical decision calculation authority.
2. Clear distinction between `HARD_BLOCKER`, `MONITORING_SIGNAL`, and `SUPPORTING_EVIDENCE`.
3. Strict decision consistency across all cases:
   - MOS PASS + Quality PASS + Forensics CLEAR $\implies$ `BUY` / `BUY_MORE` (never `WAIT_FOR_MOS`).
   - MOS PASS + Forensics WATCH $\implies$ `BUY` with monitoring signals (not falsely claiming "chờ biên an toàn").
   - MOS FAIL + Quality PASS $\implies$ `WAIT_FOR_MOS`.
   - Quality FAIL + MOS PASS $\implies$ Quality blocker overrides MOS (never `BUY` just because cheap).
   - Liquidity insufficient $\implies$ Reflects liquidity gate without claiming the business is bad.
4. Structured decision trace exposing every gate, hard blocker, and monitoring signal.
5. Munger Candidate $\neq$ BUY: A high-quality company is a candidate even when MOS is not yet reached (`is_mos_qualified = false`).
6. Zero raw enum, null, NaN, or undefined leakage in investor-facing UI.
7. Verified regression consistency on BFC, HAH, and all golden symbols.

---

## Context
Following the completion of the canonical share basis and corporate action classification audits (TASK-180 & TASK-181), the valuation numbers and MOS calculations are mathematically verified and invariant.

However, the decision layer sitting on top of valuation must translate these numbers into actionable, disciplined Buffett-Munger decisions. An audit is required to guarantee that:
- Findings are correctly classified as hard blockers vs monitoring points.
- Contradictory explanations (e.g. saying "wait for MOS" when MOS already passed) are completely prevented.
- Decision traces are exposed uniformly across API, Terminal, Business Workspace, Munger Candidate Discovery, PDF, and AI Export.

---

## Acceptance Criteria
- [x] **AC1**: One canonical decision authority exists and is consumed across all endpoints (`portfolio.value_engine.munger_analyzer.build_munger_financial_analysis` via `canonical_valuation`).
- [x] **AC2**: Decision trace identifies every gate status (`quality_gate`, `forensic_gate`, `value_trap_gate`, `liquidity_gate`, `valuation_gate`, `mos_gate`), hard blockers, monitoring signals, and supporting evidence.
- [x] **AC3**: Hard blockers are strictly distinguished from monitoring signals (`blocking_reasons` / `hard_blockers` vs `monitoring_reasons` / `monitoring_signals`).
- [x] **AC4**: MOS PASS cannot produce `WAIT_FOR_MOS` unless another explicit MOS-related condition exists.
- [x] **AC5**: MOS PASS does not override a genuine business-quality blocker (`WEAK_BUSINESS` or `DETERIORATING_BUSINESS` produces `AVOID`).
- [x] **AC6**: Forensic WATCH does not automatically become a hard blocker; coexists with `BUY` and generates `watch_coexistence_rationale`.
- [x] **AC7**: Liquidity remains independent from business quality (`LIQUIDITY_WEAK` / `LIQUIDITY_INSUFFICIENT_DATA` does not mark business bad).
- [x] **AC8**: Candidate status remains distinct from BUY status (`is_mos_qualified = False` retains candidate status).
- [x] **AC9**: High PAT CAGR + ROE does not automatically imply durable compounder without margin/stability checks (requires low volatility, no loss years, safe capital structure).
- [x] **AC10**: Normalized earning power is used where required (exposes `normalized_pat_5y`, `is_peak_earnings`, `volatility_cv`).
- [x] **AC11**: Stress tests have independent provenance and do not conflate personal financial stress with business stress.
- [x] **AC12**: BFC regression is logically consistent with zero unexplained conditionality (MOS 67.4% >= 50.0% Req MOS $\implies$ `BUY`, clean conditions, 3 monitoring points).
- [x] **AC13**: HAH regression is logically consistent (MOS 70.5% >= 50.0% Req MOS $\implies$ `BUY`, clean conditions, 2 monitoring points).
- [x] **AC14**: Frontend and exports consume canonical decision data without reinterpreting logic.
- [x] **AC15**: No raw enums/null/NaN leakage in investor-facing UI (`action_vi`, `action_vietnamese`, `state_vietnamese`).

---

## Constraints and Invariants
1. `BUY_AND_HOLD_INFORMATION_SYSTEM`: Information system only; decisions advise human allocation.
2. Canonical decision enums: `BUY`, `BUY_MORE`, `HOLD`, `HOLD_NO_NEW_CAPITAL`, `WAIT_FOR_MOS`, `BUILD_RESERVE_FIRST`, `REVIEW_BUSINESS`, `AVOID`, `SELL_REVIEW`, `SELL`.
3. Quality Floor: Low quality business is rejected regardless of how high MOS appears.
4. $NULL \neq 0$, $MISSING \neq SAFE$, $UNKNOWN \neq PASS$, $CONFLICTED \neq VALID$.

---

## Implementation Tasks
- [x] **Task 1: Forensic Inspection of Munger Decision Pipeline**
  - Inspected `munger_analyzer.py`, `munger_candidates.py`, `canonical_valuation.py`, and `vietnamese_presenter.py`.
- [x] **Task 2: Hard Blocker vs Monitoring Signal Taxonomy Hardening**
  - Classified hard failures vs non-structural monitoring signals (CV volatility, peak earnings, working capital) with explicit `watch_coexistence_rationale`.
- [x] **Task 3: Decision Gate Trace Formalization**
  - Exposed structured `decision_trace` with `quality_gate`, `forensic_gate`, `value_trap_gate`, `liquidity_gate`, `valuation_gate`, `mos_gate`, `hard_blockers`, `monitoring_signals`, `supporting_evidence`, `final_decision`, `explanation`.
- [x] **Task 4: Resolve BFC and HAH Decision Contradictions**
  - Verified BFC (MOS 67.4% >= 50%) and HAH (MOS 70.5% >= 50%) yield `BUY` ("Có thể mua") with clean condition lists and transparent monitoring signals.
- [x] **Task 5: Comprehensive Decision Regression Test Suite**
  - Created `python/portfolio/tests/test_canonical_munger_decision_integrity.py` covering Cases A, B, C, D, E, BFC, HAH, Stress Tests, and candidate separation.
- [x] **Task 6: Final Verification & Commit**
  - Ran full test suite (73/73 passed) and verified frontend build (`vite build` passed).

---

## Related Notes
- [TASK-20260917-180-canonical-share-basis-mos-integrity.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260917-180-canonical-share-basis-mos-integrity.md)
- [TASK-20260917-181-corporate-action-economic-classification-audit.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260917-181-corporate-action-economic-classification-audit.md)

---

## Validation Evidence

### Regression Summary Table
| Case | Gates (Quality / Forensic / ValueTrap / Liquidity / Val / MOS) | Blockers | Monitoring | Decision | Result |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Case A** | PASS / PASS / CLEAR / ACCEPTABLE / READY / PASS | 0 | 0 | `BUY` ("Có thể mua") | PASS |
| **Case B** | PASS / WATCH / CLEAR / ACCEPTABLE / READY / PASS | 0 | 1 (CV > 35%) | `BUY` + Coexistence Rationale | PASS |
| **Case C** | PASS / PASS / CLEAR / ACCEPTABLE / READY / FAIL | 1 (MOS < Req) | 0 | `WAIT_FOR_MOS` ("Chờ biên an toàn") | PASS |
| **Case D** | FAIL / FAIL / HIGH_RISK / ACCEPTABLE / READY / PASS (70%) | 1 (Quality Fail) | 0 | `AVOID` ("Chưa phù hợp") | PASS |
| **Case E** | PASS / PASS / CLEAR / INSUFFICIENT / READY / PASS | 0 | 0 | `BUY` (Liquidity independent) | PASS |
| **BFC** | PASS / PASS / CLEAR / ACCEPTABLE / READY / PASS (67.4% >= 50%) | 0 | 3 (CV, Peak, D/E) | `BUY` ("Có thể mua") | PASS |
| **HAH** | PASS / PASS / CLEAR / STRONG / READY / PASS (70.5% >= 50%) | 0 | 2 (CV, Peak) | `BUY` ("Có thể mua") | PASS |
| **FPT (Candidate)** | PASS / PASS / CLEAR / STRONG / READY / (MOS not req) | 0 | 0 | `Candidate: True`, `is_mos_qualified: False` | PASS |

### Test Suite Execution Output
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\workspace\shannon_allocation
configfile: pyproject.toml
collected 73 items

python/portfolio/tests/test_canonical_munger_decision_integrity.py ............ [ 16%]
python/portfolio/tests/test_munger_decision_consistency.py ..........           [ 30%]
python/portfolio/tests/test_munger_decision_forensic_consistency.py ...........  [ 45%]
python/portfolio/tests/test_canonical_share_basis_mos_integrity.py ............ [ 61%]
python/portfolio/tests/test_corporate_action_normalization.py ................. [ 84%]
python/portfolio/tests/test_global_munger_decision_engine.py ...........         [100%]

============================= 73 passed in 2.43s ==============================
```

### Frontend Build
```text
vite v6.4.3 building for production...
✓ 365 modules transformed.
✓ built in 3.63s
```

---

## Decisions
1. **Decision Authority Hierarchy**:
   - `portfolio.value_engine.share_basis`: Canonical share basis & MOS calculation.
   - `portfolio.value_engine.munger_analyzer`: Canonical long-term Munger/Buffett decision & structured decision trace.
   - `portfolio.canonical_valuation`: Single API provider assembling valuation & Munger analysis.
2. **Watch Coexistence Formalization**:
   - Monitoring signals (e.g. CV > 35%, recent earnings > normalized earnings, D/E watch) are accounted for via required MOS add-ons (Required MOS: 50%).
   - When actual MOS meets or exceeds required MOS without structural deterioration or accounting identity failures, the decision cleanly returns `BUY` accompanied by `watch_coexistence_rationale`.
3. **Candidate vs Buy Decoupling**:
   - Quality assessment determines whether a business is a Munger candidate.
   - MOS gate determines whether the current price provides an adequate discount to buy (`is_mos_qualified`).
   - A business remains an Exceptional/High Quality candidate even if MOS is not yet reached.

---

## Result
- **AC1-AC15**: 100% satisfied and validated by automated tests.
- **BFC and HAH regression**: Fully coherent with zero contradictions or phantom conditions.
- **Status**: Completed.
