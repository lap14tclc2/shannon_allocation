/**
 * Centralized Vietnamese Semantic Presentation Layer for QPort (Task 140, Task 145).
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
  UNKNOWN: 'Chưa xác định',
  NOT_APPLICABLE: 'Không áp dụng',
  MISSING: 'Chưa đủ dữ liệu',
  INSUFFICIENT_DATA: 'Chưa đủ dữ liệu',
  CLEAR: 'Chưa thấy dấu hiệu bẫy giá trị đáng kể',
  HIGH_RISK: 'Rủi ro cao',
  INFO: 'Thông tin',
  LOW: 'Rủi ro thấp',
  MEDIUM: 'Rủi ro trung bình',
  HIGH: 'Rủi ro cao',
  CRITICAL: 'Rủi ro rất cao',
  READY: 'Sẵn sàng',
  PARTIAL: 'Khả thi một phần',
  INSUFFICIENT: 'Chưa đủ dữ liệu',
  RESILIENT: 'Khả năng chống chịu tốt',
  VULNERABLE: 'Dễ bị tổn thương',
  UNSAFE: 'Dưới mức an toàn',
  DEPLETED: 'Cạn kiệt',
  EXTREME: 'Cực đoan',
  AVAILABLE: 'Có dữ liệu',
  UNAVAILABLE: 'Chưa lấy được dữ liệu',
};

export const QUALITY_TIER_MAP = {
  EXCEPTIONAL: 'Xuất sắc',
  HIGH_QUALITY: 'Chất lượng cao',
  INVESTABLE: 'Có thể đầu tư',
  WATCH: 'Cần theo dõi',
  LOW_QUALITY: 'Chất lượng thấp',
  REVIEW_BUSINESS: 'Cần xem xét thêm',
  INSUFFICIENT_DATA: 'Chưa đủ dữ liệu',
  UNKNOWN: 'Chưa xác định',
};

export const FORTRESS_STATUS_MAP = {
  SAFE: 'An toàn',
  VULNERABLE: 'Dễ tổn thương',
  UNSAFE: 'Dưới mức an toàn',
  DEPLETED: 'Cạn kiệt',
  UNKNOWN: 'Chưa cấu hình',
  INSUFFICIENT_DATA: 'Chưa đủ dữ liệu',
};

export const LIABILITY_STATUS_MAP = {
  COVERED: 'Đã được bảo đảm an toàn',
  UNCOVERED: 'Chưa được bảo đảm',
  ZERO_DEBT: 'Không có nợ ngắn hạn',
  MANAGEABLE: 'Trong tầm kiểm soát',
  HIGH_PRESSURE: 'Áp lực nợ cao',
  CRITICAL: 'Áp lực nợ nghiêm trọng',
  SAFE: 'An toàn',
  UNKNOWN: 'Chưa xác định',
};

export const SOURCE_MAP = {
  PRIMARY_SSI: 'Nguồn BCTC: SSI',
  SSI: 'Nguồn BCTC: SSI',
  DERIVED: 'Tổng hợp chuẩn hóa',
  POSTGRES_CATALOG: 'Cơ sở dữ liệu QPort',
  VNDIRECT: 'VNDirect',
  MOCK: 'Dữ liệu thử nghiệm',
};

export const DECISION_MAP = {
  BUY: 'Có thể mua',
  BUY_MORE: 'Có thể mua thêm',
  BUY_UNDER_MOS: 'Đạt chuẩn mua tích sản',
  CONDITIONAL_BUY: 'Có thể mua có điều kiện / Cần theo dõi',
  BUY_WATCH: 'Có thể mua có điều kiện / Cần theo dõi',
  WAIT_FOR_QUALITY_CONFIRMATION: 'Chờ xác nhận chất lượng tài chính',
  BUY_WITH_MOS: 'Có thể mua khi đạt Biên an toàn (MOS)',
  WAIT_FOR_IMPROVEMENT: 'Chờ bằng chứng cải thiện',
  STUDY_FURTHER: 'Tiếp tục nghiên cứu',
  HOLD: 'Tiếp tục nắm giữ',
  HOLD_NO_NEW_CAPITAL: 'Tiếp tục nắm giữ, chưa phân bổ thêm vốn',
  WAIT_FOR_MOS: 'Chờ đạt biên an toàn',
  BUILD_RESERVE_FIRST: 'Ưu tiên củng cố quỹ dự phòng trước',
  REVIEW_BUSINESS: 'Cần xem xét thêm dữ liệu doanh nghiệp',
  BUSINESS_REVIEW_INCOMPLETE: 'Đánh giá doanh nghiệp chưa hoàn tất',
  AVOID: 'Chưa phù hợp để đầu tư',
  DO_NOT_BUY: 'Không mua',
  SELL_REVIEW: 'Cần xem xét lại luận điểm nắm giữ',
  SELL: 'Cân nhắc thoái vốn',
  REDUCE: 'Cân nhắc giảm tỷ trọng',
  KEEP_CASH: 'Ưu tiên giữ tiền mặt',
};

export const CLASSIFICATION_MAP = {
  COMPOUNDER: 'Doanh nghiệp tích lũy giá trị dài hạn',
  POTENTIAL_COMPOUNDER: 'Doanh nghiệp có tiềm năng tăng trưởng giá trị dài hạn',
  AVERAGE_BUSINESS: 'Doanh nghiệp có chất lượng trung bình',
  CYCLICAL_QUALITY: 'Doanh nghiệp chất lượng mang tính chu kỳ',
  WEAK_BUSINESS: 'Chất lượng doanh nghiệp còn yếu',
  DETERIORATING_BUSINESS: 'Nền tảng kinh doanh đang suy yếu',
  INSUFFICIENT_DATA: 'Chưa đủ dữ liệu để đánh giá',
  UNKNOWN: 'Chưa xác định',
};

export const VALUETRAP_MAP = {
  CLEAR: 'Chưa thấy dấu hiệu bẫy giá trị đáng kể',
  WATCH: 'Có dấu hiệu cần theo dõi',
  HIGH_RISK: 'Nguy cơ bẫy giá trị cao',
  INSUFFICIENT_DATA: 'Chưa đủ dữ liệu',
  UNPROTECTED: 'Chưa được bảo vệ trong kịch bản thận trọng',
  STRUCTURAL_EVIDENCE: 'Bằng chứng suy giảm cấu trúc',
  POSSIBLY_STRUCTURAL: 'Có rủi ro suy giảm cấu trúc',
  LIKELY_CYCLICAL: 'Suy giảm có tính chu kỳ',
  NO_DETERIORATION: 'Không có dấu hiệu suy giảm',
};

export const DETERIORATION_MAP = {
  NO_DETERIORATION: 'Không có dấu hiệu suy giảm',
  LIKELY_CYCLICAL: 'Suy giảm có khả năng mang tính chu kỳ',
  POSSIBLY_CYCLICAL: 'Có dấu hiệu suy giảm mang tính chu kỳ',
  POSSIBLY_STRUCTURAL: 'Có rủi ro suy giảm cấu trúc',
  STRUCTURAL: 'Đã phát hiện suy giảm mang tính cấu trúc',
  STRUCTURAL_EVIDENCE: 'Bằng chứng suy giảm cấu trúc',
  UNKNOWN: 'Chưa đủ dữ liệu để xác định',
  NEUTRAL: 'Trung tính',
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

export const MARGIN_TREND_MAP = {
  EXPANDING: 'Đang mở rộng',
  STABLE: 'Ổn định',
  DECLINING: 'Đang thu hẹp',
  NOT_APPLICABLE: 'Không áp dụng',
};

export const METRIC_MAP = {
  revenue_growth: 'Tăng trưởng doanh thu',
  revenue_cagr: 'Tăng trưởng doanh thu thuần',
  net_profit_cagr: 'Tăng trưởng lợi nhuận sau thuế',
  median_roe: 'ROE trung vị',
  margin_trend: 'Xu hướng biên lợi nhuận',
  pat_volatility: 'Mức ổn định lợi nhuận',
  profit_volatility: 'Mức ổn định lợi nhuận',
  avg_cfo_pat: 'Khả năng chuyển lợi nhuận thành dòng tiền',
  latest_debt_equity: 'Mức nợ so với vốn chủ sở hữu',
  debt_equity_ratio: 'Mức nợ so với vốn chủ sở hữu',
  annual_share_growth: 'Tăng trưởng số lượng cổ phiếu',
  share_cagr: 'Tăng trưởng số lượng cổ phiếu',
  dilution: 'Mức pha loãng cổ phiếu',
  accounting_consistency: 'Tính nhất quán của báo cáo tài chính',
  forensics: 'Kiểm tra dấu hiệu bất thường',
};

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

export const FINDING_TITLES = {
  RECEIVABLES_GROW_FASTER_THAN_REVENUE: 'Khoản phải thu tăng nhanh hơn doanh thu',
  PROFIT_CASH_DIVERGENCE: 'Lợi nhuận tăng nhưng dòng tiền không theo kịp',
  WEAK_CASH_CONVERSION: 'Dòng tiền kinh doanh chưa tương ứng với lợi nhuận',
  INVENTORY_BUILDUP: 'Hàng tồn kho gia tăng bất thường',
  INVENTORY_GROWTH_EXCEEDS_SALES: 'Hàng tồn kho tăng nhanh hơn doanh thu',
  INVENTORY_GROW_FASTER_THAN_REVENUE: 'Hàng tồn kho tăng nhanh hơn doanh thu',
  DEBT_FUNDED_LOW_QUALITY_GROWTH: 'Tăng trưởng phụ thuộc nhiều vào nợ vay',
  EXCESSIVE_DEBT_LEVERAGE: 'Đòn bẩy tài chính ở mức cao',
  UNSTABLE_EARNINGS_HISTORY: 'Biến động lợi nhuận bất ổn qua các năm',
  WEAK_PROFITABILITY_ROE: 'Tỷ suất sinh lời trên vốn chủ sở hữu (ROE) khiêm tốn',
  PER_SHARE_VALUE_DILUTION: 'Lợi nhuận trên mỗi cổ phiếu (EPS) bị pha loãng',
  ACCOUNTING_IDENTITY_DISCREPANCY: 'Lệch dữ liệu phương trình kế toán',
  WEAK_BANK_ROE: 'ROE ngân hàng ở mức thấp so với tiêu chuẩn',
  LOW_BANK_CAPITAL_ADEQUACY: 'Tỷ lệ an toàn vốn chủ sở hữu ngân hàng mỏng',
  WEAK_SECURITIES_ROE: 'ROE công ty chứng khoán ở mức thấp',
  TRADING_INCOME_DEPENDENCE: 'Phụ thuộc lớn vào hoạt động tự doanh / FVTPL',
  SECURITIES_HIGH_LEVERAGE: 'Đòn bẩy công ty chứng khoán ở mức cao',
};

export function formatStatus(status) {
  if (!status) return 'Chưa xác định';
  const s = String(status).toUpperCase().trim();
  return STATUS_MAP[s] || (s.includes('_') ? s.toLowerCase().replace(/_/g, ' ') : s);
}

export function formatDecision(decision) {
  if (!decision) return 'Chưa xác định';
  const d = String(decision).toUpperCase().trim();
  return DECISION_MAP[d] || (d.includes('_') ? d.toLowerCase().replace(/_/g, ' ') : d);
}

export function formatClassification(code) {
  if (!code) return 'Chưa xác định';
  const c = String(code).toUpperCase().trim();
  return CLASSIFICATION_MAP[c] || (c.includes('_') ? c.toLowerCase().replace(/_/g, ' ') : c);
}

export function formatValueTrap(code) {
  if (!code) return 'Chưa xác định';
  const c = String(code).toUpperCase().trim();
  return VALUETRAP_MAP[c] || (c.includes('_') ? c.toLowerCase().replace(/_/g, ' ') : c);
}

export function formatDeterioration(code) {
  if (!code) return 'Chưa xác định';
  const c = String(code).toUpperCase().trim();
  return DETERIORATION_MAP[c] || (c.includes('_') ? c.toLowerCase().replace(/_/g, ' ') : c);
}

export function formatArchetype(code) {
  if (!code) return 'Chưa xác định';
  const c = String(code).toUpperCase().trim();
  return ARCHETYPE_MAP[c] || (c.includes('_') ? c.toLowerCase().replace(/_/g, ' ') : c);
}

export function formatMarginTrend(trend) {
  if (!trend) return 'Chưa xác định';
  const t = String(trend).toUpperCase().trim();
  return MARGIN_TREND_MAP[t] || (t.includes('_') ? t.toLowerCase().replace(/_/g, ' ') : t);
}

export function formatFindingTitle(code) {
  if (!code) return 'Chưa xác định';
  const uCode = String(code).toUpperCase().trim();
  if (FINDING_TITLES[uCode]) return FINDING_TITLES[uCode];
  if (uCode.includes('_')) {
    return uCode.toLowerCase().replace(/_/g, ' ').replace(/\b\w/g, (ch) => ch.toUpperCase());
  }
  return uCode;
}

export function formatQualityTier(code) {
  if (!code) return 'Chưa xác định';
  const c = String(code).toUpperCase().trim();
  return QUALITY_TIER_MAP[c] || (c.includes('_') ? c.toLowerCase().replace(/_/g, ' ') : c);
}

export function formatFortressStatus(status) {
  if (!status) return 'Chưa cấu hình';
  const s = String(status).toUpperCase().trim();
  return FORTRESS_STATUS_MAP[s] || formatStatus(s);
}

export function formatLiabilityStatus(status) {
  if (!status) return 'Chưa xác định';
  const s = String(status).toUpperCase().trim();
  return LIABILITY_STATUS_MAP[s] || (s.includes('_') ? s.toLowerCase().replace(/_/g, ' ') : s);
}

export function formatSource(src) {
  if (!src) return 'Nguồn BCTC: SSI';
  const s = String(src).toUpperCase().trim();
  return SOURCE_MAP[s] || `Nguồn: ${src}`;
}

export function formatSafeText(val, fallback = 'Chưa đủ dữ liệu') {
  if (val === null || val === undefined) return fallback;
  const str = String(val).trim();
  if (['null', 'undefined', 'nullx', 'NaN', 'N/A', 'UNKNOWN', '—', ''].includes(str)) {
    return fallback;
  }
  return str;
}

export function formatMetricName(code) {
  if (!code) return 'Chưa xác định';
  const norm = String(code).toLowerCase().trim();
  return METRIC_MAP[norm] || norm.replace(/_/g, ' ');
}

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

export function formatFindingNarrative(finding) {
  if (!finding) return null;

  if (finding.vietnamese_explanation) {
    return finding.vietnamese_explanation;
  }

  const code = finding.code || '';
  const statusStr = formatStatus(finding.status || 'WATCH');
  const title = formatFindingTitle(code);

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

export function formatPct(val, fallback = 'Chưa đủ dữ liệu') {
  if (val === null || val === undefined || isNaN(val)) {
    return fallback;
  }
  const num = Number(val);
  return (num > 0 ? '+' : '') + num.toFixed(1) + '%';
}

export function formatRatioX(val, fallback = 'Chưa đủ dữ liệu') {
  if (val === null || val === undefined || isNaN(val)) {
    return fallback;
  }
  return Number(val).toFixed(2) + 'x';
}

export function formatDebtEquity(val, archetype, fallback = 'Chưa đủ dữ liệu nợ và vốn chủ sở hữu') {
  const arch = String(archetype || '').toUpperCase().trim();
  if (arch === 'BANK') {
    return 'Không áp dụng cho ngân hàng thương mại';
  }
  if (arch === 'SECURITIES') {
    if (val !== null && val !== undefined && !isNaN(val)) {
      return Number(val).toFixed(2) + 'x (Nợ / Vốn chủ)';
    }
    return 'Thương lượng đòn bẩy tự doanh / Margin';
  }
  if (val === null || val === undefined || isNaN(val)) {
    return fallback;
  }
  return Number(val).toFixed(2) + 'x';
}

export function formatCfoPat(val, fallback = 'Chưa đủ dữ liệu dòng tiền hoạt động') {
  if (val === null || val === undefined || isNaN(val)) {
    return fallback;
  }
  return Number(val).toFixed(2) + 'x';
}

export function formatVND(num, fallback = 'Chưa có dữ liệu') {
  if (num === null || num === undefined || isNaN(num)) return fallback;
  const n = Number(num);
  if (Math.abs(n) >= 1e12) return (n / 1e12).toFixed(2) + ' nghìn tỷ';
  if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(1) + ' tỷ';
  return n.toLocaleString('vi-VN') + ' đ';
}

