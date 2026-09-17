"""
Task 192: Deterministic Sensitivity Analysis Script
"""
import os
import sys

if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "postgresql://qport:qport@127.0.0.1:5432/qport"

from decimal import Decimal
from typing import Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from portfolio.canonical_valuation import build_canonical_valuation
from portfolio.value_engine.dcf import DCFValuationModel
from portfolio.value_engine.models import ScenarioType

def run_sensitivity(symbol: str = "FPT"):
    val = build_canonical_valuation(symbol)
    rep = val["report"]
    base_scen = rep["scenarios"]["BASE"]
    oe_bridge = rep["owner_earnings_bridge"]
    shares = Decimal(str(val["shares_outstanding"]))
    net_debt = Decimal(str(base_scen["net_debt"]))
    base_oe = Decimal(str(oe_bridge["owner_earnings"]))
    price = Decimal(str(val["current_price"]))
    base_g = Decimal(str(base_scen["growth_stage1_rate"]))
    base_r = Decimal(str(base_scen["discount_rate"]))
    base_tg = Decimal(str(base_scen["terminal_growth_rate"]))
    
    print("=" * 80)
    print(f"SENSITIVITY ANALYSIS FOR {symbol} (Base OE: {base_oe/Decimal('1e9'):,.1f}B, Price: {price:,.0f} VND)")
    print(f"Base Assumptions: r = {base_r*100:.1f}%, g = {base_g*100:.1f}%, tg = {base_tg*100:.1f}%")
    print("=" * 80)
    
    # 1. Discount Rate Sensitivity (+-1%, +-2%)
    print("\n1. DISCOUNT RATE SENSITIVITY (g=base, tg=base):")
    for delta in [-Decimal("0.02"), -Decimal("0.01"), Decimal("0.00"), Decimal("0.01"), Decimal("0.02")]:
        r = base_r + delta
        scen = DCFValuationModel.calculate_scenario(
            base_owner_earnings=base_oe,
            shares_outstanding=shares,
            net_debt=net_debt,
            scenario_type=ScenarioType.BASE,
            discount_rate=r,
            growth_rate=base_g,
            growth_years=5,
            terminal_growth=base_tg,
            current_market_price=price,
        )
        iv = scen.intrinsic_value_per_share
        mos = scen.margin_of_safety_pct
        pct_change = ((iv - base_scen['intrinsic_value_per_share']) / base_scen['intrinsic_value_per_share']) * 100
        print(f"  r = {r*100:4.1f}% | IV: {iv:8,.0f} VND ({pct_change:+5.1f}%) | MOS: {mos:+5.1f}% | TV Contrib: {scen.terminal_value_contribution_pct:.1f}%")

    # 2. Stage 1 Growth Sensitivity (+-2%, +-5%)
    print("\n2. STAGE 1 GROWTH SENSITIVITY (r=base, tg=base):")
    for delta in [-Decimal("0.05"), -Decimal("0.02"), Decimal("0.00"), Decimal("0.02"), Decimal("0.05")]:
        g = base_g + delta
        scen = DCFValuationModel.calculate_scenario(
            base_owner_earnings=base_oe,
            shares_outstanding=shares,
            net_debt=net_debt,
            scenario_type=ScenarioType.BASE,
            discount_rate=base_r,
            growth_rate=g,
            growth_years=5,
            terminal_growth=base_tg,
            current_market_price=price,
        )
        iv = scen.intrinsic_value_per_share
        mos = scen.margin_of_safety_pct
        pct_change = ((iv - base_scen['intrinsic_value_per_share']) / base_scen['intrinsic_value_per_share']) * 100
        print(f"  g = {g*100:4.1f}% | IV: {iv:8,.0f} VND ({pct_change:+5.1f}%) | MOS: {mos:+5.1f}% | TV Contrib: {scen.terminal_value_contribution_pct:.1f}%")

    # 3. Terminal Growth Sensitivity (+-0.5%, +-1.0%)
    print("\n3. TERMINAL GROWTH SENSITIVITY (r=base, g=base):")
    for delta in [-Decimal("0.010"), -Decimal("0.005"), Decimal("0.000"), Decimal("0.005"), Decimal("0.010")]:
        tg = base_tg + delta
        scen = DCFValuationModel.calculate_scenario(
            base_owner_earnings=base_oe,
            shares_outstanding=shares,
            net_debt=net_debt,
            scenario_type=ScenarioType.BASE,
            discount_rate=base_r,
            growth_rate=base_g,
            growth_years=5,
            terminal_growth=tg,
            current_market_price=price,
        )
        iv = scen.intrinsic_value_per_share
        mos = scen.margin_of_safety_pct
        pct_change = ((iv - base_scen['intrinsic_value_per_share']) / base_scen['intrinsic_value_per_share']) * 100
        print(f"  tg = {tg*100:4.2f}% | IV: {iv:8,.0f} VND ({pct_change:+5.1f}%) | MOS: {mos:+5.1f}% | TV Contrib: {scen.terminal_value_contribution_pct:.1f}%")

    # 4. Maintenance CapEx Sensitivity (+-10%, +-20%)
    print("\n4. MAINTENANCE CAPEX SENSITIVITY (r=base, g=base, tg=base):")
    maint_capex = Decimal(str(oe_bridge.get("maintenance_capex") or oe_bridge.get("depreciation") or 0))
    for delta_pct in [-Decimal("0.20"), -Decimal("0.10"), Decimal("0.00"), Decimal("0.10"), Decimal("0.20")]:
        adj_capex = maint_capex * (Decimal("1") + delta_pct)
        # Recalculate OE: Net Income + D&A - adj_capex - delta_wc
        ni = Decimal(str(oe_bridge.get("net_income") or 0))
        da = Decimal(str(oe_bridge.get("depreciation") or 0))
        dwc = Decimal(str(oe_bridge.get("working_capital_change") or 0))
        adj_oe = ni + da - adj_capex - dwc
        scen = DCFValuationModel.calculate_scenario(
            base_owner_earnings=adj_oe,
            shares_outstanding=shares,
            net_debt=net_debt,
            scenario_type=ScenarioType.BASE,
            discount_rate=base_r,
            growth_rate=base_g,
            growth_years=5,
            terminal_growth=base_tg,
            current_market_price=price,
        )
        iv = scen.intrinsic_value_per_share
        mos = scen.margin_of_safety_pct
        pct_change = ((iv - base_scen['intrinsic_value_per_share']) / base_scen['intrinsic_value_per_share']) * 100
        print(f"  CapEx {delta_pct*100:+3.0f}% ({adj_capex/Decimal('1e9'):4.0f}B) -> OE: {adj_oe/Decimal('1e9'):4.0f}B | IV: {iv:8,.0f} VND ({pct_change:+5.1f}%) | MOS: {mos:+5.1f}%")

if __name__ == "__main__":
    run_sensitivity("FPT")
    run_sensitivity("BFC")
