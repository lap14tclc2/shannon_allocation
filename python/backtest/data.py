"""Load historical daily prices from the data directory into one panel.

Each symbol is a column; the index is a normalised trading date (YYYY-MM-DD).
Prices are converted from "thousands of VND" to VND via price_scale.
"""

from __future__ import annotations

import glob
import json
import os

import pandas as pd

from .config import BacktestParams


def list_symbols(data_dir: str) -> list[str]:
    """Return tickers from all *.csv files in data_dir, sorted."""
    symbols = []
    for path in sorted(glob.glob(os.path.join(data_dir, "*.csv"))):
        name = os.path.basename(path)
        ticker = name[:-4].strip().upper()
        if ticker:
            symbols.append(ticker)
    return symbols


def load_symbol(data_dir: str, ticker: str, price_scale: int) -> pd.Series:
    """Return a Series indexed by date with the symbol's close price in VND."""
    df = pd.read_csv(os.path.join(data_dir, f"{ticker}.csv"))
    col = "time"
    if col not in df.columns:
        for candidate in ("date", "datetime", "timestamp"):
            if candidate in df.columns:
                col = candidate
                break
    price_col = "close"
    if price_col not in df.columns:
        for candidate in ("adj_close", "adj close", "price"):
            if candidate in df.columns:
                price_col = candidate
                break
    df = df[[col, price_col]].copy()
    df[col] = pd.to_datetime(df[col], errors="coerce")
    df = df.dropna(subset=[col])
    df[col] = df[col].dt.normalize()
    df = df.drop_duplicates(subset=[col], keep="last")
    df = df.set_index(col)
    df = df.sort_index()
    series = df[price_col].astype(float) * price_scale
    series.name = ticker
    return series


def load_universe(name: str, data_dir: str) -> list[str] | None:
    """Load a named universe (vn30 / vn50 / vn100) from <data_dir>/universe_<name>.json."""
    if not name or name in ("all", "vn100"):
        return None
    path = os.path.join(data_dir, f"universe_{name}.json")
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Universe '{name}' not found at {path}. Run `python -m backtest.universes` to create it."
        )
    with open(path, "r", encoding="utf-8") as fh:
        return [s.strip().upper() for s in json.load(fh) if s.strip()]


def load_panel(params: BacktestParams) -> tuple[pd.DataFrame, list[str]]:
    """Load all symbols into a forward-filled DataFrame of close prices (VND).

    Returns (prices, symbols). The panel is sorted by date and forward filled so
    holdings can be valued on every trading date (suspensions use last price).
    When params.universe names an index (vn30/vn50), only those symbols are kept
    (intersected with the CSVs actually present in the data folder).
    """
    if params.symbols_file:
        symbols = _read_symbols_file(params.symbols_file)
    else:
        symbols = list_symbols(params.data_dir)
        wanted = load_universe(params.universe, params.data_dir)
        if wanted:
            available = set(symbols)
            symbols = [t for t in wanted if t in available]
            missing = [t for t in wanted if t not in available]
            if missing:
                print(f"universe '{params.universe}': {len(missing)} symbols without data skipped "
                      f"(e.g. {', '.join(missing[:5])})")
    if not symbols:
        raise FileNotFoundError(f"No CSV files found in {params.data_dir}")
    series_list = [load_symbol(params.data_dir, t, params.price_scale) for t in symbols]
    panel = pd.concat(series_list, axis=1, join="outer")
    panel = panel.sort_index()
    panel = panel.ffill()
    return panel, symbols


def _read_symbols_file(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as fh:
        return [line.strip().upper() for line in fh if line.strip()]