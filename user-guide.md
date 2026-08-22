# Shannon Allocation — User Guide

This guide describes the current production/research workflow.

The default product mode is now **Dynamic Alpha + Allocation**. The machine no longer tries to find one static stock combination that must survive every market regime. Instead, at each recalibration it re-ranks the configured universe using only information that existed before that signal, selects the strongest diversified names, and then lets ERC/risk/Shannon manage the portfolio.

The execution core remains:

```text
strictly-past alpha selection
→ ERC relative risk weights
→ optional absolute-volatility exposure overlay
→ Shannon drift bands
→ transaction costs / execution lag
```

ERC still owns relative portfolio weights. The alpha layer selects membership; it does not optimize arbitrary weights.

---

## 1. Start the application

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

The optimizer is the application start page:

```text
http://127.0.0.1:8080/
```

`/optimizer` remains an alias.

---

## 2. Default workflow: Dynamic Alpha

```text
Universe (All / VN100 / VN50 / VN30)
        ↓
At each recalibration use STRICTLY PAST prices only
        ↓
3M momentum
6M momentum
12M momentum
trend
52-week drawdown quality
short-horizon volatility penalty
        ↓
cross-sectional Alpha Score
        ↓
correlation diversification filter
        ↓
select N active stocks
        ↓
ERC relative weights
        ↓
volatility exposure overlay
        ↓
Shannon daily drift management
        ↓
optimize 1–6 recalibrations/year + timing
        ↓
rolling OOS validation
        ↓
recent pre-holdout validation
        ↓
FINAL HOLDOUT: PASS / REJECT ONLY
```

Default active portfolio size is **7 stocks**. Five to seven stocks is the intended growth-concentration range; 8–10 remains available when more diversification is desired.

The stock list may change at every recalibration. For example:

```text
Event 1: A B C D E F G
Event 2: A C D H I J K
Event 3: C H I L M N O
```

This is intentional. Market leadership is allowed to change instead of forcing one static combination through every regime.

---

## 3. Alpha Score methodology

The alpha rule is deliberately fixed and transparent. Its coefficients are **not optimizer genes** and are not tuned against the final holdout.

For each eligible ticker, strictly before the signal date, the engine computes cross-sectional normalized features and combines them approximately as:

```text
20%  3M momentum
25%  6M momentum
30%  12M momentum
15%  trend
10%  drawdown quality
-10% volatility penalty
```

Longer-horizon features that are unavailable early in history are neutral rather than treated as positive signals.

A ticker must also have a fresh observation immediately before selection. Stale/suspended names are not eligible for a new allocation.

After ranking, the engine applies a correlation filter. The primary maximum pair-correlation threshold is 0.80. If the universe cannot fill the requested portfolio, the selector relaxes the threshold deterministically rather than silently returning too few stocks.

The selector answers only:

> Which stocks should be active now?

ERC then answers:

> How should risk be distributed among those active stocks?

---

## 4. Optional fixed-combination mode

Choose **Use my own combination** when you want to own the symbol-selection decision.

You may select or import 5–10 symbols, for example:

```text
ACB, FPT, REE, VCB, VNM
```

The fixed-combination health check evaluates research-only:

- data coverage;
- 63D / 252D correlation;
- correlation clusters;
- diversification ratio;
- ERC feasibility.

Suggestions never auto-replace a ticker. The user must explicitly apply a suggestion. After approval, symbols remain fixed and only recalibration frequency/timing are optimized.

---

## 5. Capital plan

Enter:

- **Initial balance (VND)**;
- **Money added each year (VND)**.

Annual contributions are external cash flows. Performance measurement neutralizes those flows so deposits do not create fake investment returns.

Reports distinguish:

```text
cash contribution
≠
actual equity deployment
```

and record BUY cash deployed, SELL cash released and remaining cash.

---

## 6. Risk policy

Normal controls are:

- **Target volatility**;
- **Maximum OOS drawdown**;
- **Maximum single-stock weight**.

The default strategic minimum market exposure is **0%**. Therefore a valid volatility estimate may de-risk all the way to cash.

The advanced **Strategic minimum market exposure** setting is optional. It applies only when risk estimation is valid.

Missing/invalid risk data is a different state:

```text
valid risk estimate
→ volatility target determines exposure
→ optional strategic floor may apply

risk estimate unavailable
→ strategic floor does NOT override safety
→ fail closed to 0% equity
```

Allocation diagnostics distinguish these states explicitly.

---

## 7. Initial deployment and recalibration timing

The optimized 1–6 events are **recalibrations**, not permission to leave a new portfolio in cash until the first optimized date.

Initial deployment is independent:

```text
historical warm-up
        ↓
alpha selection becomes feasible
        ↓
ERC solves successfully
        ↓
risk target is deployable
        ↓
INITIAL DEPLOYMENT
        ↓
1–6 optimized RECALIBRATIONS/year
```

This prevents a late timing gene such as `[221]` from receiving artificially low TRAIN drawdown just because the portfolio waited in cash.

Between recalibrations, Shannon drift checks and risk refreshes continue normally.

Partial calendar years do not clamp missing event indices onto the final available date. Missing events are skipped and reported.

Quarterly `[1, ~61, ~122, ~183]` remains a simple benchmark only.

---

## 8. Growth ranking and live eligibility

Research is **growth-first**, but risk is not removed.

The current pre-holdout policy separates hard failures from smooth quality:

### Hard gates

```text
rolling OOS P10 return must be non-negative
rolling OOS drawdown must stay inside the configured MDD ceiling
recent pre-holdout return must not be catastrophically below -5%
```

### Soft risk/reward quality

These are no longer binary cliffs:

```text
TRAIN Calmar
validation median return / worst drawdown
recent Calmar
```

They form an explainable 0–100 quality score. A candidate with Calmar 0.34 is therefore not categorically different from one with 0.36.

The soft score weights evidence approximately:

```text
20% TRAIN quality
45% rolling OOS quality
35% recent quality
```

For Dynamic Alpha, the frozen pre-holdout winner is ranked using growth evidence plus this quality score. The final holdout is not part of that ranking.

---

## 9. Research integrity

The global final holdout is reserved before research selection:

```text
TRAIN / timing search
        ↓
rolling OOS validation
        ↓
recent pre-holdout validation
        ↓
freeze winner
════════════════════════════
FINAL HOLDOUT
════════════════════════════
PASS / REJECT ONLY
```

If the frozen winner fails the holdout, the system rejects it. It must **not** switch to another candidate simply because that candidate happened to perform better after the holdout was inspected.

The alpha coefficients are also fixed methodology rather than optimizer variables. This reduces the degrees of freedom available for backtest overfitting.

Because previously observed historical holdouts have already been inspected during development, do not treat repeated success on those same dates as fresh proof of future performance. New unseen market data is the meaningful next validation source.

---

## 10. Search quality

Dynamic Alpha no longer searches millions of static symbol combinations. Membership is determined by the alpha rule, so the optimizer mainly explores recalibration frequency/timing.

Presets:

- **Fast** — quick timing exploration;
- **Balanced** — recommended default;
- **Thorough** — wider frequency/timing coverage.

The optimizer may choose 1, 2, 3, 4, 5 or 6 recalibrations per year, subject to cyclic spacing constraints.

Multi-process candidate evaluation remains available automatically.

---

## 11. Results and audit files

After completion:

```text
/optimizer/<experiment_id>
```

Results include:

- selected recalibration count and trading-session positions;
- TRAIN metrics;
- rolling OOS metrics;
- recent pre-holdout validation;
- final assessment holdout;
- soft live-quality score;
- transaction costs and turnover;
- equity exposure;
- initial deployment diagnostics;
- Dynamic Alpha selection history;
- unique symbols touched;
- membership turnover;
- maximum selected correlation where available;
- quarterly benchmark comparison.

Use **Download all data (ZIP)** for full audit.

Dynamic Alpha reports label the portfolio as `DYNAMIC_ALPHA`; an empty static symbol field does **not** mean a zero-stock portfolio. `n_symbols` represents the active portfolio size, and membership history records the actual tickers selected at each event.

---

## 12. Core invariants

The growth refactor changes symbol selection, not the execution theory:

- alpha selection uses strictly-past market data;
- ERC remains deterministic and covariance-driven;
- alpha does not assign arbitrary weights;
- risk overlay remains explicit;
- Shannon drift logic remains rule-based;
- transaction costs and execution lag remain modeled;
- recommendation is not execution;
- missing risk data fails closed;
- final holdout never generates or re-ranks candidates.

Dynamic Alpha is a research framework for pursuing stronger persistent growth; it does **not** guarantee a target CAGR or x3/x4 capital outcome.
