"""
Task 192: Intrinsic Value / DCF Conservatism Audit - Real PostgreSQL Regression & Sensitivity Analysis.
"""
import os
import sys

if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "postgresql://qport:qport@127.0.0.1:5432/qport"

from decimal import Decimal
from typing import Dict, Any, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from portfolio.canonical_valuation import build_canonical_valuation

CORE_SYMBOLS = ["BFC", "HAH", "FPT", "DGC", "TLG", "ACB", "TCB", "TPB", "VNM", "HPG", "MWG", "VHM", "VIC", "GAS", "VRE"]

def run_regression():
    print("=" * 140)
    print("TASK 192: REAL POSTGRESQL CANONICAL DATA REGRESSION (15 CORE SYMBOLS)")
    print("=" * 140)

    results = []
    
    for sym in CORE_SYMBOLS:
        try:
            val = build_canonical_valuation(sym)
            if not val.get("ok"):
                print(f"[-] {sym:4s}: Incomplete - {val.get('error')}")
                results.append({
                    "symbol": sym,
                    "status": "INCOMPLETE",
                    "error": val.get("error"),
                })
                continue
            
            rep = val.get("report") or {}
            arch = rep.get("archetype_profile", {})
            oe_bridge = rep.get("owner_earnings_bridge") or {}
            growth = rep.get("growth_derivation") or {}
            scenarios = rep.get("scenarios") or {}
            
            base_scen = scenarios.get("BASE") or {}
            bear_scen = scenarios.get("BEAR") or {}
            bull_scen = scenarios.get("BULL") or {}
            
            base_iv = base_scen.get("intrinsic_value_per_share")
            bear_iv = bear_scen.get("intrinsic_value_per_share")
            bull_iv = bull_scen.get("intrinsic_value_per_share")
            
            discount_r = base_scen.get("discount_rate")
            term_g = base_scen.get("terminal_growth_rate")
            tv_contrib = base_scen.get("terminal_value_contribution_pct")
            
            norm_method = oe_bridge.get("normalization_method", "N/A")
            base_oe = oe_bridge.get("owner_earnings")
            
            price = val.get("current_price") or rep.get("current_market_price")
            mos = val.get("actual_mos_pct")
            req_mos = val.get("required_mos_pct")
            conf = rep.get("confidence_level")
            model_status = rep.get("model_status")
            val_model = rep.get("valuation_model") or str(arch.get("actual_model") or "")
            
            val_model_str = str(val_model) if val_model else "N/A"
            oe_str = f"{float(base_oe)/1e9:,.1f}B" if base_oe is not None else "N/A"
            r_str = f"{float(discount_r)*100:.1f}%" if discount_r is not None else "N/A"
            g_str = f"{float(term_g)*100:.1f}%" if term_g is not None else "N/A"
            tv_str = f"{float(tv_contrib):.1f}%" if tv_contrib is not None else "N/A"
            bear_str = f"{float(bear_iv):,.0f}" if bear_iv is not None else "N/A"
            base_str = f"{float(base_iv):,.0f}" if base_iv is not None else "N/A"
            bull_str = f"{float(bull_iv):,.0f}" if bull_iv is not None else "N/A"
            price_str = f"{float(price):,.0f}" if price is not None else "N/A"
            mos_str = f"{float(mos):.1f}%" if mos is not None else "N/A"
            req_mos_str = f"{float(req_mos):.1f}%" if req_mos is not None else "N/A"
            
            print(f"[+] {sym:4s} | {val_model_str:29s} | Norm: {norm_method:17s} | OE: {oe_str:>8s} | r: {r_str:>5s} | g: {g_str:>5s} | TV: {tv_str:>5s} | Bear: {bear_str:>7s} | Base: {base_str:>7s} | Bull: {bull_str:>7s} | Price: {price_str:>7s} | MOS: {mos_str:>6s} | ReqMOS: {req_mos_str:>5s} | Status: {model_status}")

            results.append({
                "symbol": sym,
                "archetype": arch.get("archetype") if isinstance(arch, dict) else "N/A",
                "model": val_model_str,
                "norm_method": norm_method,
                "base_oe": float(base_oe) if base_oe else None,
                "discount_rate": float(discount_r) if discount_r else None,
                "terminal_growth": float(term_g) if term_g else None,
                "tv_contrib": float(tv_contrib) if tv_contrib else None,
                "bear_iv": float(bear_iv) if bear_iv else None,
                "base_iv": float(base_iv) if base_iv else None,
                "bull_iv": float(bull_iv) if bull_iv else None,
                "price": float(price) if price else None,
                "mos": float(mos) if mos is not None else None,
                "req_mos": float(req_mos) if req_mos is not None else None,
                "confidence": str(conf),
                "model_status": model_status,
            })
        except Exception as e:
            print(f"[!] Error on {sym}: {e}")
            import traceback
            traceback.print_exc()

    return results

if __name__ == "__main__":
    run_regression()
