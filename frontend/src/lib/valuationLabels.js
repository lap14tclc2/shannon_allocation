export const VERDICT_LABELS = {
  BUY: 'Có thể mua',
  CONDITIONAL_BUY: 'Có thể mua có ĐK',
  WAIT_FOR_MOS: 'Chờ biên an toàn',
  DO_NOT_BUY: 'Không đạt chuẩn mua',
  INSUFFICIENT_DATA: 'Chưa đủ Dữ liệu BCTC',
  HIGH_CONVICTION_VALUE: 'Đầu tư Giá trị Tuyệt vời',
  ATTRACTIVE: 'Vùng giá Hấp dẫn',
  FAIRLY_VALUED: 'Định giá Hợp lý',
  FAIR_VALUE: 'Định giá Hợp lý',
  WATCH: 'Cần Theo dõi thêm',
  AVOID_QUALITY: 'Thận trọng Chất lượng',
  UNVALUABLE: 'Ngoài Vòng Năng lực',
  DEEP_VALUE: 'Định giá Rất Rẻ',
  UNDERVALUED: 'Dưới Giá trị Thực',
  OVERVALUED: 'Định giá Cao hơn Giá trị',
  GROWTH_PRICED_IN: 'Đã phản ánh Tăng trưởng',
  DATA_INSUFFICIENT: 'Chưa đủ Dữ liệu BCTC',
  MODEL_PENDING: 'Đang hoàn thiện Mô hình',
  MODEL_INCOMPLETE: 'Thiếu dữ liệu mô hình đặc thù',
  CLASSIFICATION_CONFLICT: 'Xung đột Phân loại ngành',
  AVOID_SOLVENCY: 'Thận trọng Khả năng Thanh toán',
  ARCHETYPE_UNSUPPORTED: 'Chưa xác định Mô hình Định giá',
  FALLBACK_MODEL_ONLY: 'Mô hình Định giá Tham chiếu',
};

export const VERDICT_PILL_CLASS = {
  BUY: 'status-pill-deep-value',
  CONDITIONAL_BUY: 'status-pill-fair',
  WAIT_FOR_MOS: 'status-pill-undervalued',
  DO_NOT_BUY: 'status-pill-distressed',
  INSUFFICIENT_DATA: 'status-pill-fair',
  HIGH_CONVICTION_VALUE: 'status-pill-deep-value',
  ATTRACTIVE: 'status-pill-undervalued',
  FAIRLY_VALUED: 'status-pill-fair',
  FAIR_VALUE: 'status-pill-fair',
  WATCH: 'status-pill-fair',
  AVOID_QUALITY: 'status-pill-distressed',
  UNVALUABLE: 'status-pill-distressed',
  AVOID_SOLVENCY: 'status-pill-distressed',
  DEEP_VALUE: 'status-pill-deep-value',
  UNDERVALUED: 'status-pill-undervalued',
  OVERVALUED: 'status-pill-overvalued',
  GROWTH_PRICED_IN: 'status-pill-overvalued',
  DATA_INSUFFICIENT: 'status-pill-fair',
  MODEL_PENDING: 'status-pill-fair',
  MODEL_INCOMPLETE: 'status-pill-distressed',
  CLASSIFICATION_CONFLICT: 'status-pill-distressed',
  ARCHETYPE_UNSUPPORTED: 'status-pill-distressed',
  FALLBACK_MODEL_ONLY: 'status-pill-fair',
};

export const ARCHETYPE_LABELS = {
  // Financials
  COMMERCIAL_BANK: 'Ngân hàng Thương mại',
  CONSUMER_FINANCE: 'Tài chính Tiêu dùng',
  SECURITIES_BROKER: 'Công ty Chứng khoán',
  NON_LIFE_INSURANCE: 'Bảo hiểm Phi nhân thọ',
  LIFE_INSURANCE: 'Bảo hiểm Nhân thọ',
  INVESTMENT_HOLDING_FINANCIAL: 'Đầu tư Tài chính',

  // Real Estate & Property
  REAL_ESTATE_DEVELOPER: 'Phát triển Bất động sản Dân dụng',
  INDUSTRIAL_REAL_ESTATE: 'Bất động sản Khu công nghiệp',
  RENTAL_REAL_ESTATE: 'Bất động sản Cho thuê & Thương mại',

  // Consumer & Retail
  CONSUMER_STAPLES: 'Hàng Tiêu dùng Thiết yếu',
  RETAIL_CHAIN: 'Chuỗi Bán lẻ',
  CONSUMER_DISCRETIONARY: 'Hàng Tiêu dùng Không thiết yếu',
  MEDIA_CONTENT: 'Truyền thông & Nội dung số',

  // Tech & Telecom
  TECHNOLOGY_SERVICES: 'Dịch vụ Công nghệ Thông tin',
  SOFTWARE_PLATFORM: 'Nền tảng Phần mềm',
  TELECOM_OPERATOR: 'Nhà mạng Viễn thông',

  // Healthcare
  PHARMACEUTICAL: 'Sản xuất Dược phẩm',
  HEALTHCARE_SERVICES: 'Dịch vụ Y tế & Bệnh viện',

  // Materials, Energy & Utilities
  BASIC_MATERIALS_METALS: 'Vật liệu Cơ bản & Luyện thép',
  COMMODITY_CHEMICAL: 'Hóa chất & Phân bón cơ bản',
  SPECIALTY_CHEMICAL: 'Hóa chất Chuyên dụng',
  BUILDING_MATERIALS: 'Vật liệu Xây dựng & Xi măng',
  MINING_RESOURCE: 'Khai khoáng & Tài nguyên',
  OIL_GAS_UPSTREAM: 'Khai thác Dầu khí',
  OILFIELD_SERVICES: 'Dịch vụ Dầu khí (Khoan & Kỹ thuật)',
  ENERGY_INFRASTRUCTURE: 'Hạ tầng Năng lượng & Phân phối Khí',
  OIL_REFINING_DOWNSTREAM: 'Lọc hóa dầu & Bán lẻ Xăng dầu',
  POWER_GENERATION_THERMAL: 'Nhiệt điện',
  POWER_GENERATION_HYDRO: 'Thủy điện',
  POWER_RENEWABLE: 'Năng lượng Tái tạo',
  WATER_UTILITY: 'Cấp thoát nước & Tiện ích',

  // Industrials & Infrastructure
  CONSTRUCTION_EPC: 'Xây dựng & Tổng thầu EPC',
  INDUSTRIAL_MANUFACTURING: 'Sản xuất Công nghiệp',
  AUTOMOTIVE: 'Sản xuất Ô tô',
  AUTO_COMPONENTS: 'Linh kiện & Phụ tùng Ô tô',
  PORT_INFRASTRUCTURE: 'Khai thác Cảng biển',
  LOGISTICS_SERVICES: 'Dịch vụ Logistics & Kho bãi',
  SHIPPING: 'Vận tải biển',
  AIRLINE: 'Vận tải Hàng không',
  AIRPORT_INFRASTRUCTURE: 'Hạ tầng Cảng Hàng không',
  CONCESSION_INFRASTRUCTURE: 'Hạ tầng Khai thác Hữu hạn (BOT/Concession)',

  // Agriculture & Conglomerates
  AGRICULTURE: 'Nông nghiệp & Trồng trọt',
  RUBBER_PLANTATION: 'Trồng trọt Cao su & Quỹ đất KCN',
  AQUACULTURE_EXPORT: 'Thủy sản & Chế biến Xuất khẩu',
  EXPORT_MANUFACTURING: 'Gia công & Sản xuất Xuất khẩu',
  HOTEL_HOSPITALITY: 'Khách sạn & Nghỉ dưỡng',
  EDUCATION_SERVICES: 'Dịch vụ Giáo dục',
  HOLDING_COMPANY: 'Công ty Quản lý Vốn (Holding)',
  CONGLOMERATE: 'Tập đoàn Đa ngành',
  GENERIC_ENTERPRISE: 'Doanh nghiệp Đại chúng',
  ARCHETYPE_UNKNOWN: 'Chưa xác định nhóm ngành',
};

export const QUALITY_TIER_LABELS = {
  EXCEPTIONAL: 'Xuất sắc',
  HIGH_QUALITY: 'Chất lượng cao',
  INVESTABLE: 'Đạt chuẩn đầu tư',
  WATCH: 'Cần theo dõi',
  LOW_QUALITY: 'Chất lượng thấp',
};

export const VALUATION_MODEL_LABELS = {
  NORMALIZED_OWNER_EARNINGS_DCF: 'Chiết khấu Lợi nhuận Thực bình quân chu kỳ',
  RESIDUAL_INCOME_MODEL: 'Mô hình Thu nhập Thặng dư (RIM)',
  LEASE_CASHFLOW_DCF: 'Chiết khấu Dòng tiền Hợp đồng Thuê đất & RNAV KCN',
  CONCESSION_DCF: 'Chiết khấu Dòng tiền Hữu hạn (Concession Life, TV=0)',
  RNAV: 'Giá trị Tài sản Ròng sau điều chỉnh (RNAV)',
  SOTP: 'Tổng các bộ phận cấu thành (SOTP)',
  DCF: 'Chiết khấu dòng tiền',
  EPV: 'Giá trị theo Sức kiếm tiền hiện tại',
  REVERSE_DCF: 'Chiết khấu ngược theo thị giá',
  MID_CYCLE_FCFF: 'Chiết khấu Dòng tiền Tự do giữa chu kỳ (Mid-cycle FCFF)',
  RESERVE_NAV: 'Giá trị Tài sản Ròng theo Trữ lượng (Reserve/Resource NAV)',
  FLEET_NAV: 'Giá trị Tài sản Ròng theo Đội tàu (Fleet NAV)',
  AIRLINE_EBITDAR: 'Định giá Hàng không theo EBITDAR điều chỉnh thuê',
  MID_CYCLE_EARNINGS: 'Thu nhập chuẩn hóa giữa chu kỳ',
};

export const MODEL_STATUS_LABELS = {
  MODEL_VERIFIED: 'Mô hình Chuẩn xác thực',
  MODEL_INCOMPLETE: 'Thiếu dữ liệu mô hình đặc thù',
  MODEL_PARTIAL: 'Bằng chứng chu kỳ một phần (PARTIAL)',
  MODEL_ESTIMATED: 'Mô hình Ước tính (giả định chưa có nguồn)',
  MODEL_PENDING: 'Đang hoàn thiện mô hình',
  FALLBACK_MODEL: 'Mô hình tham chiếu',
  FALLBACK_MODEL_ONLY: 'Mô hình Định giá Tham chiếu',
  ARCHETYPE_UNKNOWN: 'Chưa xác định nhóm ngành',
  ARCHETYPE_UNSUPPORTED: 'Chưa xác định Mô hình Định giá',
};

export function verdictLabel(code) {
  return VERDICT_LABELS[code] || code || 'Đang theo dõi';
}

export function verdictPillClass(code) {
  return VERDICT_PILL_CLASS[code] || 'status-pill-fair';
}

export function archetypeLabel(code) {
  return ARCHETYPE_LABELS[code] || code || 'Doanh nghiệp niêm yết';
}

export function qualityTierLabel(code) {
  return QUALITY_TIER_LABELS[code] || code || '—';
}

export function valuationModelLabel(code) {
  return VALUATION_MODEL_LABELS[code] || code || '—';
}

export function modelStatusLabel(code) {
  return MODEL_STATUS_LABELS[code] || code || 'Mô hình Chuẩn xác thực';
}