"""Regression tests for the user-owned fixed-combination product contract."""

from __future__ import annotations

import serve


def test_migrate_symbol_parser_accepts_common_user_formats():
    assert serve._normalise_symbols("ACB, FPT, REE, VCB, VNM") == [
        "ACB", "FPT", "REE", "VCB", "VNM"
    ]
    assert serve._normalise_symbols("acb fpt\nree\tvcb vnm") == [
        "ACB", "FPT", "REE", "VCB", "VNM"
    ]
    assert serve._normalise_symbols(["acb", "FPT", " ree "]) == [
        "ACB", "FPT", "REE"
    ]


def test_fixed_combination_size_matches_current_quant_model():
    assert serve.MIN_FIXED_SYMBOLS == 5
    assert serve.MAX_FIXED_SYMBOLS == 10


def test_empty_or_invalid_migrate_payload_does_not_create_symbols():
    assert serve._normalise_symbols(None) == []
    assert serve._normalise_symbols({"ACB": True}) == []
