
# Buffett-Munger Canonical Decision Precedence Matrix

**Document Status**: Canonical Reference  
**Engine**: `python/policy/engine.py` -> `evaluate_decision()`  

---

## 1. Decision Precedence Architecture

QPort enforces a strict, deterministic multi-gate waterfall for capital allocation decisions. Higher-priority gates dictate the primary decision state and primary reason code, while preserving all downstream and upstream blocking reasons in `blocking_reasons[]`.

### Precedence Waterfall Order

1. **Gate 1: Accounting Failure / Solvency Failure / Structural Deterioration / Value Trap High Risk** (`AVOID` / `SELL_REVIEW` / `SELL`)
2. **Gate 2: Business Review Readiness** (`REVIEW_BUSINESS` if incomplete/UNKNOWN)
3. **Gate 3: Value Trap Insufficient Data** (`REVIEW_BUSINESS`)
4. **Gate 4: Valuation Model Readiness & Base IV Availability** (`WAIT_FOR_MOS` for candidate, `HOLD` for holding)
5. **Gate 5: Margin of Safety (MOS) Threshold** (`WAIT_FOR_MOS` for candidate, `HOLD` for holding)
6. **Gate 6: Personal Balance Sheet (PBS) / Fortress Capital** (`BUILD_RESERVE_FIRST`)
7. **Gate 7: Position Capacity & Portfolio Limits** (`HOLD_NO_NEW_CAPITAL`)
8. **Gate 8: Fully Qualified Allocation Action** (`BUY` for candidate, `BUY_MORE` for holding)

---

## 2. Decision Matrix Table

| Business Review | Value Trap | Valuation / Base IV | MOS Threshold | Personal Balance Sheet | Position Capacity | Existing Holding? | Primary Decision | Primary Reason Code | All Blocking Reasons |
|---|---|---|---|---|---|---|---|---|---|
| `UNKNOWN` | `CLEAR` | `VALID` | 50% (Sufficient) | `SAFE` | < 35% | No | `REVIEW_BUSINESS` | `BUSINESS_REVIEW_INCOMPLETE` | `BUSINESS_REVIEW_INCOMPLETE`, `UNDERSTANDABILITY_UNKNOWN`, `MOAT_UNKNOWN`, `MANAGEMENT_EVIDENCE_UNKNOWN` |
| `UNKNOWN` | `CLEAR` | `VALID` | Insufficient | `UNCONFIGURED` | < 35% | No | `REVIEW_BUSINESS` | `BUSINESS_REVIEW_INCOMPLETE` | `BUSINESS_REVIEW_INCOMPLETE`, `MOS_INSUFFICIENT`, `PERSONAL_BALANCE_SHEET_UNKNOWN` |
| `FAIL` | `CLEAR` | `VALID` | 70% (Cheap) | `SAFE` | < 35% | No | `AVOID` | `STRUCTURAL_DETERIORATION` | `STRUCTURAL_DETERIORATION` |
| `FAIL` | `CLEAR` | `VALID` | 70% (Cheap) | `SAFE` | 10% | Yes | `SELL_REVIEW` | `STRUCTURAL_DETERIORATION` | `STRUCTURAL_DETERIORATION` |
| `BUSINESS_PASS` | `HIGH_RISK` | `VALID` | 40% (Sufficient) | `SAFE` | < 35% | No | `AVOID` | `VALUE_TRAP_HIGH_RISK` | `VALUE_TRAP_HIGH_RISK` |
| `BUSINESS_PASS` | `HIGH_RISK` | `VALID` | 40% (Sufficient) | `SAFE` | 15% | Yes | `SELL_REVIEW` | `VALUE_TRAP_HIGH_RISK` | `VALUE_TRAP_HIGH_RISK` |
| `BUSINESS_PASS` | `INSUFFICIENT_DATA` | `VALID` | 30% (Sufficient) | `SAFE` | < 35% | No | `REVIEW_BUSINESS` | `VALUE_TRAP_INSUFFICIENT` | `VALUE_TRAP_INSUFFICIENT` |
| `BUSINESS_PASS` | `CLEAR` | `INVALID` / None | N/A | `SAFE` | < 35% | No | `WAIT_FOR_MOS` | `VALUATION_UNAVAILABLE` | `VALUATION_UNAVAILABLE` |
| `BUSINESS_PASS` | `CLEAR` | `INVALID` / None | N/A | `SAFE` | 10% | Yes | `HOLD` | `VALUATION_UNAVAILABLE` | `VALUATION_UNAVAILABLE` |
| `BUSINESS_PASS` | `CLEAR` | `VALID` | Price > MOS | `SAFE` | < 35% | No | `WAIT_FOR_MOS` | `MOS_INSUFFICIENT` | `MOS_INSUFFICIENT` |
| `BUSINESS_PASS` | `CLEAR` | `VALID` | Price > MOS | `SAFE` | 15% | Yes | `HOLD` | `MOS_INSUFFICIENT` | `MOS_INSUFFICIENT` |
| `BUSINESS_PASS` | `CLEAR` | `VALID` | Sufficient | `UNCONFIGURED` | < 35% | No | `BUILD_RESERVE_FIRST` | `PERSONAL_BALANCE_SHEET_UNKNOWN` | `PERSONAL_BALANCE_SHEET_UNKNOWN` |
| `BUSINESS_PASS` | `CLEAR` | `VALID` | Sufficient | `UNSAFE` | < 35% | No | `BUILD_RESERVE_FIRST` | `SURVIVAL_RESERVE_INSUFFICIENT` | `SURVIVAL_RESERVE_INSUFFICIENT` |
| `BUSINESS_PASS` | `CLEAR` | `VALID` | Sufficient | `ATTENTION` | 15% | Yes | `HOLD_NO_NEW_CAPITAL` | `SURVIVAL_RESERVE_INSUFFICIENT` | `SURVIVAL_RESERVE_INSUFFICIENT` |
| `BUSINESS_PASS` | `CLEAR` | `VALID` | Sufficient | `SAFE` | >= 35% | Yes | `HOLD_NO_NEW_CAPITAL` | `POSITION_CAP_REACHED` | `POSITION_CAP_REACHED` |
| `BUSINESS_PASS` | `CLEAR` | `VALID` | Sufficient | `SAFE` | 0% | No | `BUY` | `ALL_CRITERIA_SATISFIED` | (None) |
| `BUSINESS_PASS` | `CLEAR` | `VALID` | Sufficient | `SAFE` | 15% | Yes | `BUY_MORE` | `ALL_CRITERIA_SATISFIED` | (None) |
| `FAIL` (Accounting) | `CLEAR` | `VALID` | N/A | `SAFE` | 10% | Yes | `SELL_REVIEW` | `ACCOUNTING_FAILURE` | `ACCOUNTING_FAILURE` |
| `FAIL` (Solvency) | `CLEAR` | `VALID` | N/A | `SAFE` | 10% | Yes | `SELL_REVIEW` | `SOLVENCY_FAILURE` | `SOLVENCY_FAILURE` |
| Confirmed Hard Exit | `CLEAR` | `VALID` | N/A | `SAFE` | 10% | Yes | `SELL` | `CONFIRMED_HARD_EXIT` | `CONFIRMED_HARD_EXIT` |

---

## 3. Decision Enum Definitions

- **`BUY`**: New candidate qualifying under all eligibility, valuation, MOS, and personal fortress gates.
- **`BUY_MORE`**: Existing holding qualifying under all gates with available position capacity (<35%).
- **`HOLD`**: Existing holding where business thesis is intact, but MOS is insufficient for buying more.
- **`HOLD_NO_NEW_CAPITAL`**: Existing holding where personal balance sheet is ATTENTION or position capacity reached 35%.
- **`WAIT_FOR_MOS`**: New candidate where business eligibility is established, but market price exceeds MOS entry limit.
- **`BUILD_RESERVE_FIRST`**: Candidate or holding where personal balance sheet is UNCONFIGURED, UNKNOWN, or UNSAFE.
- **`REVIEW_BUSINESS`**: Security where qualitative evidence or business review is incomplete/UNKNOWN.
- **`AVOID`**: New candidate failing accounting, solvency, structural business, or value trap standards.
- **`SELL_REVIEW`**: Existing holding with confirmed accounting, solvency, or structural business deterioration requiring review.
- **`SELL`**: Rare action reserved strictly for confirmed hard exit conditions.
