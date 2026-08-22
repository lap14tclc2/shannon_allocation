# Shannon / ERC Combination Backtest

Python backtest of the **portfolio_allocation** concept: for random combinations of
5–10 symbols, allocate money using Equal Risk Contribution (ERC) annual targets and
manage it with Shannon-style drift-band rebalancing and sell-to-buy + cash funding.

The ERC solver is a faithful port of `src/services/erc.service.ts` from the reference
TypeScript project and was verified to reproduce its annual targets exactly
(e.g. ACB/DGC/FPT → 39.42% / 24.82% / 35.76%).

## How it works

- Data: daily OHLCV CSVs in `data_dir` (`F:/data_finance/data`). Close prices are
  thousands of VND and are scaled by `price_scale` (1000) to VND.
- Combos: `num_combinations` random unique sets of `min_symbols`–`max_symbols` symbols
  (seeded → reproducible).
- Simulation (walk-forward, no look-ahead):
  - ERC targets are calibrated only on data **strictly before** each allocation date.
  - **Quarterly allocation** (default): allocation happens strictly on the first
    trading day of each quarter (Jan/Apr/Jul/Oct). Money sits in cash until the
    first quarter start that has enough aligned history to calibrate ERC.
  - A 20M VND deposit is added at the start of each calendar year.
  - Between allocations, Shannon bands trigger rebalancing back toward the locked target
    (`rebalance_every_days` = daily by default).
- Ranking: combinations are ranked by final NAV. Metrics: total return, CAGR, annualised
  volatility, Sharpe, max drawdown.

## Run

```bash
python main.py --combos 50                  # 50 random combinations, quarterly allocation
python main.py --combos 200 --seed 7        # different random sample
python main.py --combos 100 --integer-shares --allocation-freq annual
python main.py --combos 50 --plot           # also render top equity curves (PNG)
python main.py --combos 3 --run-id my_run   # explicit run id
```

Key options (`python main.py --help`):

| Flag | Default | Meaning |
|---|---|---|
| `--combos` | 50 | number of random combinations |
| `--min-symbols` / `--max-symbols` | 5 / 10 | combination size range |
| `--seed` | 42 | RNG seed for reproducibility |
| `--initial-balance` | 200000000 | starting cash (VND) |
| `--annual-deposit` | 20000000 | yearly deposit (VND) |
| `--allocation-freq` | quarterly | `quarterly` or `annual` ERC recompute |
| `--lookback` | 252 | trailing trading days for covariance |
| `--min-obs` | 60 | minimum aligned observations for ERC |
| `--normal-band` / `--soft-band` | 0.10 / 0.20 | Shannon drift bands |
| `--integer-shares` | off | whole-share execution (default fractional) |
| `--run-id` | timestamp | id of the saved run folder |
| `--plot` | off | save top equity curves PNG |

## Output

Console ranking board +:

```
results/ranking.csv                 # flat ranking table
results/runs/<run_id>/
    meta.json                       # run parameters (page header config)
    index.json                      # ranking board: one summary row per combination
    combinations/<TICKERS>.json     # full detail per combination
```

### Per-combination JSON (page-ready schema)

```json
{
  "symbols": ["DGC", "GEX", ...],
  "final_nav": 518159417.0,
  "total_return_pct": 72.72,
  "cagr_pct": 11.8,
  "annualized_volatility_pct": 28.9,
  "sharpe": 0.75,
  "max_drawdown_pct": -50.0,
  "nav_history": [["2021-08-16", 200000000.0], ...],
  "allocations": [
    {
      "year": 2022, "quarter": 1,
      "allocation_date": "2022-01-04",
      "initial_allocation": false,
      "deposit_amount": 20000000.0,
      "rebalances_since_last_allocation": 15,
      "nav_before": 227058518.0, "cash_before": 2223197.0,
      "nav_after": 227058518.0,  "cash_after": 0.0,
      "erc": {
        "observations": 251,
        "window_start": "2020-01-02", "window_end": "2021-12-31",
        "portfolio_risk": 0.31, "portfolio_variance": 0.096, "erc_error": 1e-8,
        "risk_contributions": {"DGC": 0.2, ...},
        "weights": {"DGC": 0.19, ...}
      },
      "targets": {"DGC": 0.19, ...},
      "holdings_before": [{"symbol": "DGC", "shares": 2437.7, "price": 47900, "value": 116769402.74, "weight": 0.21}],
      "recommendations": [
        {
          "symbol": "DGC", "current_weight": 0.211, "target_weight": 0.205,
          "band": "NORMAL", "drift": 0.0067, "recommendation": "HOLD",
          "target_trade_amount": 0.0, "funded_trade_amount": 0.0, "shares_to_trade": 0.0
        }
      ],
      "holdings_after": [ ... ]
    }
  ]
}
```

Notes:
- `nav_before == nav_after` is expected: in this fee-free model trades happen at the
  same market prices, so NAV is conserved; what changes is the holdings composition
  and cash.
- `deposit_amount` is non-zero only on Q1 allocations (annual 20M deposit).
- Amounts are VND (floats); weights are fractions (0..1).

## Requirements

```
pip install -r requirements.txt   # numpy, pandas, matplotlib (optional for --plot)
```

## Frontend (React SSR, Python backend)

Server-Side Rendering: the Python backend renders every page to HTML with React
(`react-dom/server` via a small Node worker) and React hydrates on the client.
Pages are URL-addressable:

| URL | Page |
|---|---|
| `/` | home — list of runs |
| `/runs/<run_id>` | ranking board |
| `/runs/<run_id>/combinations/<SLUG>` | combination detail (equity curve + allocations) |

### Build

```bash
cd frontend
npm install
npm run build        # client hydration bundle -> dist/
npm run build:ssr    # SSR bundle for Node    -> dist-ssr/
```

### Run

```bash
cd python
python serve.py --port 8080   # auto-spawns the Node SSR worker; picks a free port if 8080 busy
# open the printed URL
```

Architecture:

```
Python (serve.py)  --POST /render-->  Node (ssr/server.mjs) --> renderToString
      |                                            |
      |  builds full HTML doc (SSR content + __PAGE__ data + client bundle)
      v
   Browser  --> hydrates with React (window.__PAGE__)
```

The Python server spawns `node frontend/ssr/server.mjs` (port 8099) automatically
if it is not already running, and terminates it on shutdown. The JSON API
(`/api/runs`, `/meta`, `/index`, `/combinations/<slug>`) remains available too.

### Verify (fast, no server probing)

```bash
cd frontend && node test/smoke.mjs   # SSR render + hydration (jsdom), ~1s
cd python && python verify.py        # end-to-end page routes + Export ZIP endpoint, ~1s
```

### Web UI

- `python serve.py` serves the SSR app and auto-starts the Node renderer. The Node
  worker **reloads the React bundle automatically** whenever `npm run build:ssr`
  re-outputs it, so after a frontend rebuild there is no stale cache — just refresh
  the browser.
- Each run page has an **Export run (Markdown ZIP)** button → downloads
  `<run_id>_export.zip` (all combination reports + `_RUN.md` + `_STATS.md` +
  `ALL_COMBINATIONS.md`) via `GET /api/runs/<run_id>/export`.
- The home page links to **`/optimizer`** — a leaderboard of optimizer experiments
  (Best Return / Best Risk-Adjusted / Best Low-Drawdown / **Best Robust**), Pareto
  frontier, top candidates, per-candidate NET metrics + OOS robustness + timing/
  symbol-neighbourhood + concentration, and downloadable CSVs. Data comes from the
  structured `experiment.json` each optimizer run writes under
  `results/optimizer/<id>/`.

## Joint Portfolio + Allocation-Time Optimizer

Searches the **four annual ERC allocation times** for the most **robust out-of-sample
risk-adjusted NET performance**, not the best historical backtest. Two modes:

- `joint` (default): searches the stock subset (5–10 symbols) and the four allocation
  times **together**.
- `timing`: the portfolio set is **FIXED** (`--fixed-symbols A,B,C,D,E`) and only
  `[T1,T2,T3,T4]` is optimized — so symbol selection cannot contaminate the timing
  result, and every schedule is compared against the **same predefined portfolio**.

```bash
cd python
python optimize_main.py                              # quick joint run
python optimize_main.py --population 200 --generations 100 --random 1000   # full spec defaults
python optimize_main.py --mode timing --fixed-symbols CTG,GVR,HDB,LPB,MWG,STB,VIB --random 1000
python optimize_main.py --seed 7 --no-surrogate --finalists 10
```

Evaluation methodology (audit fixes):
1. **Walk-forward train/val/test** rolling windows; `val >= 252` and `test >= 252`
   trading days so every window contains a complete annual allocation cycle.
2. **ERC warm-up**: each window loads ~`lookback_days` of pre-window history so the
   first allocation inside the window can calibrate (no look-ahead).
3. **Full-window performance clock**: metrics are measured from the **window start**
   (cash period included), never from the first allocation — a 12% gain over 6 months
   cannot be annualized to 200%.
4. **100% coverage policy**: a candidate that fails ANY validation or test window is
   **INVALID** (`evaluate_robust(min_windows=...)`), not "partially robust".
5. **Cyclic minimum gap**: `YEAR_LENGTH + T1 - T4 >= min_gap` in addition to the three
   internal gaps (allocation repeats every year).
6. **Real trading calendar**: the max allocation day is resolved to the minimum number
   of sessions of a full calendar year in the data (day 252 is not silently skipped).
7. **Timing robustness from OOS**: neighbourhood stability is computed from the OOS
   robust scores (same metric that selected the candidate), not a train-window spike.
8. **Labeled phases**: every report/JSON/CSV separates `TRAIN`, `VALIDATION` and
   `FINAL TEST` windows; the `best_robust` leaderboard requires 100% of untouched
   test windows to pass.
9. **Quarterly baseline**: the standard four-times-per-year schedule is evaluated on
   the same symbols/windows (`baseline_comparison.csv`) so you can see whether
   optimization beats the current production schedule.

Pipeline (see `backtest/optimize/`):
1. **Costs + no look-ahead** (`P0`): configurable buy/sell fee, sell tax, slippage;
   signals computed at close[t], orders execute at close[t+1]; gross vs net
   TWR/XIRR exported; optimizer uses NET.
2. **Candidate** (`backtest/candidate.py`): `(symbols, allocation_days)` with the
   four times as trading-day positions (1..max-day, min gap 40, cyclic-valid) mapped
   per year to real market dates.
3. **Random joint-search baseline** → **NSGA-II** (Pareto ranking, crowding
   distance, elitism, symbol + timing crossover/mutation with repair; timing-only
   mode freezes the symbol set) → optional sklearn **surrogate**.
4. **Walk-forward** robust fitness = `median(OOS net TWR) - lambda * dispersion`,
   plus P10/P25/worst/MDD.
5. **Timing-neighbourhood** (±1..5 day spike detection on OOS robust scores),
   **symbol-neighbourhood** (joint mode), **concentration** checks.
6. **Reports**: leaderboards (best return / risk-adjusted / low-drawdown /
   robust), Pareto frontier, per-finalist Markdown with labelled TRAIN/VALIDATION/
   FINAL TEST, and CSVs: `optimizer_summary.csv, pareto_frontier.csv,
   top_candidates.csv, candidate_metrics.csv, walk_forward_results.csv,
   timing_robustness.csv, symbol_robustness.csv, baseline_comparison.csv,
   optimizer_config.json` under `results/optimizer/<id>/`. Everything is
   reproducible from the stored seed/config/data.

Tests: `python -m pytest backtest/tests/test_optimizer.py -q` (33 tests: candidate
validation incl. cyclic min-gap, generators/repair, NSGA-II ≥ random on a planted
problem, timing-only mode freezes symbols, 100% window coverage policy, full-window
annualization invariant, ERC warm-up, no-look-ahead execution, costs, robustness,
reproducibility).

## Export combination data for an AI / LLM

`python/export.py` turns a run's page-ready JSON into clean, AI-readable reports:

```bash
python export.py                     # most recent run, Markdown
python export.py --run <run_id>      # a specific run
python export.py --all               # also write ALL_COMBINATIONS.md (everything in one file)
python export.py --format json       # consolidated JSON instead of Markdown
python export.py --out <dir>         # output directory (default python/results/export)
```

Output (`<out>/<run_id>/`):
- `_RUN.md` — run parameters + ranking board (ranked by composite Portfolio Score)
- `_STATS.md` — cross-portfolio aggregate stats: percentiles (P10/P25/median/P75/P90)
  for NAV / TWR / XIRR / Sharpe / Sortino / MDD / score, by-portfolio-size breakdown,
  and per-symbol association
- `<TICKERS>.md` — one report per combination: composite score, TWR / XIRR / Sortino /
  Calmar / annual returns / turnover / trades, sampled NAV history, and the full
  quarterly allocation history (date, deposit, NAV before/after, cash, ERC window/
  observations/risk, target weights, executed BUY/SELL trades, holdings)
- `ALL_COMBINATIONS.md` — every combination concatenated (with `--all`)

`--format json` produces the same content as compact JSON files.

## Portfolio Score & metrics

Ranking is by a **composite Portfolio Score (0-100)** rather than raw Final NAV:

```text
Score = return quality (annualized TWR) + Sharpe + drawdown control + year consistency
```

Strategy metrics are measured from the **first investment date** (warm-up excluded):

- `TWR` / `TWR annualized` — time-weighted return, external deposits removed (strategy)
- `XIRR` — investor money-weighted annualized return (includes deposit timing)
- `Sortino`, `Calmar`, annual returns, worst year, positive-year ratio
- `Turnover`, `trade_count`

`Final NAV / total deposits - 1` (`total_return_pct`) and `cagr_pct` are kept as
informational only — they treat late deposits as if invested at time zero.