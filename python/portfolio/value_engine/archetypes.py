"""
Economic Archetype Classifier for Vietnamese Stock Universe.

Classifies 1,500+ listed companies into 21 Economic Archetypes with multi-factor overlays
to route appropriate valuation models according to Buffett-Munger principles.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class EconomicArchetype(str, Enum):
    # Financials
    COMMERCIAL_BANK = "COMMERCIAL_BANK"
    SECURITIES_FIRM = "SECURITIES_FIRM"
    INSURANCE = "INSURANCE"
    
    # Compounders & Staples
    CONSUMER_STAPLES = "CONSUMER_STAPLES"
    RETAIL_DISCRETIONARY = "RETAIL_DISCRETIONARY"
    TECHNOLOGY_SERVICES = "TECHNOLOGY_SERVICES"
    PHARMA_HEALTHCARE = "PHARMA_HEALTHCARE"
    
    # Utilities & Regulated Infrastructure
    REGULATED_UTILITY = "REGULATED_UTILITY"
    PORT_LOGISTICS = "PORT_LOGISTICS"
    TELECOM = "TELECOM"
    
    # Real Estate & Construction
    REAL_ESTATE_DEVELOPER = "REAL_ESTATE_DEVELOPER"
    INDUSTRIAL_REAL_ESTATE = "INDUSTRIAL_REAL_ESTATE"
    CONSTRUCTION_CONTRACTOR = "CONSTRUCTION_CONTRACTOR"
    
    # Capital Intensive & Cyclicals
    COMMODITY_CYCLICAL = "COMMODITY_CYCLICAL"
    BASIC_MATERIALS_METALS = "BASIC_MATERIALS_METALS"
    OIL_GAS_ENERGY = "OIL_GAS_ENERGY"
    MANUFACTURING_INDUSTRIAL = "MANUFACTURING_INDUSTRIAL"
    AGRICULTURE_AQUACULTURE = "AGRICULTURE_AQUACULTURE"
    TEXTILE_FOOTWEAR_EXPORT = "TEXTILE_FOOTWEAR_EXPORT"
    
    # Highly Volatile / Complex
    AVIATION = "AVIATION"
    SHIPPING = "SHIPPING"
    CONGLOMERATE_HOLDING = "CONGLOMERATE_HOLDING"
    GENERIC_ENTERPRISE = "GENERIC_ENTERPRISE"


class ArchetypeOverlay(str, Enum):
    CAPITAL_INTENSIVE = "CAPITAL_INTENSIVE"
    HIGH_CYCLICALITY = "HIGH_CYCLICALITY"
    REGULATED_TARIFF = "REGULATED_TARIFF"
    EXPORT_ORIENTED = "EXPORT_ORIENTED"
    ASSET_LIGHT_COMPOUNDER = "ASSET_LIGHT_COMPOUNDER"
    REAL_ESTATE_EXPOSURE = "REAL_ESTATE_EXPOSURE"
    GOVERNMENT_BACKED = "GOVERNMENT_BACKED"


@dataclass
class ArchetypeProfile:
    archetype: EconomicArchetype
    overlays: List[ArchetypeOverlay]
    base_required_mos: float  # e.g. 0.25 for 25%
    recommended_model: str
    valuation_applicable: bool = True
    reason: str = ""


# Dedicated mappings for core and active symbols
EXPLICIT_SYMBOL_ARCHETYPES: Dict[str, ArchetypeProfile] = {
    # Banks
    "MBB": ArchetypeProfile(EconomicArchetype.COMMERCIAL_BANK, [ArchetypeOverlay.GOVERNMENT_BACKED], 0.25, "RESIDUAL_INCOME_MODEL"),
    "ACB": ArchetypeProfile(EconomicArchetype.COMMERCIAL_BANK, [], 0.25, "RESIDUAL_INCOME_MODEL"),
    "TCB": ArchetypeProfile(EconomicArchetype.COMMERCIAL_BANK, [ArchetypeOverlay.REAL_ESTATE_EXPOSURE], 0.25, "RESIDUAL_INCOME_MODEL"),
    "VCB": ArchetypeProfile(EconomicArchetype.COMMERCIAL_BANK, [ArchetypeOverlay.GOVERNMENT_BACKED, ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER], 0.20, "RESIDUAL_INCOME_MODEL"),
    "VPB": ArchetypeProfile(EconomicArchetype.COMMERCIAL_BANK, [], 0.25, "RESIDUAL_INCOME_MODEL"),
    "BID": ArchetypeProfile(EconomicArchetype.COMMERCIAL_BANK, [ArchetypeOverlay.GOVERNMENT_BACKED], 0.25, "RESIDUAL_INCOME_MODEL"),
    "CTG": ArchetypeProfile(EconomicArchetype.COMMERCIAL_BANK, [ArchetypeOverlay.GOVERNMENT_BACKED], 0.25, "RESIDUAL_INCOME_MODEL"),
    
    # Compounders & Tech
    "FPT": ArchetypeProfile(EconomicArchetype.TECHNOLOGY_SERVICES, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER, ArchetypeOverlay.EXPORT_ORIENTED], 0.20, "NORMALIZED_OWNER_EARNINGS_DCF"),
    "MWG": ArchetypeProfile(EconomicArchetype.RETAIL_DISCRETIONARY, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER], 0.25, "NORMALIZED_OWNER_EARNINGS_DCF"),
    "VNM": ArchetypeProfile(EconomicArchetype.CONSUMER_STAPLES, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER], 0.20, "NORMALIZED_OWNER_EARNINGS_DCF"),
    "PNJ": ArchetypeProfile(EconomicArchetype.RETAIL_DISCRETIONARY, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER], 0.25, "NORMALIZED_OWNER_EARNINGS_DCF"),
    "SAB": ArchetypeProfile(EconomicArchetype.CONSUMER_STAPLES, [], 0.25, "NORMALIZED_OWNER_EARNINGS_DCF"),
    
    # Cyclicals & Capital Intensive
    "HPG": ArchetypeProfile(EconomicArchetype.BASIC_MATERIALS_METALS, [ArchetypeOverlay.CAPITAL_INTENSIVE, ArchetypeOverlay.HIGH_CYCLICALITY], 0.40, "NORMALIZED_OWNER_EARNINGS_DCF"),
    "DGC": ArchetypeProfile(EconomicArchetype.COMMODITY_CYCLICAL, [ArchetypeOverlay.HIGH_CYCLICALITY, ArchetypeOverlay.EXPORT_ORIENTED], 0.40, "NORMALIZED_OWNER_EARNINGS_DCF"),
    "DCM": ArchetypeProfile(EconomicArchetype.COMMODITY_CYCLICAL, [ArchetypeOverlay.HIGH_CYCLICALITY], 0.40, "NORMALIZED_OWNER_EARNINGS_DCF"),
    "DPM": ArchetypeProfile(EconomicArchetype.COMMODITY_CYCLICAL, [ArchetypeOverlay.HIGH_CYCLICALITY], 0.40, "NORMALIZED_OWNER_EARNINGS_DCF"),
    
    # Utilities, Energy & Ports
    "GAS": ArchetypeProfile(EconomicArchetype.REGULATED_UTILITY, [ArchetypeOverlay.REGULATED_TARIFF, ArchetypeOverlay.GOVERNMENT_BACKED], 0.25, "NORMALIZED_OWNER_EARNINGS_DCF"),
    "POW": ArchetypeProfile(EconomicArchetype.REGULATED_UTILITY, [ArchetypeOverlay.CAPITAL_INTENSIVE, ArchetypeOverlay.REGULATED_TARIFF], 0.25, "NORMALIZED_OWNER_EARNINGS_DCF"),
    "REE": ArchetypeProfile(EconomicArchetype.REGULATED_UTILITY, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER], 0.25, "NORMALIZED_OWNER_EARNINGS_DCF"),
    "GMD": ArchetypeProfile(EconomicArchetype.PORT_LOGISTICS, [ArchetypeOverlay.CAPITAL_INTENSIVE], 0.25, "NORMALIZED_OWNER_EARNINGS_DCF"),
    "PLX": ArchetypeProfile(EconomicArchetype.OIL_GAS_ENERGY, [ArchetypeOverlay.REGULATED_TARIFF], 0.30, "NORMALIZED_OWNER_EARNINGS_DCF"),
    
    # Real Estate & Industrial Parks
    "VHM": ArchetypeProfile(EconomicArchetype.REAL_ESTATE_DEVELOPER, [ArchetypeOverlay.CAPITAL_INTENSIVE, ArchetypeOverlay.HIGH_CYCLICALITY], 0.40, "RNAV_OR_ADJUSTED_PB"),
    "NVL": ArchetypeProfile(EconomicArchetype.REAL_ESTATE_DEVELOPER, [ArchetypeOverlay.CAPITAL_INTENSIVE, ArchetypeOverlay.HIGH_CYCLICALITY], 0.50, "RNAV_OR_ADJUSTED_PB"),
    "PDR": ArchetypeProfile(EconomicArchetype.REAL_ESTATE_DEVELOPER, [ArchetypeOverlay.HIGH_CYCLICALITY], 0.45, "RNAV_OR_ADJUSTED_PB"),
    "KDH": ArchetypeProfile(EconomicArchetype.REAL_ESTATE_DEVELOPER, [], 0.35, "RNAV_OR_ADJUSTED_PB"),
    "IDC": ArchetypeProfile(EconomicArchetype.INDUSTRIAL_REAL_ESTATE, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER], 0.30, "NORMALIZED_OWNER_EARNINGS_DCF"),
    "KBC": ArchetypeProfile(EconomicArchetype.INDUSTRIAL_REAL_ESTATE, [ArchetypeOverlay.HIGH_CYCLICALITY], 0.35, "NORMALIZED_OWNER_EARNINGS_DCF"),
    
    # Securities
    "SSI": ArchetypeProfile(EconomicArchetype.SECURITIES_FIRM, [ArchetypeOverlay.HIGH_CYCLICALITY], 0.30, "RESIDUAL_INCOME_MODEL"),
    "VCI": ArchetypeProfile(EconomicArchetype.SECURITIES_FIRM, [ArchetypeOverlay.HIGH_CYCLICALITY], 0.30, "RESIDUAL_INCOME_MODEL"),
    "HCM": ArchetypeProfile(EconomicArchetype.SECURITIES_FIRM, [ArchetypeOverlay.HIGH_CYCLICALITY], 0.30, "RESIDUAL_INCOME_MODEL"),
    "VND": ArchetypeProfile(EconomicArchetype.SECURITIES_FIRM, [ArchetypeOverlay.HIGH_CYCLICALITY], 0.35, "RESIDUAL_INCOME_MODEL"),
    
    # Aviation & Shipping
    "VJC": ArchetypeProfile(EconomicArchetype.AVIATION, [ArchetypeOverlay.CAPITAL_INTENSIVE, ArchetypeOverlay.HIGH_CYCLICALITY], 0.45, "NORMALIZED_OWNER_EARNINGS_DCF"),
    "HVN": ArchetypeProfile(EconomicArchetype.AVIATION, [ArchetypeOverlay.CAPITAL_INTENSIVE, ArchetypeOverlay.HIGH_CYCLICALITY], 0.50, "NORMALIZED_OWNER_EARNINGS_DCF"),
    "HAH": ArchetypeProfile(EconomicArchetype.SHIPPING, [ArchetypeOverlay.HIGH_CYCLICALITY], 0.40, "NORMALIZED_OWNER_EARNINGS_DCF"),
}


class ArchetypeClassifier:
    """Classifies any Vietnamese stock into its economic archetype."""

    @classmethod
    def classify(cls, symbol: str, sector_text: str = "", company_type: str = "") -> ArchetypeProfile:
        sym = str(symbol).upper().strip()
        if sym in EXPLICIT_SYMBOL_ARCHETYPES:
            return EXPLICIT_SYMBOL_ARCHETYPES[sym]

        combined = f"{sector_text} {company_type}".lower()

        if any(w in combined for w in ("ngân hàng", "bank")):
            return ArchetypeProfile(EconomicArchetype.COMMERCIAL_BANK, [], 0.25, "RESIDUAL_INCOME_MODEL")
        if any(w in combined for w in ("chứng khoán", "securities")):
            return ArchetypeProfile(EconomicArchetype.SECURITIES_FIRM, [ArchetypeOverlay.HIGH_CYCLICALITY], 0.30, "RESIDUAL_INCOME_MODEL")
        if any(w in combined for w in ("bảo hiểm", "insurance")):
            return ArchetypeProfile(EconomicArchetype.INSURANCE, [], 0.25, "RESIDUAL_INCOME_MODEL")
        if any(w in combined for w in ("bất động sản", "real estate", "địa ốc")):
            if any(w in combined for w in ("kcn", "khu công nghiệp", "industrial")):
                return ArchetypeProfile(EconomicArchetype.INDUSTRIAL_REAL_ESTATE, [], 0.30, "NORMALIZED_OWNER_EARNINGS_DCF")
            return ArchetypeProfile(EconomicArchetype.REAL_ESTATE_DEVELOPER, [ArchetypeOverlay.HIGH_CYCLICALITY], 0.40, "RNAV_OR_ADJUSTED_PB")
        if any(w in combined for w in ("thép", "steel", "kim loại", "hóa chất", "chemical", "phân bón")):
            return ArchetypeProfile(EconomicArchetype.COMMODITY_CYCLICAL, [ArchetypeOverlay.HIGH_CYCLICALITY, ArchetypeOverlay.CAPITAL_INTENSIVE], 0.40, "NORMALIZED_OWNER_EARNINGS_DCF")
        if any(w in combined for w in ("điện", "nước", "tiện ích", "utility", "năng lượng")):
            return ArchetypeProfile(EconomicArchetype.REGULATED_UTILITY, [ArchetypeOverlay.REGULATED_TARIFF], 0.25, "NORMALIZED_OWNER_EARNINGS_DCF")
        if any(w in combined for w in ("công nghệ", "phần mềm", "it services", "viễn thông")):
            return ArchetypeProfile(EconomicArchetype.TECHNOLOGY_SERVICES, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER], 0.20, "NORMALIZED_OWNER_EARNINGS_DCF")
        if any(w in combined for w in ("thực phẩm", "đồ uống", "f&b", "sữa", "tiêu dùng")):
            return ArchetypeProfile(EconomicArchetype.CONSUMER_STAPLES, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER], 0.20, "NORMALIZED_OWNER_EARNINGS_DCF")
        if any(w in combined for w in ("bán lẻ", "retail")):
            return ArchetypeProfile(EconomicArchetype.RETAIL_DISCRETIONARY, [], 0.25, "NORMALIZED_OWNER_EARNINGS_DCF")
        if any(w in combined for w in ("hàng không", "airline")):
            return ArchetypeProfile(EconomicArchetype.AVIATION, [ArchetypeOverlay.CAPITAL_INTENSIVE, ArchetypeOverlay.HIGH_CYCLICALITY], 0.45, "NORMALIZED_OWNER_EARNINGS_DCF")
        if any(w in combined for w in ("cảng", "logistics", "vận tải biển", "shipping")):
            return ArchetypeProfile(EconomicArchetype.PORT_LOGISTICS, [ArchetypeOverlay.CAPITAL_INTENSIVE], 0.25, "NORMALIZED_OWNER_EARNINGS_DCF")

        return ArchetypeProfile(EconomicArchetype.GENERIC_ENTERPRISE, [], 0.30, "NORMALIZED_OWNER_EARNINGS_DCF")
