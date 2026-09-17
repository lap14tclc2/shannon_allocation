"""
Deterministic regression tests for Canonical Share Basis, Corporate Actions, and MOS Integrity.
Validates all Acceptance Criteria (AC1 - AC13) and Cases A through I.
"""
from decimal import Decimal
import pytest

from portfolio.value_engine.share_basis import (
    ShareBasis,
    ShareBasisType,
    ShareBasisStatus,
    calculate_canonical_mos,
    resolve_canonical_share_basis,
)
from portfolio.corporate_action_normalizer import (
    CorporateActionType,
    CorporateActionEvent,
    calculate_cumulative_multiplier,
)
from portfolio.value_engine.dilution import classify_share_change
from portfolio.canonical_valuation import build_canonical_valuation


def test_case_a_no_split():
    """CASE A — No split: 100k bn IV, 1bn shares => IV/share=100k, Price=60k => MOS=40%."""
    equity_iv = Decimal("100000000000000")  # 100,000 bn VND
    shares = Decimal("1000000000")          # 1 bn shares
    iv_per_share = equity_iv / shares        # 100,000 VND
    market_price = Decimal("60000")         # 60,000 VND

    basis = ShareBasis(
        symbol="TEST",
        shares_outstanding=shares,
        diluted_shares=shares,
        valuation_share_count=shares,
        basis_type=ShareBasisType.REPORTED_LATEST_BCTC.value,
        as_of_date="2025-12-31",
        source="TEST_BCTC",
        provenance="TEST_BCTC_2025",
        status=ShareBasisStatus.VALID.value,
        cumulative_split_factor=Decimal("1.0"),
        is_compatible_with_current_price=True,
    )

    mos = calculate_canonical_mos(market_price, iv_per_share, basis)
    assert mos is not None
    assert round(mos, 2) == Decimal("40.00")


def test_case_b_pure_split_1_to_10_mos_invariance():
    """CASE B — Pure 1:10 split: economic value unchanged, MOS remains exactly 40%."""
    old_shares = Decimal("1000000000")
    split_factor = Decimal("10.0")
    new_shares = old_shares * split_factor

    old_iv_per_share = Decimal("100000")
    new_iv_per_share = old_iv_per_share / split_factor  # 10,000 VND

    old_price = Decimal("60000")
    new_price = old_price / split_factor                # 6,000 VND

    basis = ShareBasis(
        symbol="TEST",
        shares_outstanding=new_shares,
        diluted_shares=new_shares,
        valuation_share_count=new_shares,
        basis_type=ShareBasisType.CORPORATE_ACTION_ADJUSTED.value,
        as_of_date="2025-12-31",
        source="TEST_SPLIT",
        provenance="TEST_BCTC_2025_SPLIT_10X",
        status=ShareBasisStatus.VALID.value,
        cumulative_split_factor=split_factor,
        is_compatible_with_current_price=True,
    )

    mos = calculate_canonical_mos(new_price, new_iv_per_share, basis)
    assert mos is not None
    assert round(mos, 2) == Decimal("40.00")


def test_case_c_multiple_splits_cumulative():
    """CASE C — Multiple splits (1:2, 1:5, 1:10 => total 100x): MOS remains 40%."""
    corporate_actions = [
        {"effective_event_date": "2026-01-10", "dividend_type": "STOCK_SPLIT", "stock_ratio": 1.0},   # 1:2 (ratio 1.0 => factor 2.0)
        {"effective_event_date": "2026-02-10", "dividend_type": "STOCK_DIVIDEND", "stock_ratio": 4.0},# 1:5 (ratio 4.0 => factor 5.0)
        {"effective_event_date": "2026-03-01", "dividend_type": "BONUS_SHARES", "stock_ratio": 9.0},  # 1:10 (ratio 9.0 => factor 10.0)
    ]

    basis = resolve_canonical_share_basis(
        symbol="TEST",
        bctc_shares=Decimal("1000000000"),
        bctc_fiscal_year=2025,
        bctc_period_end="2025-12-31",
        corporate_actions=corporate_actions,
        current_market_price=Decimal("600"),
        diluted_shares_estimate=Decimal("1000000000"),
        valuation_date="2026-03-15",
        source="TEST_CUMULATIVE_SPLITS",
    )

    # 1.0 * 2.0 * 5.0 * 10.0 = 100.0x
    assert basis.cumulative_split_factor == Decimal("100.0")
    assert basis.shares_outstanding == Decimal("100000000000") # 100bn
    assert basis.basis_type == ShareBasisType.CORPORATE_ACTION_ADJUSTED.value

    equity_iv = Decimal("100000000000000")  # 100,000 bn VND
    iv_per_share = equity_iv / basis.shares_outstanding # 1,000 VND
    market_price = Decimal("600")

    mos = calculate_canonical_mos(market_price, iv_per_share, basis)
    assert mos is not None
    assert round(mos, 2) == Decimal("40.00")


def test_case_d_economic_dilution_distinguished_from_split():
    """CASE D — Dilution: 1bn -> 1.5bn shares via cash issue. Must NOT be treated as a pure split."""
    dilution = classify_share_change(
        shares_old=1_000_000_000,
        shares_new=1_500_000_000,
        non_economic_events=[],
        economic_events=[{"action_type": "STOCK_ISSUE", "stock_ratio": 0.5}],
    )
    assert dilution["classification"] == "EXCESSIVE_DILUTION"
    assert dilution["confirmed_economic_dilution_pct"] == 50.0
    assert dilution["non_economic_share_change_pct"] == 0.0


def test_case_e_share_count_basis_mismatch_detected():
    """CASE E — Unresolved / Conflicted share count basis blocks confident MOS calculation."""
    unresolved_basis = ShareBasis(
        symbol="TEST",
        shares_outstanding=Decimal("1000000000"),
        diluted_shares=Decimal("1000000000"),
        valuation_share_count=Decimal("1000000000"),
        basis_type=ShareBasisType.UNRESOLVED_MISMATCH.value,
        as_of_date="2024-12-31",
        source="UNVERIFIED",
        provenance="MISMATCHED_HISTORICAL",
        status=ShareBasisStatus.UNRESOLVED_MISMATCH.value,
        cumulative_split_factor=Decimal("1.0"),
        is_compatible_with_current_price=False,
    )
    mos = calculate_canonical_mos(Decimal("50000"), Decimal("100000"), unresolved_basis)
    # Unresolved basis MUST NOT produce confident MOS
    assert mos is None


def test_case_f_missing_share_count_blocks_mos():
    """CASE F — Missing share count returns None, never zero or false safety."""
    missing_basis = ShareBasis(
        symbol="TEST",
        shares_outstanding=Decimal("0"),
        diluted_shares=Decimal("0"),
        valuation_share_count=Decimal("0"),
        basis_type=ShareBasisType.INSUFFICIENT_DATA.value,
        as_of_date="",
        source="NONE",
        provenance="MISSING_DATA",
        status=ShareBasisStatus.INSUFFICIENT_DATA.value,
        cumulative_split_factor=Decimal("1.0"),
        is_compatible_with_current_price=False,
    )
    mos = calculate_canonical_mos(Decimal("50000"), Decimal("100000"), missing_basis)
    assert mos is None


def test_case_g_already_per_share_valuation_no_double_division():
    """CASE G — Bank RIM / per-share valuation does not divide by share count again."""
    from portfolio.value_engine.bank_valuation import BankValuationModel
    from portfolio.value_engine.models import ScenarioType
    from portfolio.financial_data.models import FactIdentityKey, CanonicalFact, StatementType, PeriodType, ConsolidationScope, QualityStatus

    facts = [
        CanonicalFact(
            canonical_fact_id="f1",
            identity=FactIdentityKey("sec-bank", StatementType.BALANCE_SHEET, "2024-12-31", PeriodType.FY, 2024, None, ConsolidationScope.CONSOLIDATED, "BS.EQUITY.TOTAL", "VND"),
            value=Decimal("100000000000000"),
            quality_status=QualityStatus.OFFICIAL_VERIFIED,
            decision_id="d1", winning_candidate_id="c1", candidate_ids=[], observed_at="", valid_from="", reason=""
        ),
        CanonicalFact(
            canonical_fact_id="f2",
            identity=FactIdentityKey("sec-bank", StatementType.INCOME_STATEMENT, "2024-12-31", PeriodType.FY, 2024, None, ConsolidationScope.CONSOLIDATED, "IS.PROFIT.NET", "VND"),
            value=Decimal("20000000000000"),
            quality_status=QualityStatus.OFFICIAL_VERIFIED,
            decision_id="d2", winning_candidate_id="c2", candidate_ids=[], observed_at="", valid_from="", reason=""
        )
    ]
    shares = Decimal("5000000000") # 5bn shares
    price = Decimal("25000")

    basis = ShareBasis(
        symbol="BANK_TEST",
        shares_outstanding=shares,
        diluted_shares=shares,
        valuation_share_count=shares,
        basis_type=ShareBasisType.REPORTED_LATEST_BCTC.value,
        as_of_date="2024-12-31",
        source="BANK_TEST",
        provenance="BANK_TEST_2024",
        status=ShareBasisStatus.VALID.value,
        cumulative_split_factor=Decimal("1.0"),
        is_compatible_with_current_price=True,
    )

    scenario = BankValuationModel.calculate_rim_scenario(
        current_bvps=Decimal("20000"),
        base_roe=Decimal("0.20"),
        cost_of_equity=Decimal("0.11"),
        retention_ratio=Decimal("0.80"),
        terminal_growth=Decimal("0.035"),
        shares_outstanding=shares,
        current_market_price=price,
        scenario_type=ScenarioType.BASE,
    )
    # IV/share in bank RIM is derived from BVPS (~20,000 VND) + PV excess ROE, should be ~20,000-40,000 VND range, NOT 0.005 VND (double division).
    assert scenario.intrinsic_value_per_share > Decimal("10000")
    assert scenario.equity_value == scenario.intrinsic_value_per_share * shares


def test_case_h_bfc_regression():
    """CASE H — BFC regression: verify lineage, provenance, share count (57.2M), and MOS integrity."""
    val = build_canonical_valuation("BFC", market_price=48000.0)
    assert val["ok"] is True
    assert val["symbol"] == "BFC"
    assert val["shares_outstanding"] == 57200000.0
    assert val["share_basis"] is not None
    assert val["share_basis"]["status"] == "VALID"
    assert val["base_iv"] is not None
    assert val["base_iv"] > 50000.0  # ~147,901 VND
    assert val["actual_mos_pct"] is not None
    assert val["actual_mos_pct"] > 0
    assert val["valuation_snapshot"] is not None
    assert val["valuation_snapshot"]["market_price"] == 48000.0


def test_case_i_hah_regression():
    """CASE I — HAH regression: verify lineage, provenance, and MOS integrity."""
    val = build_canonical_valuation("HAH", market_price=45000.0)
    assert val["ok"] is True
    assert val["symbol"] == "HAH"
    assert val["shares_outstanding"] is not None
    assert val["shares_outstanding"] > 0
    assert val["share_basis"] is not None
    assert val["base_iv"] is not None
    assert val["actual_mos_pct"] is not None
    assert val["valuation_snapshot"] is not None
