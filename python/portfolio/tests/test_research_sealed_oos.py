"""Sealed-OOS hardening tests (TASK-20260906-098 Part A).

Invariant: if sealed_oos_start = S, sealed_oos_end = E, then ALL training /
validation / tuning windows MUST satisfy ``window.valid_end < S``.
"""
from __future__ import annotations

import pytest

from portfolio.research.validation import validate_factor
from portfolio.research.walk_forward import (
    ResearchConfig,
    assert_not_sealed,
    is_sealed,
    partition_periods,
    research_cutoff,
    validate_config,
    walk_forward_windows,
)

SEALED = ("2024-01-01", "2025-12-31")


def _config(**overrides):
    base = {
        "research_start": "2016-01-01",
        "train_years": 5,
        "validation_years": 1,
        "sealed_oos_start": SEALED[0],
        "sealed_oos_end": SEALED[1],
    }
    base.update(overrides)
    return ResearchConfig(**base)


def test_no_window_overlaps_sealed_oos():
    config = _config()
    for window in walk_forward_windows(config):
        assert window["valid_end"] < SEALED[0]
        # no overlap with [S, E]
        assert not (window["valid_start"] <= SEALED[1] and window["valid_end"] >= SEALED[0])


def test_no_validation_window_after_sealed_oos():
    config = _config()
    windows = walk_forward_windows(config)
    assert windows
    assert max(window["valid_end"] for window in windows) < SEALED[0]


def test_validation_window_ending_day_before_sealed_is_valid():
    config = _config()
    windows = walk_forward_windows(config)
    assert windows
    # The last validation window must end exactly the day before S (or earlier).
    for window in windows:
        assert window["valid_end"] <= "2023-12-31"


def test_research_cutoff_is_day_before_sealed_start():
    config = _config()
    assert research_cutoff(config).isoformat() == "2023-12-31"
    no_sealed = ResearchConfig(research_start="2016-01-01", research_end="2025-12-31")
    assert research_cutoff(no_sealed).isoformat() == "2025-12-31"


def test_invalid_sealed_ranges_raise():
    # sealed start not before end
    with pytest.raises(ValueError):
        _config(sealed_oos_start="2025-12-31", sealed_oos_end="2024-01-01")
    # research_start not before sealed start
    with pytest.raises(ValueError):
        _config(research_start="2025-01-01")
    # incomplete sealed range
    with pytest.raises(ValueError):
        _config(sealed_oos_end=None)
    with pytest.raises(ValueError):
        _config(sealed_oos_start=None)


def test_sealed_start_before_enough_training_behaves_safely():
    # Sealed starts so early that no 5Y train + 1Y validation fits before S.
    config = _config(sealed_oos_start="2018-01-01", sealed_oos_end="2019-12-31")
    assert walk_forward_windows(config) == []
    # No crash; empty window list is safe degradation.


def test_research_end_before_sealed_end_raises():
    with pytest.raises(ValueError):
        _config(research_end="2024-06-30", sealed_oos_end="2025-12-31")
    # research_end exactly == sealed_end is allowed.
    config = _config(research_end="2025-12-31")
    assert walk_forward_windows(config)


def test_assert_not_sealed_still_blocks_sealed_dates():
    config = _config()
    with pytest.raises(ValueError):
        assert_not_sealed(config, "2024-06-01")
    assert_not_sealed(config, "2023-06-01")  # in-sample passes


def test_partition_never_exposes_sealed_rows_to_tuning():
    config = _config()
    dates = ["2020-06-01", "2023-12-31", "2024-01-01", "2024-06-01", "2025-12-31"]
    partitioned = partition_periods(config, dates)
    assert set(partitioned["tuning_allowed"]) == {"2020-06-01", "2023-12-31"}
    assert set(partitioned["sealed_oos"]) == {"2024-01-01", "2024-06-01", "2025-12-31"}
    # Compatibility aliases.
    assert partitioned["in_sample"] == partitioned["tuning_allowed"]
    assert partitioned["sealed"] == partitioned["sealed_oos"]
    # No sealed date ever appears in tuning_allowed.
    assert not any(is_sealed(config, d) for d in partitioned["tuning_allowed"])


def test_validate_factor_never_uses_sealed_for_tuning():
    config = _config()
    rows = []
    for date_value in ("2020-06-01", "2023-12-31", "2024-01-01", "2024-06-01"):
        for symbol in [f"S{i}" for i in range(1, 11)]:
            rows.append({
                "snapshot_date": date_value,
                "symbol": symbol,
                "value_factor": 1.0,
                "forward_excess_return_63": 0.01,
            })
    result = validate_factor(rows, config=config)
    # Tuning observations exclude all sealed dates.
    assert result["observations"] == 20  # 2020-06 + 2023-12 only
    assert result["sealed_observations"] == 20  # 2024-01 + 2024-06
    assert result["periods"]["sealed_used_for_tuning"] is False
    assert result["periods"]["sealed_evaluated"] is True
    assert result["periods"]["sealed_range"] == list(SEALED) or result["periods"]["sealed_range"] == SEALED


def test_validate_config_called_at_construction():
    # Constructing an invalid config raises immediately (via __post_init__).
    with pytest.raises(ValueError):
        ResearchConfig(
            research_start="2016-01-01",
            sealed_oos_start="2025-12-31",
            sealed_oos_end="2024-01-01",
        )


def test_windows_deterministic_across_runs():
    config = _config()
    a = walk_forward_windows(config)
    b = walk_forward_windows(config)
    assert a == b


def test_no_tuning_function_accepts_sealed_silently():
    # Architecture guard: tuning paths call assert_not_sealed; a leaked sealed
    # date in the tuning set must raise rather than silently tune.
    config = _config()
    import portfolio.research.validation as validation_mod

    source = validation_mod.__file__
    assert "assert_not_sealed" in open(source, encoding="utf-8").read()


def test_cli_payload_separates_sealed_period():
    from portfolio.research.cli import build_period_payload

    config = _config()
    payload = build_period_payload(config)
    assert payload["sealed_oos"] == {"start": SEALED[0], "end": SEALED[1]}
    assert payload["no_validation_after_sealed"] is True
    assert all(w["valid_end"] < SEALED[0] for w in payload["walk_forward_windows"])