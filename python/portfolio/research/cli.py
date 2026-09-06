"""Research CLI (T09-T13). Research-oriented, not user BUY/SELL endpoints.

Usage:
    python -m portfolio.research.cli build-snapshots ...
    python -m portfolio.research.cli build-outcomes ...
    python -m portfolio.research.cli validate-factor ...
    python -m portfolio.research.cli run-walk-forward ...
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone

from .snapshots import SnapshotDeps, build_snapshots
from .store import ResearchStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _run_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def cmd_build_snapshots(args) -> None:
    store = ResearchStore()
    store.create_schema()
    deps = SnapshotDeps.production()
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()] if args.symbols else []
    dates = args.dates.split(",") if args.dates else []
    run_id = _run_id("snap")
    rows = build_snapshots(deps, symbols=symbols, snapshot_dates=dates)
    count = store.write_snapshots(run_id, rows)
    print(json.dumps({"run_id": run_id, "rows": count}, default=str))


def cmd_build_outcomes(args) -> None:
    store = ResearchStore()
    store.create_schema()
    from ..research.outcomes import build_outcomes

    run_id = args.run_id
    snapshots = store.read_snapshots(run_id)
    if not snapshots:
        print(json.dumps({"error": f"no snapshots for run {run_id}"}), file=sys.stderr)
        sys.exit(1)
    benchmark_rows = store.read_benchmark_prices()
    if not benchmark_rows:
        print(json.dumps({"error": "no benchmark prices persisted"}), file=sys.stderr)
        sys.exit(1)
    import pandas as pd

    benchmark_frame = pd.DataFrame(benchmark_rows).set_index("trading_date")
    benchmark_frame.index = pd.to_datetime(benchmark_frame.index)

    def price_provider(symbol: str) -> pd.DataFrame:
        from ..finance_catalog import FINANCE_SCHEMA, _schema_connection

        with _schema_connection(FINANCE_SCHEMA) as db:
            rows = db.execute(
                "SELECT trading_date, close FROM market_prices WHERE symbol = ? "
                "ORDER BY trading_date",
                (symbol,),
            ).fetchall()
        if not rows:
            return pd.DataFrame(columns=["close"])
        frame = pd.DataFrame([dict(r) for r in rows])
        frame["trading_date"] = pd.to_datetime(frame["trading_date"])
        return frame.set_index("trading_date").sort_index()

    outcomes = build_outcomes(price_provider, benchmark_frame, snapshots)
    count = store.write_outcomes(run_id, outcomes)
    print(json.dumps({"run_id": run_id, "outcome_rows": count}, default=str))


def cmd_validate_factor(args) -> None:
    store = ResearchStore()
    store.create_schema()
    run_id = args.run_id
    snapshots = store.read_snapshots(run_id)
    from ..research.outcomes import DEFAULT_HORIZONS
    from ..research.validation import validate_factor
    from ..research.walk_forward import ResearchConfig

    # Merge outcomes (read from the store) into snapshots for validation.
    with store._connect() as db:
        outcome_rows = db.execute(
            "SELECT * FROM research_factor_outcomes WHERE run_id = ?",
            (run_id,),
        ).fetchall()
    merged = {}
    for row in outcome_rows:
        key = (row["snapshot_date"], row["symbol"])
        merged.setdefault(key, dict(row))
    enriched = []
    for snap in snapshots:
        row = dict(snap)
        outcome = merged.get((row["snapshot_date"], row["symbol"]))
        if outcome:
            h = outcome["horizon_sessions"]
            row[f"forward_stock_return_{h}"] = outcome["forward_stock_return"]
            row[f"forward_vnindex_return_{h}"] = outcome["forward_vnindex_return"]
            row[f"forward_excess_return_{h}"] = outcome["forward_excess_return"]
        enriched.append(row)

    config = ResearchConfig(
        research_start=args.research_start,
        train_years=args.train_years,
        validation_years=args.validation_years,
        sealed_oos_start=args.sealed_oos_start,
        sealed_oos_end=args.sealed_oos_end,
    )
    result = validate_factor(
        enriched,
        excess_key=f"forward_excess_return_{args.horizon}",
        config=config,
    )
    result["benchmark"] = "VNINDEX"
    result["run_id"] = run_id
    store.write_validation_run({
        "run_id": run_id,
        "factor": result["factor"],
        "horizon_sessions": result["horizon_sessions"],
        "benchmark": "VNINDEX",
        "universe_definition": args.universe or "default-liquid-vn",
        "cost_model_json": json.dumps(result.get("cost_model", {}), default=str),
        "data_hash": result.get("factor", ""),
        "created_at": _now(),
    })
    store.write_factor_result(run_id, result["factor"], result["verdict"], result)
    print(json.dumps(result, indent=2, default=str))


def build_period_payload(config) -> dict:
    """Structured period report separating walk-forward windows and sealed OOS."""
    from ..research.walk_forward import (
        research_cutoff,
        walk_forward_windows,
    )

    windows = walk_forward_windows(config)
    sealed = {
        "start": config.sealed_oos_start,
        "end": config.sealed_oos_end,
    } if (config.sealed_oos_start and config.sealed_oos_end) else None
    no_after = True
    if sealed:
        no_after = all(w["valid_end"] < sealed["start"] for w in windows)
    return {
        "research_start": config.research_start,
        "research_cutoff": research_cutoff(config).isoformat(),
        "walk_forward_windows": windows,
        "sealed_oos": sealed,
        "no_validation_after_sealed": bool(no_after),
    }


def cmd_run_walk_forward(args) -> None:
    from ..research.walk_forward import ResearchConfig

    config = ResearchConfig(
        research_start=args.research_start,
        research_end=args.research_end,
        train_years=args.train_years,
        validation_years=args.validation_years,
        sealed_oos_start=args.sealed_oos_start,
        sealed_oos_end=args.sealed_oos_end,
    )
    payload = build_period_payload(config)
    print(json.dumps(payload, indent=2, default=str))


def cmd_audit_data(args) -> None:
    from ..research.audit import audit_benchmark, audit_finance_data

    report = audit_finance_data()
    report["benchmark"] = audit_benchmark()
    print(json.dumps(report, indent=2, default=str))


def cmd_run_full_research(args) -> None:
    from ..research.runner import run_full_research
    from ..research.store import ResearchStore

    store = ResearchStore()
    result = run_full_research(
        top_n=args.top_n,
        min_recent_bars=args.min_recent_bars,
        research_start=args.research_start,
        snapshot_end=args.snapshot_end,
        research_end=args.research_end,
        sealed_oos_start=args.sealed_oos_start,
        sealed_oos_end=args.sealed_oos_end,
        train_years=args.train_years,
        validation_years=args.validation_years,
        store=store,
    )
    if args.report_path:
        from ..research.report import build_full_report_markdown
        from pathlib import Path

        path = Path(args.report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(build_full_report_markdown(result), encoding="utf-8")
        print(json.dumps({"run_id": result["run_id"], "report": str(path)}, default=str))
    else:
        from ..research.runner import summarize_results

        print(json.dumps({"run_id": result["run_id"], "summary": summarize_results(result["results"])}, indent=2, default=str))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="QPort research CLI (T09-T13)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_audit = sub.add_parser("audit-data", help="Produce the real DATA READINESS report")
    p_audit.set_defaults(func=cmd_audit_data)

    p_snap = sub.add_parser("build-snapshots", help="Build and persist factor snapshots")
    p_snap.add_argument("--symbols", help="comma-separated symbols")
    p_snap.add_argument("--dates", help="comma-separated snapshot dates (YYYY-MM-DD)")
    p_snap.set_defaults(func=cmd_build_snapshots)

    p_out = sub.add_parser("build-outcomes", help="Attach forward outcomes to a snapshot run")
    p_out.add_argument("--run-id", required=True)
    p_out.set_defaults(func=cmd_build_outcomes)

    p_val = sub.add_parser("validate-factor", help="Validate a factor and emit the research report")
    p_val.add_argument("--run-id", required=True)
    p_val.add_argument("--horizon", type=int, default=63)
    p_val.add_argument("--research-start", default="2016-01-01")
    p_val.add_argument("--train-years", type=int, default=5)
    p_val.add_argument("--validation-years", type=int, default=1)
    p_val.add_argument("--sealed-oos-start")
    p_val.add_argument("--sealed-oos-end")
    p_val.add_argument("--universe", default="default-liquid-vn")
    p_val.set_defaults(func=cmd_validate_factor)

    p_wf = sub.add_parser("run-walk-forward", help="Print chronological walk-forward windows + sealed OOS")
    p_wf.add_argument("--research-start", default="2016-01-01")
    p_wf.add_argument("--research-end")
    p_wf.add_argument("--train-years", type=int, default=5)
    p_wf.add_argument("--validation-years", type=int, default=1)
    p_wf.add_argument("--sealed-oos-start")
    p_wf.add_argument("--sealed-oos-end")
    p_wf.set_defaults(func=cmd_run_walk_forward)

    p_full = sub.add_parser("run-full-research", help="End-to-end real factor research")
    p_full.add_argument("--top-n", type=int, default=150)
    p_full.add_argument("--min-recent-bars", type=int, default=30)
    p_full.add_argument("--research-start", default="2019-01-31")
    p_full.add_argument("--snapshot-end", default="2024-12-31")
    p_full.add_argument("--research-end", default="2025-12-31")
    p_full.add_argument("--sealed-oos-start", default="2024-01-01")
    p_full.add_argument("--sealed-oos-end", default="2025-12-31")
    p_full.add_argument("--train-years", type=int, default=4)
    p_full.add_argument("--validation-years", type=int, default=1)
    p_full.add_argument("--report-path", default=None)
    p_full.set_defaults(func=cmd_run_full_research)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()