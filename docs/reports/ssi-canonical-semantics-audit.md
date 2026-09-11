# SSI Canonical Semantics Audit (Task 132C)

## Overview
This report documents the semantic correctness repair of the SSI raw financial data to canonical fact conversion pipeline in QPort (`lap14tclc2/shannon_allocation`).

Prior to Task 132C, line item mapping used unsafe fuzzy substring patterns (`pattern in normalized`), causing child line items (e.g. brokerage revenue, specific receivables) to be falsely mapped to aggregate canonical codes. Additionally, workbook processing executed destructive `DELETE FROM canonical_facts` statements, duplicate semantic payloads were re-read without payload-level deduplication, and cross-provider differences were falsely flagged as canonical conflicts.

Task 132C replaced fuzzy matching with exact normalized alias matching, implemented logical semantic payload deduplication while preserving physical file provenance, added deterministic derived total debt (`BS.DEBT.TOTAL`) calculation with archetype isolation, established explicit payload conflict reporting, and rebuilt the SSI canonical layer on PostgreSQL (`qport_finance.canonical_facts`).

---

## MAPPING

### Exact aliases
- Enforced strict exact string matching in `map_ssi_line_item()` via `CANONICAL_LINE_MAPPINGS`.
- Added explicit normalized line item entries for Income Statement (`"doanh so thuan"`, `"lailo thuan sau thue"`, `"lai gop"`, `"lailo tu hoat dong kinh doanh"`, `"lailo rong truoc thue"`, `"loi nhuan cua co dong cua cong ty me"`), Balance Sheet (`"tong cong tai san"`, `"tong nguon von"`, `"von va cac quy"`), and Cash Flow (`"luu chuyen tien thuan tu cac hoat dong kinh doanh"`).

### Removed unsafe fuzzy aliases
- Removed fuzzy loop `for norm_pattern, code in mapping_dict.items(): if norm_pattern in normalized or normalized.startswith(norm_pattern):`.
- Child line items (`"Doanh thu hoạt động môi giới chứng khoán"`, `"Phải thu khách hàng"`, `"Vay ngắn hạn ngân hàng ABC"`, `"Chi phí thuế TNDN hiện hành"`) stay `UNMAPPED` and no longer overwrite aggregate canonical facts.

---

## SEMANTIC PAYLOADS

```text
physical files: 3,783
logical payloads: 1,170
same-payload export groups: 2,613
different-payload groups: 0 (all duplicate export files shared identical financial payloads)
conflicted payload groups: 0 (exported to docs/reports/ssi-payload-conflicts.csv)
```

---

## CANONICAL FACTS

```text
before: 117,759 SSI canonical facts
after: 106,963 SSI canonical facts (eliminated 10,796 false-positive fuzzy mapping facts)
derived: 3,416 BS.DEBT.TOTAL facts (derived deterministically for industrial enterprise symbols)
unmapped rows: 4,920 (retained in ssi_raw_financial_observations for audit provenance)
```

---

## PROVIDER RESOLUTION

```text
SSI primary: PASS (SSI selected deterministically when valid SSI fact exists)
TCBS fallback: PASS (TCBS used deterministically when SSI fact is missing)
Source variance handling: PASS (recorded as SOURCE_VARIANCE warnings; no false valuation blocks)
True conflict handling: PASS (only same-provider unresolved conflicts flag CANONICAL_FACT_CONFLICT)
```

---

## ACCOUNTING RECONCILIATION

### AAA
```text
history depth: 15 FY (2011–2025)
balance sheet equation: PASS (Assets = Liabilities + Equity)
cash flow ending cash: PASS
cash continuity: PASS
PAT reconciliation: PASS
```

### AAH
```text
history depth: 6 FY (2020–2025)
balance sheet equation: PASS
statement usability: PASS (6Y history depth preserved without false DEEP_HISTORY upgrade)
```

### VIX
```text
history depth: 15 FY (2011–2025)
archetype: SECURITIES
cash continuity: CASH_CONTINUITY_VARIANCE (FY2014 ending cash vs FY2015 beginning cash flagged)
tax reconciliation: AGGREGATE_COMPONENT_INCONSISTENCY (FY2014 aggregate tax row 0 vs non-zero current tax component flagged)
```

---

## GOLDEN RUNTIME

### ACB
```text
Valuation readiness: READY
Selected provider: SSI (primary for IS/BS/CF, TCBS fallback for bank debt)
Conflicts: 0
Archetype: BANK (RIM / equity model, no CFO/CapEx/inventory requirement)
```

### DGC
```text
Valuation readiness: READY
Selected provider: SSI (primary)
Conflicts: 0
Archetype: NORMAL_ENTERPRISE / Cyclical (Normalized Owner Earnings)
```

### FPT
```text
Valuation readiness: READY
Selected provider: SSI (primary)
Conflicts: 0
Archetype: NORMAL_ENTERPRISE (Owner Earnings DCF)
```

### VIX
```text
Valuation readiness: READY
Selected provider: SSI (primary)
Conflicts: 0
Archetype: SECURITIES (Securities Financial Model)
```
