// Vietnamese human labels for the Allocation module.
// Business logic never depends on these strings; they are presentation only.

export const REASON_CODE_VI = {
  QUALITY_STRONG: 'Doanh nghiệp chất lượng cao, lợi thế cạnh tranh rõ ràng.',
  QUALITY_DETERIORATING: 'Chất lượng doanh nghiệp suy giảm, cần thận trọng.',
  HARD_REJECT: 'Vi phạm tiêu chí loại trừ cứng của Buffett/Munger.',
  THESIS_BROKEN: 'Vi phạm luận điểm đầu tư cốt lõi.',
  VALUATION_ATTRACTIVE: 'Mức giá có biên an toàn hấp dẫn.',
  VALUATION_FAIR: 'Mức giá hợp lý, chưa đủ biên an toàn vượt trội.',
  VALUATION_EXPENSIVE: 'Mức giá cao hơn giá trị hợp lý.',
  VALUATION_CONFIDENCE_LOW: 'Độ tin cậy định giá thấp, thiếu bằng chứng.',
  VALUATION_SAFETY_POSITIVE: 'Biên an toàn thực tế vượt mức yêu cầu.',
  VALUATION_SAFETY_NEGATIVE: 'Biên an toàn thực tế thấp hơn mức yêu cầu.',
  VALUATION_SAFETY_INSUFFICIENT: 'Biên an toàn chưa đủ để cam kết vốn mới.',
  VALUATION_SAFETY_IMPROVES: 'Biên an toàn của ứng viên tốt hơn rõ rệt vị thế hiện tại.',
  NO_PUBLIC_VALUATION: 'Chưa có định giá công khai.',
  POSITION_CONCENTRATED: 'Tỷ trọng nắm giữ đang quá tập trung.',
  CONCENTRATED_THESIS_RISK: 'Tỷ trọng lớn — nếu luận điểm đầu tư sai sót, mức độ ảnh hưởng đến NAV sẽ rất đáng kể.',
  CYCLICAL_EARNINGS: 'Lợi nhuận ròng mang tính chu kỳ ngành, không phải tổn thất kinh doanh vĩnh viễn.',
  BALANCE_SHEET_REVIEW: 'Chỉ số an toàn nợ vay / bảng cân đối tài chính cần được rà soát định kỳ.',
  VOLATILITY_HIGH: 'Mức độ biến động giá ngắn hạn cao hơn nền trung bình.',
  PERMANENT_LOSS_DATA_INSUFFICIENT: 'Chưa đủ dữ liệu canonical để khẳng định độ an toàn chống mất vốn vĩnh viễn.',
  RISK_CONTRIBUTION_HIGH: 'Mã này đóng góp rủi ro quá lớn cho danh mục.',
  CORRELATION_HIGH: 'Tương quan cao với các vị thế hiện tại.',
  PORTFOLIO_FIT_WEAK: 'Mức độ phù hợp với danh mục kém.',
  PORTFOLIO_FIT_IMPROVES: 'Bổ sung giúp cải thiện mức độ phù hợp rủi ro danh mục.',
  DIVERSIFICATION_IMPROVES: 'Bổ sung giúp cải thiện đa dạng hóa danh mục.',
  DIVERSIFICATION_WORSENS: 'Bổ sung làm giảm hiệu quả đa dạng hóa.',
  NO_SUPERIOR_REPLACEMENT: 'Không có cơ hội thay thế tốt hơn hẳn hiện tại.',
  SUPERIOR_REPLACEMENT_AVAILABLE: 'Có cơ hội thay thế tốt hơn rõ rệt.',
  LIQUIDITY_INSUFFICIENT: 'Thanh khoản không đủ để giao dịch quy mô cần thiết.',
  CASH_PREFERRED: 'Giữ tiền mặt là lựa chọn hợp lý hiện tại.',
  TECHNICAL_CONFIRMATION: 'Xu hướng giá xác nhận quyết định cơ bản.',
  TECHNICAL_DETERIORATION: 'Diễn biến giá suy yếu, chưa nên mua thêm.',
  DATA_INSUFFICIENT: 'Thiếu dữ liệu, không thể kết luận đáng tin cậy.',
  REVIEW_REQUIRED: 'Cần rà soát dữ liệu định giá / rủi ro.',
  WATCH_VALUATION_TOO_EXPENSIVE: 'Định giá cao hơn vùng mua an toàn.',
  WATCH_MOS_NEAR_THRESHOLD: 'Biên an toàn gần đạt ngưỡng yêu cầu.',
  WATCH_PORTFOLIO_FIT_WEAK: 'Mức độ phù hợp danh mục chưa đạt chuẩn mua.',
  WATCH_SECTOR_CONCENTRATION: 'Tỷ trọng ngành hiện tại cao, cần thêm không gian.',
  WATCH_LOW_VALUATION_CONFIDENCE: 'Mức tin cậy định giá chưa đủ cao để giải ngân.',
  WATCH_DATA_INCOMPLETE: 'Dữ liệu định giá / tài chính chưa đầy đủ.',
  WATCH_LIQUIDITY_BELOW_BUY_THRESHOLD: 'Thanh khoản đạt ngưỡng nghiên cứu nhưng chưa đủ ngưỡng MUA.',
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

export const CURRENT_WEIGHT_LABEL_VI = 'Tỷ trọng hiện tại';
export const POST_ACTION_WEIGHT_LABEL_VI = 'Tỷ trọng sau đề xuất';
export const NEW_POSITION_GUIDANCE_LABEL_VI = 'Mức vốn gợi ý khi mở vị thế mới';

export const ALLOCATION_TOOLTIPS_VI = {
  CURRENT_WEIGHT: 'Phần trăm giá trị danh mục đang nằm ở mã này.',
  POST_ACTION_WEIGHT: 'Tỷ trọng ước tính nếu làm theo khuyến nghị hiện tại.',
  NEW_POSITION_GUIDANCE: 'Mức vốn QPort gợi ý khi bắt đầu xây vị thế mới theo chất lượng, định giá và giới hạn rủi ro hiện tại. Không phải mức bắt buộc cho vị thế đang có.',
};

export const ELIGIBILITY_LABEL_VI = {
  INVESTABLE: 'Đầu tư được',
  WATCHLIST: 'Theo dõi',
  INELIGIBLE: 'Không đủ điều kiện',
};