# TASK-20260912-150: Terminal Portfolio Position Management

- **ID**: TASK-20260912-150
- **Title**: Terminal Portfolio Position Management
- **Status**: completed
- **Priority**: high
- **Date**: 2026-09-12

---

## Requirement

Nâng cấp Terminal để user có thể quản lý danh mục thực tế ngay trong Terminal.
- Hiển thị toàn bộ danh mục hiện tại.
- Thêm từng mã cổ phiếu (số lượng, giá vốn).
- Xóa từng mã cổ phiếu (soft delete).
- Chỉnh sửa từng vị thế.
- Quản lý số dư tiền mặt.
- Tính giá trị vốn đã đầu tư, giá trị thị trường, P/L và P/L %.
- Cung cấp portfolio position context cho các module phân tích và allocation.
- KHÔNG hard-code portfolio.
- KHÔNG tạo DB table mới — tái sử dụng `ledger_events` + `POSITION_IMPORT`.

## Context

Hệ thống QPort đã có:
- `ledger_events` table (SQLite) là single source of truth.
- `POSITION_IMPORT` event type để seed trực tiếp vị thế cổ phiếu.
- `CorrectablePortfolioService.delete_event()` hỗ trợ soft-delete (tạo tombstone event).
- `cash_reserve_vnd` trong `app_meta` cho tiền mặt.

## Acceptance Criteria

- [x] GET /api/portfolio/positions - computed positions với P/L
- [x] POST /api/portfolio/positions - add position (reject duplicate)
- [x] PUT /api/portfolio/positions/{symbol} - update position (guard against complex ledger)
- [x] DELETE /api/portfolio/positions/{symbol} - soft-delete all events for symbol
- [x] GET /api/portfolio/cash - cash reserve
- [x] Terminal DANH MỤC section visible với position table
- [x] Add/Edit/Delete position từ Terminal UI
- [x] Cash management trong Terminal UI
- [x] Không raw enum trên UI (hiển thị tiếng Việt chuẩn)
- [x] Persist qua reload
- [x] 23 test cases passing

## Constraints and Invariants

- Không tạo DB table mới.
- Complex ledger positions (symbols có giao dịch MUA/BÁN): block edit/delete ở Terminal, hướng dẫn user sang TransactionsPage.
- Soft-delete (tạo tombstone event hoặc vô hiệu hóa effective state), không hard-delete.

## Implementation Tasks

- [x] Append service methods (`get_positions_summary`, `add_position`, `update_position`, `delete_position`) to `CorrectablePortfolioService` in `python/portfolio/correctable_service.py`
- [x] Add 5 API endpoints (`/api/portfolio/positions`, `/api/portfolio/positions/{symbol}`, `/api/portfolio/cash`, `/api/portfolio/cash-reserve`) in `app/main.py`
- [x] Add API helpers in `frontend/src/lib/api.js`
- [x] Update `TerminalPage.jsx` with DANH MỤC section, modals, cash management, real market price calculation
- [x] Write `test_terminal_portfolio_positions.py` (23 test cases)
- [x] Update `docs/tasks/README.md`

## Decisions

1. No new tables — reuse `ledger_events` + `POSITION_IMPORT` event type.
2. Complex ledger guard — standard positions (`POSITION_IMPORT` only) can be managed directly in Terminal; complex trading history requires full transaction audit on TransactionsPage.
3. Soft-delete — `delete_position()` soft-deletes all effective events for the specified symbol.
4. Cash reserve — reuse existing `cash_reserve_vnd` key in `app_meta`.

## Validation Evidence

Executed via `$env:PYTHONPATH="python"; & "$HOME\.venv\Scripts\python.exe" -m pytest python/portfolio/tests/test_terminal_portfolio_positions.py`:
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\workspace\shannon_allocation
configfile: pyproject.toml
plugins: anyio-4.15.1
collected 23 items

python\portfolio\tests\test_terminal_portfolio_positions.py ............ [ 52%]
...........                                                              [100%]

============================= 23 passed in 9.65s ==============================
```

## Result

Hoàn tất tính năng Quản lý Danh mục Vị thế trong Terminal:
- Backend: API CRUD cho positions & cash reserve trên SQLite ledger store.
- Frontend: Terminal UI có bảng DANH MỤC đẹp mắt, modal Thêm / Sửa / Xóa vị thế, điều chỉnh Tiền mặt, tự động tính P/L theo giá thị trường real-time.
- Test: 23 test cases phủ toàn bộ các kịch bản CRUD, P/L, validation, soft-delete, cash management và complex ledger guard.
