# Audit Report: QPort Buffett Terminal — Portfolio Decision Integrity

**Task Reference**: [TASK-20260912-159-terminal-decision-integrity.md](../tasks/TASK-20260912-159-terminal-decision-integrity.md)  
**Date**: 2026-09-12  
**Status**: VERIFIED & COMPLETED  
**Branch**: `munger-buffer`  

---

## 1. Executive Summary & Flow Trace

QPort Buffett Terminal đã được rà soát và nâng cấp toàn diện để hỗ trợ nhà đầu tư trả lời rõ ràng 9 câu hỏi cốt lõi:
1. **Tôi đang sở hữu gì?** $\rightarrow$ Danh sách vị thế cổ phiếu + Lượng tiền mặt nắm giữ trong danh mục.
2. **Giá hiện tại là bao nhiêu?** $\rightarrow$ Giá thị trường cập nhật mới nhất cho từng mã (nếu chưa có giá thì ghi rõ trạng thái thay vì âm thầm coi bằng 0).
3. **Giá vốn là bao nhiêu?** $\rightarrow$ Giá vốn bình quân trên mỗi cổ phiếu theo đơn vị VND đầy đủ.
4. **Giá trị hiện tại của từng vị thế là bao nhiêu?** $\rightarrow$ Vốn đầu tư ban đầu, Giá trị thị trường hiện tại, Lãi/Lỗ và Lãi/Lỗ %.
5. **Doanh nghiệp đang được đánh giá thế nào?** $\rightarrow$ Ma trận chất lượng Munger 12 chiều (Xuất sắc, Chất lượng cao, Có thể đầu tư, v.v.).
6. **Định giá cho thấy mức MOS bao nhiêu?** $\rightarrow$ Base IV (Cơ sở), Bear IV (Thận trọng), MOS thực tế so với Required MOS (25%).
7. **Value Trap đang cảnh báo điều gì?** $\rightarrow$ Báo cáo điều tra tài chính chuyên sâu với tên cảnh báo, hiện tượng BCTC, xu hướng nhiều năm, mức độ nghiêm trọng và tác động.
8. **Quyết định Buffett/Munger hiện tại là gì?** $\rightarrow$ Khuyến nghị kỷ luật bằng tiếng Việt (Có thể mua, Có thể mua thêm, Tiếp tục nắm giữ, Chờ đạt biên an toàn, v.v.).
9. **Tôi nên làm gì tiếp theo?** $\rightarrow$ Huấn luyện viên Buffett & Munger tóm tắt hành động ưu tiên và cảnh báo mâu thuẫn hệ thống (nếu có).

### Trace Toàn Bộ Flow:
$$\text{Portfolio DB} \rightarrow \text{Positions} \rightarrow \text{Market Price} \rightarrow \text{Market Value / PnL / Weights} \rightarrow \text{Munger Quality} \rightarrow \text{Valuation/MOS} \rightarrow \text{Deep Value Trap} \rightarrow \text{Terminal Decision UI}$$

---

## 2. Raw Enum & Semantic Audit

Toàn bộ các enum nội bộ, mã máy, snake_case và chuỗi lỗi đã được chuyển ngữ 100% sang tiếng Việt tự nhiên thông qua tầng Semantic tập trung (`frontend/src/utils/vietnameseSemantics.js` và `python/portfolio/value_engine/vietnamese_presenter.py`):

| Mã Enum / Machine Code | Hiển thị Giao Diện Tiếng Việt (UI Semantic) |
| :--- | :--- |
| `REVIEW_BUSINESS` | **Cần xem xét thêm** |
| `WATCH` | **Có dấu hiệu cần theo dõi** |
| `CLEAR` | **Chưa phát hiện bẫy giá trị đáng kể** |
| `HIGH_QUALITY` | **Chất lượng cao** |
| `INVESTABLE` | **Có thể đầu tư** |
| `EXCEPTIONAL` | **Xuất sắc** |
| `POTENTIAL_COMPOUNDER` | **Doanh nghiệp có tiềm năng tăng trưởng dài hạn** |
| `PROFIT_CASH_DIVERGENCE` | **Dòng tiền kinh doanh chưa theo kịp lợi nhuận** |
| `RECEIVABLES_GROW_FASTER_THAN_REVENUE` | **Khoản phải thu tăng nhanh hơn doanh thu** |
| `INSUFFICIENT_DATA` | **Chưa đủ dữ liệu** |
| `NO_DETERIORATION` | **Không có dấu hiệu suy giảm** |
| `STRUCTURAL_EVIDENCE` | **Bằng chứng suy giảm cấu trúc** |
| `UNPROTECTED` | **Chưa được bảo vệ trong kịch bản thận trọng** |
| `UNKNOWN` | **Chưa có đủ bằng chứng từ dữ liệu BCTC** |

---

## 3. N/A & Metric Calculation Audit

Phân loại xử lý các chỉ số tài chính theo đúng nguyên tắc:
1. **Có thể tính được**: Phải tính toán chính xác từ dữ liệu BCTC chuẩn hóa SSI (ROE, Tăng trưởng LNST, CFO/PAT, Debt/Equity, Biên an toàn).
2. **Không đủ dữ liệu đầu vào**: Hiển thị rõ *"Chưa đủ dữ liệu"* thay vì `N/A`, `null`, `nullx`, `undefined`, `NaN`.
3. **Không áp dụng theo mô hình doanh nghiệp**: Hiển thị *"Không áp dụng cho ngân hàng thương mại"* đối với Debt/Equity hoặc CFO/PAT của Bank/Securities.

---

## 4. Market Price, Portfolio Value & Cash Audit

- **Công thức Tổng Tài Sản**:
  $$\text{Tổng Tài Sản Danh Mục} = \text{Giá Trị Thị Trường Cổ Phiếu} + \text{Tiền Mặt}$$
- **Tỷ trọng danh mục**: Được tính toán chuẩn xác trên Tổng Tài Sản.
- **Xử lý vị thế chưa có giá thị trường**: Có banner cảnh báo rõ ràng `Có N vị thế chưa lấy được giá thị trường`, hiển thị riêng giá trị thị trường đã xác định và vốn chưa định giá, không làm sai lệch tổng tài sản.

---

## 5. Portfolio Actions & Valuation Navigation

- Mỗi vị thế hỗ trợ: Thêm mới, Chỉnh sửa (Số lượng, Giá vốn VND đầy đủ), Xóa, Chuẩn hóa chia tách cổ phiếu (`⚡ Chia tách`).
- **Nút "Định giá"**: Nằm trên từng dòng vị thế và trong modal chi tiết, điều hướng trực tiếp sang canonical valuation route `/valuation?symbol={SYMBOL}` hoặc `/business/{SYMBOL}`.

---

## 6. Doanh Nghiệp Đáng Chú Ý (Munger Candidates Widget)

- Widget **"Cơ Hội Đầu Tư Đáng Chú Ý (Tiêu Chuẩn Munger)"** được tích hợp trực tiếp trên Buffett Terminal (`TerminalPage.jsx`).
- Tự động lấy các ứng viên xuất sắc từ backend discovery engine (`getMungerCandidates()`).
- Hiển thị đầy đủ: Mã, Phân loại chất lượng, ROE, Tăng trưởng LNST, MOS, Bẫy giá trị, Lý do đề xuất, nút "Xem phân tích" và "Định giá".

---

## 7. Value Trap & Munger Pre-Commitment (8 Câu Hỏi)

- **Value Trap Forensics**: Cung cấp chi tiết tên cảnh báo, hiện tượng BCTC, xu hướng nhiều năm, mức độ nghiêm trọng và tác động dài hạn.
- **Munger 8 Pre-Commitment Questions**: Được QPort tự động giải đáp bằng số liệu BCTC định lượng (Kết luận, Bằng chứng BCTC, Rủi ro tiềm ẩn, Mức độ nghiêm trọng, Tiêu chí kích hoạt bác bỏ luận điểm).

---

## 8. Test & Build Results

Tất cả 24 unit & integration tests chạy thành công 100%:
```text
pytest python/portfolio/tests/test_terminal_decision_integrity.py \
       python/portfolio/tests/test_munger_candidates_and_valuation_navigation.py \
       python/portfolio/tests/test_deep_value_trap_forensics.py \
       python/portfolio/tests/test_golden_baseline_regression.py -v

======================= 24 passed in 118.61s (0:01:58) ========================
```

Frontend production build (`npm --prefix frontend run build`):
```text
✓ 115 modules transformed.
dist/index.html                   1.86 kB │ gzip:   0.82 kB
dist/assets/index-BpQoWY_z.css  269.18 kB │ gzip:  45.91 kB
dist/assets/index-BDo8ZJt1.js   756.52 kB │ gzip: 207.49 kB
✓ built in 1.63s
```
