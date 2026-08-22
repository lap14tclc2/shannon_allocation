# Shannon Allocation — User Guide

This file is the current operating guide for the repository.

> **Normal product usage is UI-first.** You do **not** need to run the portfolio optimizer from the command line. The normal workflow is: build the frontend, start the Python SSR server, open `/optimizer`, configure the run in the browser, and click **Run optimizer**.

The CLI commands below are documented because they still exist in the codebase and are useful for setup, development, verification, exports, and low-level research.

---

## 1. Repository layout

```text
shannon_allocation/
├─ frontend/                 React + Vite + SSR frontend
├─ python/                   Python backtest/optimizer/server
│  ├─ main.py                random-combination backtest CLI
│  ├─ optimize_main.py       optimizer CLI (developer/research fallback)
│  ├─ serve.py               SSR web application server
│  ├─ verify.py              end-to-end verification
│  ├─ export.py              run export utility
│  ├─ requirements.txt
│  └─ backtest/
├─ user-guide.md             this file
└─ README.md
```

Default local data directory:

```text
F:/data_finance/data
```

Default result directory:

```text
python/results
```

---

# 2. Normal user workflow — UI only

## 2.1 Get the latest code

From the repository root:

```bash
git checkout main
git pull origin main
```

The project uses `main` as the working branch.

---

## 2.2 Install Python dependencies

```bash
cd python
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Return to the repository root when finished:

```bash
cd ..
```

---

## 2.3 Install frontend dependencies

Recommended reproducible install:

```bash
cd frontend
npm ci
```

If `node_modules` does not exist and you intentionally want npm to update dependency resolution:

```bash
npm install
```

---

## 2.4 Build the frontend

Both bundles are required by `python/serve.py`.

```bash
npm run build
npm run build:ssr
```

Or run the project build script that executes both builds:

```bash
npm start
```

Important: `npm start` **builds** the client and SSR bundles. It does not start the Python application server.

Return to the repository root:

```bash
cd ..
```

---

## 2.5 Start the application

```bash
cd python
python serve.py
```

Default application address:

```text
http://127.0.0.1:8080
```

If port 8080 is already occupied, the server automatically tries subsequent ports and prints the actual URL.

Custom port:

```bash
python serve.py --port 8081
```

Custom host:

```bash
python serve.py --host 0.0.0.0 --port 8080
```

Available server options:

| Option | Default | Meaning |
|---|---:|---|
| `--port` | `8080` | preferred HTTP port; server falls back to subsequent free ports |
| `--host` | `127.0.0.1` | bind address |

The Python server automatically starts the Node SSR worker. You normally do **not** start the SSR worker manually.

Stop the server with:

```text
Ctrl+C
```

---

# 3. Web UI commands/actions

Once the server is running, normal research and optimizer operations are performed in the browser.

## Main pages

| URL | Purpose |
|---|---|
| `/` | saved backtest runs |
| `/optimizer` | portfolio + allocation optimizer |
| `/optimizer/<experiment_id>` | optimizer result/leaderboard |
| `/runs/<run_id>` | random-combination backtest result |
| `/runs/<run_id>/combinations/<slug>` | individual combination detail |

## Recommended optimizer flow

Open:

```text
http://127.0.0.1:8080/optimizer
```

Then configure:

1. **Universe** — All data / VN100 / VN50 / VN30.
2. **Optimization mode**.
   - Build portfolio + optimize timing.
   - Optimize timing for an existing fixed portfolio.
3. **Portfolio size** — exactly 5–10 symbols in joint mode.
4. **Risk policy**.
   - Risk-aware volatility target.
   - Baseline 100% equity.
5. **Target volatility**.
6. **Maximum OOS drawdown**.
7. **Maximum single-stock weight**.
8. **Minimum equity exposure**.
9. **Risk refresh interval**.
10. **Search preset**.
    - Fast.
    - Balanced — recommended for the ~90-symbol universe.
    - Thorough.
11. Optionally open **Advanced search settings**.
12. Review the configuration summary.
13. Click **Run optimizer**.
14. When the run finishes, the UI automatically opens the experiment page.
15. Use **Download all data (ZIP)** to export the result for audit.

There is no required optimizer CLI command in this workflow.

---

# 4. Frontend commands

Run these from `frontend/`.

## Install dependencies

```bash
npm ci
```

or:

```bash
npm install
```

## Vite development server

```bash
npm run dev
```

This is mainly for frontend development. The production-like integrated application is served by `python serve.py` after building both bundles.

## Build browser/client bundle

```bash
npm run build
```

Output:

```text
frontend/dist/
```

## Build SSR bundle

```bash
npm run build:ssr
```

Output:

```text
frontend/dist-ssr/
```

## Build both client and SSR bundles

```bash
npm start
```

Equivalent to:

```bash
npm run build
npm run build:ssr
```

## Frontend smoke test

```bash
node test/smoke.mjs
```

This validates SSR rendering and hydration using jsdom.

---

# 5. Verification and test commands

## Full application verification

Run after the frontend bundles exist:

```bash
cd python
python verify.py
```

This checks the real Python `Handler`, SSR pages, APIs, export ZIPs, deletion behavior, and optimizer pages using an ephemeral local port.

Some checks expect at least one saved backtest/optimizer result to exist.

## Compile Python modules

From `python/`:

```bash
python -m compileall -q backtest main.py optimize_main.py serve.py
```

## Dataset-independent optimizer tests

This is the command used by CI:

```bash
python -m pytest backtest/tests/test_optimizer.py backtest/tests/test_risk_fast_optimizer.py -q -k "not TestCostsAndLookahead"
```

## Full local optimizer tests

Use this on the development machine that has the configured historical data directory (`F:/data_finance/data`):

```bash
python -m pytest backtest/tests/test_optimizer.py backtest/tests/test_risk_fast_optimizer.py -q
```

## Run only the new risk/fast-optimizer regression tests

```bash
python -m pytest backtest/tests/test_risk_fast_optimizer.py -q
```

---

# 6. Export commands

`python/export.py` exports saved random-combination backtest runs into AI-readable Markdown or JSON.

Run from `python/`.

## Export latest run as Markdown

```bash
python export.py
```

## Export a specific run

```bash
python export.py --run <run_id>
```

Example:

```bash
python export.py --run 20260822_101951
```

## Export all combinations into one consolidated file too

```bash
python export.py --all
```

## Export JSON

```bash
python export.py --format json
```

## Custom output directory

```bash
python export.py --out <directory>
```

## Combine options

```bash
python export.py --run <run_id> --format json --all --out ./my-export
```

### All export options

| Option | Default | Meaning |
|---|---|---|
| `--run` | latest run | run ID to export |
| `--out` | `python/results/export` | export root directory |
| `--format` | `md` | `md` or `json` |
| `--all` | off | also create consolidated `ALL_COMBINATIONS` output |

---

# 7. Random-combination backtest CLI

> This is a research/developer utility. Normal portfolio optimization should be launched through the web UI.

Run from `python/`.

Show help:

```bash
python main.py --help
```

Basic run:

```bash
python main.py
```

Examples:

```bash
python main.py --combos 50
python main.py --combos 200 --seed 7
python main.py --portfolio-size 7 --combos 100
python main.py --combos 100 --integer-shares --allocation-freq annual
python main.py --combos 50 --plot
python main.py --combos 3 --run-id my_run
python main.py --risk-overlay --target-vol 0.18 --portfolio-size 7
```

## All `main.py` options

### Data / universe

| Option | Default | Meaning |
|---|---|---|
| `--data-dir` | `F:/data_finance/data` | historical CSV directory |
| `--universe` | `all` | `all`, `vn30`, `vn50`, or `vn100` |

### Combination generation

| Option | Default | Meaning |
|---|---:|---|
| `--combos` | `50` | number of random combinations |
| `--portfolio-size` | unset | exact portfolio size 5–10; overrides min/max |
| `--min-symbols` | `5` | minimum random combination size |
| `--max-symbols` | `10` | maximum random combination size |
| `--seed` | `42` | deterministic random seed |

### Money

| Option | Default | Meaning |
|---|---:|---|
| `--initial-balance` | `200000000` | starting VND cash |
| `--annual-deposit` | `20000000` | yearly contribution |
| `--no-deposit` | off | disable annual deposit |

### ERC / Shannon

| Option | Default | Meaning |
|---|---:|---|
| `--lookback` | `252` | ERC covariance lookback |
| `--min-obs` | `60` | minimum aligned observations |
| `--allocation-freq` | `quarterly` | `quarterly` or `annual` |
| `--normal-band` | `0.10` | normal Shannon drift band |
| `--soft-band` | `0.20` | soft Shannon drift band |
| `--integer-shares` | off | use whole shares instead of fractional shares |
| `--rebalance` | `1` | number of trading days between band checks |

### Risk overlay

| Option | Default | Meaning |
|---|---:|---|
| `--risk-overlay` | off | enable volatility-target exposure control |
| `--no-risk-overlay` | — | explicitly disable risk overlay |
| `--target-vol` | `0.18` | target annualized volatility |
| `--risk-fast-lookback` | `63` | fast risk lookback |
| `--risk-slow-lookback` | `252` | slow risk lookback |
| `--min-equity-exposure` | `0.25` | minimum permitted equity exposure |
| `--max-position-weight` | `0.30` | relative per-symbol weight cap; `<=0` disables in the CLI implementation |

### Date range

| Option | Default | Meaning |
|---|---|---|
| `--start-date` | unset | `YYYY-MM-DD` start |
| `--end-date` | unset | `YYYY-MM-DD` end |

### Output / diagnostics

| Option | Default | Meaning |
|---|---|---|
| `--out` | `F:/workspace/shannon_allocation/python/results/ranking.csv` | ranking CSV output |
| `--top` | `20` | rows displayed in ranking board |
| `--run-id` | timestamp/generated | explicit saved run ID |
| `--no-save` | off | do not persist run artifacts |
| `--plot` | off | generate top equity curve chart |
| `--plot-top` | `10` | number of plotted portfolios |
| `--chart-out` | `.../results/top_equity.png` | chart output path |
| `--save-nav` | unset | save NAV history JSON |
| `--no-progress` | off | suppress progress output |

---

# 8. Optimizer CLI — developer/research fallback

> **Normal users should use `/optimizer` instead.** This CLI remains available for automation, debugging, regression comparison, and developer research.

Run from `python/`.

Show help:

```bash
python optimize_main.py --help
```

Default optimizer run:

```bash
python optimize_main.py
```

Examples:

```bash
python optimize_main.py --portfolio-size 7 --universe vn100
python optimize_main.py --portfolio-size 6 --risk-overlay --target-vol 0.18
python optimize_main.py --portfolio-size 8 --preselect-top 45 --robust-pool 180
python optimize_main.py --mode timing --fixed-symbols CTG,GVR,HDB,LPB,MWG,STB,VIB
```

## All `optimize_main.py` options

### Portfolio mode

| Option | Default | Meaning |
|---|---|---|
| `--mode` | `joint` | `joint` or `timing` |
| `--fixed-symbols` | unset | comma-separated symbols; required by timing mode |
| `--portfolio-size` | `7` | exact number of symbols in joint mode, 5–10 |

### Search

| Option | Default | Meaning |
|---|---:|---|
| `--population` | `60` | NSGA-II population |
| `--generations` | `30` | maximum NSGA-II generations |
| `--random` | `250` | real TRAIN random-baseline backtests |
| `--finalists` | `5` | final candidates receiving expensive checks |
| `--seed` | `42` | deterministic seed |
| `--min-gap` | `40` | minimum cyclic distance between annual allocation positions |
| `--max-day` | automatic | maximum normalized annual trading-day position |
| `--lamb` | `0.5` | robust-return dispersion penalty |
| `--no-surrogate` | off | disable surrogate candidate ranking |
| `--preselect-top` | `45` | TRAIN-only symbol preselection; `0` disables narrowing |
| `--robust-pool` | `180` | diverse candidates promoted to expensive validation |
| `--surrogate-pool` | `5000` | cheap candidate pool scored by surrogate |
| `--surrogate-proposals` | `40` | surrogate proposals promoted to real TRAIN backtests |
| `--early-stop` | `15` | stop after unchanged Pareto front for N generations; `0` disables |

### Risk controls

| Option | Default | Meaning |
|---|---:|---|
| `--risk-overlay` | on | enable volatility-target exposure control |
| `--no-risk-overlay` | — | run legacy 100% equity baseline |
| `--target-vol` | `0.18` | annualized target volatility |
| `--risk-fast-lookback` | `63` | fast volatility window |
| `--risk-slow-lookback` | `252` | slow volatility window |
| `--min-equity-exposure` | `0.25` | minimum equity exposure |
| `--max-position-weight` | `0.30` | maximum relative stock weight |
| `--max-oos-drawdown` | `35.0` | hard validation/final-holdout drawdown ceiling; `0` disables |

### OOS / holdout

| Option | Default | Meaning |
|---|---:|---|
| `--test-days` | `252` | globally untouched final holdout length |
| `--no-full-coverage` | off | allow less than complete required-window coverage; not recommended |

### Data / output

| Option | Default | Meaning |
|---|---|---|
| `--universe` | `all` | `all`, `vn30`, `vn50`, or `vn100` |
| `--data-dir` | `F:/data_finance/data` | historical CSV directory |
| `--out` | `F:/workspace/shannon_allocation/python/results/optimizer` | optimizer export directory |
| `--no-progress` | off | suppress progress output |

### UI-only optimizer control

The current browser UI also exposes the **risk refresh interval** used by the backend. Normal users should configure it from `/optimizer`; there is currently no matching `optimize_main.py` CLI flag.

---

# 9. CI-equivalent local check

To reproduce the repository CI as closely as possible:

```bash
cd python
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m compileall -q backtest main.py optimize_main.py serve.py
python -m pytest backtest/tests/test_optimizer.py backtest/tests/test_risk_fast_optimizer.py -q -k "not TestCostsAndLookahead"

cd ../frontend
npm ci
npm run build
npm run build:ssr
node test/smoke.mjs
```

For the full local data-dependent Python tests, additionally run:

```bash
cd ../python
python -m pytest backtest/tests/test_optimizer.py backtest/tests/test_risk_fast_optimizer.py -q
```

---

# 10. Fast daily developer workflow

After pulling code that does not modify frontend dependencies:

```bash
git pull origin main
cd frontend
npm run build
npm run build:ssr
cd ../python
python serve.py
```

Then open:

```text
http://127.0.0.1:8080/optimizer
```

If `package-lock.json` changed, run `npm ci` before rebuilding.

If `python/requirements.txt` changed, run `pip install -r requirements.txt` before starting the server.

---

# 11. Important operating rules

- Use the **web UI** for normal optimizer runs.
- The optimizer CLI is retained for developer/research purposes only.
- Keep production/research data at the configured data directory; do not place generated optimizer artifacts into the source tree manually.
- ERC controls **relative** stock allocation.
- The risk overlay controls **total equity exposure** and can leave capital in cash.
- Risk-aware research should be compared against the risk-overlay-OFF baseline.
- Final deployment decisions should use the globally untouched OOS holdout and should not promote a candidate merely because TRAIN return is higher.
- Download the optimizer ZIP from the experiment page when sharing a result for audit.

---

# 12. Command index

```text
SETUP
  pip install -r python/requirements.txt
  cd frontend && npm ci

FRONTEND
  npm run dev
  npm run build
  npm run build:ssr
  npm start
  node test/smoke.mjs

APP SERVER
  cd python
  python serve.py
  python serve.py --port <port>
  python serve.py --host <host> --port <port>

VERIFY / TEST
  python verify.py
  python -m compileall -q backtest main.py optimize_main.py serve.py
  python -m pytest backtest/tests/test_optimizer.py backtest/tests/test_risk_fast_optimizer.py -q -k "not TestCostsAndLookahead"
  python -m pytest backtest/tests/test_optimizer.py backtest/tests/test_risk_fast_optimizer.py -q
  python -m pytest backtest/tests/test_risk_fast_optimizer.py -q

EXPORT
  python export.py
  python export.py --run <run_id>
  python export.py --all
  python export.py --format json
  python export.py --out <directory>

RANDOM BACKTEST — developer/research
  python main.py
  python main.py --help

OPTIMIZER — developer/research fallback; UI preferred
  python optimize_main.py
  python optimize_main.py --help

NORMAL OPTIMIZER USER
  Start server → open /optimizer → configure → Run optimizer → Download all data ZIP
```
