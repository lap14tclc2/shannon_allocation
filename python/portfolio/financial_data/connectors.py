"""
Dual-channel ingestion connectors for Vietnamese financial statements (QFD-100, QFD-110, QFD-410).

System A: API ingestion (Vnstock fundamental adapter)
System B: HTML ingestion (CafeF crawler / parser adapter)
"""
from __future__ import annotations

import hashlib
import json
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
    Raw payload wrapper with integrity hash and audit metadata (QFD-100, QFD-110).
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

    def fetch_page(self, symbol: str, statement_type: StatementType) -> RawEnvelope: ...
    def parse_envelope(self, envelope: RawEnvelope) -> List[ProviderFact]: ...


class VnstockApiAdapter:
    """
    Adapter for Vnstock guest / public fundamentals API (System A).
    """
    provider_id = "vnstock_api"
    connector_version = "vnstock-fundamental@1.0.0"

    def probe(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "status": "HEALTHY",
            "auth_mode": "NONE",
            "version": self.connector_version,
        }

    def create_envelope(
        self,
        symbol: str,
        statement_type: StatementType,
        period_type: PeriodType,
        year: int,
        quarter: Optional[int],
        raw_dict: Dict[str, Any],
    ) -> RawEnvelope:
        payload_str = json.dumps(raw_dict, sort_keys=True, ensure_ascii=False)
        now_utc = datetime.now(timezone.utc).isoformat()
        return RawEnvelope(
            envelope_id=f"env-vnstock-{symbol}-{statement_type.value}-{year}-{quarter or 'FY'}",
            provider_id=self.provider_id,
            request_fingerprint=f"symbol={symbol}&type={statement_type.value}&year={year}&q={quarter}",
            requested_at=now_utc,
            received_at=now_utc,
            status_code=200,
            payload=payload_str,
            payload_hash=_hash_content(payload_str),
            connector_version=self.connector_version,
            metadata={"symbol": symbol, "year": year, "quarter": quarter},
        )

    def parse_envelope(self, envelope: RawEnvelope) -> List[ProviderFact]:
        data = json.loads(envelope.payload)
        symbol = envelope.metadata.get("symbol", "UNKNOWN")
        year = envelope.metadata.get("year", 2026)
        quarter = envelope.metadata.get("quarter", 1)
        period_type = PeriodType.QUARTER if quarter else PeriodType.FY
        
        # Period dates
        if quarter:
            q_month_map = {1: ("01-01", "03-31"), 2: ("04-01", "06-30"), 3: ("07-01", "09-30"), 4: ("10-01", "12-31")}
            s_m, e_m = q_month_map.get(quarter, ("01-01", "03-31"))
            p_start = f"{year}-{s_m}"
            p_end = f"{year}-{e_m}"
        else:
            p_start = f"{year}-01-01"
            p_end = f"{year}-12-31"

        facts: List[ProviderFact] = []
        for item in data.get("items", []):
            code = item.get("line_item_code")
            raw_val = item.get("value")
            scale = Decimal(str(item.get("scale", "1")))
            val_norm = Decimal(str(raw_val)) * scale
            st_type = StatementType(item.get("statement_type", StatementType.INCOME_STATEMENT.value))

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
                    period_type=period_type,
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
    Adapter for CafeF HTML financial statement crawler / parser (System B).
    """
    provider_id = "cafef_html"
    connector_version = "cafef-html-crawler@1.0.0"

    def probe(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "status": "HEALTHY",
            "auth_mode": "NONE",
            "version": self.connector_version,
        }

    def create_envelope(
        self,
        symbol: str,
        statement_type: StatementType,
        year: int,
        quarter: Optional[int],
        html_content: str,
    ) -> RawEnvelope:
        now_utc = datetime.now(timezone.utc).isoformat()
        return RawEnvelope(
            envelope_id=f"env-cafef-{symbol}-{statement_type.value}-{year}-{quarter or 'FY'}",
            provider_id=self.provider_id,
            request_fingerprint=f"url=https://cafef.vn/bctc/{symbol}.chn",
            requested_at=now_utc,
            received_at=now_utc,
            status_code=200,
            payload=html_content,
            payload_hash=_hash_content(html_content),
            connector_version=self.connector_version,
            metadata={"symbol": symbol, "year": year, "quarter": quarter, "statement_type": statement_type.value},
        )

    def parse_envelope(self, envelope: RawEnvelope, parsed_items: Optional[List[Dict[str, Any]]] = None) -> List[ProviderFact]:
        """
        Parses HTML envelope (with semantic extraction).
        """
        symbol = envelope.metadata.get("symbol", "UNKNOWN")
        year = envelope.metadata.get("year", 2026)
        quarter = envelope.metadata.get("quarter", 1)
        period_type = PeriodType.QUARTER if quarter else PeriodType.FY
        
        if quarter:
            q_month_map = {1: ("01-01", "03-31"), 2: ("04-01", "06-30"), 3: ("07-01", "09-30"), 4: ("10-01", "12-31")}
            s_m, e_m = q_month_map.get(quarter, ("01-01", "03-31"))
            p_start = f"{year}-{s_m}"
            p_end = f"{year}-{e_m}"
        else:
            p_start = f"{year}-01-01"
            p_end = f"{year}-12-31"

        facts: List[ProviderFact] = []
        items = parsed_items or []
        for item in items:
            code = item.get("line_item_code")
            raw_val = item.get("value")
            scale = Decimal(str(item.get("scale", "1000000")))  # CafeF commonly uses triệu VNĐ
            val_norm = Decimal(str(raw_val)) * scale
            st_type = StatementType(item.get("statement_type", StatementType.INCOME_STATEMENT.value))

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
                    period_type=period_type,
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
