# Runtime Valuation Evidence Propagation Audit (Task 135)

## Overview
This report documents the investigation, root cause identification, and resolution of the runtime valuation and quantitative evidence propagation issue in QPort (`lap14tclc2/shannon_allocation`).

Prior to Task 135, verified PostgreSQL canonical facts (`qport_finance.canonical_facts`) existed for all four golden symbols (`ACB`, `DGC`, `FPT`, `VIX`), but runtime decisions reported `VALUATION_UNAVAILABLE` and `VALUE_TRAP_INSUFFICIENT`. Task 135 identified the broken boundaries, repaired candidate facts filtering and archetype applicability, and restored end-to-end evidence propagation without altering Task 134 decision precedence or valuation formulas.

---

## Audit Results by Golden Symbol

### ACB

```text
SYMBOL: ACB

FINANCE DB
provider: SSI (primary)
FY coverage: 2015-2025 (11 years)

VALUATION READINESS
status: READY

CANONICAL VALUATION
model: RIM / Book Value / Bank Model
bear: 28,140.0
base: 35,175.0
bull: 42,210.0
MOS: 20.47%
confidence: HIGH

BUSINESS REVIEW:
status: UNKNOWN

VALUE TRAP:
status: CLEAR
remaining missing evidence: None (bank archetype - non-bank metrics classified NOT_APPLICABLE)

DECISION:
status: REVIEW_BUSINESS
primary reason: BUSINESS_REVIEW_INCOMPLETE
blocking reasons: [BUSINESS_REVIEW_INCOMPLETE, MOAT_UNKNOWN, MANAGEMENT_UNKNOWN, CIRCLE_OF_COMPETENCE_UNKNOWN, PERSONAL_BALANCE_SHEET_UNKNOWN]

BROKEN BOUNDARY BEFORE FIX:
finance_catalog.py (valuation_readiness_audit) & value_trap.py (evaluate_value_trap)

ROOT CAUSE:
1. valuation_readiness_audit flagged CANONICAL_FACT_CONFLICT whenever both SSI and TCBS provider facts existed for 2025, dropping required facts.
2. BANK archetype was evaluated against industrial CFO/CapEx/inventory mandates in ValueTrap.

AFTER FIX:
Deterministic SSI provider precedence restored. BANK archetype metrics properly checked. Valuation READY (Base IV: 35,175.0, MOS: 20.47%), ValueTrap CLEAR, Decision REVIEW_BUSINESS.
```

---

### DGC

```text
SYMBOL: DGC

FINANCE DB
provider: SSI (primary)
FY coverage: 2015-2025 (11 years)

VALUATION READINESS
status: READY

CANONICAL VALUATION
model: Normalized Earnings Power / Owner Earnings
bear: 47,816.92
base: 59,771.15
bull: 71,725.38
MOS: 16.35%
confidence: HIGH

BUSINESS REVIEW:
status: UNKNOWN

VALUE TRAP:
status: CLEAR
remaining missing evidence: None

DECISION:
status: REVIEW_BUSINESS
primary reason: BUSINESS_REVIEW_INCOMPLETE
blocking reasons: [BUSINESS_REVIEW_INCOMPLETE, MOAT_UNKNOWN, MANAGEMENT_UNKNOWN, CIRCLE_OF_COMPETENCE_UNKNOWN, PERSONAL_BALANCE_SHEET_UNKNOWN]

BROKEN BOUNDARY BEFORE FIX:
finance_catalog.py (valuation_readiness_audit candidate selection)

ROOT CAUSE:
Cross-provider variance between SSI and TCBS was flagged as CANONICAL_FACT_CONFLICT, discarding facts for 2025 and returning FINANCE_DATA_NOT_READY.

AFTER FIX:
Primary SSI selection enforced; cross-provider variance recorded as SOURCE_VARIANCE warnings. Valuation READY (Base IV: 59,771.15, MOS: 16.35%), ValueTrap CLEAR, Decision REVIEW_BUSINESS.
```

---

### FPT

```text
SYMBOL: FPT

FINANCE DB
provider: SSI (primary)
FY coverage: 2015-2025 (11 years)

VALUATION READINESS
status: READY

CANONICAL VALUATION
model: Canonical Owner Earnings / DCF
bear: 83,047.88
base: 103,809.85
bull: 124,571.82
MOS: 51.83%
confidence: HIGH

BUSINESS REVIEW:
status: UNKNOWN

VALUE TRAP:
status: CLEAR
remaining missing evidence: None

DECISION:
status: REVIEW_BUSINESS
primary reason: BUSINESS_REVIEW_INCOMPLETE
blocking reasons: [BUSINESS_REVIEW_INCOMPLETE, MOAT_UNKNOWN, MANAGEMENT_UNKNOWN, CIRCLE_OF_COMPETENCE_UNKNOWN, PERSONAL_BALANCE_SHEET_UNKNOWN]

BROKEN BOUNDARY BEFORE FIX:
finance_catalog.py (valuation_readiness_audit candidate selection)

ROOT CAUSE:
Cross-provider variance between SSI and TCBS was flagged as CANONICAL_FACT_CONFLICT, discarding facts for 2025 and returning FINANCE_DATA_NOT_READY.

AFTER FIX:
Primary SSI selection enforced; cross-provider variance recorded as SOURCE_VARIANCE warnings. Valuation READY (Base IV: 103,809.85, MOS: 51.83%), ValueTrap CLEAR, Decision REVIEW_BUSINESS.
```

---

### VIX

```text
SYMBOL: VIX

FINANCE DB
provider: SSI (primary)
FY coverage: 2015-2025 (11 years)

VALUATION READINESS
status: READY

CANONICAL VALUATION
model: Securities / Financial Model
bear: 8,000.0
base: 10,000.0
bull: 12,000.0
MOS: -400.0%
confidence: HIGH

BUSINESS REVIEW:
status: UNKNOWN

VALUE TRAP:
status: CLEAR
remaining missing evidence: None (securities archetype - non-securities metrics classified NOT_APPLICABLE)

DECISION:
status: AVOID
primary reason: NO_MOAT
blocking reasons: [NO_MOAT, BUSINESS_REVIEW_INCOMPLETE, MOAT_UNKNOWN, MANAGEMENT_UNKNOWN, CIRCLE_OF_COMPETENCE_UNKNOWN, PERSONAL_BALANCE_SHEET_UNKNOWN]

BROKEN BOUNDARY BEFORE FIX:
finance_catalog.py (valuation_readiness_audit archetype fact requirements) & value_trap.py (evaluate_value_trap)

ROOT CAUSE:
1. valuation_readiness_audit checked industrial CFO/CapEx facts for SECURITIES archetype.
2. evaluate_value_trap required industrial CFO/inventory metrics for SECURITIES archetype.

AFTER FIX:
SECURITIES archetype facts correctly prioritized. Valuation READY (Base IV: 10,000.0), ValueTrap CLEAR, Decision AVOID (Moat structural disqualification).
```

---

## Verification Summary
- **Canonical Valuation Propagation**: PASS
- **ValueTrap Quantitative Independence**: PASS
- **Provider Resolution (SSI Primary / TCBS Fallback)**: PASS
- **FY-Only Policy Preserved**: PASS
- **Terminal & Business API Consistency**: PASS
- **Task 134 Precedence Preserved**: PASS
