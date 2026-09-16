# TASK-20260916-165 — Evidence-Based Receivables Forensic Gate & Low-Base Multi-Signal Synthesis

| Field | Value |
|---|---|
| status | completed |
| created | 2026-09-16 |
| task-id | TASK-20260916-165 |

---

## Requirement

Refactor forensic logic cho `RECEIVABLES_GROW_FASTER_THAN_REVENUE` trong Munger Financial Analysis Engine:
1. Chuyển từ quy tắc cứng (10Y CAGR gap > 10% -> FAIL) sang mô hình đánh giá 5 trục bằng chứng:
   - A. Long-Term Trend (10Y Historical signal & Low-Base detection)
   - B. Recent Trend (3Y CAGR Gap prioritization)
   - C. Materiality (Receivables/Revenue, Receivables/Assets, DSO & DSO change)
   - D. Cash Conversion (3Y CFO/PAT corroboration)
   - E. Persistence (One-Off vs Persistent vs Accelerating)
2. Bảo vệ trường hợp số gốc nhỏ (Low-Base effect) khi năm gốc có số dư phải thu quá nhỏ so với doanh thu.
3. Cập nhật `munger_thresholds.py` với các named thresholds chuẩn.
4. Expose structured evidence object đầy đủ (`long_term_gap`, `recent_gap`, `receivables_to_revenue`, `dso`, `cfo_pat`, `persistence`, `materiality_status`, `low_base_distortion`).
5. Không áp dụng máy móc cho Ngân hàng (BANK) và Chứng khoán (SECURITIES) (trả về `NOT_APPLICABLE`).
6. Đảm bảo Forensic WATCH không biến thành SELL hay chặn quyết định mua khi MOS đã đạt.
7. Viết regression tests cho 7 ca kiểm thử then chốt và tạo báo cáo `docs/reports/receivables-forensic-audit.md`.

## Context

Thuật toán cũ tính `gap_full = rec_cagr_10y - rev_cagr_10y > 10%`. Khi năm gốc (FY2014) có khoản phải thu rất nhỏ, CAGR 10 năm bị phóng đại toán học, khiến hầu như toàn bộ doanh nghiệp lành mạnh (như FPT, DGC, CTR) đều bị dán cờ "Không đạt" / "Khoản phải thu tăng nhanh hơn doanh thu" mặc dù tỷ lệ phải thu / doanh thu cực thấp, DSO thấp và 3 năm gần đây thu tiền rất tốt.

## Acceptance Criteria

- [x] `munger_thresholds.py` bổ sung đầy đủ named thresholds cho 5 trục bằng chứng.
- [x] `run_receivables_forensics()` trong `munger_forensics.py` áp dụng ma trận 5 trục (Long-Term, Recent 3Y, Materiality, Cash Conversion, Persistence).
- [x] Low-base effect được phát hiện và không bị xử lý thành FAIL.
- [x] Structured finding object có đầy đủ metrics và ngữ nghĩa tiếng Việt chuẩn.
- [x] BANK và SECURITIES trả về `NOT_APPLICABLE` một cách tường minh.
- [x] Toàn bộ 7 kịch bản regression test được bổ sung và PASS 100%.
- [x] Tạo báo cáo chi tiết tại `docs/reports/receivables-forensic-audit.md`.
- [x] Commit lên branch `feature/buffett-munger-refactor` với commit message `fix(munger): make receivables forensic evidence-based`.

## Constraints and Invariants

- Bất biến sổ cái: Phân tích pháp y BCTC quan sát và đánh giá chất lượng tài chính, không phát sinh lệnh hay sửa đổi sổ cái.
- Không dùng hard universal rule (không tự động `CFO/PAT >= 0.8 => PASS` và không biến 15% thành hard threshold duy nhất).
- Missing data phải giữ trạng thái UNKNOWN/PARTIAL, không bao giờ chuyển thành PASS.

## Implementation Tasks

- [x] Task 1: Cập nhật `munger_thresholds.py` với các hằng số ngưỡng pháp y mới.
- [x] Task 2: Viết lại `run_receivables_forensics()` trong `python/portfolio/value_engine/munger_forensics.py`.
- [x] Task 3: Cập nhật `vietnamese_presenter.py` và `munger_analyzer.py` nếu cần.
- [x] Task 4: Viết bộ unit test `python/portfolio/tests/test_receivables_evidence_forensics.py`.
- [x] Task 5: Chạy audit trên các mã thực tế (ACB, DGC, FPT, VIX) và viết `docs/reports/receivables-forensic-audit.md`.
- [x] Task 6: Chuyển/tạo branch `feature/buffett-munger-refactor`, commit và hoàn tất task.

## Related Notes

- [docs/tasks/TASK-20260912-162-munger-liquidity-gate-and-semantic-audit.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-162-munger-liquidity-gate-and-semantic-audit.md)
- [python/portfolio/value_engine/munger_forensics.py](file:///c:/workspace/shannon_allocation/python/portfolio/value_engine/munger_forensics.py)
- [python/portfolio/value_engine/munger_thresholds.py](file:///c:/workspace/shannon_allocation/python/portfolio/value_engine/munger_thresholds.py)
- [docs/reports/receivables-forensic-audit.md](file:///c:/workspace/shannon_allocation/docs/reports/receivables-forensic-audit.md)

## Decisions

- Sử dụng 5 trục bằng chứng kết hợp để phân loại `status` (`PASS`, `WATCH`, `FAIL`, `UNKNOWN`) và `severity` (`INFO`, `LOW`, `MEDIUM`, `HIGH`).
- Khi phát hiện `low_base_distortion`, 10Y gap được gắn nhãn ghi chú lịch sử và trọng số chuyển hoàn toàn sang 3Y trend + Materiality + DSO.

## Validation Evidence

```text
pytest python/portfolio/tests/test_receivables_evidence_forensics.py python/portfolio/tests/test_receivables_forensics_semantic_contract.py python/portfolio/tests/test_forensic_mos_correctness.py python/portfolio/tests/test_munger_pipeline_regression.py python/portfolio/tests/test_enum_semantic_coverage.py python/portfolio/tests/test_semantic_labels.py python/portfolio/tests/test_munger_liquidity_gate.py
======================== 56 passed, 2 skipped in 1.24s ========================
```

## Result

- Hoàn thành toàn diện việc chuyển đổi `RECEIVABLES_GROW_FASTER_THAN_REVENUE` sang mô hình 5 trục bằng chứng đa tầng, loại bỏ false positives trên các doanh nghiệp tốt (FPT, DGC, CTR) và bảo vệ đầy đủ các trường hợp rủi ro thực sự.
