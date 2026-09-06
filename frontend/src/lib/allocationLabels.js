// Vietnamese human labels for the Allocation module.
// Business logic never depends on these strings; they are presentation only.

export const REASON_CODE_VI = {
  QUALITY_STRONG: 'Doanh nghiệp chất lượng cao, lợi thế cạnh tranh rõ ràng.',
  QUALITY_DETERIORATING: 'Chất lượng doanh nghiệp suy giảm, cần thận trọng.',
  HARD_REJECT: 'Vi phạm tiêu chí loại trừ cứng của Buffett/Munger.',
  VALUATION_ATTRACTIVE: 'Mức giá có biên an toàn hấp dẫn.',
  VALUATION_FAIR: 'Mức giá hợp lý, chưa đủ biên an toàn vượt trội.',
  VALUATION_EXPENSIVE: 'Mức giá cao hơn giá trị hợp lý.',
  VALUATION_CONFIDENCE_LOW: 'Độ tin cậy định giá thấp, thiếu bằng chứng.',
  VALUATION_SAFETY_POSITIVE: 'Biên an toàn thực tế vượt mức yêu cầu.',
  VALUATION_SAFETY_NEGATIVE: 'Biên an toàn thực tế thấp hơn mức yêu cầu.',
  POSITION_CONCENTRATED: 'Tỷ trọng nắm giữ đang quá tập trung.',
  RISK_CONTRIBUTION_HIGH: 'Mã này đóng góp rủi ro quá lớn cho danh mục.',
  CORRELATION_HIGH: 'Tương quan cao với các vị thế hiện tại.',
  DIVERSIFICATION_IMPROVES: 'Bổ sung giúp cải thiện đa dạng hóa danh mục.',
  DIVERSIFICATION_WORSENS: 'Bổ sung làm giảm hiệu quả đa dạng hóa.',
  NO_SUPERIOR_REPLACEMENT: 'Không có cơ hội thay thế tốt hơn hẳn hiện tại.',
  SUPERIOR_REPLACEMENT_AVAILABLE: 'Có cơ hội thay thế tốt hơn rõ rệt.',
  LIQUIDITY_INSUFFICIENT: 'Thanh khoản không đủ để giao dịch quy mô cần thiết.',
  CASH_PREFERRED: 'Giữ tiền mặt là lựa chọn hợp lý hiện tại.',
  TECHNICAL_CONFIRMATION: 'Xu hướng giá xác nhận quyết định cơ bản.',
  TECHNICAL_DETERIORATION: 'Diễn biến giá suy yếu, chưa nên mua thêm.',
  DATA_INSUFFICIENT: 'Thiếu dữ liệu, không thể kết luận đáng tin cậy.',
};

export function reasonCodeVi(code) {
  return REASON_CODE_VI[code] || code;
}

export const ACTION_LABEL_VI = {
  BUY_MORE: 'Mua thêm',
  HOLD: 'Giữ nguyên',
  WATCH: 'Theo dõi',
  REDUCE: 'Giảm bớt',
  SELL: 'Bán',
  KEEP_CASH: 'Giữ tiền mặt',
};

export const ACTION_TONE = {
  BUY_MORE: 'buy',
  HOLD: 'hold',
  WATCH: 'watch',
  REDUCE: 'reduce',
  SELL: 'sell',
  KEEP_CASH: 'cash',
};

export const POSTURE_LABEL_VI = {
  HOLD_SELECTIVE_BUY: 'Giữ vững, chỉ mua thêm chọn lọc',
  KEEP_CASH: 'Giữ tiền mặt',
  ROTATE_OR_REVIEW: 'Cân nhắc xoay vòng / rà soát danh mục',
};

export const FIT_LABEL_VI = {
  GOOD: 'Phù hợp tốt',
  MODERATE: 'Chấp nhận được',
  WEAK: 'Kém phù hợp',
  UNAVAILABLE: 'Chưa đủ dữ liệu',
};

export const CONFIDENCE_LABEL_VI = {
  HIGH: 'Cao',
  MEDIUM: 'Trung bình',
  LOW: 'Thấp',
};

export const CONVICTION_LABEL_VI = {
  STARTER: 'Vị thế khởi tạo',
  NORMAL: 'Vị thế thường',
  HIGH_CONVICTION: 'Vị thế tin cậy cao',
};

export const ELIGIBILITY_LABEL_VI = {
  INVESTABLE: 'Đầu tư được',
  WATCHLIST: 'Theo dõi',
  INELIGIBLE: 'Không đủ điều kiện',
};