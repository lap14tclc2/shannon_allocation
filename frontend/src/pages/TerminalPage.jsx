import React, { useCallback, useEffect, useRef, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import SymbolSuggestInput from '../components/SymbolSuggestInput.jsx';
import {
  addPortfolioPosition,
  deletePortfolioPosition,
  getBuffettTerminalData,
  getPortfolioPositions,
  setCashReserve,
  updatePortfolioPosition,
} from '../lib/api.js';

// ── Formatters ────────────────────────────────────────────────────────────────
const fmtNum = (n, digits = 0) =>
  n == null ? null : Number(n).toLocaleString('vi-VN', { minimumFractionDigits: digits, maximumFractionDigits: digits });
const fmtMoney = (n) => (n == null ? null : `${fmtNum(n)} ₫`);
const fmtPct = (n) => (n == null ? null : `${Number(n).toFixed(1)}%`);
const fmtPnl = (n) => {
  if (n == null) return null;
  const sign = n >= 0 ? '+' : '';
  return `${sign}${fmtNum(n)} ₫`;
};

const NA = 'Chưa có giá TT';
const EMPTY_PORTFOLIO = 'Chưa có vị thế nào';

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
function PortfolioSection() {
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
  const afterSave = () => { closeModal(); load(); };

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

  const positions = data?.positions || [];
  const summary = data?.summary || {};
  const cashReserve = data?.cash_reserve ?? 0;

  const pnlColor = (v) => (v == null ? undefined : v >= 0 ? '#48bb78' : '#fc8181');

  return (
    <section className="card" style={{ marginBottom: 24 }}>
      <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>Danh Mục</h3>
        <button
          onClick={() => setModal({ type: 'add' })}
          className="btn btn-primary"
          style={{ fontSize: 13, padding: '6px 14px' }}
        >
          + Thêm vị thế
        </button>
      </div>

      {loading && <div className="loading-state" style={{ padding: '16px 0' }}>Đang tải danh mục…</div>}
      {error && <div className="error-box">{error}</div>}

      {!loading && !error && (
        <>
          {positions.length === 0 ? (
            <div style={{ padding: '20px 0', color: 'var(--text-muted, #718096)', fontSize: 14 }}>
              {EMPTY_PORTFOLIO} — Nhấn <strong>+ Thêm vị thế</strong> để bắt đầu.
            </div>
          ) : (
            <div className="table-responsive">
              <table className="data-table" style={{ fontSize: 13 }}>
                <thead>
                  <tr>
                    <th>Mã</th>
                    <th style={{ textAlign: 'right' }}>SL</th>
                    <th style={{ textAlign: 'right' }}>Giá vốn</th>
                    <th style={{ textAlign: 'right' }}>Giá TT</th>
                    <th style={{ textAlign: 'right' }}>Vốn đầu tư</th>
                    <th style={{ textAlign: 'right' }}>Giá trị TT</th>
                    <th style={{ textAlign: 'right' }}>Lãi / Lỗ</th>
                    <th style={{ textAlign: 'right' }}>L/L%</th>
                    <th style={{ textAlign: 'right' }}>Tỷ trọng</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((p) => (
                    <tr key={p.symbol}>
                      <td><strong>{p.symbol}</strong></td>
                      <td style={{ textAlign: 'right' }}>{fmtNum(p.shares)}</td>
                      <td style={{ textAlign: 'right' }}>{fmtMoney(p.average_cost)}</td>
                      <td style={{ textAlign: 'right' }}>
                        {p.market_price != null ? fmtMoney(p.market_price) : <span style={{ color: '#718096' }}>{NA}</span>}
                      </td>
                      <td style={{ textAlign: 'right' }}>{fmtMoney(p.invested_value)}</td>
                      <td style={{ textAlign: 'right' }}>
                        {p.market_value != null && p.market_price != null
                          ? fmtMoney(p.market_value)
                          : <span style={{ color: '#718096' }}>{NA}</span>}
                      </td>
                      <td style={{ textAlign: 'right', color: pnlColor(p.unrealized_pnl) }}>
                        {p.unrealized_pnl != null ? fmtPnl(p.unrealized_pnl) : <span style={{ color: '#718096' }}>{NA}</span>}
                      </td>
                      <td style={{ textAlign: 'right', color: pnlColor(p.unrealized_pnl_pct) }}>
                        {p.unrealized_pnl_pct != null ? fmtPct(p.unrealized_pnl_pct) : <span style={{ color: '#718096' }}>—</span>}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        {p.weight != null ? fmtPct(p.weight * 100) : '—'}
                      </td>
                      <td style={{ whiteSpace: 'nowrap' }}>
                        {p.has_complex_ledger ? (
                          <a href="/transactions" style={{ fontSize: 12, color: '#718096' }}>Giao dịch</a>
                        ) : (
                          <>
                            <button
                              onClick={() => setModal({ type: 'edit', row: p })}
                              style={{ marginRight: 6, fontSize: 12, background: 'none', border: '1px solid #4a5568', borderRadius: 4, padding: '2px 8px', cursor: 'pointer', color: 'inherit' }}
                            >Sửa</button>
                            <button
                              onClick={() => setModal({ type: 'delete', row: p })}
                              style={{ fontSize: 12, background: 'none', border: '1px solid #e53e3e', borderRadius: 4, padding: '2px 8px', cursor: 'pointer', color: '#fc8181' }}
                            >Xóa</button>
                          </>
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
                <div style={{ fontSize: 12, color: '#718096' }}>Tiền mặt</div>
                <div style={{ fontWeight: 700, fontSize: 15 }}>
                  {fmtMoney(cashReserve)}
                  <button
                    onClick={() => setModal({ type: 'cash' })}
                    style={{ marginLeft: 8, fontSize: 11, background: 'none', border: '1px solid #4a5568', borderRadius: 4, padding: '2px 6px', cursor: 'pointer', color: '#718096' }}
                  >Sửa</button>
                </div>
              </div>
              {summary.total_invested > 0 && (
                <div>
                  <div style={{ fontSize: 12, color: '#718096' }}>Tổng vốn đầu tư</div>
                  <div style={{ fontWeight: 700 }}>{fmtMoney(summary.total_invested)}</div>
                </div>
              )}
              {summary.total_market_value != null && (
                <div>
                  <div style={{ fontSize: 12, color: '#718096' }}>Giá trị thị trường</div>
                  <div style={{ fontWeight: 700 }}>{fmtMoney(summary.total_market_value)}</div>
                </div>
              )}
              {summary.unrealized_pnl != null && (
                <div>
                  <div style={{ fontSize: 12, color: '#718096' }}>Lãi / Lỗ chưa thực hiện</div>
                  <div style={{ fontWeight: 700, color: pnlColor(summary.unrealized_pnl) }}>
                    {fmtPnl(summary.unrealized_pnl)} ({fmtPct(summary.unrealized_pnl_pct)})
                  </div>
                </div>
              )}
              {summary.total_portfolio_value > 0 && (
                <div>
                  <div style={{ fontSize: 12, color: '#718096' }}>Tổng danh mục</div>
                  <div style={{ fontWeight: 700 }}>{fmtMoney(summary.total_portfolio_value)}</div>
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

// ── Main Terminal page ────────────────────────────────────────────────────────
export default function TerminalPage() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getBuffettTerminalData()
      .then((res) => {
        if (res.ok) setData(res);
        else setError(res.error || 'Không thể tải dữ liệu phân tích.');
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="wealth-app-shell">
      <AppNav active="portfolio" />
      <main className="wealth-main-content" style={{ maxWidth: '1380px', margin: '0 auto', padding: '84px 24px 48px 24px', boxSizing: 'border-box' }}>
        <header className="page-header">
          <div>
            <span className="eyebrow">QPort Buffett Terminal</span>
            <h1>Trung Tâm Quyết Định Vốn Cá Nhân</h1>
          </div>
        </header>

        {/* ── DANH MỤC section (always rendered, has its own loading state) */}
        <PortfolioSection />

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
              <div className="card-header">
                <h3>Pháo Đài Tài Chính Cá Nhân</h3>
                <span className={`status-badge ${data.fortress.status}`}>
                  Dự phòng: {data.fortress.survival_reserve_status}
                </span>
              </div>
              <div className="metric-grid">
                <div className="metric-item">
                  <small>Tháng sinh tồn</small>
                  <strong>{data.fortress.survival_months} tháng</strong>
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
                  <strong>{data.fortress.near_term_liability_status}</strong>
                </div>
              </div>
              {data.fortress.survival_reserve_status === 'UNKNOWN' && (
                <div style={{ marginTop: 16 }}>
                  <a href="/capital" className="btn btn-primary" style={{ display: 'inline-block', padding: '8px 16px', background: '#0284c7', color: '#fff', borderRadius: 4, textDecoration: 'none', fontWeight: 600 }}>
                    [Cấu hình tài chính cá nhân]
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
                        <th>Mã</th><th>Chất lượng</th><th>Quyết định</th><th>Lý do chính</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.exceptions.map((exc) => (
                        <tr key={exc.symbol}>
                          <td><strong>{exc.symbol}</strong></td>
                          <td>{exc.quality_tier}</td>
                          <td><span className={`decision-tag ${exc.decision}`}>{exc.decision}</span></td>
                          <td>{exc.evidence.summary}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {/* Holdings Decision Matrix */}
            <section className="card holdings-matrix-card">
              <div className="card-header">
                <h3>Ma Trận Quyết Định Danh Mục</h3>
              </div>
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Mã</th><th>Tỷ trọng</th><th>Chất lượng</th><th>Giá thị trường</th>
                      <th>Base IV</th><th>Biên an toàn</th><th>Bẫy giá trị</th><th>Quyết định</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.holdings_matrix.map((h) => (
                      <tr key={h.symbol}>
                        <td><a href={`/business/${h.symbol}`}><strong>{h.symbol}</strong></a></td>
                        <td>{(Number(h.weight || 0) * 100).toFixed(1)}%</td>
                        <td>{h.quality_tier}</td>
                        <td>{h.price ? `${Number(h.price).toLocaleString()} VND` : '—'}</td>
                        <td>{h.base_iv ? `${Number(h.base_iv).toLocaleString()} VND` : '—'}</td>
                        <td>{h.actual_mos_pct != null ? `${Number(h.actual_mos_pct).toFixed(1)}%` : '—'}</td>
                        <td><span className={`vt-badge ${h.value_trap_status}`}>{h.value_trap_status}</span></td>
                        <td><span className={`decision-tag ${h.decision}`}>{h.decision}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
