import sys
import os
import psycopg
from collections import defaultdict
from decimal import Decimal

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, "python")

from portfolio.financial_data.models import (
    CanonicalFact, FactIdentityKey, StatementType, PeriodType,
    ConsolidationScope, QualityStatus, EntityType
)
from portfolio.value_engine.engine import ValuationEngine
from portfolio.value_engine.archetypes import ArchetypeClassifier

db_url = os.getenv("DATABASE_URL", "postgresql://qport:qport@127.0.0.1:5432/qport")

def audit_universe():
    print(f"Connecting to database: {db_url[:45]}...")
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT symbol, exchange, company_name, industry FROM qport_finance.securities ORDER BY symbol")
            securities = cur.fetchall()
            
            cur.execute("""
                SELECT symbol, count(*) as fact_count, 
                       max(fiscal_year) as latest_year,
                       array_agg(DISTINCT line_item_code) as items
                FROM qport_finance.canonical_facts
                WHERE period_type = 'FY' AND fiscal_quarter IS NULL
                GROUP BY symbol
            """)
            fact_summary = {r[0]: (r[1], r[2], set(r[3])) for r in cur.fetchall()}

    total_sec = len(securities)
    print(f"Total Securities in Database: {total_sec}")
    
    status_counts = defaultdict(int)
    exchange_counts = defaultdict(lambda: defaultdict(int))
    
    no_bctc = []
    verified_symbols = []
    unvaluable_symbols = []
    specialized_model_needed = []
    fallback_generic = []
    other_incomplete = []
    
    for sym, exch, name, ind in securities:
        if sym not in fact_summary or fact_summary[sym][0] < 5:
            status_counts["NO_BCTC_DATA"] += 1
            exchange_counts[exch]["NO_BCTC_DATA"] += 1
            no_bctc.append((sym, exch, ind))
            continue
            
        fact_count, latest_year, items = fact_summary[sym]
        
        # Check required core line items
        has_profit = "IS.PROFIT.NET" in items
        has_equity = "BS.EQUITY.TOTAL" in items
        has_shares = "IS.SHARES.OUTSTANDING" in items
        
        if not (has_profit and has_equity and has_shares):
            status_counts["INSUFFICIENT_CORE_FACTS"] += 1
            exchange_counts[exch]["INSUFFICIENT_CORE_FACTS"] += 1
            other_incomplete.append((sym, exch, ind, "Missing net_profit, equity or shares"))
            continue
            
        arch_prof = ArchetypeClassifier.classify(sym, ind)
        
        # Check model requirements
        if arch_prof.recommended_model in ("RNAV", "LEASE_CASHFLOW_DCF", "SOTP", "RESERVE_NAV", "FLEET_NAV", "AIRLINE_EBITDAR"):
            status_counts["SPECIALIZED_MODEL_GATED"] += 1
            exchange_counts[exch]["SPECIALIZED_MODEL_GATED"] += 1
            specialized_model_needed.append((sym, exch, ind, arch_prof.recommended_model, arch_prof.reason))
        elif arch_prof.archetype.value in ("GENERIC_ENTERPRISE", "ARCHETYPE_UNKNOWN"):
            status_counts["FALLBACK_GENERIC_ONLY"] += 1
            exchange_counts[exch]["FALLBACK_GENERIC_ONLY"] += 1
            fallback_generic.append((sym, exch, ind))
        else:
            status_counts["MODEL_VERIFIED_CAPABLE"] += 1
            exchange_counts[exch]["MODEL_VERIFIED_CAPABLE"] += 1
            verified_symbols.append((sym, exch, ind, arch_prof.recommended_model))

    print("\n" + "="*70)
    print(" BÁO CÁO RÀ SOÁT ĐỊNH GIÁ TOÀN THỊ TRƯỜNG (1,523 MÃ CHỨNG KHOÁN)")
    print("="*70)
    print(f"{'Trạng thái định giá':<40} | {'Số lượng':<10} | {'Tỷ lệ':<8}")
    print("-" * 70)
    for st, cnt in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (cnt / total_sec) * 100
        print(f"{st:<40} | {cnt:<10} | {pct:>6.1f}%")
    print("-" * 70)
    print(f"{'TỔNG CỘNG':<40} | {total_sec:<10} | 100.0%")
    print("="*70)
    
    print("\nPhân bổ theo Sàn Giao dịch:")
    for exch, counts in exchange_counts.items():
        print(f"  [{exch}] Tổng: {sum(counts.values())} mã | Verified Capable: {counts['MODEL_VERIFIED_CAPABLE']} | Specialized Gated: {counts['SPECIALIZED_MODEL_GATED']} | Fallback: {counts['FALLBACK_GENERIC_ONLY']} | No BCTC: {counts['NO_BCTC_DATA']}")

    print(f"\n1. Các mã đủ điều kiện MODEL_VERIFIED chuẩn ({len(verified_symbols)} mã):")
    sample_ver = [s[0] for s in verified_symbols[:35]]
    print(f"   Ví dụ 35 mã tiêu biểu: {', '.join(sample_ver)} ...")

    print(f"\n2. Các mã cần Mô hình Đặc thù Chuyên sâu ({len(specialized_model_needed)} mã):")
    by_spec = defaultdict(list)
    for sym, exch, ind, model, reason in specialized_model_needed:
        by_spec[model].append(sym)
    for model, syms in by_spec.items():
        print(f"   • {model} ({len(syms)} mã): {', '.join(syms[:10])}{' ...' if len(syms) > 10 else ''}")

    print(f"\n3. Các mã chưa có dữ liệu BCTC / Facts crawl ({len(no_bctc)} mã):")
    print(f"   Chủ yếu là các doanh nghiệp UPCOM quy mô siêu nhỏ, UPCOM cảnh báo, hoặc quỹ ETF/chứng quyền.")

if __name__ == "__main__":
    audit_universe()
