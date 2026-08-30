"""
Comprehensive Sector & Economic Archetype Valuation Registry for the Vietnamese Stock Market.

Defines 40 Economic Archetypes and 16 Universal Overlays matching Buffett-Munger
first-principles valuation. Every archetype has explicit primary, secondary, and
forbidden models, normalization policies, required fields, and base Margin of Safety.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class EconomicArchetype(str, Enum):
    # 1. Financials
    COMMERCIAL_BANK = "COMMERCIAL_BANK"
    CONSUMER_FINANCE = "CONSUMER_FINANCE"
    SECURITIES_BROKER = "SECURITIES_BROKER"
    NON_LIFE_INSURANCE = "NON_LIFE_INSURANCE"
    LIFE_INSURANCE = "LIFE_INSURANCE"
    INVESTMENT_HOLDING_FINANCIAL = "INVESTMENT_HOLDING_FINANCIAL"

    # 2. Real Estate & Property
    REAL_ESTATE_DEVELOPER = "REAL_ESTATE_DEVELOPER"
    INDUSTRIAL_REAL_ESTATE = "INDUSTRIAL_REAL_ESTATE"
    RENTAL_REAL_ESTATE = "RENTAL_REAL_ESTATE"

    # 3. Consumer, Retail & Media
    CONSUMER_STAPLES = "CONSUMER_STAPLES"
    RETAIL_CHAIN = "RETAIL_CHAIN"
    CONSUMER_DISCRETIONARY = "CONSUMER_DISCRETIONARY"
    MEDIA_CONTENT = "MEDIA_CONTENT"

    # 4. Technology & Telecom
    TECHNOLOGY_SERVICES = "TECHNOLOGY_SERVICES"
    SOFTWARE_PLATFORM = "SOFTWARE_PLATFORM"
    TELECOM_OPERATOR = "TELECOM_OPERATOR"

    # 5. Healthcare
    PHARMACEUTICAL = "PHARMACEUTICAL"
    HEALTHCARE_SERVICES = "HEALTHCARE_SERVICES"

    # 6. Materials, Energy & Utilities
    BASIC_MATERIALS_METALS = "BASIC_MATERIALS_METALS"
    COMMODITY_CHEMICAL = "COMMODITY_CHEMICAL"
    SPECIALTY_CHEMICAL = "SPECIALTY_CHEMICAL"
    BUILDING_MATERIALS = "BUILDING_MATERIALS"
    MINING_RESOURCE = "MINING_RESOURCE"
    OIL_GAS_UPSTREAM = "OIL_GAS_UPSTREAM"
    OILFIELD_SERVICES = "OILFIELD_SERVICES"
    ENERGY_INFRASTRUCTURE = "ENERGY_INFRASTRUCTURE"
    OIL_REFINING_DOWNSTREAM = "OIL_REFINING_DOWNSTREAM"
    POWER_GENERATION_THERMAL = "POWER_GENERATION_THERMAL"
    POWER_GENERATION_HYDRO = "POWER_GENERATION_HYDRO"
    POWER_RENEWABLE = "POWER_RENEWABLE"
    WATER_UTILITY = "WATER_UTILITY"

    # 7. Industrials, Infrastructure & Logistics
    CONSTRUCTION_EPC = "CONSTRUCTION_EPC"
    INDUSTRIAL_MANUFACTURING = "INDUSTRIAL_MANUFACTURING"
    AUTOMOTIVE = "AUTOMOTIVE"
    AUTO_COMPONENTS = "AUTO_COMPONENTS"
    PORT_INFRASTRUCTURE = "PORT_INFRASTRUCTURE"
    LOGISTICS_SERVICES = "LOGISTICS_SERVICES"
    SHIPPING = "SHIPPING"
    AIRLINE = "AIRLINE"
    AIRPORT_INFRASTRUCTURE = "AIRPORT_INFRASTRUCTURE"
    CONCESSION_INFRASTRUCTURE = "CONCESSION_INFRASTRUCTURE"

    # 8. Agriculture, Plantation & Conglomerates
    AGRICULTURE = "AGRICULTURE"
    RUBBER_PLANTATION = "RUBBER_PLANTATION"
    AQUACULTURE_EXPORT = "AQUACULTURE_EXPORT"
    EXPORT_MANUFACTURING = "EXPORT_MANUFACTURING"
    HOTEL_HOSPITALITY = "HOTEL_HOSPITALITY"
    EDUCATION_SERVICES = "EDUCATION_SERVICES"
    HOLDING_COMPANY = "HOLDING_COMPANY"
    CONGLOMERATE = "CONGLOMERATE"
    GENERIC_ENTERPRISE = "GENERIC_ENTERPRISE"
    ARCHETYPE_UNKNOWN = "ARCHETYPE_UNKNOWN"
    # Legacy & convenience aliases
    CONGLOMERATE_HOLDING = "CONGLOMERATE"
    SECURITIES_FIRM = "SECURITIES_BROKER"
    INSURANCE = "NON_LIFE_INSURANCE"
    PHARMA_HEALTHCARE = "PHARMACEUTICAL"
    REGULATED_UTILITY = "ENERGY_INFRASTRUCTURE"
    OIL_GAS_ENERGY = "OIL_GAS_UPSTREAM"
    RETAIL_DISCRETIONARY = "RETAIL_CHAIN"
    CONSTRUCTION_CONTRACTOR = "CONSTRUCTION_EPC"
    MANUFACTURING_INDUSTRIAL = "INDUSTRIAL_MANUFACTURING"
    AGRICULTURE_AQUACULTURE = "AGRICULTURE"
    TEXTILE_FOOTWEAR_EXPORT = "EXPORT_MANUFACTURING"
    PORT_LOGISTICS = "PORT_INFRASTRUCTURE"
    TELECOM = "TELECOM_OPERATOR"
    COMMODITY_CYCLICAL = "COMMODITY_CHEMICAL"
    AVIATION = "AIRLINE"


class ArchetypeOverlay(str, Enum):
    HIGH_CYCLICALITY = "HIGH_CYCLICALITY"
    CAPITAL_INTENSIVE = "CAPITAL_INTENSIVE"
    COMMODITY_EXPOSED = "COMMODITY_EXPOSED"
    ASSET_LIGHT_COMPOUNDER = "ASSET_LIGHT_COMPOUNDER"
    REGULATED = "REGULATED"
    CONCESSION = "CONCESSION"
    PROJECT_BASED = "PROJECT_BASED"
    EXPORT_ORIENTED = "EXPORT_ORIENTED"
    FX_SENSITIVE = "FX_SENSITIVE"
    CUSTOMER_CONCENTRATED = "CUSTOMER_CONCENTRATED"
    HIGH_LEVERAGE = "HIGH_LEVERAGE"
    STATE_INFLUENCED = "STATE_INFLUENCED"
    RELATED_PARTY_RISK = "RELATED_PARTY_RISK"
    TURNAROUND = "TURNAROUND"
    MATURE_COMPOUNDER = "MATURE_COMPOUNDER"
    EARLY_GROWTH = "EARLY_GROWTH"
    # Aliases
    REAL_ESTATE_EXPOSURE = "PROJECT_BASED"
    GOVERNMENT_BACKED = "STATE_INFLUENCED"
    REGULATED_TARIFF = "REGULATED"


@dataclass
class ArchetypeRegistryEntry:
    archetype: EconomicArchetype
    primary_model: str
    secondary_models: List[str] = field(default_factory=list)
    forbidden_models: List[str] = field(default_factory=list)
    required_fields: List[str] = field(default_factory=list)
    minimum_history_years: int = 5
    normalization_policy: str = "LATEST_OR_MID_CYCLE"
    base_mos: float = 0.25
    allowed_overlays: List[ArchetypeOverlay] = field(default_factory=list)


@dataclass
class ArchetypeProfile:
    archetype: EconomicArchetype
    overlays: List[ArchetypeOverlay]
    base_required_mos: float
    recommended_model: str
    valuation_applicable: bool = True
    reason: str = ""
    raw_provider_sector: str = ""
    normalized_sector: str = ""
    classification_confidence: str = "HIGH"  # HIGH | MEDIUM | LOW


# Comprehensive Registry for all 40 Economic Archetypes
ARCHETYPE_REGISTRY: Dict[EconomicArchetype, ArchetypeRegistryEntry] = {
    # Financials
    EconomicArchetype.COMMERCIAL_BANK: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.COMMERCIAL_BANK,
        primary_model="RESIDUAL_INCOME_MODEL",
        secondary_models=["JUSTIFIED_PB", "DIVIDEND_DISCOUNT_MODEL"],
        forbidden_models=["FCFF_DCF", "NORMALIZED_OWNER_EARNINGS_DCF", "EPV"],
        required_fields=["BS.EQUITY.TOTAL", "IS.PROFIT.NET"],
        minimum_history_years=5,
        normalization_policy="5_TO_10Y_NORMALIZED_ROE",
        base_mos=0.25,
    ),
    EconomicArchetype.CONSUMER_FINANCE: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.CONSUMER_FINANCE,
        primary_model="RESIDUAL_INCOME_MODEL",
        secondary_models=["JUSTIFIED_PB"],
        forbidden_models=["NORMALIZED_OWNER_EARNINGS_DCF"],
        minimum_history_years=5,
        base_mos=0.30,
    ),
    EconomicArchetype.SECURITIES_BROKER: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.SECURITIES_BROKER,
        primary_model="RESIDUAL_INCOME_MODEL",
        secondary_models=["JUSTIFIED_PB"],
        forbidden_models=["NORMALIZED_OWNER_EARNINGS_DCF"],
        minimum_history_years=5,
        normalization_policy="5_TO_10Y_MARKET_CYCLE",
        base_mos=0.30,
    ),
    EconomicArchetype.NON_LIFE_INSURANCE: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.NON_LIFE_INSURANCE,
        primary_model="RESIDUAL_INCOME_MODEL",
        secondary_models=["DIVIDEND_DISCOUNT_MODEL"],
        base_mos=0.25,
    ),
    EconomicArchetype.LIFE_INSURANCE: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.LIFE_INSURANCE,
        primary_model="RESIDUAL_INCOME_MODEL",
        secondary_models=["DIVIDEND_DISCOUNT_MODEL"],
        base_mos=0.30,
    ),
    EconomicArchetype.INVESTMENT_HOLDING_FINANCIAL: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.INVESTMENT_HOLDING_FINANCIAL,
        primary_model="SOTP",
        secondary_models=["RESIDUAL_INCOME_MODEL"],
        base_mos=0.30,
    ),

    # Real Estate
    EconomicArchetype.REAL_ESTATE_DEVELOPER: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.REAL_ESTATE_DEVELOPER,
        primary_model="RNAV",
        secondary_models=["PROJECT_DCF", "SOTP"],
        forbidden_models=["NORMALIZED_OWNER_EARNINGS_DCF"],
        base_mos=0.40,
    ),
    EconomicArchetype.INDUSTRIAL_REAL_ESTATE: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.INDUSTRIAL_REAL_ESTATE,
        primary_model="LEASE_CASHFLOW_DCF",
        secondary_models=["RNAV", "SOTP", "NORMALIZED_OWNER_EARNINGS_DCF"],
        forbidden_models=["GENERIC_LATEST_FY_DCF"],
        minimum_history_years=5,
        base_mos=0.25,
    ),
    EconomicArchetype.RENTAL_REAL_ESTATE: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.RENTAL_REAL_ESTATE,
        primary_model="LEASE_CASHFLOW_DCF",
        secondary_models=["RNAV"],
        base_mos=0.25,
    ),

    # Consumer & Retail
    EconomicArchetype.CONSUMER_STAPLES: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.CONSUMER_STAPLES,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        secondary_models=["EPV", "REVERSE_DCF"],
        base_mos=0.20,
    ),
    EconomicArchetype.RETAIL_CHAIN: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.RETAIL_CHAIN,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        secondary_models=["EPV"],
        base_mos=0.25,
    ),
    EconomicArchetype.CONSUMER_DISCRETIONARY: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.CONSUMER_DISCRETIONARY,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        secondary_models=["EPV"],
        base_mos=0.30,
    ),
    EconomicArchetype.MEDIA_CONTENT: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.MEDIA_CONTENT,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        base_mos=0.35,
    ),

    # Tech & Telecom
    EconomicArchetype.TECHNOLOGY_SERVICES: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.TECHNOLOGY_SERVICES,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        secondary_models=["REVERSE_DCF", "EPV"],
        base_mos=0.20,
    ),
    EconomicArchetype.SOFTWARE_PLATFORM: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.SOFTWARE_PLATFORM,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        base_mos=0.25,
    ),
    EconomicArchetype.TELECOM_OPERATOR: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.TELECOM_OPERATOR,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        secondary_models=["DIVIDEND_DISCOUNT_MODEL"],
        base_mos=0.25,
    ),

    # Healthcare
    EconomicArchetype.PHARMACEUTICAL: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.PHARMACEUTICAL,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        secondary_models=["EPV"],
        base_mos=0.25,
    ),
    EconomicArchetype.HEALTHCARE_SERVICES: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.HEALTHCARE_SERVICES,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        base_mos=0.25,
    ),

    # Materials, Energy & Utilities
    EconomicArchetype.BASIC_MATERIALS_METALS: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.BASIC_MATERIALS_METALS,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        secondary_models=["EPV"],
        normalization_policy="MID_CYCLE_7_TO_10_YEARS",
        base_mos=0.40,
    ),
    EconomicArchetype.COMMODITY_CHEMICAL: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.COMMODITY_CHEMICAL,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        normalization_policy="MID_CYCLE_7_TO_10_YEARS",
        base_mos=0.40,
    ),
    EconomicArchetype.SPECIALTY_CHEMICAL: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.SPECIALTY_CHEMICAL,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        secondary_models=["EPV"],
        base_mos=0.25,
    ),
    EconomicArchetype.BUILDING_MATERIALS: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.BUILDING_MATERIALS,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        normalization_policy="MID_CYCLE_7_TO_10_YEARS",
        base_mos=0.35,
    ),
    EconomicArchetype.MINING_RESOURCE: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.MINING_RESOURCE,
        primary_model="RESERVE_NAV",
        secondary_models=[],
        forbidden_models=["NORMALIZED_OWNER_EARNINGS_DCF"],
        required_fields=["proven_reserves", "probable_reserves", "grade", "recovery", "production_schedule", "commodity_price", "opex_per_unit", "mine_life_years", "development_capex", "royalty_tax"],
        minimum_history_years=7,
        normalization_policy="MID_CYCLE_7_TO_10_YEARS",
        base_mos=0.40,
    ),
    EconomicArchetype.OIL_GAS_UPSTREAM: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.OIL_GAS_UPSTREAM,
        primary_model="CONCESSION_DCF",
        base_mos=0.40,
    ),
    EconomicArchetype.OILFIELD_SERVICES: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.OILFIELD_SERVICES,
        primary_model="MID_CYCLE_FCFF",
        secondary_models=[],
        forbidden_models=["CONCESSION_DCF"],
        required_fields=["rig_count", "rig_utilization", "day_rate", "backlog", "rig_age"],
        minimum_history_years=7,
        normalization_policy="MID_CYCLE_7_TO_10_YEARS",
        base_mos=0.40,
    ),
    EconomicArchetype.ENERGY_INFRASTRUCTURE: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.ENERGY_INFRASTRUCTURE,
        primary_model="CONCESSION_DCF",
        secondary_models=["NORMALIZED_OWNER_EARNINGS_DCF"],
        base_mos=0.25,
    ),
    EconomicArchetype.OIL_REFINING_DOWNSTREAM: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.OIL_REFINING_DOWNSTREAM,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        normalization_policy="MID_CYCLE_7_TO_10_YEARS",
        base_mos=0.35,
    ),
    EconomicArchetype.POWER_GENERATION_THERMAL: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.POWER_GENERATION_THERMAL,
        primary_model="CONCESSION_DCF",
        secondary_models=["NORMALIZED_OWNER_EARNINGS_DCF"],
        base_mos=0.25,
    ),
    EconomicArchetype.POWER_GENERATION_HYDRO: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.POWER_GENERATION_HYDRO,
        primary_model="CONCESSION_DCF",
        secondary_models=["NORMALIZED_OWNER_EARNINGS_DCF"],
        normalization_policy="HYDROLOGY_5_TO_10_YEARS",
        base_mos=0.25,
    ),
    EconomicArchetype.POWER_RENEWABLE: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.POWER_RENEWABLE,
        primary_model="CONCESSION_DCF",
        base_mos=0.30,
    ),
    EconomicArchetype.WATER_UTILITY: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.WATER_UTILITY,
        primary_model="CONCESSION_DCF",
        secondary_models=["NORMALIZED_OWNER_EARNINGS_DCF"],
        base_mos=0.20,
    ),

    # Industrials & Infrastructure
    EconomicArchetype.CONSTRUCTION_EPC: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.CONSTRUCTION_EPC,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        secondary_models=["EPV"],
        base_mos=0.35,
    ),
    EconomicArchetype.INDUSTRIAL_MANUFACTURING: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.INDUSTRIAL_MANUFACTURING,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        secondary_models=["EPV"],
        base_mos=0.25,
    ),
    EconomicArchetype.AUTOMOTIVE: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.AUTOMOTIVE,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        base_mos=0.35,
    ),
    EconomicArchetype.AUTO_COMPONENTS: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.AUTO_COMPONENTS,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        base_mos=0.30,
    ),
    EconomicArchetype.PORT_INFRASTRUCTURE: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.PORT_INFRASTRUCTURE,
        primary_model="CONCESSION_DCF",
        secondary_models=["NORMALIZED_OWNER_EARNINGS_DCF"],
        base_mos=0.25,
    ),
    EconomicArchetype.LOGISTICS_SERVICES: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.LOGISTICS_SERVICES,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        base_mos=0.25,
    ),
    EconomicArchetype.SHIPPING: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.SHIPPING,
        primary_model="FLEET_NAV",
        secondary_models=[],
        forbidden_models=["NORMALIZED_OWNER_EARNINGS_DCF"],
        required_fields=["vessel_list", "fleet_age", "fleet_value", "charter_rate", "utilization", "remaining_fleet_life", "maintenance_capex", "debt"],
        minimum_history_years=7,
        normalization_policy="MID_CYCLE_7_TO_10_YEARS",
        base_mos=0.40,
    ),
    EconomicArchetype.AIRLINE: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.AIRLINE,
        primary_model="AIRLINE_EBITDAR",
        secondary_models=[],
        forbidden_models=["NORMALIZED_OWNER_EARNINGS_DCF"],
        required_fields=["rask", "cask", "load_factor", "fuel", "fx", "lease_liabilities", "fleet_commitments", "maintenance_reserves", "aircraft_capex"],
        minimum_history_years=7,
        base_mos=0.45,
    ),
    EconomicArchetype.AIRPORT_INFRASTRUCTURE: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.AIRPORT_INFRASTRUCTURE,
        primary_model="CONCESSION_DCF",
        base_mos=0.25,
    ),
    EconomicArchetype.CONCESSION_INFRASTRUCTURE: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.CONCESSION_INFRASTRUCTURE,
        primary_model="CONCESSION_DCF",
        base_mos=0.30,
    ),

    # Agriculture & Conglomerates
    EconomicArchetype.AGRICULTURE: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.AGRICULTURE,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        base_mos=0.35,
    ),
    EconomicArchetype.RUBBER_PLANTATION: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.RUBBER_PLANTATION,
        primary_model="LEASE_CASHFLOW_DCF",
        secondary_models=["SOTP", "NORMALIZED_OWNER_EARNINGS_DCF"],
        base_mos=0.35,
    ),
    EconomicArchetype.AQUACULTURE_EXPORT: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.AQUACULTURE_EXPORT,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        normalization_policy="MID_CYCLE_7_TO_10_YEARS",
        base_mos=0.35,
    ),
    EconomicArchetype.EXPORT_MANUFACTURING: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.EXPORT_MANUFACTURING,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        base_mos=0.30,
    ),
    EconomicArchetype.HOTEL_HOSPITALITY: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.HOTEL_HOSPITALITY,
        primary_model="LEASE_CASHFLOW_DCF",
        base_mos=0.35,
    ),
    EconomicArchetype.EDUCATION_SERVICES: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.EDUCATION_SERVICES,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        base_mos=0.25,
    ),
    EconomicArchetype.HOLDING_COMPANY: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.HOLDING_COMPANY,
        primary_model="SOTP",
        secondary_models=["NORMALIZED_OWNER_EARNINGS_DCF"],
        base_mos=0.35,
    ),
    EconomicArchetype.CONGLOMERATE: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.CONGLOMERATE,
        primary_model="SOTP",
        secondary_models=["NORMALIZED_OWNER_EARNINGS_DCF"],
        base_mos=0.35,
    ),
    EconomicArchetype.GENERIC_ENTERPRISE: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.GENERIC_ENTERPRISE,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        base_mos=0.30,
    ),
    EconomicArchetype.ARCHETYPE_UNKNOWN: ArchetypeRegistryEntry(
        archetype=EconomicArchetype.ARCHETYPE_UNKNOWN,
        primary_model="NORMALIZED_OWNER_EARNINGS_DCF",
        secondary_models=[],
        forbidden_models=[],
        minimum_history_years=5,
        normalization_policy="LATEST_OR_MID_CYCLE",
        base_mos=0.30,
    ),
}


# Dedicated mappings for active Vietnamese symbols
EXPLICIT_SYMBOL_ARCHETYPES: Dict[str, ArchetypeProfile] = {
    # 1. Banks
    "MBB": ArchetypeProfile(EconomicArchetype.COMMERCIAL_BANK, [ArchetypeOverlay.STATE_INFLUENCED], 0.25, "RESIDUAL_INCOME_MODEL", reason="Ngân hàng TMCP Quân đội"),
    "ACB": ArchetypeProfile(EconomicArchetype.COMMERCIAL_BANK, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER], 0.25, "RESIDUAL_INCOME_MODEL", reason="Ngân hàng TMCP Á Châu - Quản trị rủi ro hàng đầu"),
    "TCB": ArchetypeProfile(EconomicArchetype.COMMERCIAL_BANK, [ArchetypeOverlay.REAL_ESTATE_EXPOSURE], 0.25, "RESIDUAL_INCOME_MODEL", reason="Ngân hàng TMCP Kỹ thương"),
    "VCB": ArchetypeProfile(EconomicArchetype.COMMERCIAL_BANK, [ArchetypeOverlay.STATE_INFLUENCED, ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER], 0.20, "RESIDUAL_INCOME_MODEL", reason="Ngân hàng TMCP Ngoại thương"),
    "VPB": ArchetypeProfile(EconomicArchetype.COMMERCIAL_BANK, [ArchetypeOverlay.HIGH_LEVERAGE], 0.25, "RESIDUAL_INCOME_MODEL"),
    "BID": ArchetypeProfile(EconomicArchetype.COMMERCIAL_BANK, [ArchetypeOverlay.STATE_INFLUENCED], 0.25, "RESIDUAL_INCOME_MODEL"),
    "CTG": ArchetypeProfile(EconomicArchetype.COMMERCIAL_BANK, [ArchetypeOverlay.STATE_INFLUENCED], 0.25, "RESIDUAL_INCOME_MODEL"),
    "STB": ArchetypeProfile(EconomicArchetype.COMMERCIAL_BANK, [ArchetypeOverlay.TURNAROUND], 0.30, "RESIDUAL_INCOME_MODEL"),
    "HDB": ArchetypeProfile(EconomicArchetype.COMMERCIAL_BANK, [], 0.25, "RESIDUAL_INCOME_MODEL"),
    "TPB": ArchetypeProfile(EconomicArchetype.COMMERCIAL_BANK, [], 0.25, "RESIDUAL_INCOME_MODEL"),
    "VIB": ArchetypeProfile(EconomicArchetype.COMMERCIAL_BANK, [], 0.25, "RESIDUAL_INCOME_MODEL"),

    # 2. Securities
    "SSI": ArchetypeProfile(EconomicArchetype.SECURITIES_BROKER, [ArchetypeOverlay.HIGH_CYCLICALITY], 0.30, "RESIDUAL_INCOME_MODEL"),
    "VCI": ArchetypeProfile(EconomicArchetype.SECURITIES_BROKER, [ArchetypeOverlay.HIGH_CYCLICALITY], 0.30, "RESIDUAL_INCOME_MODEL"),
    "HCM": ArchetypeProfile(EconomicArchetype.SECURITIES_BROKER, [ArchetypeOverlay.HIGH_CYCLICALITY], 0.30, "RESIDUAL_INCOME_MODEL"),
    "VND": ArchetypeProfile(EconomicArchetype.SECURITIES_BROKER, [ArchetypeOverlay.HIGH_CYCLICALITY], 0.35, "RESIDUAL_INCOME_MODEL"),
    "FTS": ArchetypeProfile(EconomicArchetype.SECURITIES_BROKER, [ArchetypeOverlay.HIGH_CYCLICALITY], 0.30, "RESIDUAL_INCOME_MODEL"),

    # 3. Technology & Compounders
    "FPT": ArchetypeProfile(EconomicArchetype.TECHNOLOGY_SERVICES, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER, ArchetypeOverlay.EXPORT_ORIENTED], 0.20, "NORMALIZED_OWNER_EARNINGS_DCF", reason="Tập đoàn FPT - Xuất khẩu phần mềm và viễn thông"),
    "VNM": ArchetypeProfile(EconomicArchetype.CONSUMER_STAPLES, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER, ArchetypeOverlay.MATURE_COMPOUNDER], 0.20, "NORMALIZED_OWNER_EARNINGS_DCF", reason="Vinamilk - Hàng tiêu dùng thiết yếu số 1 VN"),
    "MWG": ArchetypeProfile(EconomicArchetype.RETAIL_CHAIN, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER], 0.25, "NORMALIZED_OWNER_EARNINGS_DCF", reason="Thế Giới Di Động & Bách Hóa Xanh"),
    "PNJ": ArchetypeProfile(EconomicArchetype.RETAIL_CHAIN, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER], 0.25, "NORMALIZED_OWNER_EARNINGS_DCF", reason="Vàng bạc Đá quý Phú Nhuận"),
    "SAB": ArchetypeProfile(EconomicArchetype.CONSUMER_STAPLES, [ArchetypeOverlay.MATURE_COMPOUNDER], 0.25, "NORMALIZED_OWNER_EARNINGS_DCF"),
    "MSN": ArchetypeProfile(EconomicArchetype.CONGLOMERATE, [ArchetypeOverlay.CAPITAL_INTENSIVE], 0.35, "SOTP", reason="Tập đoàn Masan"),

    # 4. Basic Materials & Cyclicals
    "HPG": ArchetypeProfile(EconomicArchetype.BASIC_MATERIALS_METALS, [ArchetypeOverlay.CAPITAL_INTENSIVE, ArchetypeOverlay.HIGH_CYCLICALITY, ArchetypeOverlay.COMMODITY_EXPOSED], 0.40, "NORMALIZED_OWNER_EARNINGS_DCF", reason="Tập đoàn Hòa Phát - Luyện thép chu kỳ quy mô lớn"),
    "HSG": ArchetypeProfile(EconomicArchetype.BASIC_MATERIALS_METALS, [ArchetypeOverlay.HIGH_CYCLICALITY, ArchetypeOverlay.COMMODITY_EXPOSED], 0.45, "NORMALIZED_OWNER_EARNINGS_DCF"),
    "NKG": ArchetypeProfile(EconomicArchetype.BASIC_MATERIALS_METALS, [ArchetypeOverlay.HIGH_CYCLICALITY, ArchetypeOverlay.COMMODITY_EXPOSED], 0.45, "NORMALIZED_OWNER_EARNINGS_DCF"),
    "DGC": ArchetypeProfile(EconomicArchetype.SPECIALTY_CHEMICAL, [ArchetypeOverlay.HIGH_CYCLICALITY, ArchetypeOverlay.COMMODITY_EXPOSED, ArchetypeOverlay.EXPORT_ORIENTED], 0.35, "NORMALIZED_OWNER_EARNINGS_DCF", reason="Hóa chất Đức Giang - Phốt pho vàng chu kỳ"),
    "DCM": ArchetypeProfile(EconomicArchetype.COMMODITY_CHEMICAL, [ArchetypeOverlay.HIGH_CYCLICALITY, ArchetypeOverlay.COMMODITY_EXPOSED], 0.40, "NORMALIZED_OWNER_EARNINGS_DCF"),
    "DPM": ArchetypeProfile(EconomicArchetype.COMMODITY_CHEMICAL, [ArchetypeOverlay.HIGH_CYCLICALITY, ArchetypeOverlay.COMMODITY_EXPOSED], 0.40, "NORMALIZED_OWNER_EARNINGS_DCF"),

    # 5. Energy Infrastructure, Utilities & Oil
    "GAS": ArchetypeProfile(EconomicArchetype.ENERGY_INFRASTRUCTURE, [ArchetypeOverlay.REGULATED, ArchetypeOverlay.CONCESSION, ArchetypeOverlay.STATE_INFLUENCED], 0.25, "CONCESSION_DCF", reason="Tổng Công ty Khí Việt Nam - Hạ tầng phân phối khí độc quyền"),
    "POW": ArchetypeProfile(EconomicArchetype.POWER_GENERATION_THERMAL, [ArchetypeOverlay.CAPITAL_INTENSIVE, ArchetypeOverlay.REGULATED], 0.25, "CONCESSION_DCF"),
    "REE": ArchetypeProfile(EconomicArchetype.CONGLOMERATE, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER], 0.25, "SOTP", reason="Cơ Điện Lạnh REE - Năng lượng, Nước và BĐS cho thuê"),
    "PLX": ArchetypeProfile(EconomicArchetype.OIL_REFINING_DOWNSTREAM, [ArchetypeOverlay.REGULATED], 0.30, "NORMALIZED_OWNER_EARNINGS_DCF"),
    "PVD": ArchetypeProfile(EconomicArchetype.OILFIELD_SERVICES, [ArchetypeOverlay.HIGH_CYCLICALITY, ArchetypeOverlay.CAPITAL_INTENSIVE], 0.40, "MID_CYCLE_FCFF", reason="PV Drilling - Dịch vụ khoan giàn dầu, không phải chủ sở hữu trữ lượng."),
    "PVS": ArchetypeProfile(EconomicArchetype.OILFIELD_SERVICES, [ArchetypeOverlay.HIGH_CYCLICALITY, ArchetypeOverlay.PROJECT_BASED], 0.40, "MID_CYCLE_FCFF", reason="PTSC - Dịch vụ kỹ thuật dầu khí biển, không phải nhà thầu xây dựng thông thường."),

    # 6. Industrial Real Estate (IDC, SZC, BCM, KBC...)
    "IDC": ArchetypeProfile(EconomicArchetype.INDUSTRIAL_REAL_ESTATE, [ArchetypeOverlay.PROJECT_BASED, ArchetypeOverlay.CONCESSION], 0.25, "LEASE_CASHFLOW_DCF", reason="Tổng Công ty IDICO - Quỹ đất KCN lớn và dòng tiền cho thuê đất thực tế"),
    "SZC": ArchetypeProfile(EconomicArchetype.INDUSTRIAL_REAL_ESTATE, [ArchetypeOverlay.PROJECT_BASED], 0.30, "LEASE_CASHFLOW_DCF", reason="Sonadezi Châu Đức"),
    "BCM": ArchetypeProfile(EconomicArchetype.INDUSTRIAL_REAL_ESTATE, [ArchetypeOverlay.STATE_INFLUENCED, ArchetypeOverlay.PROJECT_BASED], 0.30, "LEASE_CASHFLOW_DCF", reason="Becamex IDC"),
    "KBC": ArchetypeProfile(EconomicArchetype.INDUSTRIAL_REAL_ESTATE, [ArchetypeOverlay.HIGH_CYCLICALITY, ArchetypeOverlay.PROJECT_BASED], 0.35, "LEASE_CASHFLOW_DCF", reason="Đô thị Kinh Bắc"),
    "NTC": ArchetypeProfile(EconomicArchetype.INDUSTRIAL_REAL_ESTATE, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER], 0.25, "LEASE_CASHFLOW_DCF", reason="Nam Tân Uyên"),
    "SIP": ArchetypeProfile(EconomicArchetype.INDUSTRIAL_REAL_ESTATE, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER], 0.25, "LEASE_CASHFLOW_DCF", reason="Sài Gòn VRG"),
    "PHR": ArchetypeProfile(EconomicArchetype.RUBBER_PLANTATION, [ArchetypeOverlay.PROJECT_BASED], 0.30, "SOTP", reason="Cao su Phước Hòa - SOTP cao su và KCN"),
    "DPR": ArchetypeProfile(EconomicArchetype.RUBBER_PLANTATION, [ArchetypeOverlay.PROJECT_BASED], 0.30, "SOTP", reason="Cao su Đồng Phú - SOTP cao su và KCN"),

    # 7. Rubber Plantation & Conglomerate
    "GVR": ArchetypeProfile(EconomicArchetype.RUBBER_PLANTATION, [ArchetypeOverlay.STATE_INFLUENCED, ArchetypeOverlay.PROJECT_BASED], 0.35, "SOTP", reason="Tập đoàn Cao su Việt Nam - SOTP: Vườn cây cao su + Quỹ đất chuyển đổi KCN lớn nhất nước"),
    "VIC": ArchetypeProfile(EconomicArchetype.CONGLOMERATE, [ArchetypeOverlay.CAPITAL_INTENSIVE, ArchetypeOverlay.HIGH_LEVERAGE], 0.50, "SOTP", reason="Tập đoàn Vingroup"),
    "VEA": ArchetypeProfile(EconomicArchetype.HOLDING_COMPANY, [ArchetypeOverlay.STATE_INFLUENCED, ArchetypeOverlay.MATURE_COMPOUNDER], 0.25, "SOTP", reason="VEAM - Tổng Công ty Máy động lực & Máy nông nghiệp: SOTP 3 liên doanh ô tô - xe máy (Toyota 30%, Honda 20%, Ford 25%) và quỹ tiền mặt ròng"),
    "VHM": ArchetypeProfile(EconomicArchetype.REAL_ESTATE_DEVELOPER, [ArchetypeOverlay.CAPITAL_INTENSIVE, ArchetypeOverlay.HIGH_CYCLICALITY], 0.40, "RNAV", reason="Vinhomes - BĐS Dân dụng quy mô lớn"),
    "NVL": ArchetypeProfile(EconomicArchetype.REAL_ESTATE_DEVELOPER, [ArchetypeOverlay.HIGH_LEVERAGE, ArchetypeOverlay.TURNAROUND], 0.50, "RNAV"),
    "KDH": ArchetypeProfile(EconomicArchetype.REAL_ESTATE_DEVELOPER, [], 0.35, "RNAV"),

    # 8. Ports, Logistics, Aviation & Pharma
    "GMD": ArchetypeProfile(EconomicArchetype.PORT_INFRASTRUCTURE, [ArchetypeOverlay.CAPITAL_INTENSIVE, ArchetypeOverlay.CONCESSION], 0.25, "CONCESSION_DCF", reason="Gemadept - Cảng biển & Logistics"),
    "HAH": ArchetypeProfile(EconomicArchetype.SHIPPING, [ArchetypeOverlay.HIGH_CYCLICALITY, ArchetypeOverlay.CAPITAL_INTENSIVE], 0.40, "FLEET_NAV", reason="Hải An - Vận tải biển"),
    "VOS": ArchetypeProfile(EconomicArchetype.SHIPPING, [ArchetypeOverlay.HIGH_CYCLICALITY, ArchetypeOverlay.CAPITAL_INTENSIVE], 0.40, "FLEET_NAV", reason="Vinaship - Vận tải biển"),
    "VJC": ArchetypeProfile(EconomicArchetype.AIRLINE, [ArchetypeOverlay.CAPITAL_INTENSIVE, ArchetypeOverlay.HIGH_LEVERAGE], 0.45, "AIRLINE_EBITDAR", reason="Vietjet Air - Hàng không chi phí thấp"),
    "HVN": ArchetypeProfile(EconomicArchetype.AIRLINE, [ArchetypeOverlay.STATE_INFLUENCED, ArchetypeOverlay.TURNAROUND], 0.50, "AIRLINE_EBITDAR", reason="Vietnam Airlines - Hàng không quốc gia"),
    "DHG": ArchetypeProfile(EconomicArchetype.PHARMACEUTICAL, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER], 0.20, "NORMALIZED_OWNER_EARNINGS_DCF", reason="Dược Hậu Giang"),
    "TRA": ArchetypeProfile(EconomicArchetype.PHARMACEUTICAL, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER], 0.25, "NORMALIZED_OWNER_EARNINGS_DCF"),

    # 9. Previously GENERIC_ENTERPRISE symbols (68-symbol audit set, task 058)
    "ACV": ArchetypeProfile(EconomicArchetype.AIRPORT_INFRASTRUCTURE, [ArchetypeOverlay.REGULATED, ArchetypeOverlay.CONCESSION, ArchetypeOverlay.STATE_INFLUENCED], 0.25, "CONCESSION_DCF", reason="Tổng Công ty Cảng Hàng không Việt Nam - phí sân bay có quản lý nhà nước"),
    "BCC": ArchetypeProfile(EconomicArchetype.BUILDING_MATERIALS, [ArchetypeOverlay.HIGH_CYCLICALITY, ArchetypeOverlay.COMMODITY_EXPOSED], 0.35, "NORMALIZED_OWNER_EARNINGS_DCF", reason="Xi măng Bỉm Sơn - vật liệu xây dựng chu kỳ"),
    "BSR": ArchetypeProfile(EconomicArchetype.OIL_REFINING_DOWNSTREAM, [ArchetypeOverlay.HIGH_CYCLICALITY, ArchetypeOverlay.COMMODITY_EXPOSED], 0.35, "NORMALIZED_OWNER_EARNINGS_DCF", reason="Lọc hóa dầu Dung Quất - nhà máy lọc dầu"),
    "CII": ArchetypeProfile(EconomicArchetype.CONCESSION_INFRASTRUCTURE, [ArchetypeOverlay.CONCESSION, ArchetypeOverlay.PROJECT_BASED], 0.30, "CONCESSION_DCF", reason="CII - đầu tư hạ tầng BOT giao thông & nước"),
    "CTD": ArchetypeProfile(EconomicArchetype.CONSTRUCTION_EPC, [ArchetypeOverlay.PROJECT_BASED], 0.35, "NORMALIZED_OWNER_EARNINGS_DCF", reason="Coteccons - nhà thầu xây dựng"),
    "FCN": ArchetypeProfile(EconomicArchetype.CONSTRUCTION_EPC, [ArchetypeOverlay.PROJECT_BASED], 0.35, "NORMALIZED_OWNER_EARNINGS_DCF", reason="Fecon - nhà thầu hạ tầng & năng lượng"),
    "HAG": ArchetypeProfile(EconomicArchetype.AGRICULTURE, [ArchetypeOverlay.HIGH_CYCLICALITY], 0.35, "NORMALIZED_OWNER_EARNINGS_DCF", reason="HAGL Agrico - nông nghiệp"),
    "HHV": ArchetypeProfile(EconomicArchetype.CONCESSION_INFRASTRUCTURE, [ArchetypeOverlay.CONCESSION, ArchetypeOverlay.CAPITAL_INTENSIVE], 0.30, "CONCESSION_DCF", reason="Đèo Cả - hạ tầng giao thông BOT"),
    "HT1": ArchetypeProfile(EconomicArchetype.BUILDING_MATERIALS, [ArchetypeOverlay.HIGH_CYCLICALITY, ArchetypeOverlay.COMMODITY_EXPOSED], 0.35, "NORMALIZED_OWNER_EARNINGS_DCF", reason="Xi măng Hà Tiên - vật liệu xây dựng chu kỳ"),
    # 10. Power / water / BOT split (audit round 3) — separate economics, do not
    #     lump thermal/hydro/water/renewable/BOT under one concession archetype.
    "PPC": ArchetypeProfile(EconomicArchetype.POWER_GENERATION_THERMAL, [ArchetypeOverlay.CAPITAL_INTENSIVE, ArchetypeOverlay.REGULATED], 0.25, "CONCESSION_DCF", reason="Phả Lại - nhiệt điện than, PPA + fuel pass-through"),
    "NT2": ArchetypeProfile(EconomicArchetype.POWER_GENERATION_THERMAL, [ArchetypeOverlay.CAPITAL_INTENSIVE, ArchetypeOverlay.REGULATED], 0.25, "CONCESSION_DCF", reason="Nhiệt điện Ninh Bình - nhiệt điện"),
    "VSH": ArchetypeProfile(EconomicArchetype.POWER_GENERATION_HYDRO, [ArchetypeOverlay.REGULATED, ArchetypeOverlay.CONCESSION], 0.25, "CONCESSION_DCF", reason="Thủy điện Vĩnh Sơn - Sông Hinh, hydrology 5-10Y"),
    "CHP": ArchetypeProfile(EconomicArchetype.POWER_GENERATION_HYDRO, [ArchetypeOverlay.REGULATED, ArchetypeOverlay.CONCESSION], 0.25, "CONCESSION_DCF", reason="Thủy điện Trị An - hydrology 5-10Y"),
    "BWE": ArchetypeProfile(EconomicArchetype.WATER_UTILITY, [ArchetypeOverlay.REGULATED, ArchetypeOverlay.CONCESSION], 0.20, "CONCESSION_DCF", reason="Biwase - cấp nước + môi trường, tariff & volume"),
    "TDM": ArchetypeProfile(EconomicArchetype.WATER_UTILITY, [ArchetypeOverlay.REGULATED, ArchetypeOverlay.CONCESSION], 0.20, "CONCESSION_DCF", reason="Thủ Dầu Một - cấp nước, tariff & volume"),
    "GEG": ArchetypeProfile(EconomicArchetype.POWER_RENEWABLE, [ArchetypeOverlay.PROJECT_BASED, ArchetypeOverlay.REGULATED], 0.30, "CONCESSION_DCF", reason="Gia Lai Electricity - điện gió, PPA + capacity factor"),
    "KSV": ArchetypeProfile(EconomicArchetype.MINING_RESOURCE, [ArchetypeOverlay.COMMODITY_EXPOSED, ArchetypeOverlay.CAPITAL_INTENSIVE], 0.40, "RESERVE_NAV", reason="Khoáng sản TKV - khai khoáng, cần NAV trữ lượng"),
    "MSH": ArchetypeProfile(EconomicArchetype.EXPORT_MANUFACTURING, [ArchetypeOverlay.EXPORT_ORIENTED], 0.30, "NORMALIZED_OWNER_EARNINGS_DCF", reason="May Sông Hồng - gia công dệt may xuất khẩu"),
    "MSR": ArchetypeProfile(EconomicArchetype.MINING_RESOURCE, [ArchetypeOverlay.COMMODITY_EXPOSED, ArchetypeOverlay.CAPITAL_INTENSIVE], 0.40, "RESERVE_NAV", reason="Masan High-Tech Materials - vonfram, cần NAV trữ lượng"),
    "PC1": ArchetypeProfile(EconomicArchetype.POWER_RENEWABLE, [ArchetypeOverlay.PROJECT_BASED, ArchetypeOverlay.CAPITAL_INTENSIVE], 0.30, "CONCESSION_DCF", reason="PC1 Group - điện tái tạo & xây lắp điện"),
    "TCM": ArchetypeProfile(EconomicArchetype.EXPORT_MANUFACTURING, [ArchetypeOverlay.EXPORT_ORIENTED], 0.30, "NORMALIZED_OWNER_EARNINGS_DCF", reason="Dệt may Thành Công - gia công xuất khẩu"),
    "TNH": ArchetypeProfile(EconomicArchetype.PHARMACEUTICAL, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER], 0.25, "NORMALIZED_OWNER_EARNINGS_DCF", reason="Dược phẩm"),
    "VGI": ArchetypeProfile(EconomicArchetype.TELECOM_OPERATOR, [ArchetypeOverlay.STATE_INFLUENCED, ArchetypeOverlay.EARLY_GROWTH], 0.25, "NORMALIZED_OWNER_EARNINGS_DCF", reason="Viettel Global - viễn thông quốc tế"),
}


class ArchetypeClassifier:
    """Classifies any Vietnamese stock into its economic archetype with conflict gate."""

    @classmethod
    def classify(cls, symbol: str, sector_text: str = "", company_type: str = "") -> ArchetypeProfile:
        sym = str(symbol).upper().strip()
        if sym in EXPLICIT_SYMBOL_ARCHETYPES:
            prof = EXPLICIT_SYMBOL_ARCHETYPES[sym]
            prof.raw_provider_sector = sector_text or "Doanh nghiệp niêm yết"
            return prof

        combined = f"{sym} {sector_text} {company_type}".lower()

        # 1. Financials
        if any(w in combined for w in ("ngân hàng", "bank")):
            return ArchetypeProfile(EconomicArchetype.COMMERCIAL_BANK, [ArchetypeOverlay.REGULATED], 0.25, "RESIDUAL_INCOME_MODEL", raw_provider_sector=sector_text)
        if any(w in combined for w in ("chứng khoán", "securities")):
            return ArchetypeProfile(EconomicArchetype.SECURITIES_BROKER, [ArchetypeOverlay.HIGH_CYCLICALITY], 0.30, "RESIDUAL_INCOME_MODEL", raw_provider_sector=sector_text)
        if any(w in combined for w in ("bảo hiểm", "insurance")):
            return ArchetypeProfile(EconomicArchetype.NON_LIFE_INSURANCE, [ArchetypeOverlay.REGULATED], 0.25, "RESIDUAL_INCOME_MODEL", raw_provider_sector=sector_text)

        # 2. Industrial Real Estate (KCN) vs Residential Real Estate
        if any(w in combined for w in ("kcn", "khu công nghiệp", "industrial park", "industrial real estate", "idico", "becamex", "sonadezi", "nam tân uyên", "kinh bắc", "vrg")):
            return ArchetypeProfile(EconomicArchetype.INDUSTRIAL_REAL_ESTATE, [ArchetypeOverlay.PROJECT_BASED, ArchetypeOverlay.CONCESSION], 0.25, "LEASE_CASHFLOW_DCF", raw_provider_sector=sector_text)
        if any(w in combined for w in ("bất động sản", "real estate", "địa ốc", "bđs")):
            return ArchetypeProfile(EconomicArchetype.REAL_ESTATE_DEVELOPER, [ArchetypeOverlay.PROJECT_BASED, ArchetypeOverlay.HIGH_CYCLICALITY], 0.40, "RNAV", raw_provider_sector=sector_text)

        # 3. Materials, Energy & Utilities
        if any(w in combined for w in ("thép", "steel", "kim loại", "metal")):
            return ArchetypeProfile(EconomicArchetype.BASIC_MATERIALS_METALS, [ArchetypeOverlay.CAPITAL_INTENSIVE, ArchetypeOverlay.HIGH_CYCLICALITY, ArchetypeOverlay.COMMODITY_EXPOSED], 0.40, "NORMALIZED_OWNER_EARNINGS_DCF", raw_provider_sector=sector_text)
        if any(w in combined for w in ("phân bón", "fertilizer", "hóa chất", "chemical")):
            return ArchetypeProfile(EconomicArchetype.COMMODITY_CHEMICAL, [ArchetypeOverlay.HIGH_CYCLICALITY, ArchetypeOverlay.COMMODITY_EXPOSED], 0.40, "NORMALIZED_OWNER_EARNINGS_DCF", raw_provider_sector=sector_text)
        if any(w in combined for w in ("khí", "gas infrastructure", "đường ống")):
            return ArchetypeProfile(EconomicArchetype.ENERGY_INFRASTRUCTURE, [ArchetypeOverlay.REGULATED, ArchetypeOverlay.CONCESSION], 0.25, "CONCESSION_DCF", raw_provider_sector=sector_text)
        if any(w in combined for w in ("thủy điện", "hydropower")):
            return ArchetypeProfile(EconomicArchetype.POWER_GENERATION_HYDRO, [ArchetypeOverlay.REGULATED, ArchetypeOverlay.CONCESSION], 0.25, "CONCESSION_DCF", raw_provider_sector=sector_text)
        if any(w in combined for w in ("nhiệt điện", "thermal power")):
            return ArchetypeProfile(EconomicArchetype.POWER_GENERATION_THERMAL, [ArchetypeOverlay.CAPITAL_INTENSIVE, ArchetypeOverlay.REGULATED], 0.25, "CONCESSION_DCF", raw_provider_sector=sector_text)
        if any(w in combined for w in ("điện gió", "điện mặt trời", "wind", "solar", "năng lượng tái tạo", "renewable")):
            return ArchetypeProfile(EconomicArchetype.POWER_RENEWABLE, [ArchetypeOverlay.PROJECT_BASED, ArchetypeOverlay.REGULATED], 0.30, "CONCESSION_DCF", raw_provider_sector=sector_text)
        if any(w in combined for w in ("cấp nước", "nước sạch", "thoát nước", "water utility", "nước")):
            return ArchetypeProfile(EconomicArchetype.WATER_UTILITY, [ArchetypeOverlay.REGULATED, ArchetypeOverlay.CONCESSION], 0.20, "CONCESSION_DCF", raw_provider_sector=sector_text)
        if any(w in combined for w in ("điện", "tiện ích", "năng lượng", "power", "utility")):
            return ArchetypeProfile(EconomicArchetype.CONCESSION_INFRASTRUCTURE, [ArchetypeOverlay.REGULATED, ArchetypeOverlay.CONCESSION], 0.25, "CONCESSION_DCF", raw_provider_sector=sector_text)

        # 4. Tech & Consumer
        if any(w in combined for w in ("công nghệ", "phần mềm", "it services", "software")):
            return ArchetypeProfile(EconomicArchetype.TECHNOLOGY_SERVICES, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER], 0.20, "NORMALIZED_OWNER_EARNINGS_DCF", raw_provider_sector=sector_text)
        if any(w in combined for w in ("thực phẩm", "đồ uống", "f&b", "sữa", "tiêu dùng", "consumer staples")):
            return ArchetypeProfile(EconomicArchetype.CONSUMER_STAPLES, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER], 0.20, "NORMALIZED_OWNER_EARNINGS_DCF", raw_provider_sector=sector_text)
        if any(w in combined for w in ("bán lẻ", "retail")):
            return ArchetypeProfile(EconomicArchetype.RETAIL_CHAIN, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER], 0.25, "NORMALIZED_OWNER_EARNINGS_DCF", raw_provider_sector=sector_text)
        if any(w in combined for w in ("dược", "thuốc", "y tế", "pharma", "healthcare")):
            return ArchetypeProfile(EconomicArchetype.PHARMACEUTICAL, [ArchetypeOverlay.ASSET_LIGHT_COMPOUNDER], 0.20, "NORMALIZED_OWNER_EARNINGS_DCF", raw_provider_sector=sector_text)

        # 5. Logistics, Ports & Aviation
        if any(w in combined for w in ("cảng", "port")):
            return ArchetypeProfile(EconomicArchetype.PORT_INFRASTRUCTURE, [ArchetypeOverlay.CAPITAL_INTENSIVE, ArchetypeOverlay.CONCESSION], 0.25, "CONCESSION_DCF", raw_provider_sector=sector_text)
        if any(w in combined for w in ("vận tải biển", "shipping")):
            return ArchetypeProfile(EconomicArchetype.SHIPPING, [ArchetypeOverlay.HIGH_CYCLICALITY, ArchetypeOverlay.CAPITAL_INTENSIVE], 0.40, "FLEET_NAV", raw_provider_sector=sector_text)
        if any(w in combined for w in ("hàng không", "airline", "aviation")):
            return ArchetypeProfile(EconomicArchetype.AIRLINE, [ArchetypeOverlay.CAPITAL_INTENSIVE, ArchetypeOverlay.HIGH_LEVERAGE], 0.45, "AIRLINE_EBITDAR", raw_provider_sector=sector_text)
        if any(w in combined for w in ("logistics", "kho bãi")):
            return ArchetypeProfile(EconomicArchetype.LOGISTICS_SERVICES, [], 0.25, "NORMALIZED_OWNER_EARNINGS_DCF", raw_provider_sector=sector_text)

        # 6. Agriculture & Plantation
        if any(w in combined for w in ("cao su", "rubber", "mủ")):
            return ArchetypeProfile(EconomicArchetype.RUBBER_PLANTATION, [ArchetypeOverlay.PROJECT_BASED], 0.35, "LEASE_CASHFLOW_DCF", raw_provider_sector=sector_text)
        if any(w in combined for w in ("thủy sản", "tôm", "cá tra", "seafood", "aquaculture")):
            return ArchetypeProfile(EconomicArchetype.AQUACULTURE_EXPORT, [ArchetypeOverlay.HIGH_CYCLICALITY, ArchetypeOverlay.EXPORT_ORIENTED], 0.35, "NORMALIZED_OWNER_EARNINGS_DCF", raw_provider_sector=sector_text)

        # Uncertain classification: prefer ARCHETYPE_UNKNOWN over a silent generic DCF +
        # MODEL_VERIFIED (audit 68-symbol). GENERIC_ENTERPRISE is reserved for companies
        # that are explicitly known to be generic (see EXPLICIT_SYMBOL_ARCHETYPES).
        return ArchetypeProfile(
            EconomicArchetype.ARCHETYPE_UNKNOWN,
            [],
            0.30,
            "NORMALIZED_OWNER_EARNINGS_DCF",
            raw_provider_sector=sector_text,
            classification_confidence="LOW",
            reason="Không đủ bằng chứng phân loại ngành nghề kinh doanh để chọn mô hình định giá đặc thù.",
        )
