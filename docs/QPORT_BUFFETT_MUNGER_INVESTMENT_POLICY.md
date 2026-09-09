# QPort Buffett–Munger Canonical Investment Policy

> **Document Status:** Authoritative System Policy  
> **Task Reference:** [TASK-20260909-116](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260909-116-qport-buffett-munger-investment-policy.md)  
> **Scope:** Entire QPort Architecture (Policy Engine, Value Engine, Allocation, UI, AI Coach)

---

## 1. Core Philosophy & Principles

QPort is a personal capital decision system built on the investment principles of Warren Buffett and Charlie Munger.

### Canonical Product Principle
> **Strong personal balance sheet + great businesses + sensible prices + patience = durable compounding.**

### Canonical Decision Principle
> **QPort must optimize for durable compounding, not trading activity, volatility minimization, or short-term portfolio optimization.**

---

## 2. Decision Precedence Order

Every decision in QPort MUST follow this strict evaluation sequence:

```text
1. Personal capital durability (Survival reserve & fortress health)
2. Circle of competence (Understandability & business bounds)
3. Business quality (Economic moat & competitive advantage)
4. Financial strength (Solvency & balance sheet resilience)
5. Earnings durability (Owner earnings & cash conversion)
6. Management / capital allocation (Retained earnings productivity)
7. Intrinsic value (Conservative Bear / Base / Bull DCF & RIM)
8. Margin of Safety (Required discount based on business quality)
9. Position sizing / cost of being wrong (Portfolio capacity & concentration)
10. Long-term compounding (Holding through noise)
```

---

## 3. Explicitly Prohibited Relationships & Triggers

The following triggers and automatic decisions are strictly **PROHIBITED** across all core decision modules:

| Prohibited Trigger | Prohibited Automatic Action | Permitted Role in QPort |
|---|---|---|
| Volatility is high | `SELL` | Advanced diagnostic metric only |
| Risk contribution / ERC high | `REDUCE` / `SELL` | Advanced diagnostic metric only |
| Portfolio drawdown increases | `SELL` / `REBALANCE` | Diagnostic metric for crash stress engine |
| Stock price drops | `BUY_MORE` | Price drop alone does not justify buying |
| Unrealized gain is high | `TAKE_PROFIT` | Price appreciation of a great business is encouraged |
| Target weight deviation | Automatic rebalance trade | Portfolio sizing limit only |
| Technical indicator / Chart pattern | Any investment decision | Excluded from QPort core engine |

---

## 4. Canonical Decision States & Rules

QPort produces exactly 10 deterministic decision states. Same input context MUST produce the same state.

```text
BUY
BUY_MORE
HOLD
HOLD_NO_NEW_CAPITAL
WAIT_FOR_MOS
BUILD_RESERVE_FIRST
REVIEW_BUSINESS
AVOID
SELL_REVIEW
SELL
```

### 4.1 State Definitions & Precedence Hierarchy

```python
if personal_survival_reserve_unsafe:
    BUILD_RESERVE_FIRST

elif accounting_unreliable or critical_data_conflicted:
    AVOID (new candidate) or SELL_REVIEW (existing holding)

elif solvency_failure:
    AVOID (new candidate) or SELL_REVIEW (existing holding)

elif business_quality_fail or value_trap_high_risk:
    AVOID (new candidate) or REVIEW_BUSINESS (existing holding)

elif valuation_invalid or base_iv_unavailable:
    WAIT_FOR_MOS or REVIEW_BUSINESS

elif price > base_iv * (1 - required_mos):
    WAIT_FOR_MOS

elif position_capacity_exceeded:
    HOLD_NO_NEW_CAPITAL

elif business_pass and value_trap_clear and mos_sufficient and capital_available:
    BUY (new candidate) or BUY_MORE (existing holding)

else:
    HOLD
```

---

## 5. First-Class UNKNOWN & Missing-Data Degradation

### 5.1 Canonical Invariants
- `NULL != 0`: Missing numeric fields must never be replaced with zero.
- `MISSING != SAFE`: Missing liability or risk data does not imply safety.
- `UNKNOWN != PASS`: Unavailable qualitative evidence (moat, management) must never default to `PASS`.
- `CONFLICTED != VALID`: Data discrepancies between sources block automatic buying.

### 5.2 Qualitative Dimensions
Allowed qualitative states: `PASS`, `WATCH`, `FAIL`, `UNKNOWN`, `NOT_APPLICABLE`.
- If moat or management quality is `UNKNOWN`, decision degrades to `REVIEW_BUSINESS` or requires user policy override.

---

## 6. Personal Balance Sheet Integration

Deployable capital is NOT equal to total cash.

$$\text{Available Long-Term Capital} = \text{Deployable Cash} + \text{New Contributions} + \text{Reinvestable Dividends} - \text{Survival Reserve Target} - \text{Near-Term Liabilities}$$

If $\text{Available Long-Term Capital} \le 0$, decision for all buy candidates becomes:
```text
BUILD_RESERVE_FIRST
```

---

## 7. Value Trap Gate & Precedence

Attractiveness of $P < \text{Base IV}$ is invalid unless the Value Trap Gate passes.

Execution order:
```text
Business Review -> Value Trap Gate -> Valuation/MOS -> Balance Sheet -> Position Capacity -> Decision
```

If Value Trap Gate status is `HIGH_RISK`, decision MUST be `REVIEW_BUSINESS` or `AVOID`.

---

## 8. Concentration & No-Action Semantics

### Concentration
High weight in a great business does NOT trigger an automatic sale.
Risk is evaluated as:
$$\text{Weight} \times \text{Cost of Being Wrong} \times \text{Permanent Loss Severity}$$
High concentration limits new capital deployment (`HOLD_NO_NEW_CAPITAL`) without forcing liquidation.

### No-Action Outcome
`HOLD` / `NO ACTION REQUIRED` is a primary successful outcome of QPort. The system celebrates patience and avoiding unnecessary turnover.
