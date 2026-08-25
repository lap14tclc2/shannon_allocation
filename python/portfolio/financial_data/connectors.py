"""
Dual-channel ingestion connectors with real fetching & append-only envelopes (QFD-100, QFD-110, QFD-200).
"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol

from .models import (
    ConsolidationScope,
    FactIdentityKey,
    PeriodType,
    ProviderFact,
    StatementType,
)
from .taxonomy import get_required_period_type


def _hash_content(content: str | bytes) -> str:
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


@dataclass
class SourceDocument:
    """
    Metadata about an external document/page (QFD-230).
    """
    document_id: str
    provider_id: str
    url: str
    content_hash: str
    document_type: str  # HTML, JSON_API, PDF
    fetched_at: str  # ISO-8601 UTC
    published_at: Optional[str] = None
    http_status: int = 200
    mime_type: str = "text/html"


@dataclass
class RawEnvelope:
    """
    Append-only raw payload wrapper (QFD-200).
    ID is uniquely derived from provider, request fingerprint, timestamp, and content hash.
    """
    envelope_id: str
    provider_id: str
    request_fingerprint: str
    requested_at: str
    received_at: str
    status_code: int
    payload: str
    payload_hash: str
    connector_version: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class FinancialApiProvider(Protocol):
    provider_id: str

    def probe(self) -> Dict[str, Any]: ...
    def get_statements(
        self,
        symbol: str,
        statement_type: StatementType,
        period_type: PeriodType,
        year: int,
        quarter: Optional[int] = None,
    ) -> RawEnvelope: ...
    def parse_envelope(self, envelope: RawEnvelope) -> List[ProviderFact]: ...


class FinancialHtmlProvider(Protocol):
    provider_id: str

    def probe(self) -> Dict[str, Any]: ...
    def fetch_page(self, symbol: str, statement_type: StatementType) -> RawEnvelope: ...
    def parse_envelope(self, envelope: RawEnvelope) -> List[ProviderFact]: ...


class VnstockApiAdapter:
    """
    Adapter for Vnstock public fundamentals API (System A, QFD-100).
    """
    provider_id = "vnstock_api"
    connector_version = "vnstock-fundamental@1.0.0"

    def probe(self) -> Dict[str, Any]:
        """
        Performs a dynamic probe on Vnstock company overview.
        """
        try:
            from vnstock import Reference
            ref = Reference()
            df = ref.company.overview("FPT")
            healthy = not df.empty
            return {
                "provider_id": self.provider_id,
                "status": "HEALTHY" if healthy else "DEGRADED",
                "auth_mode": "NONE",
                "version": self.connector_version,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            return {
                "provider_id": self.provider_id,
                "status": "DEGRADED",
                "auth_mode": "NONE",
                "version": self.connector_version,
                "error": str(exc),
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

    def fetch_live_statements(
        self,
        symbol: str,
        statement_type: StatementType = StatementType.INCOME_STATEMENT,
    ) -> RawEnvelope:
        """
        Live network fetch using Vnstock.
        """
        from vnstock import Vnstock
        stock = Vnstock().stock(symbol=symbol, source="VCI")
        req_iso = datetime.now(timezone.utc).isoformat()
        
        if statement_type == StatementType.BALANCE_SHEET:
            df = stock.finance.balance_sheet(period="quarter", lang="vi")
        elif statement_type == StatementType.CASH_FLOW:
            df = stock.finance.cash_flow(period="quarter", lang="vi")
        else:
            df = stock.finance.income_statement(period="quarter", lang="vi")

        payload_dict = {"symbol": symbol, "items": json.loads(df.to_json(orient="records", force_ascii=False))}
        return self.create_envelope(
            symbol=symbol,
            statement_type=statement_type,
            period_type=PeriodType.QUARTER,
            year=datetime.now(timezone.utc).year,
            quarter=None,
            raw_dict=payload_dict,
            requested_at=req_iso,
        )

    def create_envelope(
        self,
        symbol: str,
        statement_type: StatementType,
        period_type: PeriodType,
        year: int,
        quarter: Optional[int],
        raw_dict: Dict[str, Any],
        requested_at: Optional[str] = None,
    ) -> RawEnvelope:
        payload_str = json.dumps(raw_dict, sort_keys=True, ensure_ascii=False)
        payload_hash = _hash_content(payload_str)
        now_utc = datetime.now(timezone.utc).isoformat()
        req_time = requested_at or now_utc
        
        # Append-only unique ID (QFD-200)
        env_id = f"env-{self.provider_id}-{symbol}-{statement_type.value}-{payload_hash[:12]}-{now_utc.replace(':', '-')}"
        
        return RawEnvelope(
            envelope_id=env_id,
            provider_id=self.provider_id,
            request_fingerprint=f"symbol={symbol}&type={statement_type.value}&year={year}&q={quarter}",
            requested_at=req_time,
            received_at=now_utc,
            status_code=200,
            payload=payload_str,
            payload_hash=payload_hash,
            connector_version=self.connector_version,
            metadata={"symbol": symbol, "year": year, "quarter": quarter, "statement_type": statement_type.value},
        )

    def parse_envelope(self, envelope: RawEnvelope) -> List[ProviderFact]:
        data = json.loads(envelope.payload)
        symbol = envelope.metadata.get("symbol", "UNKNOWN")
        year = envelope.metadata.get("year", 2026)
        quarter = envelope.metadata.get("quarter", 1)
        raw_st = envelope.metadata.get("statement_type", StatementType.INCOME_STATEMENT.value)
        statement_type = StatementType(raw_st)
        
        # Balance Sheet must strictly be INSTANT (QFD-240)
        period_type = get_required_period_type(statement_type, PeriodType.QUARTER if quarter else PeriodType.FY)

        if quarter:
            q_month_map = {1: ("01-01", "03-31"), 2: ("04-01", "06-30"), 3: ("07-01", "09-30"), 4: ("10-01", "12-31")}
            s_m, e_m = q_month_map.get(quarter, ("01-01", "03-31"))
            p_start = f"{year}-{s_m}" if period_type != PeriodType.INSTANT else None
            p_end = f"{year}-{e_m}"
        else:
            p_start = f"{year}-01-01" if period_type != PeriodType.INSTANT else None
            p_end = f"{year}-12-31"

        facts: List[ProviderFact] = []
        for item in data.get("items", []):
            code = item.get("line_item_code")
            raw_val = item.get("value")
            scale = Decimal(str(item.get("scale", "1")))
            val_norm = Decimal(str(raw_val)) * scale if raw_val is not None else Decimal("0")
            st_type = StatementType(item.get("statement_type", statement_type.value))

            facts.append(
                ProviderFact(
                    security_id=f"sec-{symbol.lower()}",
                    symbol_observed=symbol,
                    statement_type=st_type,
                    line_item_code=code,
                    label_observed=item.get("label", code),
                    value_raw=str(raw_val),
                    value_normalized=val_norm,
                    currency=item.get("currency", "VND"),
                    scale_observed=scale,
                    period_start=p_start,
                    period_end=p_end,
                    period_type=get_required_period_type(st_type, period_type),
                    fiscal_year=year,
                    fiscal_quarter=quarter,
                    consolidation_scope=ConsolidationScope(item.get("scope", "CONSOLIDATED")),
                    provider_id=self.provider_id,
                    source_document_id=envelope.envelope_id,
                    observed_at=envelope.received_at,
                    parser_version=self.connector_version,
                )
            )
        return facts


class CafeFHtmlAdapter:
    """
    Adapter for CafeF HTML crawler & parser (System B, QFD-110).
    """
    provider_id = "cafef_html"
    connector_version = "cafef-html-crawler@1.0.0"

    def probe(self) -> Dict[str, Any]:
        """
        Performs a dynamic probe against CafeF endpoint.
        """
        test_url = "https://s.cafef.vn/bao-cao-tai-chinh/FPT/IncSta/2024/4/0/0/ket-qua-hoat-dong-kinh-doanh-.chn"
        req = urllib.request.Request(test_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                status_ok = resp.status == 200
                return {
                    "provider_id": self.provider_id,
                    "status": "HEALTHY" if status_ok else "DEGRADED",
                    "auth_mode": "NONE",
                    "version": self.connector_version,
                    "http_status": resp.status,
                    "checked_at": now_iso,
                }
        except Exception as exc:
            return {
                "provider_id": self.provider_id,
                "status": "DEGRADED",
                "auth_mode": "NONE",
                "version": self.connector_version,
                "error": str(exc),
                "checked_at": now_iso,
            }

    def fetch_page(self, symbol: str, statement_type: StatementType = StatementType.INCOME_STATEMENT) -> RawEnvelope:
        """
        Live network crawl from CafeF.
        """
        type_segment = "IncSta" if statement_type == StatementType.INCOME_STATEMENT else "BSheet"
        url = f"https://s.cafef.vn/bao-cao-tai-chinh/{symbol}/{type_segment}/2024/4/0/0/bctc.chn"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        req_iso = datetime.now(timezone.utc).isoformat()
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        
        return self.create_envelope(
            symbol=symbol,
            statement_type=statement_type,
            year=2024,
            quarter=4,
            html_content=html,
            url=url,
        )

    def create_envelope(
        self,
        symbol: str,
        statement_type: StatementType,
        year: int,
        quarter: Optional[int],
        html_content: str,
        url: str = "",
    ) -> RawEnvelope:
        now_utc = datetime.now(timezone.utc).isoformat()
        payload_hash = _hash_content(html_content)
        env_id = f"env-{self.provider_id}-{symbol}-{statement_type.value}-{payload_hash[:12]}-{now_utc.replace(':', '-')}"
        
        return RawEnvelope(
            envelope_id=env_id,
            provider_id=self.provider_id,
            request_fingerprint=f"url={url or 'https://cafef.vn/bctc/' + symbol}",
            requested_at=now_utc,
            received_at=now_utc,
            status_code=200,
            payload=html_content,
            payload_hash=payload_hash,
            connector_version=self.connector_version,
            metadata={"symbol": symbol, "year": year, "quarter": quarter, "statement_type": statement_type.value},
        )

    def parse_envelope(self, envelope: RawEnvelope, parsed_items: Optional[List[Dict[str, Any]]] = None) -> List[ProviderFact]:
        symbol = envelope.metadata.get("symbol", "UNKNOWN")
        year = envelope.metadata.get("year", 2026)
        quarter = envelope.metadata.get("quarter", 1)
        raw_st = envelope.metadata.get("statement_type", StatementType.INCOME_STATEMENT.value)
        statement_type = StatementType(raw_st)
        period_type = get_required_period_type(statement_type, PeriodType.QUARTER if quarter else PeriodType.FY)

        if quarter:
            q_month_map = {1: ("01-01", "03-31"), 2: ("04-01", "06-30"), 3: ("07-01", "09-30"), 4: ("10-01", "12-31")}
            s_m, e_m = q_month_map.get(quarter, ("01-01", "03-31"))
            p_start = f"{year}-{s_m}" if period_type != PeriodType.INSTANT else None
            p_end = f"{year}-{e_m}"
        else:
            p_start = f"{year}-01-01" if period_type != PeriodType.INSTANT else None
            p_end = f"{year}-12-31"

        facts: List[ProviderFact] = []
        items = parsed_items or []
        for item in items:
            code = item.get("line_item_code")
            raw_val = item.get("value")
            scale = Decimal(str(item.get("scale", "1000000")))
            val_norm = Decimal(str(raw_val)) * scale if raw_val is not None else Decimal("0")
            st_type = StatementType(item.get("statement_type", statement_type.value))

            facts.append(
                ProviderFact(
                    security_id=f"sec-{symbol.lower()}",
                    symbol_observed=symbol,
                    statement_type=st_type,
                    line_item_code=code,
                    label_observed=item.get("label", code),
                    value_raw=str(raw_val),
                    value_normalized=val_norm,
                    currency="VND",
                    scale_observed=scale,
                    period_start=p_start,
                    period_end=p_end,
                    period_type=get_required_period_type(st_type, period_type),
                    fiscal_year=year,
                    fiscal_quarter=quarter,
                    consolidation_scope=ConsolidationScope(item.get("scope", "CONSOLIDATED")),
                    provider_id=self.provider_id,
                    source_document_id=envelope.envelope_id,
                    observed_at=envelope.received_at,
                    parser_version=self.connector_version,
                )
            )
        return facts
