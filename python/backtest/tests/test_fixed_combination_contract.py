"""Regression tests for optimizer product-level parsing and bounds."""

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


def test_portfolio_size_bounds_match_quant_model():
    assert serve.MIN_FIXED_SYMBOLS == 5
    assert serve.MAX_FIXED_SYMBOLS == 10


def test_allocation_search_bounds_are_variable_not_fixed_quarterly():
    assert serve.MIN_ALLOCATIONS == 1
    assert serve.MAX_ALLOCATIONS == 6
    assert serve.MIN_ALLOCATIONS < 4 < serve.MAX_ALLOCATIONS


def test_supported_product_universes_include_full_joint_search():
    assert {"all", "vn100", "vn50", "vn30"}.issubset(serve.VALID_UNIVERSES)


def test_empty_or_invalid_migrate_payload_does_not_create_symbols():
    assert serve._normalise_symbols(None) == []
    assert serve._normalise_symbols({"ACB": True}) == []
