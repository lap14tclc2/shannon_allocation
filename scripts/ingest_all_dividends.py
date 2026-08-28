import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from portfolio.finance_catalog import _reconcile_dividend_document, _schema_connection, FINANCE_SCHEMA

def fetch_and_save_dividend(symbol: str) -> tuple[str, bool, int, str]:
    url = f"https://cafef.vn/du-lieu/DuLieu.aspx?cat_id=1009&san=hose&symbol={symbol}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            _reconcile_dividend_document(symbol, "cafef", html, None)
            return (symbol, True, len(html), "")
    except Exception as e:
        return (symbol, False, 0, str(e))

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with _schema_connection(FINANCE_SCHEMA) as db:
        # Get all securities
        all_syms = [r["symbol"] for r in db.execute("SELECT symbol FROM securities ORDER BY symbol ASC").fetchall()]
        already_done = set(r["symbol"] for r in db.execute("SELECT DISTINCT symbol FROM dividend_canonical").fetchall())

    remaining = [s for s in all_syms if s not in already_done]
    total = len(remaining)
    print(f"Total universe: {len(all_syms)} | Already ingested: {len(already_done)} | Remaining: {total}")
    
    if not remaining:
        print("All symbols are already ingested!")
        return

    success_cnt = 0
    fail_cnt = 0
    start_time = time.time()

    # Use 12 concurrent workers with polite rate-limiting
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch_and_save_dividend, sym): sym for sym in remaining}
        done_cnt = 0
        for future in as_completed(futures):
            sym, ok, size, err = future.result()
            done_cnt += 1
            if ok:
                success_cnt += 1
            else:
                fail_cnt += 1
            
            if done_cnt % 50 == 0 or done_cnt == total:
                elapsed = time.time() - start_time
                rps = done_cnt / elapsed if elapsed > 0 else 0
                print(f"[{done_cnt}/{total}] ({(done_cnt/total*100):.1f}%) - Success: {success_cnt}, Failed: {fail_cnt} | Rate: {rps:.1f} sym/s")

    print(f"\n=======================================================")
    print(f"COMPLETED ALL! Ingested {success_cnt} stocks, Failed/No data: {fail_cnt}")
    print(f"Total time elapsed: {time.time() - start_time:.1f}s")
    print(f"=======================================================")

if __name__ == "__main__":
    main()
