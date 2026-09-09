"""Decision evidence contract and explainable payload models (T09)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DecisionRuleTrigger:
    """Individual rule triggering a decision condition."""

    rule_id: str
    metric: str
    value: Any
    threshold: Any
    status: str  # PASS, FAIL, WATCH, TRIGGERED
    source: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DecisionEvidence:
    """Canonical explainable decision evidence payload."""

    symbol: str
    decision: str  # BUY, BUY_MORE, HOLD, HOLD_NO_NEW_CAPITAL, WAIT_FOR_MOS, BUILD_RESERVE_FIRST, REVIEW_BUSINESS, AVOID, SELL_REVIEW, SELL
    confidence: str  # HIGH, MEDIUM, LOW

    summary: str
    reasons: list[str] = field(default_factory=list)
    facts: list[dict[str, Any]] = field(default_factory=list)
    rules_triggered: list[DecisionRuleTrigger] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)
    what_changed: list[str] = field(default_factory=list)
    what_would_change_decision: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["rules_triggered"] = [r.to_dict() if isinstance(r, DecisionRuleTrigger) else r for r in self.rules_triggered]
        return d
