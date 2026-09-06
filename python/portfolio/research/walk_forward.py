"""T13 — Chronological walk-forward windows and sealed OOS.

Time-series data is NEVER randomly split. Windows are strictly chronological.

Config concept:
    research_start      first in-sample date
    train_years         rolling training window length (default 5)
    validation_years    out-of-sample validation step length (default 1)
    sealed_oos_start    final sealed period start (excluded from ALL tuning)
    sealed_oos_end      final sealed period end

SEALED-OOS INVARIANT
--------------------
If ``sealed_oos_start = S`` and ``sealed_oos_end = E`` then ALL training /
validation / tuning windows MUST satisfy::

    window.valid_end < S

No tuning/validation window may overlap [S, E], start inside [S, E], or
continue after E in the same research run. The sealed period is the FINAL
untouched period.

Enforcement:
- ``walk_forward_windows`` uses ``research_cutoff(config)`` (the day before S)
  as its effective upper boundary, so no validation window can reach S.
- ``validate_config`` rejects structurally invalid ranges at construction.
- ``assert_not_sealed`` is a second defensive guard for any tuning path.
- ``partition_periods`` returns ``tuning_allowed`` / ``sealed_oos`` explicitly.
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


def _iso(value) -> str:
    return date.fromisoformat(str(value)[:10]).isoformat()


@dataclass(frozen=True)
class ResearchConfig:
    research_start: str
    research_end: str | None = None
    train_years: int = 5
    validation_years: int = 1
    sealed_oos_start: str | None = None
    sealed_oos_end: str | None = None

    def __post_init__(self) -> None:
        validate_config(self)


def validate_config(config: "ResearchConfig") -> None:
    """Validate sealed-OOS structural invariants. Raises ValueError."""
    if config.train_years <= 0 or config.validation_years <= 0:
        raise ValueError("train_years and validation_years must be positive")

    start = _iso(config.research_start)
    sealed_start = _iso(config.sealed_oos_start) if config.sealed_oos_start else None
    sealed_end = _iso(config.sealed_oos_end) if config.sealed_oos_end else None
    research_end = _iso(config.research_end) if config.research_end else None

    if (sealed_start is None) != (sealed_end is None):
        raise ValueError(
            "sealed_oos_start and sealed_oos_end must both be set (or both unset)"
        )

    if sealed_start is not None:
        if not sealed_start < sealed_end:
            raise ValueError(
                f"sealed_oos_start ({sealed_start}) must be before sealed_oos_end ({sealed_end})"
            )
        if not start < sealed_start:
            raise ValueError(
                f"research_start ({start}) must be before sealed_oos_start ({sealed_start})"
            )
    if research_end is not None and sealed_end is not None:
        if not sealed_end <= research_end:
            raise ValueError(
                f"sealed_oos_end ({sealed_end}) must not exceed research_end ({research_end})"
            )


def research_cutoff(config: "ResearchConfig") -> date:
    """Effective inclusive upper bound for training/validation window generation.

    When a sealed OOS is configured, the cutoff is the day BEFORE
    ``sealed_oos_start``, guaranteeing ``window.valid_end < sealed_oos_start``.
    Otherwise it is ``research_end`` (or today when research_end is unset).
    """
    validate_config(config)
    if config.sealed_oos_start:
        return date.fromisoformat(_iso(config.sealed_oos_start)) - timedelta(days=1)
    if config.research_end:
        return date.fromisoformat(_iso(config.research_end))
    return date.today()


def walk_forward_windows(config: "ResearchConfig") -> list[dict]:
    """Chronological rolling windows: train -> validate. Never random.

    All generated windows satisfy ``valid_end < sealed_oos_start`` when a sealed
    period is configured. When the training window cannot fit before the sealed
    boundary, the window list is empty (safe degradation).
    """
    validate_config(config)
    start = date.fromisoformat(_iso(config.research_start))
    end = research_cutoff(config)
    windows: list[dict] = []
    valid_start = add_years(start, config.train_years)
    while valid_start <= end:
        valid_end = min(add_years(valid_start, config.validation_years) - timedelta(days=1), end)
        if valid_end < valid_start:
            break
        train_end = valid_start - timedelta(days=1)
        windows.append({
            "train_start": start.isoformat(),
            "train_end": train_end.isoformat(),
            "valid_start": valid_start.isoformat(),
            "valid_end": valid_end.isoformat(),
        })
        valid_start = valid_end + timedelta(days=1)
    return windows


def is_sealed(config: "ResearchConfig", date_value) -> bool:
    if not config.sealed_oos_start or not config.sealed_oos_end:
        return False
    value = _iso(date_value)
    return config.sealed_oos_start <= value <= config.sealed_oos_end


def assert_not_sealed(config: "ResearchConfig", date_value) -> None:
    """Defensive guard: a sealed-OOS date must never reach a tuning path."""
    if is_sealed(config, date_value):
        raise ValueError(
            f"sealed OOS date {date_value} cannot be used for tuning "
            f"({config.sealed_oos_start}..{config.sealed_oos_end})"
        )


def partition_periods(config: "ResearchConfig", dates: list[str]) -> dict:
    """Partition dates into tuning-allowed vs sealed-OOS.

    Explicit semantics (new names):
        ``tuning_allowed``  -> dates NOT in the sealed window (may be tuned)
        ``sealed_oos``      -> dates strictly inside [sealed_oos_start, sealed_oos_end]

    Compatibility aliases (retained): ``in_sample`` == ``tuning_allowed`` and
    ``sealed`` == ``sealed_oos``.
    """
    tuning_allowed: list[str] = []
    sealed_oos: list[str] = []
    for value in dates:
        if is_sealed(config, value):
            sealed_oos.append(value)
        else:
            tuning_allowed.append(value)
    return {
        "tuning_allowed": tuning_allowed,
        "sealed_oos": sealed_oos,
        "in_sample": tuning_allowed,
        "sealed": sealed_oos,
        "sealed_range": (config.sealed_oos_start, config.sealed_oos_end)
        if config.sealed_oos_start and config.sealed_oos_end
        else None,
    }