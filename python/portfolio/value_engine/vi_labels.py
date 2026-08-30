"""
Vietnamese human-friendly labels for internal enum codes.

Maps technical English enum values (verdict status, economic archetype,
quality tier, valuation model, overlays) to natural Vietnamese for retail investors.
"""
from __future__ import annotations

from typing import Dict

VAL_VERDICT_VI: Dict[str, str] = {
    "HIGH_CONVICTION_VALUE": "Đầu tư Giá trị Tuyệt vời",
    "ATTRACTIVE": "Vùng giá Hấp dẫn",
    "FAIRLY_VALUED": "Định giá Hợp lý",
    "FAIR_VALUE": "Định giá Hợp lý",
    "WATCH": "Cần Theo dõi thêm",
    "AVOID_QUALITY": "Thận trọng Chất lượng",
    "UNVALUABLE": "Ngoài Vòng Năng lực",
    "DEEP_VALUE": "Định giá Rất Rẻ",
    "UNDERVALUED": "Dưới Giá trị Thực",
    "OVERVALUED": "Định giá Cao hơn Giá trị",
    "GROWTH_PRICED_IN": "Đã phản ánh Tăng trưởng",
    "DATA_INSUFFICIENT": "Chưa đủ Dữ liệu BCTC",
    "MODEL_PENDING": "Đang hoàn thiện Mô hình",
    "MODEL_INCOMPLETE": "Thiếu dữ liệu mô hình đặc thù",
    "MODEL_ESTIMATED": "Mô hình Ước tính (giả định chưa có nguồn)",
    "CLASSIFICATION_CONFLICT": "Xung đột Phân loại ngành",
    "AVOID_SOLVENCY": "Thận trọng Khả năng Thanh toán",
    "ARCHETYPE_UNSUPPORTED": "Chưa xác định Mô hình Định giá",
    "FALLBACK_MODEL_ONLY": "Mô hình Định giá Tham chiếu",
}

ARCHETYPE_VI: Dict[str, str] = {
    # 1. Financials
    "COMMERCIAL_BANK": "Ngân hàng Thương mại",
    "CONSUMER_FINANCE": "Tài chính Tiêu dùng",
    "SECURITIES_BROKER": "Công ty Chứng khoán",
    "NON_LIFE_INSURANCE": "Bảo hiểm Phi nhân thọ",
    "LIFE_INSURANCE": "Bảo hiểm Nhân thọ",
    "INVESTMENT_HOLDING_FINANCIAL": "Đầu tư Tài chính",

    # 2. Real Estate & Property
    "REAL_ESTATE_DEVELOPER": "Phát triển Bất động sản Dân dụng",
    "INDUSTRIAL_REAL_ESTATE": "Bất động sản Khu công nghiệp",
    "RENTAL_REAL_ESTATE": "Bất động sản Cho thuê & Thương mại",

    # 3. Consumer & Retail
    "CONSUMER_STAPLES": "Hàng Tiêu dùng Thiết yếu",
    "RETAIL_CHAIN": "Chuỗi Bán lẻ",
    "CONSUMER_DISCRETIONARY": "Hàng Tiêu dùng Không thiết yếu",
    "MEDIA_CONTENT": "Truyền thông & Nội dung số",

    # 4. Tech & Telecom
    "TECHNOLOGY_SERVICES": "Dịch vụ Công nghệ",
    "SOFTWARE_PLATFORM": "Nền tảng Phần mềm",
    "TELECOM_OPERATOR": "Nhà mạng Viễn thông",

    # 5. Healthcare
    "PHARMACEUTICAL": "Sản xuất Dược phẩm",
    "HEALTHCARE_SERVICES": "Dịch vụ Y tế & Bệnh viện",

    # 6. Materials, Energy & Utilities
    "BASIC_MATERIALS_METALS": "Vật liệu Cơ bản & Luyện thép",
    "COMMODITY_CHEMICAL": "Hóa chất & Phân bón cơ bản",
    "SPECIALTY_CHEMICAL": "Hóa chất Chuyên dụng",
    "BUILDING_MATERIALS": "Vật liệu Xây dựng & Xi măng",
    "MINING_RESOURCE": "Khai khoáng & Tài nguyên",
    "OIL_GAS_UPSTREAM": "Khai thác Dầu khí",
    "OILFIELD_SERVICES": "Dịch vụ Dầu khí (Khoan & Kỹ thuật)",
    "ENERGY_INFRASTRUCTURE": "Hạ tầng Năng lượng & Phân phối Khí",
    "OIL_REFINING_DOWNSTREAM": "Lọc hóa dầu & Bán lẻ Xăng dầu",
    "POWER_GENERATION_THERMAL": "Nhiệt điện",
    "POWER_GENERATION_HYDRO": "Thủy điện",
    "POWER_RENEWABLE": "Năng lượng Tái tạo",
    "WATER_UTILITY": "Cấp thoát nước & Tiện ích",

    # 7. Industrials & Infrastructure
    "CONSTRUCTION_EPC": "Xây dựng & Tổng thầu EPC",
    "INDUSTRIAL_MANUFACTURING": "Sản xuất Công nghiệp",
    "AUTOMOTIVE": "Sản xuất Ô tô",
    "AUTO_COMPONENTS": "Linh kiện & Phụ tùng Ô tô",
    "PORT_INFRASTRUCTURE": "Khai thác Cảng biển",
    "LOGISTICS_SERVICES": "Dịch vụ Logistics & Kho bãi",
    "SHIPPING": "Vận tải biển",
    "AIRLINE": "Vận tải Hàng không",
    "AIRPORT_INFRASTRUCTURE": "Hạ tầng Cảng Hàng không",
    "CONCESSION_INFRASTRUCTURE": "Hạ tầng Khai thác Hữu hạn (BOT/Concession)",

    # 8. Agriculture & Conglomerate
    "AGRICULTURE": "Nông nghiệp & Trồng trọt",
    "RUBBER_PLANTATION": "Trồng trọt Cao su & Quỹ đất KCN",
    "AQUACULTURE_EXPORT": "Thủy sản & Chế biến Xuất khẩu",
    "EXPORT_MANUFACTURING": "Gia công & Sản xuất Xuất khẩu",
    "HOTEL_HOSPITALITY": "Khách sạn & Nghỉ dưỡng",
    "EDUCATION_SERVICES": "Dịch vụ Giáo dục",
    "HOLDING_COMPANY": "Công ty Quản lý Vốn (Holding)",
    "CONGLOMERATE": "Tập đoàn Đa ngành",
    "GENERIC_ENTERPRISE": "Doanh nghiệp Đại chúng",
    "ARCHETYPE_UNKNOWN": "Chưa xác định nhóm ngành",
}

OVERLAY_VI: Dict[str, str] = {
    "HIGH_CYCLICALITY": "Tính chu kỳ cao (+10% MOS)",
    "CAPITAL_INTENSIVE": "Thâm dụng vốn (+5% MOS)",
    "COMMODITY_EXPOSED": "Nhạy cảm giá hàng hóa (+5-10% MOS)",
    "ASSET_LIGHT_COMPOUNDER": "Tăng trưởng nhẹ vốn (Asset-light)",
    "REGULATED": "Chịu quản lý biểu giá nhà nước",
    "CONCESSION": "Hợp đồng khai thác hữu hạn (Finite-life)",
    "PROJECT_BASED": "Mô hình theo chu kỳ dự án",
    "EXPORT_ORIENTED": "Định hướng xuất khẩu",
    "FX_SENSITIVE": "Nhạy cảm tỷ giá",
    "CUSTOMER_CONCENTRATED": "Phụ thuộc khách hàng lớn (+5% MOS)",
    "HIGH_LEVERAGE": "Đòn bẩy tài chính cao (+5-10% MOS)",
    "STATE_INFLUENCED": "Có chi phối vốn nhà nước",
    "RELATED_PARTY_RISK": "Rủi ro giao dịch bên liên quan (+10% MOS)",
    "TURNAROUND": "Doanh nghiệp đang tái cấu trúc",
    "MATURE_COMPOUNDER": "Tăng trưởng ổn định trưởng thành",
    "EARLY_GROWTH": "Tăng trưởng giai đoạn đầu",
}

QUALITY_TIER_VI: Dict[str, str] = {
    "EXCEPTIONAL": "Xuất sắc",
    "HIGH_QUALITY": "Chất lượng cao",
    "INVESTABLE": "Đạt chuẩn đầu tư",
    "WATCH": "Cần theo dõi",
    "LOW_QUALITY": "Chất lượng thấp",
}

VALUATION_MODEL_VI: Dict[str, str] = {
    "NORMALIZED_OWNER_EARNINGS_DCF": "Chiết khấu Lợi nhuận Thực bình quân chu kỳ",
    "RESIDUAL_INCOME_MODEL": "Mô hình Thu nhập Thặng dư (RIM)",
    "LEASE_CASHFLOW_DCF": "Chiết khấu Dòng tiền Hợp đồng Thuê đất & RNAV KCN",
    "CONCESSION_DCF": "Chiết khấu Dòng tiền Hữu hạn (Concession Life, TV=0)",
    "RNAV": "Giá trị Tài sản Ròng sau điều chỉnh (RNAV)",
    "SOTP": "Tổng các bộ phận cấu thành (SOTP)",
    "DCF": "Chiết khấu dòng tiền",
    "EPV": "Giá trị theo Sức kiếm tiền hiện tại",
    "REVERSE_DCF": "Chiết khấu ngược theo thị giá",
    "MID_CYCLE_FCFF": "Chiết khấu Dòng tiền Tự do giữa chu kỳ (Mid-cycle FCFF)",
    "RESERVE_NAV": "Giá trị Tài sản Ròng theo Trữ lượng (Reserve/Resource NAV)",
    "FLEET_NAV": "Giá trị Tài sản Ròng theo Đội tàu (Fleet NAV)",
    "AIRLINE_EBITDAR": "Định giá Hàng không theo EBITDAR điều chỉnh thuê (Lease-adjusted)",
    "MID_CYCLE_EARNINGS": "Thu nhập chuẩn hóa giữa chu kỳ",
}

MOAT_VI: Dict[str, str] = {
    "WIDE": "Hào kinh tế sâu rộng",
    "NARROW": "Có lợi thế cạnh tranh nhất định",
    "NONE": "Không có hào kinh tế rõ nét",
}


def verdict_vi(code: str) -> str:
    return VAL_VERDICT_VI.get(code, code)


def archetype_vi(code: str) -> str:
    return ARCHETYPE_VI.get(code, code)


def overlay_vi(code: str) -> str:
    return OVERLAY_VI.get(code, code)


def quality_tier_vi(code: str) -> str:
    return QUALITY_TIER_VI.get(code, code)


def valuation_model_vi(code: str) -> str:
    return VALUATION_MODEL_VI.get(code, code)


def moat_vi(code: str) -> str:
    return MOAT_VI.get(code, code)