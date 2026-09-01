"""
Numeric-Only Validation & Regime Engine (feedback.txt).

Sub-package value_engine.validation cung cấp pipeline:
  anomaly_detector (Layer 1) -> coherence_checker (Layer 2) -> regime_detector &
  cycle_detector (Layer 3) -> materiality_checker -> validation_gate (resolver).
"""
from .validation_gate import ValidationResult, run_validation_gate

__all__ = ["ValidationResult", "run_validation_gate"]