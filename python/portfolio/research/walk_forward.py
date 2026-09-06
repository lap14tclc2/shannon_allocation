"""T13 — Chronological walk-forward windows and sealed OOS.

Time-series data is NEVER randomly split. Windows are strictly chronological.

Config concept:
    research_start      first in-sample date
    train_years         rolling training window length (default 5)
    validation_years    out-of-sample validation step length (default 1)
    sealed_oos_start    final sealed period start (excluded from ALL tuning)
    sealed_oos_end      final sealed period end

The sealed OOS period is protected by construction: tuning functions receive
only in-sample partitions; any date inside the sealed window raises a guard.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


def add_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        # Feb 29 -> Feb 28 on non-leap target years.
        return value.replace(year=value.year + years, day=28)


@dataclass(frozen=True)
class ResearchConfig:
    research_start: str
    research_end: str | None = None
    train_years: int = 5
    validation_years: int = 1
    sealed_oos_start: str | None = None
    sealed_oos_end: str | None = None

    def __post_init__(self) -> None:
        if self.train_years <= 0 or self.validation_years <= 0:
            raise ValueError("train_years and validation_years must be positive")


def walk_forward_windows(config: ResearchConfig) -> list[dict]:
    """Chronological rolling windows: train -> validate. Never random."""
    start = date.fromisoformat(config.research_start)
    end = date.fromisoformat(config.research_end) if config.research_end else date.today()
    windows: list[dict] = []
    valid_start = add_years(start, config.train_years)
    while valid_start < end:
        valid_end = min(add_years(valid_start, config.validation_years) - timedelta(days=1), end)
        train_end = valid_start - timedelta(days=1)
        windows.append({
            "train_start": start.isoformat(),
            "train_end": train_end.isoformat(),
            "valid_start": valid_start.isoformat(),
            "valid_end": valid_end.isoformat(),
        })
        if valid_end >= end:
            break
        valid_start = valid_end + timedelta(days=1)
    return windows


def is_sealed(config: ResearchConfig, date_value) -> bool:
    if not config.sealed_oos_start or not config.sealed_oos_end:
        return False
    value = date.fromisoformat(str(date_value)[:10])
    return config.sealed_oos_start <= value.isoformat() <= config.sealed_oos_end


def assert_not_sealed(config: ResearchConfig, date_value) -> None:
    """Guard: a sealed-OOS date must never reach a tuning path."""
    if is_sealed(config, date_value):
        raise ValueError(
            f"sealed OOS date {date_value} cannot be used for tuning "
            f"({config.sealed_oos_start}..{config.sealed_oos_end})"
        )


def partition_periods(config: ResearchConfig, dates: list[str]) -> dict:
    """Partition dates into in-sample (tuning-allowed) vs sealed-OOS.

    Tuning code should consume ONLY ``in_sample`` dates. Returns:
        {"in_sample": [...], "sealed": [...], "sealed_range": (start, end) or None}
    """
    in_sample: list[str] = []
    sealed: list[str] = []
    for value in dates:
        if is_sealed(config, value):
            sealed.append(value)
        else:
            in_sample.append(value)
    return {
        "in_sample": in_sample,
        "sealed": sealed,
        "sealed_range": (config.sealed_oos_start, config.sealed_oos_end)
        if config.sealed_oos_start and config.sealed_oos_end
        else None,
    }