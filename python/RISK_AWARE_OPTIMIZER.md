# Risk-Aware Optimizer — RESEARCH ONLY

> **Operational status:** archived behind the QPort Research Lab.  
> This optimizer does not control the Buy & Hold portfolio and cannot write to
> the operational ledger.

The current operational specification is `../BUY_AND_HOLD_SYSTEM_SPEC.md`.

## Research purpose

This module family exists to test historical questions about:

- ERC relative risk weighting;
- volatility-target exposure overlays;
- Shannon drift/rebalancing policies;
- static/dynamic symbol selection;
- 1–6 annual recalibration schedules;
- walk-forward/OOS robustness;
- final assessment holdouts;
- transaction-cost sensitivity.

It remains useful for evidence generation, but all outputs are proposals only.

```text
RESEARCH EXPERIMENT
       ↓
metrics / report / candidate
       ↓
PROPOSAL ONLY
       ↓
USER DECISION
       ↓
real broker action
       ↓
explicit operational ledger event
```

There is intentionally no direct `optimizer → portfolio` write path.

## Research entrypoints

```bash
python optimize_main.py ...
python research_main.py ...
```

Web:

```text
/research
/research/optimizer
```

Old `/optimizer` URLs are compatibility aliases into Research Lab.

## Historical methodology retained

The research engine still contains the methodology developed before the Buy &
Hold refactor, including:

```text
TRAIN search
→ rolling OOS validation
→ recent pre-holdout evidence
→ freeze winner
→ final assessment holdout PASS/REJECT
```

It also retains Dynamic Alpha and legacy combination-search implementations for
comparative research.

These components must not be interpreted as mandatory operational portfolio
rules. In particular, the live portfolio does not have:

```text
annual allocation dates
optimized recalibration dates
automatic Dynamic Alpha membership changes
automatic volatility-driven SELL/de-risk execution
an optimizer-selected live candidate
```

## Testing

Research regressions are deliberately separated from lightweight operational CI
because they are more expensive and some depend on private/local historical data.
Run them when research code changes or before publishing research conclusions.

The operational product is tested independently under `portfolio/tests/`.
