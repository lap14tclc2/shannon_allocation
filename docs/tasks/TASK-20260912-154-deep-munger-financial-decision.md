# TASK-20260912-154: Deep Audit & Refactor Munger BCTC-Only Decision Engine

- **ID**: TASK-20260912-154
- **Title**: Deep Audit & Refactor Munger BCTC-Only Decision Engine
- **Status**: completed
- **Priority**: high
- **Date**: 2026-09-12

---

## Requirement

1. Audit toàn bộ decision engine và value engine của QPort để chuyển đổi triệt để sang mô hình Munger BCTC-Only.
2. Nguồn dữ liệu duy nhất cho quyết định tài chính: BCTC thường niên SSI đã canonicalize vào PostgreSQL (FY2011–FY2025). Không sử dụng news, sentiment, analyst report hay phỏng vấn định tính.
3. Loại bỏ việc Qualitative UNKNOWN (Circle of competence, qualitative moat, management integrity) làm blocker chặn quyết định tài chính (`UNKNOWN` -> `REVIEW_BUSINESS` -> không mua).
4. Thiết kế lại Waterfall 16 Gate quyết định theo đúng thứ tự nghiêm ngặt (Data Completeness -> Accounting Consistency -> Balance Sheet -> Earnings Quality -> Cash Conversion -> Earnings Durability -> Capital Efficiency -> Capital Allocation -> Dilution -> Financial Forensics -> Value Trap -> Normalized Earnings -> Bear Case -> Valuation -> MOS -> Personal Capital).
5. Đảm bảo nguyên lý Munger: MOS là điều kiện về GIÁ, Financial Quality là điều kiện về DOANH NGHIỆP. Tuyệt đối không để MOS cao tự động biến một cổ phiếu có forensic warning/rủi ro thành BUY.
6. Deep dive CFO/PAT: chuỗi từng năm, median, mean, weighted ratio, số năm CFO < PAT, số năm CFO < 0, giải thích rõ các mâu thuẫn (như IDC có mean 3.08x do 1 năm đột biến nhưng các năm khác CFO < PAT).
7. Deep dive Receivables: tính Revenue CAGR vs Receivables CAGR, YoY từng năm, phân loại temporary vs persistent vs accelerating và tăng severity nếu kéo dài.
8. Deep dive Normalized Earnings: latest PAT, 3Y, 5Y, 10Y normalized, long-term median, mean, volatility (CV), phát hiện earnings peak/trough bất thường.
9. Deep dive Value Trap: tổng hợp 8+ chiều rủi ro, phân loại CLEAR / WATCH / HIGH_RISK với evidence cụ thể.
10. Tự động hóa Munger Q1–Q8 và measurable invalidation criteria dựa trên dữ liệu thật.
11. Rà soát UI ngữ nghĩa: 100% tiếng Việt, không để lọt bất kỳ mã enum backend nào (`PROFIT_CASH_DIVERGENCE`, `UNKNOWN`, `NOT_APPLICABLE`, `nullx`, `N/A`).
12. Deep dive audit thực tế trên golden symbols (IDC, ACB, DGC, FPT, VIX), giải thích sâu trường hợp IDC.

## Context

- `canonical_facts` trong PostgreSQL chứa hơn 286,000 sự kiện BCTC lịch sử.
- Architecture hiện tại đã có `munger_analyzer.py`, `munger_forensics.py`, `munger_thesis_challenge.py`, `policy/engine.py`.
- Đã tinh chỉnh sâu sắc các forensics logic, xóa bỏ các tàn dư blocker định tính, và liên kết chặt chẽ giữa Value Engine, Policy Engine và Terminal/Business UI.

## Acceptance Criteria

- [x] AC1: BCTC SSI là nguồn duy nhất; không có qualitative blocker.
- [x] AC2: 16-gate decision waterfall được triển khai đầy đủ và nhất quán.
- [x] AC3: CFO/PAT được bóc tách chi tiết từng năm kèm giải thích mâu thuẫn.
- [x] AC4: Phải thu vs Doanh thu phân biệt temporary / persistent / accelerating.
- [x] AC5: Normalized earnings bóc tách 3Y/5Y/10Y/median/volatility và phát hiện dị thường.
- [x] AC6: Value trap phân loại rõ ràng với đầy đủ bằng chứng thực tế.
- [x] AC7: MOS cao không tự động tạo false BUY khi có forensic warning.
- [x] AC8: Munger Q1-Q8 trả lời tự động bằng dữ liệu và có tiêu chí bác bỏ cụ thể.
- [x] AC9: Zero raw enum leakage trên toàn bộ frontend presentation layer.
- [x] AC10: Golden audit trên IDC, ACB, DGC, FPT, VIX thành công, giải thích rõ case IDC.
- [x] AC11: Bộ regression tests đầy đủ đạt 100% PASS (89/89 tests).
- [x] AC12: Frontend build PASS.

## Implementation Tasks

- [x] Phase 1: Nâng cấp `portfolio/value_engine/munger_forensics.py` (CFO/PAT chuỗi + mâu thuẫn, Receivables persistent/accelerating, 10 forensic pairings).
- [x] Phase 2: Nâng cấp `portfolio/value_engine/munger_analyzer.py` (Normalized earnings volatility, 16-gate waterfall, anti false-BUY gate).
- [x] Phase 3: Nâng cấp `portfolio/policy/engine.py` và `portfolio/policy/context_builder.py` để đồng bộ 16 gate và loại bỏ qualitative blockers.
- [x] Phase 4: Nâng cấp `portfolio/value_engine/munger_thesis_challenge.py` và `portfolio/value_engine/vietnamese_presenter.py`.
- [x] Phase 5: Nâng cấp `portfolio/canonical_valuation.py` hỗ trợ fallback lookup thị giá từ DB.
- [x] Phase 6: Xây dựng script audit và test suite `test_deep_munger_decision_engine.py`.
- [x] Phase 7: Chạy kiểm thử toàn diện, build frontend, cập nhật task note sang `completed`, commit và push.

## Validation Evidence

### 1. Pytest Results (89/89 passed)
```powershell
$env:PYTHONPATH="python"; $env:DATABASE_URL="postgresql://qport:qport@127.0.0.1:5432/qport"; python -m pytest python/portfolio/tests/test_deep_munger_decision_engine.py python/portfolio/tests/test_munger_financial_analysis.py python/portfolio/tests/test_munger_thesis_challenge.py python/portfolio/tests/test_munger_12d_metrics.py python/portfolio/tests/test_munger_business_valuation_integration.py python/portfolio/tests/test_munger_pipeline_regression.py python/portfolio/tests/test_buffett_munger_rule_engine.py python/portfolio/tests/test_buffett_munger_api_integration.py python/portfolio/tests/test_buffett_munger_end_to_end_integration.py python/portfolio/tests/test_decision_precedence.py python/portfolio/tests/test_financial_data.py python/portfolio/tests/test_financial_pipeline.py python/portfolio/tests/test_business_review_and_value_trap.py
============================= 89 passed in 15.70s =============================
```

### 2. Frontend Build
```powershell
npm --prefix frontend run build
✓ built in 1.71s
```

### 3. Golden Symbol Deep Dive Audit
- **IDC**: 12 năm lịch sử (2014-2025). Mean CFO/PAT = 3.08x (do 1 năm đột biến thu trước), nhưng có năm CFO < PAT, độ biến động LNST 80.6%. Mặc dù MOS = +37.6% (>= 25.0%), hệ thống ngăn chặn false BUY và chuyển thành `WAIT_FOR_MOS` kèm cảnh báo phân kỳ dòng tiền và biến động lợi nhuận.
- **ACB**: 15 năm lịch sử (2011-2025). Archetype Ngân hàng, Value Trap CLEAR. Thị giá 22,050 đ vs Base IV 27,055 đ (MOS = 18.5% < 25.0%) -> `WAIT_FOR_MOS`.
- **DGC**: 15 năm lịch sử (2011-2025). Compounder, Thị giá 38,751 đ vs Base IV 80,704 đ (MOS = 52.0% >= 50.0%), độ biến động 115.2% & cảnh báo chuyển hóa tiền mặt -> `WAIT_FOR_MOS` (Anti false-BUY).
- **FPT**: 15 năm lịch sử (2011-2025). Compounder, Thị giá 72,700 đ vs Base IV 95,282 đ (MOS = 23.7% >= 20.0%), cảnh báo phương trình kế toán & độ biến động 64.1% -> `WAIT_FOR_MOS`.
- **VIX**: 15 năm lịch sử (2011-2025). Công ty chứng khoán, xếp loại `WEAK_BUSINESS`, độ biến động LNST 218.9% (đột biến đỉnh chu kỳ) -> `AVOID` bất kể MOS +54.9%.

## Decisions

- Tách bạch tuyệt đối giữa điều kiện Doanh nghiệp (Financial Quality / Forensics / Value Trap) và điều kiện Giá (Valuation / Base IV / Bear IV / MOS). Một cổ phiếu dù có MOS +50% nhưng có rủi ro suy giảm cấu trúc hoặc bẫy giá trị thì quyết định vẫn là `AVOID` hoặc `WAIT_FOR_MOS / REVIEW_FINANCIAL_QUALITY`, tuyệt đối không `BUY`.
- Các yếu tố định tính không thể chứng minh từ BCTC được đánh dấu thông tin rõ ràng nhưng không chặn luồng quyết định vốn.

## Result

- Hệ thống quyết định đầu tư dài hạn Munger BCTC-Only đã được nâng cấp toàn diện, vận hành 100% dựa trên dữ liệu BCTC chuẩn hóa PostgreSQL.
- Toàn bộ 16 gate quyết định, 10 forensic pairings, CFO/PAT chuỗi đa năm, Normalized earnings power và Munger Q1-Q8 hoạt động chuẩn xác và hoàn toàn bằng tiếng Việt.
