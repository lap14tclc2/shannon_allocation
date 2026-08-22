# Risk-Aware Exact-N Optimizer

This branch adds a drawdown-focused layer around the existing ERC/Shannon engine without replacing ERC.

## What changed

- User chooses an exact portfolio size (`5..10`).
- ERC still determines relative stock weights.
- Optional volatility targeting determines total equity exposure; unused exposure stays in cash.
- Fast/slow portfolio volatility: 63D and 252D by default; the higher estimate controls exposure.
- Optional max single-stock weight.
- CDaR95, underwater ratio, and longest underwater period are reported.
- Validation and final holdout can enforce a hard maximum-drawdown budget.
- Missing/stale closes are no longer forward-filled into covariance/risk estimation. Forward-fill is only used for valuation.
- Slippage is charged using an adverse actual execution price on both buys and sells.
- The last 252 sessions are one globally untouched final holdout.

## Faster search for ~90 symbols

The exact combinatorial search is far too large to enumerate. The optimizer now uses:

1. **TRAIN-only pre-screen**: e.g. 90 -> 45 symbols using data quality + individual risk/quality.
2. **Random real baseline**: default 250 candidates.
3. **NSGA-II**: default population 60 / 30 generations, exact-N genome, optional early stop.
4. **Surrogate ranking**: default 5,000 candidates are scored cheaply; only 40 are promoted to real TRAIN backtests.
5. **Racing shortlist**: only ~180 diverse TRAIN candidates receive full rolling VALIDATION.
6. **Finalists only**: neighbourhood robustness + one untouched 252-session FINAL HOLDOUT.

Validation/test information is never used in the pre-screen or surrogate.

## Recommended first experiment

Use the web optimizer or CLI. Start with **7 stocks** and the full available/VN100-style universe.

```bash
cd python
pip install -r requirements.txt
python optimize_main.py \
  --universe all \
  --portfolio-size 7 \
  --population 60 \
  --generations 30 \
  --random 250 \
  --preselect-top 45 \
  --robust-pool 180 \
  --surrogate-pool 5000 \
  --surrogate-proposals 40 \
  --early-stop 15 \
  --risk-overlay \
  --target-vol 0.18 \
  --min-equity-exposure 0.25 \
  --max-position-weight 0.30 \
  --max-oos-drawdown 35 \
  --seed 42
```

## A/B control experiment

Run the same search budget and seed with the overlay disabled:

```bash
python optimize_main.py \
  --universe all \
  --portfolio-size 7 \
  --population 60 \
  --generations 30 \
  --random 250 \
  --preselect-top 45 \
  --robust-pool 180 \
  --surrogate-pool 5000 \
  --surrogate-proposals 40 \
  --early-stop 15 \
  --no-risk-overlay \
  --max-oos-drawdown 35 \
  --seed 42
```

Note: the MDD gate still applies in the control optimizer. If no baseline candidate survives -35%, rerun the control with `--max-oos-drawdown 45` or `0` and record that fact instead of tuning until it passes.

## Volatility sensitivity experiment

Do **not** immediately optimize the target volatility to one historical value. Run a small grid with identical seed/search settings:

- 12%
- 15%
- 18%
- 20%
- 22%

Prefer a broad plateau where drawdown/CDaR improve without a sharp collapse in FINAL HOLDOUT return.

## Metrics to compare

Focus on:

- FINAL HOLDOUT Net TWR
- FINAL HOLDOUT Sharpe
- FINAL HOLDOUT MDD
- FINAL HOLDOUT CDaR95
- Validation robust return and P10 TWR
- Average/minimum equity exposure
- Turnover and transaction-cost % NAV
- Timing-neighbourhood stability
- Optimized timing vs standard quarterly baseline on the **same symbols**

Do not select a live candidate just because TRAIN or VALIDATION return is higher.

## Result bundle

From the web UI, use **Download all data (ZIP)** for the experiment and provide that ZIP for audit.

Key files:

- `optimizer_config.json`
- `optimizer_summary.csv`
- `candidate_metrics.csv`
- `top_candidates.csv`
- `pareto_frontier.csv`
- `baseline_comparison.csv`
- `timing_robustness.csv`
- `symbol_robustness.csv`
- `recommendation.json`
- `experiment.json`

## Safety / interpretation

The risk overlay is not a forecast. It is a deterministic exposure controller using information strictly available before each signal. A lower drawdown in historical tests is not a guarantee of lower future drawdown. The intended promotion rule remains: research proposes; a user explicitly approves live changes.
