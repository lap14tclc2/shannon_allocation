"""Verification tool for SSI runtime database integration (Task 132B)."""

from __future__ import annotations

import argparse
import os
import sys
from urllib.parse import urlparse

from portfolio.finance_catalog import _schema_connection, FINANCE_SCHEMA
from portfolio.financial_data.store import FinancialDataStore


def get_safe_db_identity() -> dict[str, str]:
    """Parse DATABASE_URL safely without revealing credentials."""
    raw = os.environ.get("DATABASE_URL", "postgresql://qport:qport@127.0.0.1:5432/qport")
    parsed = urlparse(raw)
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": str(parsed.port or 5432),
        "database": (parsed.path or "/qport").lstrip("/"),
        "schema": FINANCE_SCHEMA,
        "canonical_table": f"{FINANCE_SCHEMA}.canonical_facts",
        "raw_ssi_table": f"{FINANCE_SCHEMA}.ssi_raw_financial_observations",
        "ssi_import_file_table": f"{FINANCE_SCHEMA}.ssi_import_files",
    }


def verify_ssi_runtime() -> bool:
    db_meta = get_safe_db_identity()
    print("=" * 60)
    print(" QPORT SSI RUNTIME DATABASE VERIFICATION ")
    print("=" * 60)
    print(f"Host:            {db_meta['host']}:{db_meta['port']}")
    print(f"Database:        {db_meta['database']}")
    print(f"Schema:          {db_meta['schema']}")
    print(f"Canonical Table: {db_meta['canonical_table']}")
    print("-" * 60)

    with _schema_connection(FINANCE_SCHEMA) as conn:
        # 1. Total Universe & Provider Distribution
        res = conn.execute(
            """SELECT provider, COUNT(DISTINCT symbol) AS symbols, COUNT(*) AS facts
               FROM canonical_facts
               GROUP BY provider
               ORDER BY facts DESC"""
        ).fetchall()

        print("\nPROVIDER DISTRIBUTION IN CANONICAL_FACTS:")
        total_facts = 0
        total_symbols = 0
        ssi_facts = 0
        ssi_symbols = 0

        for row in res:
            p = row["provider"]
            syms = row["symbols"]
            facts = row["facts"]
            total_facts += facts
            print(f"  - Provider: {p:<10} | Symbols: {syms:<5} | Facts: {facts:,}")
            if p == "ssi":
                ssi_facts = facts
                ssi_symbols = syms

        # 2. SSI Ingestion Tables Check
        res_files = conn.execute("SELECT COUNT(*) AS cnt, COUNT(DISTINCT symbol) AS syms FROM ssi_import_files WHERE import_status = 'SUCCESS'").fetchone()
        import_files_cnt = res_files["cnt"] if res_files else 0
        import_files_syms = res_files["syms"] if res_files else 0

        res_obs = conn.execute("SELECT COUNT(*) AS cnt FROM ssi_raw_financial_observations").fetchone()
        raw_obs_cnt = res_obs["cnt"] if res_obs else 0

        print("\nSSI INGESTION METRICS IN DB:")
        print(f"  - Successful Import Files: {import_files_cnt:,}")
        print(f"  - Unique SSI Symbols:      {import_files_syms}")
        print(f"  - Raw SSI Observations:    {raw_obs_cnt:,}")
        print(f"  - Canonical SSI Facts:     {ssi_facts:,}")

        # 3. Golden Symbols Check (ACB, DGC, FPT, VIX)
        golden_symbols = ["ACB", "DGC", "FPT", "VIX"]
        print("\nGOLDEN SYMBOLS SSI FACT CHECK:")

        all_golden_ok = True
        for sym in golden_symbols:
            ssi_sym_facts = conn.execute(
                "SELECT COUNT(*) AS cnt FROM canonical_facts WHERE symbol = ? AND provider = 'ssi'",
                (sym,),
            ).fetchone()["cnt"]

            total_sym_facts = conn.execute(
                "SELECT COUNT(*) AS cnt FROM canonical_facts WHERE symbol = ?",
                (sym,),
            ).fetchone()["cnt"]

            providers = [
                row["provider"]
                for row in conn.execute(
                    "SELECT DISTINCT provider FROM canonical_facts WHERE symbol = ?",
                    (sym,),
                ).fetchall()
            ]

            print(f"  - [{sym}] Total Facts: {total_sym_facts:<5} | SSI Facts: {ssi_sym_facts:<5} | Providers: {', '.join(providers)}")
            if ssi_sym_facts == 0:
                all_golden_ok = False

        print("-" * 60)
        if ssi_facts > 0 and ssi_symbols >= 300 and all_golden_ok:
            print("STATUS: PASS — SSI fundamental data is active in PostgreSQL runtime.")
            return True
        else:
            print("STATUS: FAIL — SSI fundamental data is missing or incomplete in PostgreSQL runtime.")
            return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify SSI PostgreSQL runtime integration.")
    args = parser.parse_args()
    success = verify_ssi_runtime()
    sys.exit(0 if success else 1)
