import React, { useMemo, useRef, useState } from 'react';
import { commitPortfolioImport, previewPortfolioImport } from '../lib/api.js';
import { formatMoney, formatShares } from '../lib/format.js';
import { IMPORT_EVENT_TYPES, importTemplate, parseQuickImport } from '../lib/quickImport.js';

const EVENT_LABELS = {
  POSITION_IMPORT: 'Vị thế đầu kỳ', CASH_DEPOSIT: 'Nạp tiền', BUY: 'Mua', SELL: 'Bán',
  RIGHTS_ISSUE: 'Quyền mua', CASH_WITHDRAW: 'Rút tiền', CASH_DIVIDEND: 'Cổ tức tiền',
  STOCK_DIVIDEND: 'Cổ tức cổ phiếu', SPLIT: 'Tách / gộp', FEE: 'Phí',
};

export default function QuickImportPanel({ today, locale = 'vi', onCommitted }) {
  const [mode, setMode] = useState('CURRENT');
  const [text, setText] = useState('');
  const [sourceName, setSourceName] = useState('quick-paste');
  const fileInputRef = useRef(null);
  const [preview, setPreview] = useState(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const parsedCount = useMemo(() => {
    try { return parseQuickImport(text, { mode, today }).length; } catch { return 0; }
  }, [text, mode, today]);

  function switchMode(nextMode) {
    setMode(nextMode);
    setText('');
    setPreview(null);
    setMessage('');
  }

  function clearInput() {
    setText('');
    setSourceName('quick-paste');
    setPreview(null);
    setMessage('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  async function loadFile(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      setMessage('Tệp vượt quá 5 MB. Hãy chia thành các lô tối đa 1.000 dòng.');
      return;
    }
    if (!/\.(csv|tsv|txt)$/i.test(file.name)) {
      setMessage('Hãy lưu Excel thành CSV/TSV, hoặc copy trực tiếp các ô từ Excel rồi dán vào đây.');
      return;
    }
    setText(await file.text());
    setSourceName(file.name);
    setPreview(null);
    setMessage('');
  }

  function requestBody() {
    return { mode, source_name: sourceName, rows: parseQuickImport(text, { mode, today }) };
  }

  async function runPreview() {
    setBusy(true); setMessage(''); setPreview(null);
    try { setPreview(await previewPortfolioImport(requestBody())); }
    catch (error) { setMessage(error.message); }
    finally { setBusy(false); }
  }

  async function commit() {
    setBusy(true); setMessage('');
    try {
      const result = await commitPortfolioImport({ ...requestBody(), idempotency_key: preview?.idempotency_key });
      setMessage(result.deduplicated ? 'Dữ liệu này đã được nhập trước đó; QPort không tạo bản ghi trùng.' : `Đã nhập an toàn ${result.row_count} giao dịch.`);
      if (typeof onCommitted === 'function') await onCommitted(result);
    } catch (error) { setMessage(error.message); }
    finally { setBusy(false); }
  }

  return <details className="card quick-import-panel">
    <summary>
      <div><span className="eyebrow">Onboarding 5 giây</span><b>Nhập nhanh bằng text / CSV</b><small>Dán từ Excel, xem trước và đối soát trước khi ghi sổ.</small></div>
      <span className="quick-import-count">{parsedCount || '—'} dòng</span>
    </summary>
    <div className="quick-import-body">
      <div className="import-mode-switch" role="radiogroup" aria-label="Chế độ nhập dữ liệu">
        <button type="button" role="radio" aria-checked={mode === 'CURRENT'} className={mode === 'CURRENT' ? 'active' : ''} onClick={() => switchMode('CURRENT')}>
          <b>Số dư hiện tại</b><span>Bắt đầu theo dõi từ hôm nay, không dựng lệnh mua giả.</span>
        </button>
        <button type="button" role="radio" aria-checked={mode === 'HISTORICAL'} className={mode === 'HISTORICAL' ? 'active' : ''} onClick={() => switchMode('HISTORICAL')}>
          <b>Lịch sử đầy đủ</b><span>Giữ ngày và toàn bộ loại giao dịch để tính lại hiệu suất.</span>
        </button>
      </div>

      <div className="quick-import-guidance" id="quick-import-guidance">
        <b>{mode === 'CURRENT' ? 'Cột: Mã, Số lượng, Giá vốn, CTCK, Tài khoản' : 'CSV có tiêu đề; hỗ trợ toàn bộ loại giao dịch'}</b>
        <span>{mode === 'CURRENT'
          ? 'Có thể thêm CASH_DEPOSIT bằng CSV có tiêu đề. Ngày được khóa về hôm nay.'
          : IMPORT_EVENT_TYPES.map(type => EVENT_LABELS[type]).join(' · ')}</span>
      </div>

      <label>Dữ liệu cần nhập
        <textarea
          className="quick-import-textarea"
          value={text}
          placeholder={importTemplate(mode)}
          aria-describedby="quick-import-guidance"
          onChange={event => { setText(event.target.value); setPreview(null); setMessage(''); }}
          spellCheck="false"
        />
      </label>
      <div className="quick-import-file-row">
        <label className="btn-variant quick-import-file">Chọn CSV / TSV / TXT<input ref={fileInputRef} type="file" accept=".csv,.tsv,.txt,text/csv,text/tab-separated-values,text/plain" onChange={loadFile} /></label>
        <span className="muted">Excel: copy vùng dữ liệu rồi dán, hoặc Save As CSV UTF-8.</span>
      </div>
      <div className="button-row quick-import-actions">
        <button className="btn-primary" type="button" onClick={runPreview} disabled={busy || !text.trim()}>{busy ? 'Đang kiểm tra…' : 'Kiểm tra & xem trước'}</button>
        <button className="btn-secondary quick-import-clear" type="button" onClick={clearInput} disabled={busy || (!text && !preview && !message)} aria-label="Xóa dữ liệu nhập nhanh">Xóa dữ liệu</button>
      </div>
      {message && <div className="run-message">{message}</div>}

      {preview && <div className="quick-import-preview">
        <div className="section-head compact-section-head"><div><h3>{preview.row_count} dòng hợp lệ</h3><p className="muted">Chưa có dữ liệu nào được ghi. Kiểm tra số dư dự kiến trước khi xác nhận.</p></div><span className="status-pill status-valid">Sẵn sàng</span></div>
        <div className="table-scroll"><table className="ranking quick-import-table">
          <thead><tr><th>Ngày</th><th>Loại</th><th>Mã</th><th className="num">SL</th><th className="num">Giá / Số tiền</th><th>CTCK</th></tr></thead>
          <tbody>{preview.rows.map((row, index) => <tr key={`${row.event_date}-${row.event_type}-${index}`}>
            <td>{row.event_date}</td><td>{EVENT_LABELS[row.event_type] || row.event_type}</td><td><b>{row.symbol || '—'}</b></td>
            <td className="num">{row.quantity ? formatShares(row.quantity, locale) : '—'}</td>
            <td className="num">{row.price ? `${formatMoney(row.price, false, locale)} ₫/CP` : row.amount ? `${formatMoney(row.amount, false, locale)} ₫` : row.ratio ? `×${row.ratio}` : '—'}</td>
            <td>{row.metadata?.broker_code || '—'}</td>
          </tr>)}</tbody>
        </table></div>
        <div className="import-reconciliation">
          <div><span>Tiền dự kiến</span><b>{formatMoney(preview.reconciliation.cash, false, locale)} ₫</b></div>
          <div><span>Sổ vị thế</span><b>{preview.reconciliation.holding_count}</b></div>
          <div><span>Tổng cổ phiếu</span><b>{formatShares(preview.reconciliation.total_shares, locale)}</b></div>
          <div><span>Đối soát</span><b>{preview.reconciliation.status}</b></div>
        </div>
        {preview.warnings?.map(warning => <div className="info-callout" key={warning}>{warning}</div>)}
        <div className="button-row"><button className="btn-primary" type="button" onClick={commit} disabled={busy}>{busy ? 'Đang ghi sổ…' : `Xác nhận nhập ${preview.row_count} dòng`}</button></div>
      </div>}
    </div>
  </details>;
}
