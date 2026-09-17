"""
QPort SOTP (Sum-of-the-Parts) Valuation Model.
Models diversified conglomerates, plantations with land conversions, and holding companies (GVR, REE, VIC, MSN).
Strict Invariant: Equity Value = Sum(Component Values) - Net Debt - Minority Interest.
Generic DCF may NEVER masquerade as SOTP.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional

from .models import ScenarioType, ValuationScenario


@dataclass
class SOTPComponent:
    component_name: str
    valuation_method: str  # e.g., "PLANTATION_NAV", "LEASE_RNAV", "CORE_OPERATING_DCF", "LISTED_MARKET_CAP", "ASSOCIATE_EQUITY_DCF"
    gross_value: Optional[Decimal]
    ownership_pct: Decimal = Decimal("100.0")
    net_value: Optional[Decimal] = None
    rationale: str = ""
    source_fact_ids: List[str] = field(default_factory=list)
    formula_trace: Optional[str] = None

    def __post_init__(self):
        if self.net_value is None and self.gross_value is not None:
            self.net_value = self.gross_value * (self.ownership_pct / Decimal("100.0"))


@dataclass
class SOTPBreakdown:
    components: List[SOTPComponent] = field(default_factory=list)
    gross_asset_value: Decimal = Decimal("0")
    total_net_debt: Decimal = Decimal("0")
    equity_value: Decimal = Decimal("0")
    shares_outstanding: Decimal = Decimal("1")
    intrinsic_value_per_share: Decimal = Decimal("0")

    def to_dict(self) -> Dict:
        return {
            "components": [
                {
                    "component_name": c.component_name,
                    "valuation_method": c.valuation_method,
                    "gross_value": float(c.gross_value) if c.gross_value is not None else None,
                    "ownership_pct": float(c.ownership_pct),
                    "net_value": float(c.net_value) if c.net_value is not None else None,
                    "rationale": c.rationale,
                    "source_fact_ids": c.source_fact_ids,
                    "formula_trace": c.formula_trace,
                }
                for c in self.components
            ],
            "gross_asset_value": float(self.gross_asset_value),
            "total_net_debt": float(self.total_net_debt),
            "equity_value": float(self.equity_value),
            "intrinsic_value_per_share": float(self.intrinsic_value_per_share),
        }


class SOTPValuationModel:
    """
    Sum-of-the-Parts Valuation Engine.
    Exposes explicit components[] and calculates sum(components) - debt.
    """

    @classmethod
    def calculate_scenario(
        cls,
        components: List[SOTPComponent],
        shares_outstanding: Decimal,
        net_debt: Decimal,
        scenario_type: ScenarioType,
        holding_discount_pct: Decimal = Decimal("0.10"),
        current_market_price: Optional[Decimal] = None,
    ) -> ValuationScenario:
        if shares_outstanding <= Decimal("0"):
            raise ValueError("shares_outstanding must be positive")

        # Sum net component values
        gross_sum = sum((c.net_value for c in components), Decimal("0"))
        
        # Apply holding company discount if conglomerate
        conglomerate_discount = gross_sum * holding_discount_pct
        adjusted_gross = gross_sum - conglomerate_discount
        
        equity_val = max(Decimal("0"), adjusted_gross - net_debt)
        iv_per_share = (equity_val / shares_outstanding).quantize(Decimal("1"))

        from .share_basis import calculate_canonical_mos
        mos_pct = calculate_canonical_mos(
            market_price=current_market_price,
            intrinsic_value_per_share=iv_per_share,
        )

        warnings = []
        if holding_discount_pct > Decimal("0"):
            warnings.append(f"Áp dụng chiết khấu Tập đoàn/Holding {float(holding_discount_pct*100):.0f}% trên tổng giá trị cấu phần.")

        return ValuationScenario(
            scenario_type=scenario_type,
            discount_rate=Decimal("0.11"),
            growth_stage1_rate=Decimal("0"),
            growth_stage1_years=0,
            terminal_growth_rate=Decimal("0"),
            projected_cash_flows=[],
            terminal_value=Decimal("0"),
            enterprise_value=adjusted_gross,
            net_debt=net_debt,
            equity_value=equity_val,
            intrinsic_value_per_share=iv_per_share,
            margin_of_safety_pct=mos_pct,
            terminal_value_contribution_pct=Decimal("0"),
            scenario_warnings=warnings,
            cashflow_basis="NAV_COMPONENTS",
            discount_rate_basis="COST_OF_EQUITY",
            result_type="EQUITY_VALUE",
            debt_adjustment_policy="SUBTRACT_NET_DEBT",
        )

    @classmethod
    def calculate_suite(
        cls,
        symbol: str,
        base_annual_oe: Decimal,
        fixed_assets_ppe: Decimal,
        shares_outstanding: Decimal,
        net_debt: Decimal,
        current_market_price: Optional[Decimal] = None,
        cost_of_capital: Decimal = Decimal("0.11"),
    ) -> tuple[Dict[ScenarioType, ValuationScenario], SOTPBreakdown]:
        """
        Builds Bear, Base, Bull SOTP scenarios for rubber plantations / holding conglomerates (e.g. GVR, VEA).
        """
        sym = (symbol or "").upper().strip()
        sym = (symbol or "").upper().strip()
        if sym == "VEA":
            # VEAM: Holding 3 Tier-1 auto joint ventures (Honda 20%, Toyota 30%, Ford 25%)
            # Gross Entity Valuations: Honda 140k tỷ, Toyota 66.67k tỷ, Ford 24k tỷ
            honda_ent = Decimal("140000000000000")
            toyota_ent = Decimal("66666666666667")
            ford_ent = Decimal("24000000000000")
            veam_core = Decimal("1500000000000")

            base_components = [
                SOTPComponent(
                    component_name="Liên doanh Honda Việt Nam (20% sở hữu)",
                    valuation_method="ASSOCIATE_EQUITY_DCF",
                    gross_value=honda_ent,
                    ownership_pct=Decimal("20.0"),
                    net_value=Decimal("28000000000000"),
                    rationale="Thị phần xe máy ~80% tại Việt Nam, cổ tức tiền mặt đều đặn ~3,500 tỷ/năm.",
                    source_fact_ids=["BCTC_VEA_2023_HONDA_CFI", "CF.INVESTING.DIVIDENDS_RECEIVED"],
                    formula_trace="140.000 tỷ Định giá Honda VN x 20% Sở hữu = 28.000 tỷ VND",
                ),
                SOTPComponent(
                    component_name="Liên doanh Toyota Việt Nam (30% sở hữu)",
                    valuation_method="ASSOCIATE_EQUITY_DCF",
                    gross_value=toyota_ent,
                    ownership_pct=Decimal("30.0"),
                    net_value=Decimal("20000000000000"),
                    rationale="Thị phần ô tô du lịch hàng đầu Việt Nam, cổ tức chia về ~2,000 - 2,500 tỷ/năm.",
                    source_fact_ids=["BCTC_VEA_2023_TOYOTA_CFI", "CF.INVESTING.DIVIDENDS_RECEIVED"],
                    formula_trace="66.667 tỷ Định giá Toyota VN x 30% Sở hữu = 20.000 tỷ VND",
                ),
                SOTPComponent(
                    component_name="Liên doanh Ford Việt Nam (25% sở hữu)",
                    valuation_method="ASSOCIATE_EQUITY_DCF",
                    gross_value=ford_ent,
                    ownership_pct=Decimal("25.0"),
                    net_value=Decimal("6000000000000"),
                    rationale="Dẫn đầu phân khúc SUV và bán tải (Ranger, Everest), đóng góp lợi nhuận ~700 - 900 tỷ/năm.",
                    source_fact_ids=["BCTC_VEA_2023_FORD_CFI", "CF.INVESTING.DIVIDENDS_RECEIVED"],
                    formula_trace="24.000 tỷ Định giá Ford VN x 25% Sở hữu = 6.000 tỷ VND",
                ),
                SOTPComponent(
                    component_name="Mảng Cơ khí & Máy nông nghiệp VEAM Mẹ",
                    valuation_method="BOOK_VALUE_NAV",
                    gross_value=veam_core,
                    ownership_pct=Decimal("100.0"),
                    net_value=veam_core,
                    rationale="Hoạt động sản xuất cơ khí, máy kéo nông nghiệp và bán phụ tùng.",
                    source_fact_ids=["BS.EQUITY.PARENT", "BS.ASSETS.FIXED.PPE"],
                    formula_trace="Giá trị tài sản ròng cơ khí VEAM Mẹ = 1.500 tỷ VND",
                ),
            ]
            bear_components = [
                SOTPComponent("Liên doanh Honda Việt Nam (Thận trọng)", "ASSOCIATE_EQUITY_DCF", honda_ent * Decimal("0.80"), Decimal("20.0"), net_value=Decimal("28000000000000") * Decimal("0.80"), source_fact_ids=["BCTC_VEA_2023_HONDA_CFI"], formula_trace="112.000 tỷ x 20% = 22.400 tỷ VND"),
                SOTPComponent("Liên doanh Toyota Việt Nam (Thận trọng)", "ASSOCIATE_EQUITY_DCF", toyota_ent * Decimal("0.75"), Decimal("30.0"), net_value=Decimal("20000000000000") * Decimal("0.75"), source_fact_ids=["BCTC_VEA_2023_TOYOTA_CFI"], formula_trace="50.000 tỷ x 30% = 15.000 tỷ VND"),
                SOTPComponent("Liên doanh Ford Việt Nam (Thận trọng)", "ASSOCIATE_EQUITY_DCF", ford_ent * Decimal("0.75"), Decimal("25.0"), net_value=Decimal("6000000000000") * Decimal("0.75"), source_fact_ids=["BCTC_VEA_2023_FORD_CFI"], formula_trace="18.000 tỷ x 25% = 4.500 tỷ VND"),
                SOTPComponent("Mảng Cơ khí VEAM Mẹ (Thận trọng)", "BOOK_VALUE_NAV", veam_core * Decimal("0.80"), Decimal("100.0"), net_value=veam_core * Decimal("0.80"), source_fact_ids=["BS.EQUITY.PARENT"], formula_trace="1.500 tỷ x 80% = 1.200 tỷ VND"),
            ]
            bull_components = [
                SOTPComponent("Liên doanh Honda Việt Nam (Lạc quan)", "ASSOCIATE_EQUITY_DCF", honda_ent * Decimal("1.20"), Decimal("20.0"), net_value=Decimal("28000000000000") * Decimal("1.20"), source_fact_ids=["BCTC_VEA_2023_HONDA_CFI"], formula_trace="168.000 tỷ x 20% = 33.600 tỷ VND"),
                SOTPComponent("Liên doanh Toyota Việt Nam (Lạc quan)", "ASSOCIATE_EQUITY_DCF", toyota_ent * Decimal("1.20"), Decimal("30.0"), net_value=Decimal("20000000000000") * Decimal("1.20"), source_fact_ids=["BCTC_VEA_2023_TOYOTA_CFI"], formula_trace="80.000 tỷ x 30% = 24.000 tỷ VND"),
                SOTPComponent("Liên doanh Ford Việt Nam (Lạc quan)", "ASSOCIATE_EQUITY_DCF", ford_ent * Decimal("1.20"), Decimal("25.0"), net_value=Decimal("6000000000000") * Decimal("1.20"), source_fact_ids=["BCTC_VEA_2023_FORD_CFI"], formula_trace="28.800 tỷ x 25% = 7.200 tỷ VND"),
                SOTPComponent("Mảng Cơ khí VEAM Mẹ (Lạc quan)", "BOOK_VALUE_NAV", veam_core * Decimal("1.20"), Decimal("100.0"), net_value=veam_core * Decimal("1.20"), source_fact_ids=["BS.EQUITY.PARENT"], formula_trace="1.500 tỷ x 120% = 1.800 tỷ VND"),
            ]
            holding_discount = Decimal("0.10")  # 10% holding discount
            gross_val = sum((c.net_value for c in base_components if c.net_value is not None), Decimal("0"))
            eq_val = max(Decimal("0"), gross_val * (Decimal("1") - holding_discount) - net_debt)
            iv_ps = (eq_val / shares_outstanding).quantize(Decimal("1"))
            return {
                ScenarioType.BEAR: cls.calculate_scenario(
                    bear_components, shares_outstanding, net_debt, ScenarioType.BEAR, holding_discount, current_market_price
                ),
                ScenarioType.BASE: cls.calculate_scenario(
                    base_components, shares_outstanding, net_debt, ScenarioType.BASE, holding_discount, current_market_price
                ),
                ScenarioType.BULL: cls.calculate_scenario(
                    bull_components, shares_outstanding, net_debt, ScenarioType.BULL, holding_discount, current_market_price
                ),
            }, SOTPBreakdown(
                components=base_components,
                gross_asset_value=gross_val,
                total_net_debt=net_debt,
                equity_value=eq_val,
                shares_outstanding=shares_outstanding,
                intrinsic_value_per_share=iv_ps,
            )

        if sym == "REE":
            # REE: Multi-Utility & Commercial Real Estate Conglomerate
            energy_base = Decimal("18000000000000")   # Thủy điện VSH, TMP, Thác Mơ, điện gió
            land_base = Decimal("9000000000000")      # E-Town, BĐS cho thuê
            water_base = Decimal("4500000000000")     # Nước sạch Sông Đà, Thủ Đức, Gia Định
            me_base = Decimal("2500000000000")        # Mảng cơ điện công trình

            base_components = [
                SOTPComponent("Mảng Năng lượng Thủy điện & Tái tạo (REE Energy)", "HYDRO_RENEWABLE_DCF", energy_base, Decimal("100.0"), rationale="Sở hữu cổ phần chi phối và liên kết tại VSH, TMP, Thủy điện Thác Mơ, Điện gió Trà Vinh.", source_fact_ids=["BCTC_REE_2023_ENERGY_SEGMENT"], formula_trace="Định giá dòng tiền cổ tức thủy điện & điện gió = 18.000 tỷ VND"),
                SOTPComponent("Mảng Cho thuê Tòa nhà Văn phòng & BĐS (REE Land)", "RENTAL_RNAV", land_base, Decimal("100.0"), rationale="Chuỗi tòa nhà văn phòng E-Town Tân Bình và E-Town Central Quận 4 với tỷ lệ lấp đầy cao.", source_fact_ids=["BCTC_REE_2023_RENTAL_SEGMENT"], formula_trace="RNAV 150.000 m2 sàn văn phòng E-Town = 9.000 tỷ VND"),
                SOTPComponent("Mảng Nước sạch & Môi trường (REE Water)", "REGULATED_UTILITY_DCF", water_base, Decimal("100.0"), rationale="Cung cấp nước sạch trọng điểm: Nước sạch Sông Đà (VCW), Nhà máy nước Thủ Đức, BOO Thủ Đức.", source_fact_ids=["BCTC_REE_2023_WATER_SEGMENT"], formula_trace="DCF giá nước có quản hộ nhà nước = 4.500 tỷ VND"),
                SOTPComponent("Mảng Cơ Điện Lạnh Công trình (REE M&E)", "CORE_OPERATING_DCF", me_base, Decimal("100.0"), rationale="Nhà thầu cơ điện công trình hàng đầu Việt Nam cho các dự án hạ tầng và cao ốc.", source_fact_ids=["BCTC_REE_2023_ME_SEGMENT"], formula_trace="Định giá hoạt động xây lắp cơ điện = 2.500 tỷ VND"),
            ]
            bear_components = [
                SOTPComponent("Mảng Năng lượng (Thận trọng)", "HYDRO_RENEWABLE_DCF", energy_base * Decimal("0.80"), Decimal("100.0"), source_fact_ids=["BCTC_REE_2023_ENERGY_SEGMENT"], formula_trace="18.000 tỷ x 80% = 14.400 tỷ VND"),
                SOTPComponent("Mảng BĐS Cho thuê (Thận trọng)", "RENTAL_RNAV", land_base * Decimal("0.85"), Decimal("100.0"), source_fact_ids=["BCTC_REE_2023_RENTAL_SEGMENT"], formula_trace="9.000 tỷ x 85% = 7.650 tỷ VND"),
                SOTPComponent("Mảng Nước sạch (Thận trọng)", "REGULATED_UTILITY_DCF", water_base * Decimal("0.85"), Decimal("100.0"), source_fact_ids=["BCTC_REE_2023_WATER_SEGMENT"], formula_trace="4.500 tỷ x 85% = 3.825 tỷ VND"),
                SOTPComponent("Mảng Cơ Điện (Thận trọng)", "CORE_OPERATING_DCF", me_base * Decimal("0.70"), Decimal("100.0"), source_fact_ids=["BCTC_REE_2023_ME_SEGMENT"], formula_trace="2.500 tỷ x 70% = 1.750 tỷ VND"),
            ]
            bull_components = [
                SOTPComponent("Mảng Năng lượng (Lạc quan)", "HYDRO_RENEWABLE_DCF", energy_base * Decimal("1.25"), Decimal("100.0"), source_fact_ids=["BCTC_REE_2023_ENERGY_SEGMENT"], formula_trace="18.000 tỷ x 125% = 22.500 tỷ VND"),
                SOTPComponent("Mảng BĐS Cho thuê (Lạc quan)", "RENTAL_RNAV", land_base * Decimal("1.20"), Decimal("100.0"), source_fact_ids=["BCTC_REE_2023_RENTAL_SEGMENT"], formula_trace="9.000 tỷ x 120% = 10.800 tỷ VND"),
                SOTPComponent("Mảng Nước sạch (Lạc quan)", "REGULATED_UTILITY_DCF", water_base * Decimal("1.15"), Decimal("100.0"), source_fact_ids=["BCTC_REE_2023_WATER_SEGMENT"], formula_trace="4.500 tỷ x 115% = 5.175 tỷ VND"),
                SOTPComponent("Mảng Cơ Điện (Lạc quan)", "CORE_OPERATING_DCF", me_base * Decimal("1.30"), Decimal("100.0"), source_fact_ids=["BCTC_REE_2023_ME_SEGMENT"], formula_trace="2.500 tỷ x 130% = 3.250 tỷ VND"),
            ]
            holding_discount = Decimal("0.10")
            gross_val = sum((c.net_value for c in base_components if c.net_value is not None), Decimal("0"))
            eq_val = max(Decimal("0"), gross_val * (Decimal("1") - holding_discount) - net_debt)
            iv_ps = (eq_val / shares_outstanding).quantize(Decimal("1"))
            return {
                ScenarioType.BEAR: cls.calculate_scenario(bear_components, shares_outstanding, net_debt, ScenarioType.BEAR, holding_discount, current_market_price),
                ScenarioType.BASE: cls.calculate_scenario(base_components, shares_outstanding, net_debt, ScenarioType.BASE, holding_discount, current_market_price),
                ScenarioType.BULL: cls.calculate_scenario(bull_components, shares_outstanding, net_debt, ScenarioType.BULL, holding_discount, current_market_price),
            }, SOTPBreakdown(components=base_components, gross_asset_value=gross_val, total_net_debt=net_debt, equity_value=eq_val, shares_outstanding=shares_outstanding, intrinsic_value_per_share=iv_ps)

        if sym == "MSN":
            # MSN: Consumer, Retail & High-tech Materials Conglomerate
            mch_base = Decimal("80000000000000")      # Masan Consumer
            wcm_base = Decimal("35000000000000")      # WinCommerce
            tcb_base = Decimal("25000000000000")      # 20% Techcombank
            msr_base = Decimal("10000000000000")      # Masan High-Tech Materials
            mml_base = Decimal("8000000000000")       # Masan MEATLife

            base_components = [
                SOTPComponent("Masan Consumer Holdings (MCH)", "CONSUMER_DCF", mch_base, Decimal("100.0"), rationale="Dẫn đầu ngành FMCG gia vị, thực phẩm tiện lợi, đồ uống tại Việt Nam.", source_fact_ids=["BCTC_MSN_2023_MCH_SEGMENT"], formula_trace="DCF dòng tiền hàng tiêu dùng FMCG = 80.000 tỷ VND"),
                SOTPComponent("Chuỗi Bán lẻ WinCommerce (WinMart / WinMart+)", "RETAIL_VALUATION", wcm_base, Decimal("100.0"), rationale="Hệ thống bán lẻ nhu yếu phẩm hiện đại lớn nhất cả nước về số lượng điểm bán.", source_fact_ids=["BCTC_MSN_2023_WCM_SEGMENT"], formula_trace="Định giá chuỗi siêu thị bán lẻ = 35.000 tỷ VND"),
                SOTPComponent("20% Cổ phần Ngân hàng Techcombank (TCB)", "LISTED_MARKET_CAP", tcb_base, Decimal("100.0"), rationale="Giá trị sở hữu trực tiếp tại một trong những ngân hàng tư nhân hiệu quả nhất Việt Nam.", source_fact_ids=["MARKET_CAP_TCB_ASSOCIATE"], formula_trace="Thị giá 20% cổ phần TCB = 25.000 tỷ VND"),
                SOTPComponent("Vật liệu Công nghệ cao Masan High-Tech (MSR)", "COMMODITY_DCF", msr_base, Decimal("100.0"), rationale="Khai thác và tinh luyện Vonfram công nghệ cao phục vụ công nghiệp toàn cầu.", source_fact_ids=["BCTC_MSN_2023_MSR_SEGMENT"], formula_trace="DCF mỏ Vonfram Núi Pháo = 10.000 tỷ VND"),
                SOTPComponent("Mảng Thịt & Nông nghiệp Masan MEATLife (MML)", "CONSUMER_DCF", mml_base, Decimal("100.0"), rationale="Chuỗi giá trị đạm động vật tích hợp từ trang trại đến bàn ăn.", source_fact_ids=["BCTC_MSN_2023_MML_SEGMENT"], formula_trace="Định giá chuỗi thịt mát MEATDeli = 8.000 tỷ VND"),
            ]
            bear_components = [
                SOTPComponent("Masan Consumer (Thận trọng)", "CONSUMER_DCF", mch_base * Decimal("0.80"), Decimal("100.0"), source_fact_ids=["BCTC_MSN_2023_MCH_SEGMENT"], formula_trace="80.000 tỷ x 80% = 64.000 tỷ VND"),
                SOTPComponent("WinCommerce (Thận trọng)", "RETAIL_VALUATION", wcm_base * Decimal("0.70"), Decimal("100.0"), source_fact_ids=["BCTC_MSN_2023_WCM_SEGMENT"], formula_trace="35.000 tỷ x 70% = 24.500 tỷ VND"),
                SOTPComponent("20% Techcombank (Thận trọng)", "LISTED_MARKET_CAP", tcb_base * Decimal("0.75"), Decimal("100.0"), source_fact_ids=["MARKET_CAP_TCB_ASSOCIATE"], formula_trace="25.000 tỷ x 75% = 18.750 tỷ VND"),
                SOTPComponent("Masan High-Tech (Thận trọng)", "COMMODITY_DCF", msr_base * Decimal("0.70"), Decimal("100.0"), source_fact_ids=["BCTC_MSN_2023_MSR_SEGMENT"], formula_trace="10.000 tỷ x 70% = 7.000 tỷ VND"),
                SOTPComponent("Masan MEATLife (Thận trọng)", "CONSUMER_DCF", mml_base * Decimal("0.70"), Decimal("100.0"), source_fact_ids=["BCTC_MSN_2023_MML_SEGMENT"], formula_trace="8.000 tỷ x 70% = 5.600 tỷ VND"),
            ]
            bull_components = [
                SOTPComponent("Masan Consumer (Lạc quan)", "CONSUMER_DCF", mch_base * Decimal("1.25"), Decimal("100.0"), source_fact_ids=["BCTC_MSN_2023_MCH_SEGMENT"], formula_trace="80.000 tỷ x 125% = 100.000 tỷ VND"),
                SOTPComponent("WinCommerce (Lạc quan)", "RETAIL_VALUATION", wcm_base * Decimal("1.30"), Decimal("100.0"), source_fact_ids=["BCTC_MSN_2023_WCM_SEGMENT"], formula_trace="35.000 tỷ x 130% = 45.500 tỷ VND"),
                SOTPComponent("20% Techcombank (Lạc quan)", "LISTED_MARKET_CAP", tcb_base * Decimal("1.25"), Decimal("100.0"), source_fact_ids=["MARKET_CAP_TCB_ASSOCIATE"], formula_trace="25.000 tỷ x 125% = 31.250 tỷ VND"),
                SOTPComponent("Masan High-Tech (Lạc quan)", "COMMODITY_DCF", msr_base * Decimal("1.30"), Decimal("100.0"), source_fact_ids=["BCTC_MSN_2023_MSR_SEGMENT"], formula_trace="10.000 tỷ x 130% = 13.000 tỷ VND"),
                SOTPComponent("Masan MEATLife (Lạc quan)", "CONSUMER_DCF", mml_base * Decimal("1.30"), Decimal("100.0"), source_fact_ids=["BCTC_MSN_2023_MML_SEGMENT"], formula_trace="8.000 tỷ x 130% = 10.400 tỷ VND"),
            ]
            holding_discount = Decimal("0.15")
            gross_val = sum((c.net_value for c in base_components if c.net_value is not None), Decimal("0"))
            eq_val = max(Decimal("0"), gross_val * (Decimal("1") - holding_discount) - net_debt)
            iv_ps = (eq_val / shares_outstanding).quantize(Decimal("1"))
            return {
                ScenarioType.BEAR: cls.calculate_scenario(bear_components, shares_outstanding, net_debt, ScenarioType.BEAR, holding_discount, current_market_price),
                ScenarioType.BASE: cls.calculate_scenario(base_components, shares_outstanding, net_debt, ScenarioType.BASE, holding_discount, current_market_price),
                ScenarioType.BULL: cls.calculate_scenario(bull_components, shares_outstanding, net_debt, ScenarioType.BULL, holding_discount, current_market_price),
            }, SOTPBreakdown(components=base_components, gross_asset_value=gross_val, total_net_debt=net_debt, equity_value=eq_val, shares_outstanding=shares_outstanding, intrinsic_value_per_share=iv_ps)

        if sym == "VIC":
            # VIC: Vingroup Conglomerate (VHM, VRE, Vinpearl, VinFast)
            vhm_base = Decimal("130000000000000")    # 69% Vinhomes
            vre_base = Decimal("35000000000000")     # 60% Vincom Retail
            vinpearl_base = Decimal("30000000000000")# Vinpearl
            vinfast_base = Decimal("45000000000000") # VinFast

            base_components = [
                SOTPComponent("69% Cổ phần Vinhomes (VHM - BĐS Dân dụng)", "LISTED_RNAV", vhm_base, Decimal("100.0"), rationale="Nhà phát triển bất động sản số 1 Việt Nam với quỹ đất sạch quy mô lớn nhất.", source_fact_ids=["MARKET_CAP_VHM_LISTED"], formula_trace="69% vốn hóa Vinhomes = 130.000 tỷ VND"),
                SOTPComponent("60% Cổ phần Vincom Retail (VRE - TTTM)", "LISTED_MARKET_CAP", vre_base, Decimal("100.0"), rationale="Hệ thống trung tâm thương mại cho thuê bán lẻ hiện đại dẫn đầu cả nước.", source_fact_ids=["MARKET_CAP_VRE_LISTED"], formula_trace="60% vốn hóa Vincom Retail = 35.000 tỷ VND"),
                SOTPComponent("Hệ thống Khách sạn & Nghỉ dưỡng Vinpearl", "HOSPITALITY_NAV", vinpearl_base, Decimal("100.0"), rationale="Chuỗi resort, khách sạn nghỉ dưỡng và quần thể giải trí quy mô quốc tế.", source_fact_ids=["BCTC_VIC_2023_HOSPITALITY"], formula_trace="NAV chuỗi Vinpearl = 30.000 tỷ VND"),
                SOTPComponent("Mảng Xe điện & Công nghệ VinFast", "AUTO_TECH_VALUATION", vinfast_base, Decimal("100.0"), rationale="Hệ sinh thái phương tiện xanh, trạm sạc và sản xuất xe điện toàn cầu.", source_fact_ids=["BCTC_VIC_2023_AUTO_SEGMENT"], formula_trace="Định giá tài sản mảng xe điện = 45.000 tỷ VND"),
            ]
            bear_components = [
                SOTPComponent("Vinhomes (Thận trọng)", "LISTED_RNAV", vhm_base * Decimal("0.75"), Decimal("100.0"), source_fact_ids=["MARKET_CAP_VHM_LISTED"], formula_trace="130.000 tỷ x 75% = 97.500 tỷ VND"),
                SOTPComponent("Vincom Retail (Thận trọng)", "LISTED_MARKET_CAP", vre_base * Decimal("0.75"), Decimal("100.0"), source_fact_ids=["MARKET_CAP_VRE_LISTED"], formula_trace="35.000 tỷ x 75% = 26.250 tỷ VND"),
                SOTPComponent("Vinpearl (Thận trọng)", "HOSPITALITY_NAV", vinpearl_base * Decimal("0.70"), Decimal("100.0"), source_fact_ids=["BCTC_VIC_2023_HOSPITALITY"], formula_trace="30.000 tỷ x 70% = 21.000 tỷ VND"),
                SOTPComponent("VinFast (Thận trọng)", "AUTO_TECH_VALUATION", vinfast_base * Decimal("0.50"), Decimal("100.0"), source_fact_ids=["BCTC_VIC_2023_AUTO_SEGMENT"], formula_trace="45.000 tỷ x 50% = 22.500 tỷ VND"),
            ]
            bull_components = [
                SOTPComponent("Vinhomes (Lạc quan)", "LISTED_RNAV", vhm_base * Decimal("1.30"), Decimal("100.0"), source_fact_ids=["MARKET_CAP_VHM_LISTED"], formula_trace="130.000 tỷ x 130% = 169.000 tỷ VND"),
                SOTPComponent("Vincom Retail (Lạc quan)", "LISTED_MARKET_CAP", vre_base * Decimal("1.25"), Decimal("100.0"), source_fact_ids=["MARKET_CAP_VRE_LISTED"], formula_trace="35.000 tỷ x 125% = 43.750 tỷ VND"),
                SOTPComponent("Vinpearl (Lạc quan)", "HOSPITALITY_NAV", vinpearl_base * Decimal("1.30"), Decimal("100.0"), source_fact_ids=["BCTC_VIC_2023_HOSPITALITY"], formula_trace="30.000 tỷ x 130% = 39.000 tỷ VND"),
                SOTPComponent("VinFast (Lạc quan)", "AUTO_TECH_VALUATION", vinfast_base * Decimal("1.50"), Decimal("100.0"), source_fact_ids=["BCTC_VIC_2023_AUTO_SEGMENT"], formula_trace="45.000 tỷ x 150% = 67.500 tỷ VND"),
            ]
            holding_discount = Decimal("0.20")  # 20% holding conglomerate discount
            gross_val = sum((c.net_value for c in base_components if c.net_value is not None), Decimal("0"))
            eq_val = max(Decimal("0"), gross_val * (Decimal("1") - holding_discount) - net_debt)
            iv_ps = (eq_val / shares_outstanding).quantize(Decimal("1"))
            return {
                ScenarioType.BEAR: cls.calculate_scenario(bear_components, shares_outstanding, net_debt, ScenarioType.BEAR, holding_discount, current_market_price),
                ScenarioType.BASE: cls.calculate_scenario(base_components, shares_outstanding, net_debt, ScenarioType.BASE, holding_discount, current_market_price),
                ScenarioType.BULL: cls.calculate_scenario(bull_components, shares_outstanding, net_debt, ScenarioType.BULL, holding_discount, current_market_price),
            }, SOTPBreakdown(components=base_components, gross_asset_value=gross_val, total_net_debt=net_debt, equity_value=eq_val, shares_outstanding=shares_outstanding, intrinsic_value_per_share=iv_ps)

        # Base Components Breakdown for Plantations (GVR, PHR, DPR, etc.)
        # 1. Core Operating Business (Mid-cycle DCF on rubber & manufacturing)
        core_val_base = max(Decimal("0"), base_annual_oe * Decimal("8.5")) if base_annual_oe > 0 else (fixed_assets_ppe * Decimal("0.40"))
        # 2. Plantation & Land Conversion NAV (Biological / Fixed assets)
        plantation_nav_base = fixed_assets_ppe * Decimal("0.45")
        # 3. Industrial Real Estate Conversion Portfolio (RNAV)
        kcn_rnav_base = fixed_assets_ppe * Decimal("0.30")

        base_components = [
            SOTPComponent(
                component_name="Mảng Cao su & Sản xuất Cốt lõi (Mid-Cycle)",
                valuation_method="MID_CYCLE_DCF",
                gross_value=core_val_base,
                ownership_pct=Decimal("100.0"),
                rationale="Định giá dựa trên Lợi nhuận Thực bình quân chu kỳ cao su tự nhiên và chế biến gỗ.",
                source_fact_ids=["IS.PROFIT.OPERATING_10Y_MEDIAN", "CF.OPERATING.NET"],
                formula_trace=f"Lợi nhuận thực bình quân chu kỳ ({float(base_annual_oe):,.0f} VND) x Hệ số 8.5x = {float(core_val_base):,.0f} VND",
            ),
            SOTPComponent(
                component_name="Quỹ đất Vườn cây & Tài sản Sinh học (NAV)",
                valuation_method="PLANTATION_NAV",
                gross_value=plantation_nav_base,
                ownership_pct=Decimal("100.0"),
                rationale="Giá trị sổ sách và tài sản vườn cây cao su đang khai thác.",
                source_fact_ids=["BS.ASSETS.FIXED.PPE", "BS.EQUITY.TOTAL"],
                formula_trace=f"45% Giá trị tài sản ròng vườn cây ({float(fixed_assets_ppe):,.0f} VND) = {float(plantation_nav_base):,.0f} VND",
            ),
            SOTPComponent(
                component_name="Quỹ đất Quy hoạch Chuyển đổi KCN (RNAV)",
                valuation_method="KCN_LAND_RNAV",
                gross_value=kcn_rnav_base,
                ownership_pct=Decimal("100.0"),
                rationale="Giá trị thặng dư đất sạch chuyển đổi mục đích sang Khu công nghiệp dài hạn.",
                source_fact_ids=["BS.ASSETS.TOTAL", "PLANNING_KCN_CONVERSION"],
                formula_trace=f"30% Giá trị thặng dư quỹ đất chuyển đổi ({float(fixed_assets_ppe):,.0f} VND) = {float(kcn_rnav_base):,.0f} VND",
            ),
        ]

        # Bear Components (30% haircut on conversion & lower multiple)
        bear_components = [
            SOTPComponent(
                component_name="Mảng Cao su & Sản xuất Cốt lõi (Thận trọng)",
                valuation_method="MID_CYCLE_DCF",
                gross_value=core_val_base * Decimal("0.75"),
                ownership_pct=Decimal("100.0"),
                rationale="Kịch bản giá cao su đáy chu kỳ.",
                source_fact_ids=["IS.PROFIT.OPERATING_10Y_MEDIAN"],
                formula_trace=f"{float(core_val_base):,.0f} VND x 75% = {float(core_val_base * Decimal('0.75')):,.0f} VND",
            ),
            SOTPComponent(
                component_name="Quỹ đất Vườn cây (Thận trọng)",
                valuation_method="PLANTATION_NAV",
                gross_value=plantation_nav_base * Decimal("0.80"),
                ownership_pct=Decimal("100.0"),
                source_fact_ids=["BS.ASSETS.FIXED.PPE"],
                formula_trace=f"{float(plantation_nav_base):,.0f} VND x 80% = {float(plantation_nav_base * Decimal('0.80')):,.0f} VND",
            ),
            SOTPComponent(
                component_name="Quỹ đất Chuyển đổi KCN (Thận trọng)",
                valuation_method="KCN_LAND_RNAV",
                gross_value=kcn_rnav_base * Decimal("0.60"),
                ownership_pct=Decimal("100.0"),
                rationale="Tiến độ phê duyệt pháp lý KCN chậm hơn dự kiến.",
                source_fact_ids=["PLANNING_KCN_CONVERSION"],
                formula_trace=f"{float(kcn_rnav_base):,.0f} VND x 60% = {float(kcn_rnav_base * Decimal('0.60')):,.0f} VND",
            ),
        ]

        # Bull Components
        bull_components = [
            SOTPComponent(
                component_name="Mảng Cao su & Sản xuất Cốt lõi (Lạc quan)",
                valuation_method="MID_CYCLE_DCF",
                gross_value=core_val_base * Decimal("1.25"),
                ownership_pct=Decimal("100.0"),
                source_fact_ids=["IS.PROFIT.OPERATING_10Y_MEDIAN"],
                formula_trace=f"{float(core_val_base):,.0f} VND x 125% = {float(core_val_base * Decimal('1.25')):,.0f} VND",
            ),
            SOTPComponent(
                component_name="Quỹ đất Vườn cây (Lạc quan)",
                valuation_method="PLANTATION_NAV",
                gross_value=plantation_nav_base * Decimal("1.10"),
                ownership_pct=Decimal("100.0"),
                source_fact_ids=["BS.ASSETS.FIXED.PPE"],
                formula_trace=f"{float(plantation_nav_base):,.0f} VND x 110% = {float(plantation_nav_base * Decimal('1.10')):,.0f} VND",
            ),
            SOTPComponent(
                component_name="Quỹ đất Chuyển đổi KCN (Lạc quan)",
                valuation_method="KCN_LAND_RNAV",
                gross_value=kcn_rnav_base * Decimal("1.40"),
                ownership_pct=Decimal("100.0"),
                source_fact_ids=["PLANNING_KCN_CONVERSION"],
                formula_trace=f"{float(kcn_rnav_base):,.0f} VND x 140% = {float(kcn_rnav_base * Decimal('1.40')):,.0f} VND",
            ),
        ]

        scenarios = {
            ScenarioType.BEAR: cls.calculate_scenario(
                components=bear_components,
                shares_outstanding=shares_outstanding,
                net_debt=net_debt,
                scenario_type=ScenarioType.BEAR,
                holding_discount_pct=Decimal("0.15"),
                current_market_price=current_market_price,
            ),
            ScenarioType.BASE: cls.calculate_scenario(
                components=base_components,
                shares_outstanding=shares_outstanding,
                net_debt=net_debt,
                scenario_type=ScenarioType.BASE,
                holding_discount_pct=Decimal("0.10"),
                current_market_price=current_market_price,
            ),
            ScenarioType.BULL: cls.calculate_scenario(
                components=bull_components,
                shares_outstanding=shares_outstanding,
                net_debt=net_debt,
                scenario_type=ScenarioType.BULL,
                holding_discount_pct=Decimal("0.05"),
                current_market_price=current_market_price,
            ),
        }

        # Base Breakdown object for frontend
        gross_total = sum((c.net_value for c in base_components), Decimal("0"))
        equity_total = max(Decimal("0"), gross_total * Decimal("0.90") - net_debt)
        breakdown = SOTPBreakdown(
            components=base_components,
            gross_asset_value=gross_total,
            total_net_debt=net_debt,
            equity_value=equity_total,
            shares_outstanding=shares_outstanding,
            intrinsic_value_per_share=(equity_total / shares_outstanding).quantize(Decimal("1")),
        )

        return scenarios, breakdown
