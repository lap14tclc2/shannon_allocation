import React, { useCallback, useEffect, useRef, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import SymbolSuggestInput from '../components/SymbolSuggestInput.jsx';
import { navigate } from '../lib/navigation.js';
import {
  addPortfolioPosition,
  applySplitAdjustment,
  deletePortfolioPosition,
  getBuffettTerminalData,
  getPortfolioPositions,
  getSplitAdjustment,
  setCashReserve,
  updatePortfolioPosition,
} from '../lib/api.js';
import {
  formatDecision,
  formatFortressStatus,
  formatLiabilityStatus,
  formatQualityTier,
  formatSafeText,
  formatSource,
  formatStatus,
  formatValueTrap,
  formatFindingNarrative,
} from '../utils/vietnameseSemantics.js';
import '../terminal-page.css';

// ── Formatters ────────────────────────────────────────────────────────────────
const fmtNum = (n, digits = 0) =>
  n == null || isNaN(n)
    ? null
    : Number(n).toLocaleString('vi-VN', { minimumFractionDigits: digits, maximumFractionDigits: digits });

const fmtMoney = (n) => (n == null || isNaN(n) ? '—' : `${fmtNum(n)} ₫`);

const fmtPct = (n) => (n == null || isNaN(n) ? '—' : `${Number(n).toFixed(1)}%`);

const fmtPnl = (n) => {
  if (n == null || isNaN(n)) return '—';
  const sign = n >= 0 ? '+' : '';
  return `${sign}${fmtNum(n)} ₫`;
};

const NA_PRICE = 'Chưa lấy được giá thị trường';
const EMPTY_PORTFOLIO = 'Chưa có vị thế nào trong danh mục';

// ── Modal overlay ─────────────────────────────────────────────────────────────
function Modal({ onClose, children }) {
  const overlayRef = useRef(null);
  useEffect(() => {
    const handleKey = (e) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [onClose]);
  return (
    <div
      ref={overlayRef}
      onClick={(e) => e.target === overlayRef.current && onClose()}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.65)', zIndex: 1000,
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px',
      }}
    >
      <div style={{
        background: 'var(--panel, var(--card-bg, #fffaf0))',
        border: '1px solid var(--border-strong, var(--border, #9c927f))',
        borderRadius: 12, padding: 28, minWidth: 340, maxWidth: 480, width: '100%',
        boxShadow: '0 24px 48px rgba(0,0,0,0.3)',
        color: 'var(--text, #201d18)',
      }}>
        {children}
      </div>
    </div>
  );
}

// ── Position form (Add / Edit) ────────────────────────────────────────────────
function PositionForm({ title, initial = {}, holdingSymbols = [], onSave, onCancel }) {
  const [symbol, setSymbol] = useState(initial.symbol || '');
  const [quantity, setQuantity] = useState(initial.quantity != null ? String(initial.quantity) : '');
  const [avgCost, setAvgCost] = useState(initial.average_cost != null ? String(initial.average_cost) : '');
  const [err, setErr] = useState(null);
  const [saving, setSaving] = useState(false);
  const isEdit = !!initial.symbol;
  const [splitInfo, setSplitInfo] = useState(null);
  const [loadingSplit, setLoadingSplit] = useState(false);

  useEffect(() => {
    const sym = (symbol || initial.symbol || '').trim().toUpperCase();
    if (sym && isEdit) {
      setLoadingSplit(true);
      getSplitAdjustment(sym)
        .then((res) => {
          if (res?.ok && res?.has_adjustment) {
            setSplitInfo(res);
          } else {
            setSplitInfo(null);
          }
        })
        .catch(() => setSplitInfo(null))
        .finally(() => setLoadingSplit(false));
    }
  }, [symbol, isEdit, initial.symbol]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErr(null);
    const sym = symbol.trim().toUpperCase();
    const qty = parseFloat(quantity.replace(/,/g, ''));
    const cost = parseFloat(avgCost.replace(/,/g, ''));
    if (!sym) return setErr('Vui lòng nhập mã cổ phiếu.');
    if (!/^[A-Z0-9]{2,10}$/.test(sym)) return setErr('Mã cổ phiếu không hợp lệ (2–10 ký tự chữ/số).');
    if (!qty || qty <= 0 || !isFinite(qty)) return setErr('Số lượng phải lớn hơn 0.');
    if (!cost || cost <= 0 || !isFinite(cost)) return setErr('Giá vốn phải lớn hơn 0.');
    if (cost < 1000) return setErr('Giá vốn phải nhập theo đơn vị VND đầy đủ (ví dụ: 73800, không phải 73.8).');
    setSaving(true);
    try {
      await onSave(sym, qty, cost);
    } catch (ex) {
      setErr(ex.message || 'Có lỗi xảy ra. Vui lòng thử lại.');
      setSaving(false);
    }
  };

  const inputStyle = {
    width: '100%',
    padding: '9px 12px',
    borderRadius: 6,
    border: '1px solid var(--border-strong, var(--border, #9c927f))',
    background: 'var(--input, var(--panel-subtle, #ffffff))',
    color: 'var(--text, #201d18)',
    fontSize: 14,
    marginTop: 4,
    boxSizing: 'border-box',
    outline: 'none',
  };
  const labelStyle = {
    display: 'block',
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--text, #201d18)',
    marginTop: 14,
  };

  return (
    <form onSubmit={handleSubmit}>
      <h3 style={{ margin: '0 0 16px', fontSize: 18, color: 'var(--text, #201d18)' }}>{title}</h3>
      {!isEdit && (
        <div>
          <label style={{ ...labelStyle, marginTop: 0 }}>Mã cổ phiếu *</label>
          <div style={{ marginTop: 4 }}>
            <SymbolSuggestInput
              value={symbol}
              onChange={setSymbol}
              onSelectSecurity={(sec) => setSymbol(sec.symbol)}
              holdingSymbols={holdingSymbols}
              placeholder="Tìm mã hoặc tên công ty (ví dụ: FPT, HPG, MBB...)"
              autoFocus
            />
          </div>
        </div>
      )}
      {isEdit && <div style={{ ...labelStyle, marginTop: 0 }}>Mã cổ phiếu: <strong>{initial.symbol}</strong></div>}
      
      {splitInfo?.has_adjustment && (
        <div style={{
          background: 'rgba(2, 132, 199, 0.08)',
          border: '1px solid #0284c7',
          borderRadius: 8,
          padding: '12px 14px',
          marginTop: 12,
          marginBottom: 8,
          fontSize: 12,
        }}>
          <div style={{ fontWeight: 700, color: '#0284c7', marginBottom: 4 }}>
            ⚡ Cổ tức cổ phiếu / chia tách gần nhất (Hệ số: {splitInfo.cumulative_factor}x)
          </div>
          {splitInfo.latest_event && (
            <div style={{ color: '#4a5568', fontSize: 11, marginBottom: 6 }}>
              • Sự kiện: {splitInfo.latest_event.dividend_type === 'STOCK_DIVIDEND' ? 'Cổ tức cổ phiếu' : (splitInfo.latest_event.dividend_type === 'BONUS_SHARE' ? 'Thưởng cổ phiếu' : 'Chia tách')} {(splitInfo.latest_event.stock_ratio * 100).toFixed(1)}% (Ngày chốt: {splitInfo.latest_event.event_date})
            </div>
          )}
          <div style={{ color: 'var(--text, #201d18)', marginBottom: 8, lineHeight: 1.5 }}>
            • Số lượng sau chia đề xuất: <strong>{Number(splitInfo.adjusted_shares).toLocaleString('vi-VN')} cp</strong><br />
            • Giá vốn sau chia đề xuất: <strong>{Number(splitInfo.adjusted_cost).toLocaleString('vi-VN')} ₫</strong> (Bảo toàn vốn: {Number(splitInfo.total_invested).toLocaleString('vi-VN')} ₫)
          </div>
          <button
            type="button"
            onClick={() => {
              setQuantity(String(splitInfo.adjusted_shares));
              setAvgCost(String(splitInfo.adjusted_cost));
            }}
            style={{
              background: '#0284c7', color: '#fff', border: 'none', borderRadius: 4,
              padding: '6px 12px', cursor: 'pointer', fontWeight: 600, fontSize: 12,
            }}
          >
            Tự động điền số liệu sau chia tách
          </button>
        </div>
      )}

      <label style={labelStyle}>
        Số lượng (cổ phiếu) *
        <input
          style={inputStyle}
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          placeholder="Ví dụ: 3000"
          inputMode="numeric"
          required
        />
      </label>
      <label style={labelStyle}>
        Giá vốn bình quân (VND/cp) *
        <input
          style={inputStyle}
          value={avgCost}
          onChange={(e) => setAvgCost(e.target.value)}
          placeholder="Ví dụ: 73800"
          inputMode="numeric"
          required
        />
      </label>
      {err && <div style={{ color: '#fc8181', fontSize: 13, marginTop: 12 }}>{err}</div>}
      <div style={{ display: 'flex', gap: 8, marginTop: 24, justifyContent: 'flex-end' }}>
        <button type="button" onClick={onCancel} className="btn btn-secondary" disabled={saving}>Hủy</button>
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? 'Đang lưu…' : isEdit ? 'Cập nhật' : 'Thêm vị thế'}
        </button>
      </div>
    </form>
  );
}

// ── Cash form ─────────────────────────────────────────────────────────────────
function CashForm({ current, onSave, onCancel }) {
  const [value, setValue] = useState(current != null ? String(current) : '');
  const [err, setErr] = useState(null);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErr(null);
    const amount = parseFloat(value.replace(/,/g, ''));
    if (!isFinite(amount) || amount < 0) return setErr('Số tiền mặt phải >= 0.');
    setSaving(true);
    try {
      await onSave(amount);
    } catch (ex) {
      setErr(ex.message || 'Có lỗi xảy ra.');
      setSaving(false);
    }
  };

  const inputStyle = {
    width: '100%',
    padding: '9px 12px',
    borderRadius: 6,
    border: '1px solid var(--border-strong, var(--border, #9c927f))',
    background: 'var(--input, var(--panel-subtle, #ffffff))',
    color: 'var(--text, #201d18)',
    fontSize: 14,
    marginTop: 4,
    boxSizing: 'border-box',
    outline: 'none',
  };

  return (
    <form onSubmit={handleSubmit}>
      <h3 style={{ margin: '0 0 16px', fontSize: 18, color: 'var(--text, #201d18)' }}>Cập nhật Tiền mặt</h3>
      <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: 'var(--text, #201d18)' }}>
        Số tiền mặt (VND) *
        <input
          autoFocus
          style={inputStyle}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ví dụ: 50000000"
          inputMode="numeric"
        />
      </label>
      {err && <div style={{ color: '#fc8181', fontSize: 13, marginTop: 12 }}>{err}</div>}
      <div style={{ display: 'flex', gap: 8, marginTop: 24, justifyContent: 'flex-end' }}>
        <button type="button" onClick={onCancel} className="btn btn-secondary" disabled={saving}>Hủy</button>
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? 'Đang lưu…' : 'Lưu'}
        </button>
      </div>
    </form>
  );
}

// ── Delete confirm ────────────────────────────────────────────────────────────
function DeleteConfirm({ symbol, onConfirm, onCancel }) {
  const [deleting, setDeleting] = useState(false);
  const handleConfirm = async () => {
    setDeleting(true);
    try { await onConfirm(); } catch { setDeleting(false); }
  };
  return (
    <div>
      <h3 style={{ margin: '0 0 12px', fontSize: 16 }}>Xóa vị thế</h3>
      <p style={{ color: 'var(--text-muted, #718096)', fontSize: 14 }}>
        Xóa vị thế <strong>{symbol}</strong> khỏi danh mục?
        Thao tác này không thể hoàn tác qua Terminal.
      </p>
      <div style={{ display: 'flex', gap: 8, marginTop: 20, justifyContent: 'flex-end' }}>
        <button onClick={onCancel} className="btn btn-secondary" disabled={deleting}>Hủy</button>
        <button onClick={handleConfirm} disabled={deleting} style={{
          background: '#e53e3e', color: '#fff', border: 'none', borderRadius: 6,
          padding: '8px 16px', cursor: 'pointer', fontWeight: 600,
        }}>
          {deleting ? 'Đang xóa…' : 'Xóa'}
        </button>
      </div>
    </div>
  );
}

// ── Portfolio DANH MỤC section ────────────────────────────────────────────────
function PortfolioSection({ onRefreshTerminal }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [modal, setModal] = useState(null); // {type, row}

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getPortfolioPositions()
      .then(setData)
      .catch((err) => setError(err.message || 'Không thể tải danh mục.'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const closeModal = () => setModal(null);
  const afterSave = () => {
    closeModal();
    load();
    if (onRefreshTerminal) onRefreshTerminal();
  };

  const handleAdd = async (sym, qty, cost) => {
    await addPortfolioPosition(sym, qty, cost);
    afterSave();
  };
  const handleEdit = async (sym, qty, cost) => {
    await updatePortfolioPosition(sym, qty, cost);
    afterSave();
  };
  const handleDelete = async (sym) => {
    await deletePortfolioPosition(sym);
    afterSave();
  };
  const handleCash = async (amount) => {
    await setCashReserve(amount);
    afterSave();
  };

  const handleAutoSplit = async (sym) => {
    if (!window.confirm(`Tự động chuẩn hóa số lượng và giá vốn cho vị thế ${sym} sau các đợt chia tách/cổ tức cổ phiếu?\n(Tổng vốn đầu tư ban đầu sẽ được bảo toàn tuyệt đối).`)) return;
    try {
      const res = await applySplitAdjustment(sym);
      if (res?.ok) {
        alert(res.message || 'Chuẩn hóa thành công.');
        afterSave();
      } else {
        alert(res?.error || 'Không thể chuẩn hóa.');
      }
    } catch (ex) {
      alert(ex.message || 'Có lỗi xảy ra.');
    }
  };

  const positions = data?.positions || [];
  const summary = data?.summary || {};
  const cashReserve = data?.cash_reserve ?? 0;
  const unvaluedCount = summary?.unvalued_positions_count || 0;
  const valuedCount = summary?.valued_positions_count || 0;

  const pnlColor = (v) => (v == null ? undefined : v >= 0 ? '#48bb78' : '#fc8181');

  return (
    <section className="card" style={{ marginBottom: 24 }}>
      <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h3 style={{ margin: 0 }}>Danh Mục Nắm Giữ</h3>
          <small style={{ color: 'var(--text-muted, #718096)' }}>
            Quản lý vị thế cổ phiếu và lượng tiền mặt nắm giữ
          </small>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => load()}
            className="btn btn-secondary"
            style={{ fontSize: 13, padding: '6px 12px' }}
            title="Tải lại dữ liệu giá và danh mục"
          >
            Làm mới giá
          </button>
          <button
            onClick={() => setModal({ type: 'add' })}
            className="btn btn-primary"
            style={{ fontSize: 13, padding: '6px 14px' }}
          >
            + Thêm vị thế
          </button>
        </div>
      </div>

      {unvaluedCount > 0 && (
        <div style={{
          background: 'rgba(237, 137, 54, 0.12)',
          border: '1px solid #ed8936',
          borderRadius: 8,
          padding: '10px 16px',
          margin: '12px 0',
          fontSize: 13,
          color: '#dd6b20',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 8,
        }}>
          <div>
            <strong>Lưu ý về định giá:</strong> Có {unvaluedCount}/{positions.length} vị thế chưa lấy được giá thị trường.
            Giá trị thị trường đã xác định: <strong>{fmtMoney(summary.valued_market_value)}</strong> ({valuedCount} vị thế).
            Vốn chưa định giá: <strong>{fmtMoney(summary.unvalued_invested)}</strong>.
          </div>
          <button
            onClick={() => load()}
            style={{
              background: '#dd6b20', color: '#fff', border: 'none', borderRadius: 4,
              padding: '4px 10px', fontSize: 12, cursor: 'pointer', fontWeight: 600,
            }}
          >
            Thử lấy lại giá
          </button>
        </div>
      )}

      {loading && <div className="loading-state" style={{ padding: '16px 0' }}>Đang tải danh mục…</div>}
      {error && <div className="error-box">{error}</div>}

      {!loading && !error && (
        <>
          {positions.length === 0 ? (
            <div style={{ padding: '24px 0', color: 'var(--text-muted, #718096)', fontSize: 14, textAlign: 'center' }}>
              {EMPTY_PORTFOLIO} — Nhấn <strong>+ Thêm vị thế</strong> để bắt đầu theo dõi.
            </div>
          ) : (
            <div className="table-responsive">
              <table className="data-table" style={{ fontSize: 13 }}>
                <thead>
                  <tr>
                    <th>Mã</th>
                    <th style={{ textAlign: 'right' }}>Số lượng</th>
                    <th style={{ textAlign: 'right' }}>Giá vốn bình quân</th>
                    <th style={{ textAlign: 'right' }}>Giá thị trường</th>
                    <th style={{ textAlign: 'right' }}>Vốn đầu tư</th>
                    <th style={{ textAlign: 'right' }}>Giá trị thị trường</th>
                    <th style={{ textAlign: 'right' }}>Lãi / Lỗ</th>
                    <th style={{ textAlign: 'right' }}>Lãi / Lỗ %</th>
                    <th style={{ textAlign: 'right' }}>Tỷ trọng</th>
                    <th>Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((p) => (
                    <tr key={p.symbol}>
                      <td>
                        <a href={`/business/${p.symbol}`} style={{ fontWeight: 700, color: 'inherit', textDecoration: 'none' }}>
                          {p.symbol}
                        </a>
                      </td>
                      <td style={{ textAlign: 'right' }}>{fmtNum(p.shares)}</td>
                      <td style={{ textAlign: 'right' }}>{fmtMoney(p.average_cost)}</td>
                      <td style={{ textAlign: 'right' }}>
                        {p.market_price != null ? (
                          fmtMoney(p.market_price)
                        ) : (
                          <span style={{ color: '#e53e3e', fontSize: 12 }} title="Hệ thống chưa tìm thấy giá thị trường cho mã này">
                            {NA_PRICE}
                          </span>
                        )}
                      </td>
                      <td style={{ textAlign: 'right' }}>{fmtMoney(p.invested_value)}</td>
                      <td style={{ textAlign: 'right' }}>
                        {p.market_value != null && p.market_price != null ? (
                          fmtMoney(p.market_value)
                        ) : (
                          <span style={{ color: 'var(--text-muted, #718096)' }}>
                            Chưa tính
                          </span>
                        )}
                      </td>
                      <td style={{ textAlign: 'right', color: pnlColor(p.unrealized_pnl) }}>
                        {p.unrealized_pnl != null ? fmtPnl(p.unrealized_pnl) : <span style={{ color: 'var(--text-muted, #718096)' }}>—</span>}
                      </td>
                      <td style={{ textAlign: 'right', color: pnlColor(p.unrealized_pnl_pct) }}>
                        {p.unrealized_pnl_pct != null ? fmtPct(p.unrealized_pnl_pct) : <span style={{ color: 'var(--text-muted, #718096)' }}>—</span>}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        {p.weight != null ? fmtPct(p.weight * 100) : '—'}
                      </td>
                      <td style={{ whiteSpace: 'nowrap' }}>
                        {p.has_complex_ledger ? (
                          <div className="table-action-group">
                            <a
                              href={`/valuation?symbol=${p.symbol}`}
                              onClick={(e) => { e.preventDefault(); navigate(`/valuation?symbol=${p.symbol}`); }}
                              className="table-btn table-btn-val"
                              title="Xem định giá DCF/RIM và Biên an toàn"
                            >Định giá</a>
                            <a href="/transactions" style={{ fontSize: 12, color: '#718096', marginLeft: 4 }}>Lịch sử sổ cái</a>
                          </div>
                        ) : (
                          <div className="table-action-group">
                            <a
                              href={`/valuation?symbol=${p.symbol}`}
                              onClick={(e) => { e.preventDefault(); navigate(`/valuation?symbol=${p.symbol}`); }}
                              className="table-btn table-btn-val"
                              title="Xem định giá DCF/RIM và Biên an toàn"
                            >Định giá</a>
                            <button
                              onClick={() => handleAutoSplit(p.symbol)}
                              title="Tự động chuẩn hóa số lượng và giá vốn sau chia tách/cổ tức cổ phiếu"
                              className="table-btn table-btn-split"
                            >⚡ Chia tách</button>
                            <button
                              onClick={() => setModal({ type: 'edit', row: p })}
                              className="table-btn table-btn-edit"
                            >Sửa</button>
                            <button
                              onClick={() => setModal({ type: 'delete', row: p })}
                              className="table-btn table-btn-delete"
                            >Xóa</button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Cash row + summary */}
          <div style={{ borderTop: '1px solid var(--border, #2d3748)', marginTop: 16, paddingTop: 16 }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 24, alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: 12, color: 'var(--text-muted, #718096)' }}>Tiền mặt danh mục</div>
                <div style={{ fontWeight: 700, fontSize: 15 }}>
                  {fmtMoney(cashReserve)}
                  <button
                    onClick={() => setModal({ type: 'cash' })}
                    style={{ marginLeft: 8, fontSize: 11, background: 'none', border: '1px solid #4a5568', borderRadius: 4, padding: '2px 6px', cursor: 'pointer', color: 'inherit' }}
                  >Sửa tiền mặt</button>
                </div>
              </div>
              {summary.total_invested > 0 && (
                <div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted, #718096)' }}>Tổng vốn đầu tư</div>
                  <div style={{ fontWeight: 700 }}>{fmtMoney(summary.total_invested)}</div>
                </div>
              )}
              {summary.valued_market_value != null && (
                <div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted, #718096)' }}>
                    {unvaluedCount > 0 ? 'Giá trị thị trường đã xác định' : 'Giá trị thị trường cổ phiếu'}
                  </div>
                  <div style={{ fontWeight: 700 }}>
                    {fmtMoney(summary.valued_market_value)}
                    {unvaluedCount > 0 && <small style={{ fontWeight: 400, color: 'var(--text-muted, #718096)', marginLeft: 4 }}>({valuedCount}/{positions.length} mã)</small>}
                  </div>
                </div>
              )}
              {summary.unrealized_pnl != null && (
                <div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted, #718096)' }}>Lãi / Lỗ chưa thực hiện</div>
                  <div style={{ fontWeight: 700, color: pnlColor(summary.unrealized_pnl) }}>
                    {fmtPnl(summary.unrealized_pnl)} ({fmtPct(summary.unrealized_pnl_pct)})
                  </div>
                </div>
              )}
              {summary.total_portfolio_value > 0 && (
                <div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted, #718096)' }}>
                    {unvaluedCount > 0 ? 'Tổng tài sản ước tính' : 'Tổng tài sản danh mục'}
                  </div>
                  <div style={{ fontWeight: 700, fontSize: 16 }}>{fmtMoney(summary.total_portfolio_value)}</div>
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* Modals */}
      {modal?.type === 'add' && (
        <Modal onClose={closeModal}>
          <PositionForm
            title="Thêm vị thế"
            holdingSymbols={positions.map((p) => p.symbol)}
            onSave={handleAdd}
            onCancel={closeModal}
          />
        </Modal>
      )}
      {modal?.type === 'edit' && (
        <Modal onClose={closeModal}>
          <PositionForm
            title={`Chỉnh sửa vị thế ${modal.row.symbol}`}
            initial={{ symbol: modal.row.symbol, quantity: modal.row.shares, average_cost: modal.row.average_cost }}
            onSave={(sym, qty, cost) => handleEdit(sym, qty, cost)}
            onCancel={closeModal}
          />
        </Modal>
      )}
      {modal?.type === 'delete' && (
        <Modal onClose={closeModal}>
          <DeleteConfirm symbol={modal.row.symbol} onConfirm={() => handleDelete(modal.row.symbol)} onCancel={closeModal} />
        </Modal>
      )}
      {modal?.type === 'cash' && (
        <Modal onClose={closeModal}>
          <CashForm current={cashReserve} onSave={handleCash} onCancel={closeModal} />
        </Modal>
      )}
    </section>
  );
}

// ── Detail Drawer / Modal for Matrix row ──────────────────────────────────────
function HoldingDetailModal({ item, onClose }) {
  if (!item) return null;
  const val = item.valuation || {};
  const vTrap = item.value_trap || {};
  const findings = vTrap.findings || [];

  return (
    <Modal onClose={onClose}>
      <div style={{ maxWidth: 520 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0, fontSize: 20 }}>
            {item.symbol} — Chi Tiết Phân Tích
          </h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 18, cursor: 'pointer', color: 'inherit' }}>✕</button>
        </div>

        <div className="metric-grid" style={{ marginBottom: 16 }}>
          <div className="metric-item">
            <small>Chất lượng doanh nghiệp</small>
            <strong>{formatQualityTier(item.quality_tier)}</strong>
          </div>
          <div className="metric-item">
            <small>Quyết định</small>
            <strong style={{ color: '#0284c7' }}>{formatDecision(item.decision)}</strong>
          </div>
          <div className="metric-item">
            <small>Giá thị trường</small>
            <strong>{item.price ? `${fmtNum(item.price)} ₫` : 'Chưa lấy được giá'}</strong>
          </div>
          <div className="metric-item">
            <small>Base IV (Cơ sở)</small>
            <strong>{item.base_iv ? `${fmtNum(item.base_iv)} ₫` : 'Chưa đủ dữ liệu'}</strong>
          </div>
          <div className="metric-item">
            <small>Bear IV (Thận trọng)</small>
            <strong>{item.bear_iv ? `${fmtNum(item.bear_iv)} ₫` : 'Chưa đủ dữ liệu'}</strong>
          </div>
          <div className="metric-item">
            <small>Biên an toàn (MOS)</small>
            <strong>{item.actual_mos_pct != null ? `${Number(item.actual_mos_pct).toFixed(1)}%` : 'Chưa thể tính'}</strong>
          </div>
          <div className="metric-item">
            <small>Trạng thái bẫy giá trị</small>
            <strong>{formatValueTrap(item.value_trap_status)}</strong>
          </div>
          <div className="metric-item">
            <small>Tỷ trọng danh mục</small>
            <strong>{item.weight != null ? `${(Number(item.weight) * 100).toFixed(1)}%` : '0%'}</strong>
          </div>
        </div>

        {findings.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <h4 style={{ fontSize: 14, margin: '0 0 8px' }}>Cảnh báo tài chính phát hiện ({findings.length})</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 180, overflowY: 'auto' }}>
              {findings.map((f, idx) => {
                const narrative = formatFindingNarrative(f);
                return (
                  <div key={idx} style={{ padding: '8px 12px', background: 'var(--panel-subtle, rgba(0,0,0,0.03))', borderRadius: 6, fontSize: 12 }}>
                    <div style={{ fontWeight: 600, color: '#dd6b20' }}>
                      {narrative ? narrative.tieu_de : formatSafeText(f.code)}
                    </div>
                    <div style={{ color: 'var(--text-muted, #718096)', marginTop: 2 }}>
                      {narrative ? narrative.dieu_gi_dang_xay_ra : (f.explanation || f.impact || '')}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div style={{ marginTop: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <a
            href={`/business/${item.symbol}`}
            className="btn btn-primary"
            style={{ textDecoration: 'none', display: 'inline-block', fontSize: 13 }}
          >
            Mở trang phân tích doanh nghiệp chi tiết →
          </a>
          <button type="button" onClick={onClose} className="btn btn-secondary" style={{ fontSize: 13 }}>
            Đóng
          </button>
        </div>
      </div>
    </Modal>
  );
}

// ── Main Terminal page ────────────────────────────────────────────────────────
export default function TerminalPage() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [selectedHolding, setSelectedHolding] = useState(null);

  const loadData = useCallback(() => {
    setLoading(true);
    getBuffettTerminalData()
      .then((res) => {
        if (res.ok) setData(res);
        else setError(res.error || 'Không thể tải dữ liệu phân tích.');
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const holdings = data?.holdings_matrix || [];
  const buyableCount = holdings.filter((h) => ['BUY', 'BUY_MORE'].includes(h.decision)).length;
  const watchCount = holdings.filter((h) => ['WAIT_FOR_MOS', 'HOLD', 'WATCH'].includes(h.decision)).length;
  const reviewCount = holdings.filter((h) => ['REVIEW_BUSINESS', 'SELL_REVIEW', 'BUILD_RESERVE_FIRST'].includes(h.decision)).length;
  const valueTrapWarningCount = holdings.filter((h) => ['WATCH', 'HIGH_RISK'].includes(h.value_trap_status)).length;

  return (
    <div className="wealth-app-shell">
      <AppNav active="portfolio" />
      <main className="wealth-main-content" style={{ maxWidth: '1380px', margin: '0 auto', padding: '84px 24px 48px 24px', boxSizing: 'border-box' }}>
        <header className="page-header" style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
            <div>
              <span className="eyebrow">QPort Buffett Terminal</span>
              <h1 style={{ margin: '4px 0' }}>Trung Tâm Quyết Định Vốn Cá Nhân</h1>
              <p style={{ margin: 0, color: 'var(--text-muted, #718096)', fontSize: 13 }}>
                Hệ thống hỗ trợ ra quyết định đầu tư dài hạn theo triết lý Warren Buffett &amp; Charlie Munger
              </p>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted, #718096)', textAlign: 'right' }}>
              <div>{formatSource('PRIMARY_SSI')}</div>
              <div style={{ marginTop: 2 }}>Giá thị trường: Cập nhật mới nhất</div>
            </div>
          </div>
        </header>

        {/* ── High-level Overview Summary ────────────────────────────────────────── */}
        {data && (
          <section className="card" style={{ marginBottom: 24, padding: '16px 20px', background: 'var(--panel, #ffffff)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 16 }}>
              <div>
                <small style={{ color: 'var(--text-muted, #718096)', fontSize: 12 }}>Số mã trong danh mục</small>
                <div style={{ fontSize: 20, fontWeight: 700 }}>{holdings.length} mã</div>
              </div>
              <div>
                <small style={{ color: 'var(--text-muted, #718096)', fontSize: 12 }}>Cơ hội có thể mua</small>
                <div style={{ fontSize: 20, fontWeight: 700, color: buyableCount > 0 ? '#48bb78' : 'inherit' }}>
                  {buyableCount} mã
                </div>
              </div>
              <div>
                <small style={{ color: 'var(--text-muted, #718096)', fontSize: 12 }}>Đang theo dõi / Giữ</small>
                <div style={{ fontSize: 20, fontWeight: 700 }}>{watchCount} mã</div>
              </div>
              <div>
                <small style={{ color: 'var(--text-muted, #718096)', fontSize: 12 }}>Cần xem xét thêm</small>
                <div style={{ fontSize: 20, fontWeight: 700, color: reviewCount > 0 ? '#dd6b20' : 'inherit' }}>
                  {reviewCount} mã
                </div>
              </div>
              <div>
                <small style={{ color: 'var(--text-muted, #718096)', fontSize: 12 }}>Cảnh báo bẫy giá trị</small>
                <div style={{ fontSize: 20, fontWeight: 700, color: valueTrapWarningCount > 0 ? '#e53e3e' : 'inherit' }}>
                  {valueTrapWarningCount} mã
                </div>
              </div>
            </div>
          </section>
        )}

        {/* ── DANH MỤC section (always rendered, has its own loading state) */}
        <PortfolioSection onRefreshTerminal={loadData} />

        {/* ── Buffett / Munger analysis sections */}
        {loading && <div className="loading-state">Đang tải dữ liệu Pháo đài và Ma trận quyết định…</div>}
        {error && <div className="error-box">Lỗi: {error}</div>}

        {data && (
          <div className="terminal-grid">
            {/* Coach Summary */}
            <section className="card coach-summary-card">
              <div className="card-header">
                <h3>Huấn Luyện Viên Buffett &amp; Munger</h3>
              </div>
              <div className="coach-narrative">
                <p><strong>{data.coach_summary}</strong></p>
              </div>
            </section>

            {/* Personal Fortress */}
            <section className="card fortress-card">
              <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3>Pháo Đài Tài Chính Cá Nhân</h3>
                <span className={`status-badge ${data.fortress.status || 'UNKNOWN'}`}>
                  Dự phòng: {formatFortressStatus(data.fortress.survival_reserve_status)}
                </span>
              </div>
              <div className="metric-grid">
                <div className="metric-item">
                  <small>Tháng sinh tồn</small>
                  <strong>{data.fortress.survival_months != null ? `${data.fortress.survival_months} tháng` : 'Chưa xác định'}</strong>
                </div>
                <div className="metric-item">
                  <small>Vốn khả dụng dài hạn</small>
                  <strong>{fmtMoney(data.fortress.available_long_term_capital)}</strong>
                </div>
                <div className="metric-item">
                  <small>Tiền mặt cơ hội</small>
                  <strong>{fmtMoney(data.fortress.opportunity_cash)}</strong>
                </div>
                <div className="metric-item">
                  <small>Trạng thái nợ ngắn hạn</small>
                  <strong>{formatLiabilityStatus(data.fortress.near_term_liability_status)}</strong>
                </div>
              </div>
              {data.fortress.survival_reserve_status === 'UNKNOWN' && (
                <div style={{ marginTop: 16 }}>
                  <a href="/capital" className="btn btn-primary" style={{ display: 'inline-block', padding: '8px 16px', textDecoration: 'none', fontWeight: 600 }}>
                    Cấu hình bảng cân đối cá nhân →
                  </a>
                </div>
              )}
            </section>

            {/* Exceptions */}
            {data.exceptions && data.exceptions.length > 0 && (
              <section className="card attention-card">
                <div className="card-header">
                  <h3>Cần Chú Ý Đặc Biệt ({data.exceptions.length})</h3>
                </div>
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Mã</th>
                        <th>Chất lượng doanh nghiệp</th>
                        <th>Quyết định</th>
                        <th>Lý do chính</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.exceptions.map((exc) => (
                        <tr key={exc.symbol} onClick={() => setSelectedHolding(exc)} style={{ cursor: 'pointer' }}>
                          <td><strong>{exc.symbol}</strong></td>
                          <td>{formatQualityTier(exc.quality_tier)}</td>
                          <td>
                            <span className={`decision-tag ${exc.decision}`}>
                              {formatDecision(exc.decision)}
                            </span>
                          </td>
                          <td>{formatSafeText(exc.evidence?.summary, 'Cần xem xét thêm')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {/* Holdings Decision Matrix */}
            <section className="card holdings-matrix-card">
              <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ margin: 0 }}>Ma Trận Quyết Định Danh Mục</h3>
                  <small style={{ color: 'var(--text-muted, #718096)' }}>
                    Nhấn vào từng hàng để xem phân tích định giá chi tiết và cảnh báo tài chính
                  </small>
                </div>
              </div>
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Mã</th>
                      <th style={{ textAlign: 'right' }}>Tỷ trọng</th>
                      <th>Chất lượng doanh nghiệp</th>
                      <th style={{ textAlign: 'right' }}>Giá thị trường</th>
                      <th style={{ textAlign: 'right' }}>Base IV (Định giá)</th>
                      <th style={{ textAlign: 'right' }}>Biên an toàn (MOS)</th>
                      <th>Bẫy giá trị</th>
                      <th>Quyết định</th>
                    </tr>
                  </thead>
                  <tbody>
                    {holdings.map((h) => (
                      <tr
                        key={h.symbol}
                        onClick={() => setSelectedHolding(h)}
                        style={{ cursor: 'pointer' }}
                        title="Nhấn để xem chi tiết phân tích"
                      >
                        <td>
                          <a
                            href={`/business/${h.symbol}`}
                            onClick={(e) => e.stopPropagation()}
                            style={{ fontWeight: 700, color: 'inherit', textDecoration: 'none' }}
                          >
                            {h.symbol}
                          </a>
                        </td>
                        <td style={{ textAlign: 'right' }}>{(Number(h.weight || 0) * 100).toFixed(1)}%</td>
                        <td>{formatQualityTier(h.quality_tier)}</td>
                        <td style={{ textAlign: 'right' }}>
                          {h.price ? `${fmtNum(h.price)} ₫` : <span style={{ color: 'var(--text-muted, #718096)' }}>—</span>}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          {h.base_iv ? `${fmtNum(h.base_iv)} ₫` : <span style={{ color: 'var(--text-muted, #718096)' }}>Chưa đủ dữ liệu</span>}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          {h.actual_mos_pct != null ? `${Number(h.actual_mos_pct).toFixed(1)}%` : <span style={{ color: 'var(--text-muted, #718096)' }}>—</span>}
                        </td>
                        <td>
                          <span className={`vt-badge ${h.value_trap_status || 'CLEAR'}`}>
                            {formatValueTrap(h.value_trap_status)}
                          </span>
                        </td>
                        <td>
                          <span className={`decision-tag ${h.decision || 'HOLD'}`}>
                            {formatDecision(h.decision)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        )}

        {/* Modal drill-down for holding */}
        {selectedHolding && (
          <HoldingDetailModal
            item={selectedHolding}
            onClose={() => setSelectedHolding(null)}
          />
        )}
      </main>
    </div>
  );
}
