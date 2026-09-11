"""Rebuild SSI canonical facts safely from ssi_raw_financial_observations."""

import sys
from datetime import datetime, timezone
import re
from portfolio.finance_catalog import _schema_connection, FINANCE_SCHEMA
from portfolio.financial_data.ssi_ingestion import (
    map_ssi_line_item,
    derive_total_debt_facts,
)


def rebuild():
    print("Rebuilding SSI canonical facts from ssi_raw_financial_observations...", flush=True)
    now_str = datetime.now(timezone.utc).isoformat()

    with _schema_connection(FINANCE_SCHEMA) as conn:
        before_ssi_count = conn.execute("SELECT count(*) as c FROM canonical_facts WHERE provider='ssi'").fetchone()["c"]
        print(f"BEFORE SSI canonical facts count: {before_ssi_count}")

        # Fetch raw observations deterministically ordered by id DESC (latest observation wins)
        rows = conn.execute(
            """SELECT symbol, statement_type, raw_line_name, period, fiscal_year, value
               FROM ssi_raw_financial_observations
               WHERE value IS NOT NULL AND fiscal_year IS NOT NULL
               ORDER BY id DESC"""
        ).fetchall()

        print(f"Fetched {len(rows)} raw observations for canonical re-mapping.", flush=True)

        # Group by (symbol, statement_type)
        grouped: dict[tuple[str, str], list[dict]] = {}
        for r in rows:
            sym = str(r["symbol"]).upper().strip()
            st_type = str(r["statement_type"])
            grouped.setdefault((sym, st_type), []).append(r)

        # Delete existing SSI canonical facts cleanly before inserting rebuilt canonical facts
        conn.execute("DELETE FROM canonical_facts WHERE provider='ssi'")

        canonical_facts_inserted = 0
        derived_facts_inserted = 0

        for (sym, st_type), obs_list in grouped.items():
            canonical_batch: list[tuple] = []
            # Deduplicate by (line_item_code, fiscal_year) for the same symbol & statement
            seen_keys = set()

            for obs in obs_list:
                line_name = obs["raw_line_name"]
                fy = int(obs["fiscal_year"])
                val = float(obs["value"])

                code, map_status = map_ssi_line_item(line_name, st_type)
                if code and map_status == "MAPPED":
                    key = (code, fy)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        canonical_batch.append((
                            sym, st_type, code, val, fy, f"{fy}-12-31", now_str
                        ))

            # Derive BS.DEBT.TOTAL
            derived_debt = derive_total_debt_facts(canonical_batch, sym)

            if canonical_batch:
                upsert_items = [
                    (item[0], item[1], item[2], item[3], 'FY', item[4], None, item[5], 'ssi', 'PRIMARY_SSI', item[6])
                    for item in canonical_batch
                ]
                conn.executemany(
                    """INSERT INTO canonical_facts
                       (symbol, statement_type, line_item_code, value, period_type, fiscal_year, fiscal_quarter, period_end, provider, quality_status, observed_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT (symbol, statement_type, line_item_code, period_type, fiscal_year, fiscal_quarter, provider)
                       DO UPDATE SET value = EXCLUDED.value, quality_status = EXCLUDED.quality_status, observed_at = EXCLUDED.observed_at""",
                    upsert_items,
                )
                canonical_facts_inserted += len(upsert_items)

            if derived_debt:
                derived_items = [
                    (item[0], item[1], item[2], item[3], 'FY', item[4], None, item[5], 'ssi', 'DERIVED', item[6])
                    for item in derived_debt
                ]
                conn.executemany(
                    """INSERT INTO canonical_facts
                       (symbol, statement_type, line_item_code, value, period_type, fiscal_year, fiscal_quarter, period_end, provider, quality_status, observed_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT (symbol, statement_type, line_item_code, period_type, fiscal_year, fiscal_quarter, provider)
                       DO UPDATE SET value = EXCLUDED.value, quality_status = EXCLUDED.quality_status, observed_at = EXCLUDED.observed_at""",
                    derived_items,
                )
                derived_facts_inserted += len(derived_items)


        after_ssi_count = conn.execute("SELECT count(*) as c FROM canonical_facts WHERE provider='ssi'").fetchone()["c"]
        print(f"AFTER SSI canonical facts count: {after_ssi_count}")
        print(f"Derived facts count inserted: {derived_facts_inserted}")
        print("Rebuild complete!", flush=True)


if __name__ == "__main__":
    rebuild()
