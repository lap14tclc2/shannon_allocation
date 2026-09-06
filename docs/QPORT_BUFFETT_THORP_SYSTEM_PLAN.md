# QPORT — BUFFETT CORE + THORP OVERLAY
## SYSTEM PLAN

version: 1.0
status: proposed
audience: coding agents / maintainers / portfolio-research agents
target_repo: lap14tclc2/shannon_allocation
reference_architecture: lap14tclc2/recommended_share

---

## 0. DOCUMENT CONTRACT

This file defines **WHAT QPort should become**, the investment philosophy, system boundaries,
module responsibilities, invariants, milestones, and acceptance gates.

It is NOT a low-level coding checklist. Implementation details live in `IMPLEMENTATION.md`.
Runtime task progress should live in `docs/tasks/` or a `TASK_STATE.md` equivalent.

Precedence:

`SYSTEM_PLAN.md > approved ADR > task acceptance criteria > implementation notes > conversation`

Any implementation that violates an invariant requires an ADR before merge.

---

# 1. MISSION

QPort is a long-term Vietnamese equity wealth-management system for retail investors.

Primary objective:

> Own high-quality businesses at sensible prices, size them conservatively,
> preserve capital, avoid unnecessary turnover, and compound wealth over decades.

The system is intentionally NOT:
- a high-frequency or daily rotation engine;
- a pure technical trading system;
- an opaque AI recommendation engine;
- a forced fully-invested optimizer;
- a pure Buffett clone;
- a pure Edward Thorp market-neutral/stat-arb clone.

Target philosophy:

`Buffett Core (~70%) + Thorp Overlay (~30%)`

Meaning:

- **Buffett Core decides WHAT is worth owning.**
- **Thorp Overlay decides HOW MUCH capital should be exposed to each opportunity.**
- **Opportunity-cost logic decides WHEN capital should move.**
- **Cash is a valid allocation.**
- **HOLD is the default action.**

---

# 2. PRIMARY USER QUESTION

Every Allocation evaluation must answer:

> “Given my current portfolio, current valuation, business quality, portfolio risk,
> and available alternatives, do I need to change anything now?”

Valid final actions:

`BUY_MORE | HOLD | WATCH | REDUCE | SELL | KEEP_CASH`

No autonomous execution.

---

# 3. SYSTEM PRINCIPLES

## P1 — BUSINESS FIRST

A security must be investable before it can be allocated.

Investability is determined by:
- business quality;
- financial durability;
- solvency;
- accounting reliability;
- dilution;
- valuation confidence;
- archetype-specific rules;
- hard rejects.

Technical momentum must never turn a fundamentally ineligible stock into a BUY.

## P2 — VALUE IS NOT THE WHOLE SCORE

Valuation is a source of expected return and safety, not the complete portfolio decision.

The system should expose:

`valuation_safety = actual_mos - required_mos`

instead of blindly reusing a broad valuation score that already includes quality/risk.

Avoid double-counting:
- quality;
- leverage;
- cyclicality;
- confidence.

## P3 — RISK DOES NOT PICK STOCKS

Correlation/covariance/ERC/risk contribution decide allocation limits and portfolio fit.

They do NOT decide whether a company is worth owning.

Canonical separation:

`Edge decides WHAT.`
`Risk decides HOW MUCH.`

## P4 — HOLD IS DEFAULT

The engine should prefer no action unless a threshold is crossed.

A new candidate must be materially better after:
- valuation;
- quality;
- portfolio fit;
- transaction cost;
- tax/slippage;
- concentration impact.

## P5 — CASH IS AN ASSET

If there is no compelling opportunity, keep cash.

The system must never force full deployment.

## P6 — NO FAKE EXPECTED ALPHA

Do not display numerical expected alpha until historical calibration is point-in-time safe and passes OOS validation.

Until then use:
- `UNAVAILABLE`;
- `INSUFFICIENT_EVIDENCE`;
- qualitative historical profile.

## P7 — POINT-IN-TIME OR NO BACKTEST CLAIM

Historical Value/Quality backtests must use only data available to the market at the evaluation time.

Required fields:

`period_end, published_at, known_at, received_at, available_from`

Rule:

`analysis_time T must never consume data with available_from > T`

If published date is unknown:
- use a documented conservative availability lag;
- mark provenance as estimated;
- lower research confidence.

## P8 — ONE SOURCE OF TRUTH FOR RISK

Reuse current QPort portfolio risk engine.

Do NOT create a second Thorp risk engine.

Canonical engine owns:
- covariance;
- correlation;
- volatility;
- risk contribution;
- HHI;
- effective positions;
- ERC reference;
- diversification ratio;
- VaR/CVaR;
- downside metrics.

---

# 4. TARGET MODULE MODEL

```text
                   DATA LAYER
                       |
         +-------------+-------------+
         |                           |
 FUNDAMENTAL / FINANCE          MARKET DATA
         |                           |
         v                           v
  BUFFETT CORE                 PRICE FEATURES
 Quality + Valuation        Momentum / Reversal
         |                           |
         +-------------+-------------+
                       |
                INVESTABILITY
                       |
                  pass / fail
                       |
                       v
               OPPORTUNITY ENGINE
                       |
          holdings <-> candidates
                       |
                       v
              THORP RISK OVERLAY
      correlation / covariance / RC / ERC
                       |
                       v
                ALLOCATION ENGINE
                       |
       BUY_MORE / HOLD / REDUCE / SELL / CASH
```

---

# 5. EXISTING QPORT MODULE RESPONSIBILITIES

## `/valuation`

Question:

> “What is this company worth and how safe is the valuation?”

Keep:
- intrinsic value;
- DCF / EPV / owner earnings;
- archetype-specific models;
- dynamic margin of safety;
- valuation confidence;
- hard reject evidence.

Do not turn this page into a portfolio allocator.

## `/risk`

Question:

> “What risks and dependencies exist inside my current portfolio?”

Keep:
- correlation matrix;
- covariance;
- volatility;
- risk contribution;
- ERC reference;
- concentration;
- diversification;
- VaR/CVaR.

Do not produce stock-selection recommendations.

## `/screener`

Question:

> “Which companies deserve further research?”

Role:
- candidate discovery;
- quality filter;
- valuation filter;
- liquidity filter;
- industry/sector filter.

Screener may suggest candidates but MUST NOT output final portfolio BUY actions.

## `/allocation` (new user-facing module)

Question:

> “Where should my capital stay, increase, decrease, or remain as cash?”

This module orchestrates:
- current holdings;
- screener candidates;
- Buffett eligibility;
- valuation safety;
- portfolio fit;
- opportunity cost;
- risk overlay.

Backend may retain internal `thorp` naming if desired, but user-facing name should be `Allocation / Phân bổ vốn`.

---

# 6. BUFFETT CORE

## 6.1 Eligibility

Security status:

`INVESTABLE | WATCHLIST | INELIGIBLE`

Inputs should include:
- quality tier;
- normalized ROE/ROIC;
- owner earnings / FCF;
- earnings and margin stability;
- debt burden;
- cash conversion;
- dilution;
- solvency;
- accounting quality;
- business archetype;
- valuation confidence;
- hard rejects.

Hard-reject examples:
- `SOLVENCY_RISK`
- `ACCOUNTING_UNRELIABLE`
- `UNNORMALIZABLE_EARNINGS`
- `EXCESSIVE_DILUTION`
- `DATA_INSUFFICIENT`

Hard reject => `INELIGIBLE`, regardless of technical strength.

## 6.2 Valuation factor

Preferred primary valuation measure:

`valuation_safety = actual_mos - required_mos`

Secondary:
- intrinsic value gap;
- valuation percentile within comparable universe;
- model confidence;
- valuation-method agreement.

Do NOT map MOS directly to expected alpha.

## 6.3 Quality factor

Quality remains distinct from valuation to avoid double-counting.

Quality evidence should be explainable and deterministic.

---

# 7. THORP OVERLAY

Thorp Overlay is a portfolio risk and sizing layer, not an independent stock-picker.

## 7.1 Inputs

- current portfolio weights;
- candidate proposed weight;
- covariance;
- pairwise and portfolio correlation;
- risk contribution;
- sector exposure;
- concentration;
- effective positions;
- diversification ratio;
- liquidity;
- valuation confidence;
- optional validated factor evidence.

## 7.2 Output

For each investable security:

```text
starter_weight
normal_weight_range
risk_cap
suggested_target
reason_codes[]
```

Reference sizing bands for initial implementation only:

- Starter: 3–5%
- Normal: 7–12%
- High conviction: 12–18%
- Hard position cap: configurable, default 20%

Final target:

`target_weight = min(conviction_weight, risk_cap)`

These are governance defaults, not research-derived alpha weights.

## 7.3 ERC role

ERC is a **risk reference**, not a mandatory portfolio target.

Use it to identify:
- unusually large risk contribution;
- concentration hidden by nominal capital weights.

Never force all positions to ERC weights.

---

# 8. OPPORTUNITY-COST ENGINE

Core rule:

`Sell only when expected future opportunity elsewhere is materially better, or thesis/risk is broken.`

## 8.1 Replacement edge

Before calibrated expected alpha exists:

```text
replacement_advantage =
candidate_opportunity_score
- holding_opportunity_score
- cost_buffer
```

After validated alpha calibration exists:

```text
replacement_edge =
candidate_expected_alpha
- holding_expected_alpha
- transaction_cost
- estimated_slippage
```

Rotation occurs only if threshold is exceeded.

## 8.2 SELL reasons

A SELL/REDUCE may occur only for:
1. thesis invalidation;
2. severe quality deterioration;
3. extreme overvaluation;
4. excessive concentration / risk;
5. materially superior replacement;
6. user-specific liquidity/cash need.

A lower rank alone is not enough.

---

# 9. SCREENER → ALLOCATION CANDIDATE FLOW

```text
Screener
  -> top eligible candidates
  -> Buffett eligibility
  -> valuation safety
  -> portfolio-fit simulation
  -> opportunity comparison
  -> Allocation suggestion
```

`/allocation` should display only a small candidate set, e.g. 3–5 strongest opportunities.

If no candidate crosses the action threshold:

`NO_COMPELLING_NEW_OPPORTUNITY`

and preserve cash / existing holdings.

---

# 10. TECHNICAL FACTORS

Momentum/reversal are secondary.

Allowed uses:
- entry timing;
- staged accumulation;
- warning on deteriorating market behavior;
- relative-strength confirmation;
- avoiding aggressive buying into severe breakdown.

Not allowed:
- overriding fundamental ineligibility;
- becoming the primary long-term thesis;
- generating automatic high-turnover rotation.

Initial technical features may include:
- 3M/6M/12M momentum;
- 1M reversal;
- relative strength vs VNIndex;
- volatility regime.

They must be empirically validated later.

---

# 11. RESEARCH LAYER

The research layer exists to validate or reject investment hypotheses.

Required pipeline:

```text
Raw data
 -> PIT-safe snapshots
 -> factor values
 -> future benchmark-relative outcomes
 -> IC / quantile spread
 -> walk-forward
 -> sealed OOS
 -> factor confidence
 -> optional expected-alpha calibration
```

Required first benchmark:
`VNINDEX`

Target:
`forward_excess_return = stock_forward_return - VNINDEX_forward_return`

Do not optimize for hit rate alone.

Primary research metrics:
- Rank IC;
- top-bottom quantile spread;
- excess CAGR;
- Information Ratio;
- Sharpe;
- max drawdown;
- turnover;
- cost-adjusted performance;
- regime stability;
- exposure concentration.

---

# 12. DATA TRUTH / EVIDENCE MODEL

Borrow the strongest principle from `recommended_share`:
every research claim must be traceable to time-valid evidence.

For factor snapshot / recommendation evidence:

```text
evidence_id
symbol
factor
as_of
known_at
received_at
source
source_record_id
status
freshness
confidence
```

No recommendation should depend on:
- stale critical valuation facts without warning;
- data known only after the decision timestamp;
- fabricated fallback values;
- silent provider substitution.

---

# 13. DECISION OUTPUT CONTRACT

Per holding:

```json
{
  "symbol": "FPT",
  "eligibility": "INVESTABLE",
  "business_quality": "HIGH",
  "valuation_status": "FAIR",
  "valuation_safety": -0.06,
  "current_weight": 0.28,
  "risk_contribution": 0.41,
  "portfolio_fit": "MODERATE",
  "action": "HOLD",
  "target_range": [0.10, 0.16],
  "reason_codes": [
    "QUALITY_STRONG",
    "VALUATION_NOT_CHEAP",
    "RISK_CONTRIBUTION_HIGH",
    "NO_SUPERIOR_REPLACEMENT"
  ],
  "confidence": "MEDIUM"
}
```

Per candidate:

```json
{
  "symbol": "VNM",
  "source": "SCREENER",
  "eligibility": "INVESTABLE",
  "candidate_rank": 2,
  "portfolio_fit": "GOOD",
  "action": "BUY_MORE",
  "starter_weight": 0.05,
  "reason_codes": []
}
```

Portfolio summary:

```json
{
  "posture": "HOLD_SELECTIVE_BUY",
  "cash_current": 0.10,
  "cash_suggested_range": [0.08, 0.15],
  "no_action_required": false
}
```

---

# 14. UI PRINCIPLES

## Homepage

Answer only:
1. portfolio value;
2. long-term return;
3. portfolio quality;
4. major risk;
5. whether action is required.

Preferred state:

`NO ACTION REQUIRED`

is a first-class positive outcome.

## Allocation Page

Sections:
1. Portfolio Verdict
2. Holdings Allocation Table
3. New Opportunities (3–5 max)
4. Proposed Changes
5. Risk Impact Before/After
6. Evidence / confidence
7. Create Transaction Draft

No auto-trade.

---

# 15. ACTION CADENCE

Data may refresh daily.

Decision cadence:
- Daily: data + risk monitoring
- Weekly: opportunity/watchlist review
- Quarterly: full fundamental thesis review
- Event-driven: earnings, major corporate event, material valuation/risk break
- Trades: threshold-triggered only

Avoid daily top-N rotation.

---

# 16. IMPLEMENTATION MILESTONES

## M0 — Architecture Contract
- add plan/spec documents;
- define invariants;
- architecture tests.

## M1 — Allocation V1 using current data
- reuse current valuation;
- reuse current risk engine;
- consume screener candidates;
- deterministic rule-based actions;
- no expected alpha;
- no Kelly.

## M2 — Buffett Portfolio Intelligence
- thesis state;
- quality trend;
- valuation trend;
- conviction / allocation bands;
- explicit reason codes.

## M3 — PIT Research Foundation
- publication/availability timestamps;
- VNIndex benchmark;
- PIT-safe historical snapshots;
- no-look-ahead tests.

## M4 — Factor Validation
- Value;
- Quality;
- Momentum;
- Reversal;
- forward excess returns;
- IC / quantiles / walk-forward / OOS.

## M5 — Evidence-Calibrated Allocation
- factor confidence;
- optional expected-alpha model;
- opportunity-cost calibration;
- adaptive but conservative weights.

## M6 — Forward Paper Validation
- use multi-portfolio to maintain a model portfolio;
- compare model vs user actual;
- monitor live forward results;
- detect factor decay.

---

# 17. NON-GOALS FOR V1

Do not implement in V1:
- Kelly sizing;
- numeric expected alpha;
- ML model;
- auto execution;
- macro prediction engine;
- daily rebalance;
- VNIndex direction prediction;
- futures hedging;
- high-frequency signals;
- duplicate risk engine.

---

# 18. ACCEPTANCE GATES

System cannot be called production Thorp allocation until:

### V1 Gate
- deterministic output;
- explanation reason codes;
- valuation and risk engines reused;
- no double-counting;
- no auto trade;
- no fake alpha.

### PIT Gate
- historical finance facts have `available_from`;
- tests prove no fact is visible before availability;
- benchmark alignment verified.

### Research Gate
- factor snapshots reproducible;
- forward returns reproducible;
- IC/quantile spreads reported;
- costs included.

### OOS Gate
- chronological OOS;
- sealed period;
- no parameter tuning on sealed period;
- results survive costs;
- regime sensitivity reported.

### Capital Gate
Only after all above:
- expected alpha may be displayed;
- fractional Kelly may be researched;
- never enable full Kelly by default.

---

# 19. FINAL TARGET

The final product should behave like:

> Buffett chooses durable businesses and demands a sensible price.
> Thorp prevents us from over-betting correlated risks.
> QPort moves capital only when the new opportunity is materially superior.
> Time and compounding do the rest.

Core identity:

`QPort = Long-Term Capital Allocation System`

not:

`QPort = Trading Signal Generator`
