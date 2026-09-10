"""Qualitative Evidence and Munger Precommitment Framework Models (Task 133)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


QualitativeDimension = Literal[
    "UNDERSTANDABILITY",
    "MOAT",
    "MANAGEMENT_CAPITAL_ALLOCATION",
    "ACCOUNTING_RELIABILITY_QUALITATIVE",
    "CIRCLE_OF_COMPETENCE",
]

EvidenceStatus = Literal["PASS", "WATCH", "FAIL", "UNKNOWN", "NOT_APPLICABLE"]
ConfidenceLevel = Literal["HIGH", "MEDIUM", "LOW"]
EvidenceSource = Literal[
    "MANUAL_USER_REVIEW",
    "ANNUAL_REPORT",
    "MANAGEMENT_DISCLOSURE",
    "REGULATORY_FILING",
    "COMPANY_PRESENTATION",
    "EXTERNAL_RESEARCH",
    "AI_SUMMARY",
]


@dataclass
class QualitativeEvidenceItem:
    """Individual structured qualitative evidence item."""

    symbol: str
    dimension: QualitativeDimension
    status: EvidenceStatus
    confidence: ConfidenceLevel = "MEDIUM"
    evidence_type: str | None = None
    evidence_text: str | None = None
    supporting_evidence: list[str] = field(default_factory=list)
    counter_evidence: list[str] = field(default_factory=list)
    source: EvidenceSource = "MANUAL_USER_REVIEW"
    source_date: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reviewed_at: str | None = None
    reviewer: str | None = "USER"

    def __post_init__(self):
        if self.evidence_text and not self.supporting_evidence and not self.counter_evidence:
            if self.status == "FAIL":
                self.counter_evidence = [self.evidence_text]
            else:
                self.supporting_evidence = [self.evidence_text]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QualitativeEvidenceItem:
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


MUNGER_PRECOMMITMENT_QUESTIONS = [
    ("Q1", "What would make this thesis wrong?"),
    ("Q2", "What evidence would show the moat is weakening?"),
    ("Q3", "What if normalized earnings fall 30%?"),
    ("Q4", "What if intrinsic value is overstated by 30%?"),
    ("Q5", "Could I hold if price falls 50%?"),
    ("Q6", "Would I own this if the exchange closed for 5 years?"),
    ("Q7", "Am I buying because value increased or merely because price fell?"),
    ("Q8", "What evidence would falsify my thesis?"),
]


@dataclass
class MungerChecklistQuestion:
    """Individual question in the Munger Precommitment Checklist."""

    question_id: str
    question_text: str
    status: Literal["ANSWERED", "UNANSWERED", "CONCERN"] = "UNANSWERED"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MungerChecklist:
    """Munger Precommitment Checklist for a stock thesis."""

    symbol: str
    questions: list[MungerChecklistQuestion] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def overall_status(self) -> str:
        if any(q.status == "CONCERN" for q in self.questions):
            return "CONCERN"
        if all(q.status == "ANSWERED" for q in self.questions):
            return "ANSWERED"
        return "UNANSWERED"

    def concerns(self) -> list[str]:
        return [q.question_id for q in self.questions if q.status == "CONCERN"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "overall_status": self.overall_status(),
            "concerns": self.concerns(),
            "questions": [q.to_dict() for q in self.questions],
            "updated_at": self.updated_at,
        }


def build_default_munger_checklist(symbol: str) -> MungerChecklist:
    """Construct an initial un-answered Munger Precommitment Checklist."""
    questions = [
        MungerChecklistQuestion(question_id=qid, question_text=qtext)
        for qid, qtext in MUNGER_PRECOMMITMENT_QUESTIONS
    ]
    return MungerChecklist(symbol=symbol.strip().upper(), questions=questions)


class QualitativeEvalResult(dict):
    """Result dict supporting tuple unpacking (status, supporting, counter)."""

    def __getitem__(self, item: Any) -> Any:
        if isinstance(item, int):
            keys = ["status", "supporting", "counter"]
            return super().__getitem__(keys[item])
        return super().__getitem__(item)

    def __iter__(self):
        return iter((self["status"], self["supporting"], self["counter"]))


def evaluate_qualitative_dimension(
    arg1: list[QualitativeEvidenceItem] | str,
    arg2: list[QualitativeEvidenceItem] | str,
) -> QualitativeEvalResult:
    """Evaluate canonical status and evidence summary for a qualitative dimension.
    
    Accepts either (dimension, items) or (items, dimension).
    """
    if isinstance(arg1, str):
        dimension = arg1
        items = arg2 if isinstance(arg2, list) else []
    else:
        items = arg1 if isinstance(arg1, list) else []
        dimension = arg2 if isinstance(arg2, str) else ""

    dim_items = [item for item in items if isinstance(item, QualitativeEvidenceItem) and item.dimension == dimension]
    if not dim_items:
        return QualitativeEvalResult({
            "status": "UNKNOWN",
            "confidence": "LOW",
            "supporting": [],
            "counter": [],
            "missing": ["Explicit evidence required"],
        })

    supporting: list[str] = []
    counter: list[str] = []
    has_pass = False
    has_fail = False
    has_ai_only = True

    for item in dim_items:
        supporting.extend(item.supporting_evidence)
        counter.extend(item.counter_evidence)

        if item.source != "AI_SUMMARY":
            has_ai_only = False

        if item.status == "FAIL":
            has_fail = True
        elif item.status == "PASS":
            has_pass = True

    if counter or has_fail:
        final_status = "FAIL" if has_fail else "WATCH"
        confidence = "HIGH"
    elif has_pass:
        final_status = "WATCH" if has_ai_only else "PASS"
        confidence = "MEDIUM" if has_ai_only else "HIGH"
    else:
        final_status = "UNKNOWN"
        confidence = "LOW"

    missing = []
    if final_status == "UNKNOWN":
        missing.append("Explicit evidence required")

    return QualitativeEvalResult({
        "status": final_status,
        "confidence": confidence,
        "supporting": list(dict.fromkeys(supporting)),
        "counter": list(dict.fromkeys(counter)),
        "missing": missing,
    })
