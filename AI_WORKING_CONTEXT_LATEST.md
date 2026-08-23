# QPort AI Working Context — Latest UX Addendum

> Read `AI_WORKING_CONTEXT.md` first, then read this file.
>
> This addendum records the latest user-facing decisions made after the larger handoff was consolidated. When this file conflicts with older UX descriptions in `AI_WORKING_CONTEXT.md`, prefer this file and verified current `main` code.

Last updated: **2026-08-23**

## 1. Fund Manager Review is judgment, not a metric dashboard

The Portfolio-page **Fund manager review** must remain concise and readable for a normal long-term investor.

Its job is to answer:

```text
What would an experienced portfolio manager notice first?
What matters at portfolio level?
What deserves monitoring next?
```

Current presentation:

```text
Manager view
→ one main portfolio-level judgment

Portfolio construction
→ concentration / conviction interpretation

Risk & resilience
→ plain-language portfolio-risk interpretation
→ link to /risk for details

Performance & income
→ plain-language tracked-performance interpretation
→ link to /performance for details

What I would watch next
→ at most a few monitoring priorities
```

### Do not move these advanced fields back into the primary Fund Manager Review

Detailed quantitative/operational evidence belongs elsewhere:

```text
HHI
ERC reference
VaR / CVaR
raw correlation
covariance methodology
risk-contribution tables
tax-lot detail
broker/account counts
operational exception tables
raw observation counts as dashboard tiles
```

The review may use underlying evidence internally to form a conclusion, but it should not expose a dense professional-analytics grid to the normal user.

### Evidence discipline

- If D1 risk history is immature, say the risk conclusion is still building.
- If tracked performance history is short, say so explicitly.
- A concentrated portfolio is not automatically wrong; frame it as conviction + dependence on the largest theses.
- Drawdown is a reason to review drivers/thesis integrity, not an automatic SELL rule.
- Risk contribution is information only.
- The review must never create allocation or trading instructions.

Current implementation:

```text
frontend/src/components/FundManagerReview.jsx
frontend/src/fund-manager-review.css
```

Detailed quantitative analysis remains in:

```text
frontend/src/pages/RiskPage.jsx
```

## 2. Guide is for a normal user, not a developer/operator

The in-app `/guide` page is now an onboarding/manual for someone who simply wants to track a portfolio correctly.

The main guide must **not** start with:

```text
npm
pip
python serve.py
server installation
institutional-lite workflow
settlement internals
NAV restatement internals
tax-lot mechanics
```

Those belong in README/developer docs or optional advanced material.

### Current Guide information architecture

```text
1. Start here
   → sign in
   → import what you already own
   → check Portfolio
   → verify against broker before trusting analytics

2. What each page answers
   → Portfolio
   → Transactions
   → Performance
   → Risk (advanced)

3. Common things you will do
   → existing holding / Position import
   → BUY / rights/new issue
   → SELL
   → correct a mistake
   → dividends

4. Understand the status words
   → READY
   → BUILDING
   → STALE / PARTIAL
   → ERROR

5. Dividends + Risk/Performance concepts
   → explained in normal language

6. If something looks wrong
   → simple troubleshooting

7. Advanced: Data integrity rules
   → collapsed and optional
```

### Guide principles

- Explain the task before the architecture.
- Prefer user-visible terms and examples.
- `BUILDING` is not `ERROR`.
- Missing data is not zero.
- Risk can use older D1 market history.
- Performance must start from actual tracked/effective portfolio history; do not invent historical portfolio performance.
- ERC is an advanced diagnostic reference only, never a target allocation.
- Received dividends section is hidden when no real received dividend event exists.
- Dividend provider duplicates are canonicalized rather than shown as multiple economic events.

Current implementation:

```text
frontend/src/pages/GuidePage.jsx
frontend/src/guide-friendly.css
```

## 3. UX boundary to preserve

QPort should have two layers:

```text
NORMAL USER
plain language
real holdings
real transactions
manager judgment
simple status/readiness
simple troubleshooting

        ↓ progressive disclosure

ADVANCED / AUDIT
Risk technical details
ERC
HHI
VaR/CVaR
methodology
operations
settlement
reconciliation
AI audit export
```

Do not remove the advanced evidence. Keep it available, but do not force the normal user to understand it in order to use the product.

## 4. Regression contracts added/updated

Relevant contracts:

```text
python/portfolio/tests/test_fund_manager_review_contract.py
python/portfolio/tests/test_normal_user_guide_contract.py
python/portfolio/tests/test_risk_readability_and_ai_handoff_contract.py
```

When changing these surfaces, update the implementation and contracts together.
