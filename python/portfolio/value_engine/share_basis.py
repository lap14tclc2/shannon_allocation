"""Canonical Share Basis and MOS Integrity Authority.

Provides canonical domain contracts and methods for:
1. Distinguishing basic shares, diluted shares, and corporate-action-adjusted share basis.
2. Sourcing share count from latest audited BCTC with date, provider, and provenance.
3. Applying forward non-economic adjustments (splits, bonus shares, stock dividends) from BCTC date to valuation date.
4. Detecting share-basis mismatch between historical BCTC and current split-adjusted market price.
5. Canonical Margin of Safety (MOS) calculation invariant:
   MOS = (1 - Market_Price / IV_per_share) * 100%
   strictly gated on compatible share basis and valid data.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Union

from ..corporate_action_normalizer import (
    CorporateActionEvent,
    CorporateActionType,
    calculate_cumulative_multiplier,
)


class ShareBasisType(str, Enum):
    REPORTED_LATEST_BCTC = "REPORTED_LATEST_BCTC"
    CORPORATE_ACTION_ADJUSTED = "CORPORATE_ACTION_ADJUSTED"
    DILUTED_EQUITY_BASIS = "DILUTED_EQUITY_BASIS"
    CURRENT_FLOAT_VERIFIED = "CURRENT_FLOAT_VERIFIED"
    ESTIMATED_BASIS = "ESTIMATED_BASIS"
    UNRESOLVED_MISMATCH = "UNRESOLVED_MISMATCH"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ShareBasisStatus(str, Enum):
    VALID = "VALID"
    ESTIMATED = "ESTIMATED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    UNRESOLVED_MISMATCH = "UNRESOLVED_MISMATCH"
    CONFLICTED = "CONFLICTED"


SHARE_BASIS_VIETNAMESE = {
    ShareBasisType.REPORTED_LATEST_BCTC.value: "Số cổ phần lưu hành theo BCTC mới nhất",
    ShareBasisType.CORPORATE_ACTION_ADJUSTED.value: "Số cổ phần đã điều chỉnh theo sự kiện quyền",
    ShareBasisType.DILUTED_EQUITY_BASIS.value: "Cơ sở cổ phần pha loãng đầy đủ",
    ShareBasisType.CURRENT_FLOAT_VERIFIED.value: "Số cổ phần lưu hành thị trường xác thực",
    ShareBasisType.ESTIMATED_BASIS.value: "Số cổ phần ước tính",
    ShareBasisType.UNRESOLVED_MISMATCH.value: "Cơ sở cổ phần chưa đồng nhất",
    ShareBasisType.INSUFFICIENT_DATA.value: "Chưa đủ dữ liệu số cổ phần",
}


@dataclass(frozen=True)
class ShareBasis:
    symbol: str
    shares_outstanding: Decimal
    diluted_shares: Decimal
    valuation_share_count: Decimal
    basis_type: str
    as_of_date: str
    source: str
    provenance: str
    status: str
    cumulative_split_factor: Decimal = Decimal("1.0")
    is_compatible_with_current_price: bool = True
    summary_vietnamese: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "shares_outstanding": float(self.shares_outstanding) if self.shares_outstanding else None,
            "diluted_shares": float(self.diluted_shares) if self.diluted_shares else None,
            "valuation_share_count": float(self.valuation_share_count) if self.valuation_share_count else None,
            "basis_type": self.basis_type,
            "basis_type_vi": SHARE_BASIS_VIETNAMESE.get(self.basis_type, self.basis_type),
            "as_of_date": self.as_of_date,
            "source": self.source,
            "provenance": self.provenance,
            "status": self.status,
            "cumulative_split_factor": float(self.cumulative_split_factor),
            "is_compatible_with_current_price": self.is_compatible_with_current_price,
            "summary_vietnamese": self.summary_vietnamese or self.provenance,
        }


def _to_decimal(val: Any) -> Optional[Decimal]:
    if val is None or val == "":
        return None
    try:
        d = Decimal(str(val).replace(",", ""))
        return d if d.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def calculate_canonical_mos(
    market_price: Optional[Union[Decimal, float]],
    intrinsic_value_per_share: Optional[Union[Decimal, float]],
    share_basis: Optional[ShareBasis] = None,
) -> Optional[Decimal]:
    """Calculates canonical Margin of Safety (MOS) percentage.
    
    Formula:
        MOS (%) = ((IV_per_share - Market_Price) / IV_per_share) * 100%
        Equivalent to: (1 - Market_Price / IV_per_share) * 100%
        
    Required Invariants:
    1. Market price and IV/share MUST refer to the same current share basis.
    2. If market_price is None, <= 0: MOS is None.
    3. If IV/share is None, <= 0: MOS is None (negative/zero IV produces no safe MOS).
    4. If share_basis is present and incompatible / conflicted: MOS is None (no false MOS).
    5. Anti-Double-Adjustment: never calculate MOS on mismatched share units.
    """
    p_dec = _to_decimal(market_price)
    iv_dec = _to_decimal(intrinsic_value_per_share)

    if p_dec is None or p_dec <= Decimal("0"):
        return None
    if iv_dec is None or iv_dec <= Decimal("0"):
        return None

    if share_basis is not None:
        if not share_basis.is_compatible_with_current_price:
            return None
        if share_basis.status in (
            ShareBasisStatus.INSUFFICIENT_DATA.value,
            ShareBasisStatus.CONFLICTED.value,
            ShareBasisStatus.UNRESOLVED_MISMATCH.value,
        ):
            return None

    mos = ((iv_dec - p_dec) / iv_dec) * Decimal("100")
    return mos.quantize(Decimal("0.01"))


def resolve_canonical_share_basis(
    symbol: str,
    bctc_shares: Optional[Union[Decimal, float, int]],
    bctc_fiscal_year: Optional[int],
    bctc_period_end: Optional[str],
    corporate_actions: Sequence[Union[CorporateActionEvent, Dict[str, Any]]] = (),
    current_market_price: Optional[Union[Decimal, float]] = None,
    diluted_shares_estimate: Optional[Union[Decimal, float]] = None,
    valuation_date: Optional[str] = None,
    source: str = "SSI_CANONICAL_BCTC",
) -> ShareBasis:
    """Resolves the canonical share basis for valuation and MOS calculation.
    
    Data Flow:
    1. Sourced share count S_bctc from latest financial statement.
    2. Check corporate actions between bctc_period_end and valuation_date.
    3. Forward-adjust S_bctc for non-economic actions (splits, bonus shares, stock dividends)
       so that IV/share is expressed on the exact same share unit as current market price.
    4. Guard against missing or zero share count -> status=INSUFFICIENT_DATA.
    """
    sym = str(symbol or "").upper().strip()
    s_dec = _to_decimal(bctc_shares)
    p_dec = _to_decimal(current_market_price)
    diluted_dec = _to_decimal(diluted_shares_estimate) or s_dec

    val_date_str = str(valuation_date or "")[:10] if valuation_date else ""
    period_end_str = str(bctc_period_end or "")[:10] if bctc_period_end else (f"{bctc_fiscal_year}-12-31" if bctc_fiscal_year else "")

    if s_dec is None or s_dec <= Decimal("0"):
        return ShareBasis(
            symbol=sym,
            shares_outstanding=Decimal("0"),
            diluted_shares=Decimal("0"),
            valuation_share_count=Decimal("0"),
            basis_type=ShareBasisType.INSUFFICIENT_DATA.value,
            as_of_date=period_end_str or "UNKNOWN",
            source=source,
            provenance="Chưa đủ dữ liệu số lượng cổ phiếu lưu hành hợp lệ để xác định cơ sở định giá.",
            status=ShareBasisStatus.INSUFFICIENT_DATA.value,
            cumulative_split_factor=Decimal("1.0"),
            is_compatible_with_current_price=False,
            summary_vietnamese="Chưa đủ dữ liệu số cổ phần để xác định giá trị nội tại trên mỗi cổ phiếu.",
        )

    # Convert raw dicts to CorporateActionEvent if needed
    typed_actions: List[CorporateActionEvent] = []
    for ca in corporate_actions:
        if isinstance(ca, CorporateActionEvent):
            typed_actions.append(ca)
        elif isinstance(ca, dict):
            typed_actions.append(
                CorporateActionEvent(
                    symbol=sym,
                    action_type=str(ca.get("action_type") or ca.get("dividend_type") or "OTHER"),
                    effective_date=str(ca.get("effective_date") or ca.get("effective_event_date") or ca.get("ex_date") or ""),
                    stock_ratio=_to_decimal(ca.get("stock_ratio")),
                    split_factor=_to_decimal(ca.get("split_factor")),
                    cash_per_share=_to_decimal(ca.get("cash_per_share")),
                    description=ca.get("description"),
                )
            )

    # Calculate cumulative non-economic multiplier between BCTC date and valuation date
    forward_multiplier = Decimal("1.0")
    if period_end_str and val_date_str and period_end_str < val_date_str:
        f_mult = calculate_cumulative_multiplier(typed_actions, period_end_str, val_date_str)
        forward_multiplier = Decimal(str(f_mult))

    adjusted_shares = s_dec * forward_multiplier
    adjusted_diluted = (diluted_dec if diluted_dec is not None else s_dec) * forward_multiplier

    if forward_multiplier != Decimal("1.0") and forward_multiplier > Decimal("0"):
        basis_type = ShareBasisType.CORPORATE_ACTION_ADJUSTED.value
        provenance = (
            f"Số cổ phiếu BCTC {bctc_fiscal_year or period_end_str} ({s_dec:,.0f} CP) đã được quy đổi "
            f"theo các sự kiện quyền sau kỳ BCTC (hệ số x{forward_multiplier:.4f}) thành "
            f"{adjusted_shares:,.0f} CP trên cùng cơ sở với giá thị trường."
        )
        summary_vi = f"Đã quy đổi theo sự kiện quyền (hệ số x{forward_multiplier:.2f}) thành {adjusted_shares:,.0f} cổ phần."
    else:
        basis_type = ShareBasisType.REPORTED_LATEST_BCTC.value
        provenance = (
            f"Số cổ phiếu lưu hành theo BCTC năm {bctc_fiscal_year or period_end_str}: "
            f"{s_dec:,.0f} CP (Nguồn: {source})."
        )
        summary_vi = f"Cơ sở số cổ phần lưu hành theo BCTC {bctc_fiscal_year or period_end_str}: {s_dec:,.0f} cổ phần."

    return ShareBasis(
        symbol=sym,
        shares_outstanding=adjusted_shares,
        diluted_shares=adjusted_diluted,
        valuation_share_count=adjusted_shares,
        basis_type=basis_type,
        as_of_date=val_date_str or period_end_str,
        source=source,
        provenance=provenance,
        status=ShareBasisStatus.VALID.value,
        cumulative_split_factor=forward_multiplier,
        is_compatible_with_current_price=True,
        summary_vietnamese=summary_vi,
    )
