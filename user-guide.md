# Shannon Allocation — User Guide

This is the operating guide for the current product workflow.

> **The user owns the stock combination.** The application does not search for or replace symbols. The normal workflow is: select/import 5–10 symbols, enter the capital plan, configure risk constraints, and let the system optimize the four annual allocation times.

The quantitative core remains ERC + risk overlay + Shannon drift management. Arbitrary portfolio weights are not optimized: ERC determines relative weights from historical covariance at each allocation event.

---

## 1. Product workflow

```text
User selects/imports symbols
        ↓
Fixed combination (5–10 symbols)
        ↓
Initial balance + annual contribution
        ↓
Optimize 4 allocation times/year
        ↓
ERC relative weights
        ↓
Optional absolute-risk overlay
        ↓
Shannon drift bands
        ↓
Rolling OOS validation
        ↓
Recent validation
        ↓
Untouched final holdout
```

The optimizer is **not allowed** to add, remove or replace a symbol selected by the user.

---

## 2. Start the application

From the repository root, get the current `main` branch:

```bash
git checkout main
git pull origin main
```

Install Python dependencies:

```bash
cd python
python -m pip install --upgrade pip
pip install -r requirements.txt
cd ..
```

Install and build the frontend:

```bash
cd frontend
npm ci
npm run build
npm run build:ssr
cd ..
```

Start the integrated SSR application:

```bash
cd python
python serve.py
```

Default address:

```text
http://127.0.0.1:8080
```

If port 8080 is busy the server tries subsequent ports and prints the actual URL.

---

## 3. Allocation Optimizer UI

Open:

```text
http://127.0.0.1:8080/optimizer
```

### 3.1 Choose your combination

There are two supported methods.

**Checkbox selection**

- The UI loads every ticker that has price data.
- Search for a ticker and click its checkbox.
- Current model constraint: 5–10 symbols.
- Once the run starts, the selected set is frozen.

**Migrate an existing combination**

Paste the ticker list into **Migrate an existing combination** and click **Import combination**.

Accepted examples:

```text
ACB, FPT, REE, VCB, VNM
```

```text
ACB FPT REE VCB VNM
```

```json
["ACB", "FPT", "REE", "VCB", "VNM"]
```

Migration at this stage imports the **combination composition**. Holdings, historical cost basis and broker transactions are a separate live-portfolio migration concern.

### 3.2 Capital plan

Enter:

- **Initial balance (VND)** — cash available at the beginning of the simulation.
- **Money added each year (VND)** — external contribution added on the first trading session of each new calendar year.

The result distinguishes:

- when money was contributed;
- when money was actually deployed into equities;
- cash released by sells;
- remaining cash after execution.

### 3.3 Risk policy

The existing quantitative theory is unchanged:

- ERC controls relative stock risk weights.
- The volatility overlay may scale total equity exposure and leave the remainder in cash.
- Shannon bands manage drift between allocation events.

Configurable controls include:

- target volatility;
- maximum OOS drawdown gate;
- maximum single-stock weight;
- minimum equity exposure.

### 3.4 Allocation search quality

The search now changes **only four annual allocation positions**.

Presets:

- **Fast** — quick timing exploration.
- **Balanced** — recommended default for a fixed combination.
- **Thorough** — more timing candidates and validation work.

Advanced settings expose seed, population, generations, random timing samples, validation shortlist, surrogate pool and early-stop patience.

### 3.5 Run

Click:

```text
Optimize allocation
```

The application then evaluates schedules using the fixed symbols and capital plan.

The normal flow is:

```text
Fixed symbols
→ timing search
→ ERC
→ risk overlay
→ Shannon drift
→ rolling OOS validation
→ recent validation
→ untouched final holdout
```

---

## 4. Important invariants

### User-selected symbols are immutable during a run

The HTTP optimizer endpoint accepts only timing mode. Requests for the retired joint symbol-search mode are rejected.

### Exactly four allocation events per year

The optimizer searches the timing of the four annual allocation events subject to the existing minimum-gap/cyclic-gap rules.

### ERC remains deterministic

The system does not optimize arbitrary stock weights to chase historical return. ERC continues to derive relative risk weights from data available before each signal date.

### Recommendation is not execution

Research output is a recommendation. Live portfolio state must ultimately come from actual TradeExecution records.

### Final holdout is not a tuning target

The final holdout is reserved for assessment and must not be repeatedly tuned against to manufacture a better backtest.

---

## 5. Results and exports

After a run completes, the browser opens:

```text
/optimizer/<experiment_id>
```

The result includes research winners, allocation schedules, validation/holdout metrics, capital deployment history, risk diagnostics and the quarterly baseline comparison.

Use **Download all data (ZIP)** for audit/review.

Historical experiments generated before the fixed-combination refactor remain readable.

---

## 6. Developer/research note

Some older Python modules still contain joint-symbol search machinery for historical research and reproducibility. It is not part of the normal product contract and is not reachable through the allocation optimizer UI/API.

The production-facing contract is:

```text
fixed symbols + capital plan + risk policy
        ↓
allocation timing optimization only
```
