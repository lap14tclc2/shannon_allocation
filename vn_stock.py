import multiprocessing as mp
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import time
import re
import sys


# ============================================================
# CONFIG
# ============================================================

TICKERS = ["REE", "IDC", "VNM"]

START_DATE = datetime(2021, 8, 9)
END_DATE = datetime(2026, 8, 9)

CHUNK_DAYS = 150

DATA_DIR = Path("data")
CACHE_DIR = DATA_DIR / "_cache"

DATA_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)


# ============================================================
# CHILD PROCESS
# ============================================================

def api_worker(ticker, start, end, result_queue):
    """
    Process con.

    Nếu vnstock crash / sys.exit:
    process này chết, MAIN vẫn sống.
    """

    try:

        from vnstock.ui import Market

        mkt = Market()

        df = mkt.equity(ticker).ohlcv(
            start=start,
            end=end,
            interval="1D"
        )

        if df is None or df.empty:

            result_queue.put({
                "status": "empty"
            })

            return


        # DataFrame -> records
        result_queue.put({
            "status": "success",
            "data": df.to_json(
                orient="split",
                date_format="iso"
            )
        })


    except Exception as e:

        result_queue.put({
            "status": "error",
            "error": str(e)
        })


# ============================================================
# RATE LIMIT DETECTION
# ============================================================

def get_wait_seconds(text):

    patterns = [
        r"Chờ\s+(\d+)\s*giây",
        r"chờ\s+(\d+)\s*giây",
        r"wait\s+(\d+)\s*seconds?",
        r"retry\s+after\s+(\d+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return int(match.group(1)) + 2

    return 60


def is_rate_limit(text):

    text = text.lower()

    keywords = [
        "rate limit",
        "rate limit exceeded",
        "20 requests",
        "wait to retry",
        "maximum api request",
        "429",
    ]

    return any(
        x in text
        for x in keywords
    )


# ============================================================
# REQUEST WITH PROCESS ISOLATION
# ============================================================

def request_ohlcv(ticker, start, end):

    retry = 0

    while True:

        print()
        print(
            f"[REQUEST] {ticker} "
            f"{start} -> {end}"
        )

        queue = mp.Queue()

        process = mp.Process(
            target=api_worker,
            args=(
                ticker,
                start,
                end,
                queue
            )
        )

        process.start()

        # ----------------------------------------------------
        # Chờ process tối đa 120 giây
        # ----------------------------------------------------

        process.join(
            timeout=120
        )


        # ----------------------------------------------------
        # Nếu process vẫn còn sống
        # ----------------------------------------------------

        if process.is_alive():

            print(
                "[WARNING] API process timeout"
            )

            process.terminate()
            process.join()

            retry += 1

            print(
                "Retry sau 10 giây..."
            )

            time.sleep(10)

            continue


        # ----------------------------------------------------
        # Lấy kết quả
        # ----------------------------------------------------

        result = None

        if not queue.empty():

            result = queue.get()


        # ----------------------------------------------------
        # Process chết nhưng không trả result
        # ----------------------------------------------------

        if result is None:

            print(
                f"[PROCESS EXIT] "
                f"exitcode={process.exitcode}"
            )

            # Một số trường hợp Vnstock tự terminate
            # mà không gửi exception về Python.
            #
            # Ta coi đây là temporary failure.

            retry += 1

            wait = 10

            print(
                f"Process chết. "
                f"Retry sau {wait}s..."
            )

            time.sleep(wait)

            continue


        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        if result["status"] == "success":

            df = pd.read_json(
                result["data"],
                orient="split"
            )

            print(
                f"[OK] {len(df)} rows"
            )

            return df


        # ----------------------------------------------------
        # EMPTY
        # ----------------------------------------------------

        if result["status"] == "empty":

            print(
                "[EMPTY]"
            )

            return pd.DataFrame()


        # ----------------------------------------------------
        # ERROR
        # ----------------------------------------------------

        if result["status"] == "error":

            error = result["error"]

            print(
                f"[ERROR] {error}"
            )

            if is_rate_limit(error):

                retry += 1

                wait = get_wait_seconds(
                    error
                )

                print()
                print(
                    "========================================"
                )
                print(
                    "RATE LIMIT"
                )
                print(
                    f"Retry #{retry}"
                )
                print(
                    f"Waiting {wait}s..."
                )
                print(
                    "========================================"
                )

                time.sleep(wait)

                continue


            # lỗi khác
            raise RuntimeError(error)


# ============================================================
# CACHE
# ============================================================

def cache_file(ticker, start, end):

    return (
        CACHE_DIR /
        f"{ticker}_{start}_{end}.json"
    )


def download_chunk(ticker, start, end):

    file = cache_file(
        ticker,
        start,
        end
    )


    # --------------------------------------------------------
    # CACHE HIT
    # --------------------------------------------------------

    if file.exists():

        print(
            f"[CACHE] {ticker} "
            f"{start} -> {end}"
        )

        return pd.read_json(
            file,
            orient="split"
        )


    # --------------------------------------------------------
    # API
    # --------------------------------------------------------

    df = request_ohlcv(
        ticker,
        start,
        end
    )


    # --------------------------------------------------------
    # SAVE CACHE
    # --------------------------------------------------------

    if df is not None and not df.empty:

        df.to_json(
            file,
            orient="split",
            date_format="iso"
        )

    return df


# ============================================================
# DOWNLOAD TICKER
# ============================================================

def download_ticker(ticker):

    print()
    print("=" * 70)
    print(f"DOWNLOAD {ticker}")
    print("=" * 70)

    chunks = []

    current = START_DATE

    while current <= END_DATE:

        chunk_end = min(
            current +
            timedelta(
                days=CHUNK_DAYS - 1
            ),
            END_DATE
        )

        start = current.strftime(
            "%Y-%m-%d"
        )

        end = chunk_end.strftime(
            "%Y-%m-%d"
        )


        df = download_chunk(
            ticker,
            start,
            end
        )


        if (
            df is not None
            and not df.empty
        ):

            chunks.append(df)


        current = (
            chunk_end +
            timedelta(days=1)
        )


    # --------------------------------------------------------
    # MERGE
    # --------------------------------------------------------

    if not chunks:

        print(
            f"[WARNING] "
            f"No data for {ticker}"
        )

        return


    df = pd.concat(
        chunks,
        ignore_index=True
    )


    # --------------------------------------------------------
    # CLEAN
    # --------------------------------------------------------

    if "time" in df.columns:

        df["time"] = pd.to_datetime(
            df["time"]
        )

        df = (
            df
            .drop_duplicates(
                subset=["time"]
            )
            .sort_values("time")
            .reset_index(drop=True)
        )


    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    output = (
        DATA_DIR /
        f"{ticker}.csv"
    )

    df.to_csv(
        output,
        index=False
    )


    print()
    print(
        f"[DONE] {ticker}"
    )

    print(
        f"Rows: {len(df):,}"
    )

    print(
        f"File: {output}"
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    # Quan trọng trên Windows
    mp.freeze_support()

    for ticker in TICKERS:

        download_ticker(ticker)

    print()
    print("=" * 70)
    print("ALL DONE")
    print("=" * 70)