/**
 * Centralized Vietnamese Semantic Presentation Layer for QPort.
 *
 * Separates machine calculation semantics from investor-facing Vietnamese explanations.
 * Converts internal codes, raw math operators, and findings into natural financial Vietnamese
 * while retaining precision and formula evidence for audit drill-downs.
 */

export const STATUS_MAP = {
  PASS: 'Đạt',
  GOOD: 'Tốt',
  WATCH: 'Cần theo dõi',
  FAIL: 'Không đạt',
  UNKNOWN: 'Chưa đủ dữ liệu',
  NOT_APPLICABLE: 'Không áp dụng',
  CLEAR: 'Chưa phát hiện rủi ro đáng kể',
  HIGH_RISK: 'Rủi ro cao',
  INFO: 'Thông tin',
  LOW: 'Rủi ro thấp',
  MEDIUM: 'Rủi ro trung bình',
  HIGH: 'Rủi ro cao',
  CRITICAL: 'Rủi ro rất cao',
};

export const DECISION_MAP = {
  BUY: 'Có thể mua',
  BUY_MORE: 'Có thể mua thêm',
  HOLD: 'Tiếp tục nắm giữ',
  HOLD_NO_NEW_CAPITAL: 'Tiếp tục nắm giữ, chưa phân bổ thêm vốn',
  WAIT_FOR_MOS: 'Chờ mức giá có biên an toàn tốt hơn',
  BUILD_RESERVE_FIRST: 'Ưu tiên củng cố quỹ dự phòng trước',
  REVIEW_BUSINESS: 'Cần xem xét thêm dữ liệu doanh nghiệp',
  AVOID: 'Chưa phù hợp để đầu tư',
  SELL_REVIEW: 'Cần xem xét lại luận điểm nắm giữ',
  SELL: 'Cân nhắc thoái vốn',
};

export const CLASSIFICATION_MAP = {
  COMPOUNDER: 'Doanh nghiệp tích lũy giá trị dài hạn',
  POTENTIAL_COMPOUNDER: 'Doanh nghiệp có tiềm năng tăng trưởng giá trị dài hạn',
  AVERAGE_BUSINESS: 'Doanh nghiệp có chất lượng trung bình',
  CYCLICAL_QUALITY: 'Doanh nghiệp chất lượng mang tính chu kỳ',
  WEAK_BUSINESS: 'Chất lượng doanh nghiệp còn yếu',
  DETERIORATING_BUSINESS: 'Nền tảng kinh doanh đang suy yếu',
  INSUFFICIENT_DATA: 'Chưa đủ dữ liệu để đánh giá',
};

export const VALUETRAP_MAP = {
  CLEAR: 'Chưa phát hiện dấu hiệu bẫy giá trị đáng kể',
  WATCH: 'Có dấu hiệu cần theo dõi',
  HIGH_RISK: 'Nguy cơ bẫy giá trị cao',
  INSUFFICIENT_DATA: 'Chưa đủ dữ liệu để đánh giá',
};

export const DETERIORATION_MAP = {
  NO_DETERIORATION: 'Chưa phát hiện xu hướng suy giảm đáng kể',
  LIKELY_CYCLICAL: 'Suy giảm có khả năng mang tính chu kỳ',
  POSSIBLY_CYCLICAL: 'Có dấu hiệu suy giảm mang tính chu kỳ',
  POSSIBLY_STRUCTURAL: 'Có dấu hiệu suy giảm có thể mang tính cấu trúc',
  STRUCTURAL: 'Đã phát hiện suy giảm mang tính cấu trúc',
  UNKNOWN: 'Chưa đủ dữ liệu để xác định',
};

export const ARCHETYPE_MAP = {
  NORMAL_ENTERPRISE: 'Doanh nghiệp sản xuất / thương mại thông thường',
  BANK: 'Ngân hàng thương mại',
  SECURITIES: 'Công ty chứng khoán',
  REAL_ESTATE: 'Bất động sản',
  INSURANCE: 'Bảo hiểm',
  HOLDING: 'Công ty quản lý / đầu tư vốn',
  CYCLICAL: 'Doanh nghiệp mang tính chu kỳ',
};

export const METRIC_MAP = {
  revenue_growth: 'Tăng trưởng doanh thu',
  revenue_cagr: 'Tăng trưởng doanh thu thuần',
  net_profit_cagr: 'Tăng trưởng lợi nhuận sau thuế',
  median_roe: 'ROE trung vị',
  margin_trend: 'Xu hướng biên lợi nhuận',
  pat_volatility: 'Mức ổn định lợi nhuận',
  avg_cfo_pat: 'Khả năng chuyển lợi nhuận thành dòng tiền',
  latest_debt_equity: 'Mức nợ so với vốn chủ sở hữu',
  dilution: 'Mức pha loãng cổ phiếu',
  accounting_consistency: 'Tính nhất quán của báo cáo tài chính',
  forensics: 'Kiểm tra dấu hiệu bất thường',
};

export function formatClassification(code) {
  if (!code) return 'Chưa xác định';
  return CLASSIFICATION_MAP[String(code).toUpperCase()] || String(code);
}

export function formatValueTrap(code) {
  if (!code) return 'Chưa xác định';
  return VALUETRAP_MAP[String(code).toUpperCase()] || String(code);
}

export function formatDeterioration(code) {
  if (!code) return 'Chưa xác định';
  return DETERIORATION_MAP[String(code).toUpperCase()] || String(code);
}

export function formatArchetype(code) {
  if (!code) return 'Chưa xác định';
  return ARCHETYPE_MAP[String(code).toUpperCase()] || String(code);
}

export function formatMetricName(code) {
  if (!code) return '';
  return METRIC_MAP[String(code).toLowerCase()] || String(code).replace(/_/g, ' ');
}

export const COMPARISON_MAP = {
  'actual_mos >= required_mos': 'Biên an toàn đạt yêu cầu',
  'actual_mos < required_mos': 'Biên an toàn chưa đạt yêu cầu',
  'price < base_intrinsic_value': 'Giá thị trường thấp hơn giá trị nội tại cơ sở',
  'price >= base_intrinsic_value': 'Giá thị trường cao hơn hoặc bằng giá trị nội tại cơ sở',
  'receivables_growth > revenue_growth': 'Khoản phải thu tăng nhanh hơn doanh thu',
  'receivables_growth <= revenue_growth': 'Khoản phải thu tăng trưởng tương đương hoặc chậm hơn doanh thu',
  'inventory_growth > revenue_growth': 'Hàng tồn kho tăng nhanh hơn doanh thu',
  'inventory_growth <= revenue_growth': 'Hàng tồn kho tăng trưởng kiểm soát tốt so với doanh thu',
  'debt > cash': 'Nợ vay cao hơn lượng tiền mặt',
  'debt <= cash': 'Tiền mặt duy trì cao hơn tổng nợ vay',
  'cfo < pat': 'Dòng tiền kinh doanh nhỏ hơn lợi nhuận sau thuế',
  'cfo >= pat': 'Dòng tiền kinh doanh bảo chứng mạnh mẽ cho lợi nhuận sau thuế',
  'normalized_earnings_trend < 0': 'Sức kiếm tiền bình thường hóa đang suy giảm',
  'normalized_earnings_trend >= 0': 'Sức kiếm tiền bình thường hóa duy trì ổn định',
};

export const SYSTEM_INVARIANTS_MAP = {
  NULL_NOT_ZERO: {
    formula: 'NULL != 0',
    title: 'Dữ liệu thiếu (NULL)',
    explanation: 'Thiếu dữ liệu không được xem là giá trị bằng không.',
  },
  UNKNOWN_NOT_PASS: {
    formula: 'UNKNOWN != PASS',
    title: 'Chưa đủ dữ liệu',
    explanation: 'Chưa đủ dữ liệu để kết luận đạt.',
  },
  WATCH_NOT_FAIL: {
    formula: 'WATCH != FAIL',
    title: 'Cảnh báo theo dõi',
    explanation: 'Cần theo dõi, nhưng chưa đủ bằng chứng để kết luận không đạt.',
  },
  NOT_APPLICABLE_NOT_UNKNOWN: {
    formula: 'NOT_APPLICABLE != UNKNOWN',
    title: 'Không áp dụng',
    explanation: 'Chỉ tiêu không phù hợp với loại hình doanh nghiệp, không phải do thiếu dữ liệu.',
  },
};

export const FINDING_TITLES = {
  RECEIVABLES_GROW_FASTER_THAN_REVENUE: 'Khoản phải thu tăng nhanh hơn doanh thu',
  INVENTORY_GROW_FASTER_THAN_REVENUE: 'Hàng tồn kho tăng nhanh hơn doanh thu',
  WEAK_CASH_CONVERSION: 'Dòng tiền kinh doanh chưa tương ứng với lợi nhuận',
  DEBT_FUNDED_LOW_QUALITY_GROWTH: 'Tăng trưởng phụ thuộc nhiều vào nợ vay',
  EXCESSIVE_DEBT_LEVERAGE: 'Đòn bẩy tài chính ở mức cao',
  UNSTABLE_EARNINGS_HISTORY: 'Biến động lợi nhuận bất ổn qua các năm',
  WEAK_PROFITABILITY_ROE: 'Tỷ suất sinh lời trên vốn chủ sở hữu (ROE) khiêm tốn',
  PER_SHARE_VALUE_DILUTION: 'Lợi nhuận trên mỗi cổ phiếu (EPS) bị pha loãng',
  ACCOUNTING_IDENTITY_DISCREPANCY: 'Lệch dữ liệu phương trình kế toán',
};

/**
 * Format status code to investor Vietnamese
 */
export function formatStatus(status) {
  if (!status) return 'Chưa xác định';
  return STATUS_MAP[String(status).toUpperCase()] || String(status);
}

/**
 * Format investment decision state to investor Vietnamese
 */
export function formatDecision(decision) {
  if (!decision) return 'Chưa xác định';
  return DECISION_MAP[String(decision).toUpperCase()] || String(decision);
}

/**
 * Format math comparison expression to human readable Vietnamese
 */
export function formatComparison(expr) {
  if (!expr) return '';
  const norm = String(expr).trim();
  if (COMPARISON_MAP[norm]) return COMPARISON_MAP[norm];

  return norm
    .replace(/>=/g, ' đạt hoặc vượt ')
    .replace(/<=/g, ' nhỏ hơn hoặc bằng ')
    .replace(/>/g, ' lớn hơn ')
    .replace(/</g, ' nhỏ hơn ')
    .replace(/==/g, ' bằng ')
    .replace(/!=/g, ' khác ')
    .replace(/_/g, ' ');
}

/**
 * Format a finding object into structured 6-question investor narrative
 */
export function formatFindingNarrative(finding) {
  if (!finding) return null;

  // Use pre-computed backend vietnamese_explanation if provided
  if (finding.vietnamese_explanation) {
    return finding.vietnamese_explanation;
  }

  const code = finding.code || '';
  const statusStr = formatStatus(finding.status || 'WATCH');
  const title = FINDING_TITLES[code] || (code ? code.replace(/_/g, ' ').toUpperCase() : 'Cảnh báo tài chính');

  return {
    tieu_de: title,
    dieu_gi_dang_xay_ra: finding.explanation || `Phát hiện chỉ tiêu ${title} thuộc diện phân tích tài chính.`,
    xu_huong_keo_dai: finding.start_period && finding.end_period ? `Giai đoạn FY${finding.start_period}–FY${finding.end_period}` : 'Theo dõi lịch sử tài chính nhiều năm',
    vi_sao_quan_trong: 'Chỉ tiêu này trực tiếp ảnh hưởng đến sức khỏe tài chính và dòng tiền doanh nghiệp.',
    muc_do_nghiem_trong: statusStr,
    du_lieu_chung_minh: finding.impact || 'Dữ liệu BCTC chuẩn hóa SSI',
    anh_huong_dai_han: 'Cần xem xét kỹ trong mô hình định giá và xác định Biên an toàn (MOS).',
  };
}
