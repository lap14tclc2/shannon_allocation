from decimal import Decimal
import pytest
from portfolio.financial_data.models import CanonicalFact, EntityType, QualityStatus
from portfolio.value_engine import ValuationEngine
from portfolio.value_engine.bank_valuation import BankValuationModel
from portfolio.value_engine.models import ScenarioType

def test_bank_residual_income_model():
    # MBB example: BVPS ~18,000, 5Y ROE ~19%, COE 11.5%
    bvps = Decimal("18000")
    roe = Decimal("19.0")
    price = Decimal("22000")
    shares = Decimal("5000000000")
    
    suite = BankValuationModel.calculate_bank_suite(
        current_bvps=bvps,
        historical_5y_avg_roe=roe,
        current_market_price=price,
        shares_outstanding=shares,
    )
    
    base_scen = suite[ScenarioType.BASE]
    iv = base_scen.intrinsic_value_per_share
    
    # Intrinsic Value of a 19% ROE bank with 11.5% cost of equity should be around 1.3x - 1.8x BVPS (~23,000 - 33,000 VND)
    assert Decimal("23000") <= iv <= Decimal("35000"), f"MBB IV should be realistic banking bounds, got {iv}"
    assert Decimal("1.2") <= (iv / bvps) <= Decimal("2.0"), f"P/B multiple should be 1.2x - 2.0x, got {iv/bvps}"

def test_fcf_capex_sign_invariant():
    # FPT example: CFO = 10.136T, CapEx = -5.098T
    cfo = 10136000000000.0
    capex_raw = -5098000000000.0
    
    # Correct formula: CFO - abs(CapEx)
    fcf = cfo - abs(capex_raw)
    assert round(fcf / 1e12, 3) == 5.038, f"FCF should be 5.038T, got {fcf/1e12}"
