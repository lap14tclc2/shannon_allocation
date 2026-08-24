from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Protocol

import pandas as pd
import requests

from .external_cache import cached_external_call, ttl_from_env
from .vnstock_isolated import run_vnstock_task, vnstock_available

log = logging.getLogger(__name__)
THOUSAND_VND_SOURCES = {"vndirect", "vnstock"}
MARKET_CACHE_TTL_SECONDS = ttl_from_env("QPORT_MARKET_CACHE_TTL_SECONDS", 300)


class MarketDataError(RuntimeError):
    pass


def canonical_vnd_price(value, source: str | None):
    if value is None or pd.isna(value): return None
    price = float(value)
    if str(source or "").lower() in THOUSAND_VND_SOURCES and 0 < abs(price) < 1000: return price * 1000.0
    return price


class MarketDataProvider(Protocol):
    name: str
    def daily_history(self, symbol: str, start: str, end: str) -> pd.DataFrame: ...
    def health(self) -> dict: ...


@dataclass
class VndirectProvider:
    base_url: str = "https://dchart-api.vndirect.com.vn/dchart/history"
    timeout: float = 15.0
    max_retries: int = 2
    name: str = "vndirect"
    BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0 Safari/537.36"

    @staticmethod
    def _unix(value: str) -> int:
        return int(datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())

    def daily_history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        params = {"resolution":"D","symbol":symbol.upper(),"from":self._unix(start),"to":self._unix(end)+86400}
        last_error = None
        for attempt in range(max(1, int(self.max_retries))):
            try:
                response = requests.get(self.base_url, params=params, headers={"User-Agent":self.BROWSER_UA}, timeout=self.timeout)
                response.raise_for_status(); body=response.json()
                if body.get("s") != "ok" or not body.get("t"): raise MarketDataError(f"VNDIRECT returned no data for {symbol}")
                df = pd.DataFrame({
                    "open":pd.to_numeric(body.get("o",[]),errors="coerce"), "high":pd.to_numeric(body.get("h",[]),errors="coerce"),
                    "low":pd.to_numeric(body.get("l",[]),errors="coerce"), "close":pd.to_numeric(body.get("c",[]),errors="coerce"),
                    "volume":pd.to_numeric(body.get("v",[]),errors="coerce"),
                }, index=pd.to_datetime(body["t"],unit="s",utc=True).tz_localize(None))
                df.index=df.index.normalize(); df.index.name="ts"; df=df.dropna(subset=["close"]); df=df[~df.index.duplicated(keep="last")].sort_index(); df["source"]=self.name
                return df
            except Exception as exc:
                last_error=exc
                if attempt+1 < max(1,int(self.max_retries)): time.sleep(.4*(2**attempt))
        raise MarketDataError(f"VNDIRECT failed for {symbol}: {last_error}")

    def health(self) -> dict: return {"provider":self.name,"available":True,"auth_required":False}


class VnstockProvider:
    """Optional Vnstock D1 adapter isolated from the QPort server process."""
    name = "vnstock"

    def __init__(self, chunk_days: int = 150, request_delay: float = .15) -> None:
        if not vnstock_available():
            raise MarketDataError("vnstock is not installed/importable")
        self.chunk_days=int(chunk_days); self.request_delay=float(request_delay); self.api_mode="isolated_spawn"

    @staticmethod
    def _normalize(raw: pd.DataFrame, symbol: str) -> pd.DataFrame:
        if raw is None or raw.empty: return pd.DataFrame()
        out=raw.copy()
        if "time" in out.columns: ts=pd.to_datetime(out["time"])
        elif "ts" in out.columns: ts=pd.to_datetime(out["ts"])
        elif out.index.name: ts=pd.to_datetime(out.index)
        else: raise MarketDataError(f"vnstock returned no timestamp column for {symbol}")
        out["ts"]=pd.DatetimeIndex(ts).normalize(); required=["open","high","low","close","volume"]
        missing=[c for c in required if c not in out.columns]
        if missing: raise MarketDataError(f"vnstock missing columns for {symbol}: {missing}")
        out=out[["ts",*required]].copy()
        for c in required: out[c]=pd.to_numeric(out[c],errors="coerce")
        out=out.dropna(subset=["close"]).drop_duplicates("ts",keep="last").set_index("ts").sort_index(); out["source"]="vnstock"
        return out

    def daily_history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        start_date=date.fromisoformat(start); end_date=date.fromisoformat(end); frames=[]; current=start_date
        while current <= end_date:
            chunk_end=min(end_date,current+timedelta(days=self.chunk_days-1))
            try:
                result=run_vnstock_task("ohlcv", {"symbol":symbol.upper(),"start":current.isoformat(),"end":chunk_end.isoformat()})
                self.api_mode=str(result.get("api_variant") or self.api_mode)
                raw=pd.DataFrame(result.get("data") or [])
            except Exception as exc:
                raise MarketDataError(f"vnstock failed for {symbol} {current}..{chunk_end}: {exc}") from exc
            normalized=self._normalize(raw,symbol)
            if not normalized.empty: frames.append(normalized)
            current=chunk_end+timedelta(days=1)
            if current<=end_date and self.request_delay>0: time.sleep(self.request_delay)
        if not frames: raise MarketDataError(f"vnstock returned no data for {symbol}")
        out=pd.concat(frames).sort_index(); return out[~out.index.duplicated(keep="last")]

    def health(self) -> dict:
        return {"provider":self.name,"available":True,"auth_required":False,"api_mode":self.api_mode,"isolation":"CHILD_PROCESS"}


class AutoMarketData:
    name="auto"
    def __init__(self, providers: list[MarketDataProvider] | None=None) -> None:
        if providers is not None: self.providers=list(providers); return
        resolved=[]
        try: resolved.append(VnstockProvider())
        except MarketDataError as exc: log.info("vnstock provider unavailable: %s",exc)
        resolved.append(VndirectProvider()); self.providers=resolved

    @staticmethod
    def _clone_frame(frame: pd.DataFrame) -> pd.DataFrame:
        return frame.copy(deep=True)

    def _provider_history(self, provider: MarketDataProvider, symbol: str, start: str, end: str) -> pd.DataFrame:
        key = (provider.name, symbol.upper(), start, end)
        return cached_external_call(
            "market-history",
            key,
            lambda: provider.daily_history(symbol, start, end),
            ttl_seconds=MARKET_CACHE_TTL_SECONDS,
            clone=self._clone_frame,
        )

    def daily_history(self,symbol,start,end):
        errors=[]
        for provider in self.providers:
            try:
                df=self._provider_history(provider,symbol,start,end)
                if not df.empty:return df
            except Exception as exc: errors.append(f"{provider.name}: {exc}")
        raise MarketDataError(f"All providers failed for {symbol}: {' | '.join(errors)}")

    def daily_history_with_source(self,symbol,start,end):
        errors=[]
        for provider in self.providers:
            try:
                df=self._provider_history(provider,symbol,start,end)
                if not df.empty:return df,provider.name
            except Exception as exc: errors.append(f"{provider.name}: {exc}")
        raise MarketDataError(f"All providers failed for {symbol}: {' | '.join(errors)}")

    def health(self):
        return {
            "provider":"auto",
            "policy":[p.name for p in self.providers],
            "providers":[p.health() for p in self.providers],
            "warm_cache_ttl_seconds": MARKET_CACHE_TTL_SECONDS,
        }


def frame_to_price_rows(symbol: str, df: pd.DataFrame, source: str | None=None) -> list[dict]:
    fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"); rows=[]
    for ts,row in df.iterrows():
        row_source=str(source or row.get("source") or "unknown").lower()
        rows.append({
            "symbol":symbol.upper(),"trading_date":pd.Timestamp(ts).date().isoformat(),
            "open":canonical_vnd_price(row.get("open"),row_source),"high":canonical_vnd_price(row.get("high"),row_source),
            "low":canonical_vnd_price(row.get("low"),row_source),"close":canonical_vnd_price(row["close"],row_source),
            "volume":float(row["volume"]) if pd.notna(row.get("volume")) else None,"source":row_source,"fetched_at":fetched_at,"is_final":True,"data_quality":"VALID",
        })
    return rows
