# Shannon Allocation — User Guide

This is the operating guide for the current product workflow.

The default product mode is now **Joint Growth Search**: the machine searches the stock combination together with the annual ERC/risk recalibration frequency and timing. A manual fixed-combination mode remains available when the user wants to own the symbol-selection decision.

The quantitative execution core remains:

```text
ERC relative risk weights
→ optional absolute-volatility exposure overlay
→ Shannon drift bands
→ transaction costs / execution lag
```

The optimizer does **not** optimize arbitrary stock weights. ERC still determines relative weights from covariance using only information available before each signal.

---

## 1. Product workflow

### Default: Joint Growth Search

```text
Universe (All / VN100 / VN50 / VN30)
        ↓
Machine searches exact-N stock combination
        ↓
Initial deployment as soon as calibration is ready
        ↓
Machine searches 1–6 ERC/risk recalibration events per year
        ↓
Machine searches the trading-session positions of those events
        ↓
ERC relative weights
        ↓
Risk overlay
        ↓
Shannon daily drift management
        ↓
Rolling OOS validation + hard MDD gate
        ↓
Recent pre-holdout validation
        ↓
Untouched final holdout
```

Search/ranking is **growth-first**. Drawdown is not removed; it is enforced as a hard OOS/final validation constraint instead of being rewarded so strongly during TRAIN that the search collapses toward ultra-defensive low-return portfolios.

### Optional: Use my own combination

```text
User selects/imports 5–10 symbols
        ↓
Combination health check
        ↓
Optional user-approved diversification suggestions
        ↓
Symbols frozen
        ↓
Initial deployment as soon as calibration is ready
        ↓
Machine searches 1–6 recalibration events + timing
        ↓
Same ERC / risk / Shannon / OOS pipeline
```

---

## 2. Start the application

```bash
git checkout main
git pull origin main

cd frontend
npm ci
npm run build
npm run build:ssr

cd ../python
pip install -r requirements.txt
python serve.py
```

Default address:

```text
http://127.0.0.1:8080
```

Open the optimizer:

```text
http://127.0.0.1:8080/optimizer
```

---

## 3. Search mode

### 3.1 Optimize combination + allocation

This is the default.

Choose:

- search universe: All data, VN100, VN50 or VN30;
- exact portfolio size: 5–10 stocks.

The machine is allowed to change symbols during research search.

It also searches the annual recalibration frequency. The candidate genome may contain **1–6 recalibration events per year**. With the current 40-session cyclic minimum gap, six is approximately the natural maximum for a normal Vietnamese trading year.

The system then searches the actual trading-session positions of those events.

Quarterly allocation is retained only as a **benchmark**, not as a constraint.

### 3.2 Use my own combination

Select checkboxes or paste an existing composition, for example:

```text
ACB, FPT, REE, VCB, VNM
```

or:

```json
["ACB", "FPT", "REE", "VCB", "VNM"]
```

The health check evaluates research-only data coverage, 63D/252D correlation, correlation clusters, diversification and ERC feasibility. Suggestions never auto-replace a ticker; the user must explicitly apply them.

After approval, symbols remain fixed while frequency/timing are optimized.

---

## 4. Capital plan

Enter:

- **Initial balance (VND)**;
- **Money added each year (VND)**.

Annual contributions are external cash flows. Reports distinguish:

- contribution date;
- actual deployment date;
- BUY cash deployed;
- SELL cash released;
- remaining cash.

Performance metrics neutralize external contributions so deposits do not create fake investment returns.

---

## 5. Risk policy

Normal user controls are:

- target volatility;
- maximum OOS drawdown;
- maximum single-stock weight.

The default strategic minimum market exposure is **0%**. That means a valid volatility estimate is allowed to reduce equity exposure all the way to cash when risk becomes high.

The strategic floor is available only in **Advanced Risk Settings**. A non-zero value means: even when volatility targeting would prefer less equity, keep at least that configured market exposure.

Missing/invalid risk data is a separate state and always uses the fail-closed policy:

```text
valid risk estimate
→ volatility target decides exposure
→ optional advanced strategic floor may apply

risk estimate unavailable
→ strategic floor does NOT apply
→ fail closed to 0% equity / cash
```

This distinction is important: **volatility de-risking** and **risk-data failure** are not the same thing and are reported separately in allocation diagnostics.

The intended philosophy remains:

```text
SEARCH / RANKING: growth first
RISK: hard validation gate
```

A candidate that breaches the configured OOS drawdown ceiling is rejected even when its TRAIN return is high.

---

## 6. Initial deployment vs recalibration frequency

A new research portfolio no longer waits for the optimizer's first annual timing event before investing.

The system first finds the earliest look-ahead-free date where strictly-past aligned history is sufficient to calibrate ERC. That date is treated as **INITIAL DEPLOYMENT**.

```text
historical warm-up
        ↓
ERC/risk calibration becomes valid
        ↓
INITIAL DEPLOYMENT
        ↓
measurement / ongoing portfolio
        ↓
1–6 optimized RECALIBRATION events per year
```

This prevents a late schedule such as `[221]` from receiving artificially low TRAIN drawdown simply because the portfolio sat in cash waiting for session 221.

The 1–6 candidate events therefore mean **ERC/risk target recalibrations**, not the initial act of putting a new portfolio to work.

Shannon drift checks continue between recalibration events according to the strategy rules.

The optimizer currently searches:

```text
1, 2, 3, 4, 5 or 6 recalibration events per year
```

and the valid trading-session positions for each count, respecting the cyclic minimum-gap rule.

Examples of valid candidate schedules may look like:

```text
[121]
[35, 163]
[28, 112, 201]
[1, 61, 122, 183]
[15, 63, 111, 159, 207]
[1, 41, 81, 121, 161, 201]
```

The number of events is selected by research performance; four is no longer privileged except as the simple quarterly benchmark.

---

## 7. Search quality

For Joint Growth Search:

- **Fast** — quick combination/frequency/timing exploration;
- **Balanced** — recommended default;
- **Thorough** — larger real + surrogate search.

Large-universe standard presets are automatically adapted by the backend to reduce expensive real simulations while increasing cheap surrogate coverage.

Multi-core candidate evaluation remains enabled automatically.

---

## 8. Research integrity

The global final holdout is reserved before symbol screening or candidate generation.

```text
TRAIN / screening / NSGA / surrogate
        ↓
rolling validation
        ↓
recent pre-holdout validation
        ↓
════════════════════════════
UNTOUCHED FINAL HOLDOUT
════════════════════════════
```

Do not repeatedly modify the algorithm to fit the same observed holdout return. The holdout is an assessment layer, not a feature generator.

---

## 9. Results

After completion:

```text
/optimizer/<experiment_id>
```

The report contains:

- selected symbols;
- optimized recalibration count and trading-session positions;
- initial-deployment date;
- TRAIN metrics;
- rolling OOS metrics;
- recent validation;
- final holdout;
- capital/deployment history;
- transaction costs;
- risk exposure and explicit risk state;
- timing and symbol robustness diagnostics;
- comparison against the simple quarterly schedule for the same symbol set.

Use **Download all data (ZIP)** for audit/review.

---

## 10. Core invariants

The refactor changes the research search space, not the portfolio mechanics:

- ERC remains deterministic and covariance-driven;
- risk overlay remains explicit;
- strategic minimum exposure defaults to 0%;
- missing risk data fails closed independently of the strategic floor;
- initial deployment is separate from optimized annual recalibration frequency;
- Shannon drift logic remains rule based;
- transaction costs and execution lag remain modeled;
- recommendation is not execution;
- final holdout is never used to generate a candidate.
