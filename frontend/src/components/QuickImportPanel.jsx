import React, { useMemo, useRef, useState } from 'react';
import { commitPortfolioImport, previewPortfolioImport } from '../lib/api.js';
import { formatMoney, formatShares } from '../lib/format.js';
import { importTemplate, parseQuickImport } from '../lib/quickImport.js';

const EVENT_LABELS = {
  POSITION_IMPORT: 'Vị thế đầu kỳ',
  CASH_DEPOSIT: 'Nạp tiền',
};

export default function QuickImportPanel({ today, locale = 'vi', onCommitted }) {
  const [text, setText] = useState('');
  const [sourceName, setSourceName] = useState('quick-paste');
  const [confirmed, setConfirmed] = useState(false);
  const fileInputRef = useRef(null);
  const [preview, setPreview] = useState(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const parsedCount = useMemo(() => {
    try { return parseQuickImport(text, { today }).length; } catch { return 0; }
  }, [text, today]);

  function clearInput() {
    setText('');
    setSourceName('quick-paste');
    setConfirmed(false);
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
    return {
      mode: 'CURRENT',
      source_name: sourceName,
      cost_basis_adjusted: confirmed,
      rows: parseQuickImport(text, { today }),
    };
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
      <div><span className="eyebrow">Onboarding 5 giây</span><b>Nhập nhanh số dư hiện tại</b><small>Dán từ Excel, xem trước và đối soát trước khi ghi sổ.</small></div>
      <span className="quick-import-count">{parsedCount || '—'} dòng</span>
    </summary>
    <div className="quick-import-body">
      <div className="quick-import-guidance" id="quick-import-guidance">
        <b>Cột: Mã, Số lượng, Giá vốn sau điều chỉnh, CTCK, Tài khoản</b>
        <span>QPort tự ghi ngày hôm nay theo giờ Việt Nam; người dùng không cần chọn ngày. Có thể thêm CASH_DEPOSIT bằng CSV có tiêu đề.</span>
      </div>

      <div className="cost-basis-guidance" id="quick-import-cost-guidance">
        <p><b>Giá vốn sau điều chỉnh (VND/cp):</b> nhập giá vốn hiện tại sau khi đã điều chỉnh cho các lần chia/tách, cổ tức bằng cổ phiếu và cổ phiếu thưởng trước hôm nay. Không tự trừ cổ tức tiền mặt khỏi giá vốn. QPort bắt đầu theo dõi từ hôm nay và không tái dựng các sự kiện trước ngày này.</p>
        <details className="cost-basis-guide">
          <summary>Ví dụ và cách tính giá vốn sau điều chỉnh</summary>
          <ul>
            <li>Trước khi tách: <b>100 CP × 100.000 VND</b>.</li>
            <li>Sau khi tách 2:1: <b>200 CP × 50.000 VND</b>.</li>
            <li>Tổng giá vốn vẫn là <b>10.000.000 VND</b>.</li>
            <li>Cổ tức cổ phiếu / cổ phiếu thưởng làm tăng số lượng và giảm giá vốn bình quân tương ứng.</li>
            <li>Cổ tức tiền mặt không làm thay đổi giá vốn bạn nhập.</li>
            <li>Không nhập giá mua gốc chưa điều chỉnh nếu số lượng đã là số lượng sau chia/tách.</li>
            <li>Giá dùng đơn vị <b>VND đầy đủ trên mỗi cổ phiếu</b> (ví dụ 72.000, không phải 72).</li>
          </ul>
        </details>
      </div>

      <label>Dữ liệu cần nhập
        <textarea
          className="quick-import-textarea"
          value={text}
          placeholder={importTemplate()}
          aria-describedby="quick-import-guidance quick-import-cost-guidance"
          onChange={event => { setText(event.target.value); setPreview(null); setMessage(''); }}
          spellCheck="false"
        />
      </label>
      <div className="quick-import-file-row">
        <label className="btn-variant quick-import-file">Chọn CSV / TSV / TXT<input ref={fileInputRef} type="file" accept=".csv,.tsv,.txt,text/csv,text/tab-separated-values,text/plain" onChange={loadFile} /></label>
        <span className="muted">Excel: copy vùng dữ liệu rồi dán, hoặc Save As CSV UTF-8.</span>
      </div>
      <label className="quick-import-confirm">
        <input type="checkbox" checked={confirmed} onChange={event => { setConfirmed(event.target.checked); setPreview(null); setMessage(''); }} />
        <span>Tôi xác nhận số lượng và giá vốn đã phản ánh toàn bộ chia/tách, cổ tức cổ phiếu và cổ phiếu thưởng trước hôm nay.</span>
      </label>

      <div className="button-row quick-import-actions">
        <button className="btn-primary" type="button" onClick={runPreview} disabled={busy || !text.trim() || !confirmed}>{busy ? 'Đang kiểm tra…' : 'Kiểm tra & xem trước'}</button>
        <button className="btn-secondary quick-import-clear" type="button" onClick={clearInput} disabled={busy || (!text && !preview && !message)} aria-label="Xóa dữ liệu nhập nhanh">Xóa dữ liệu</button>
      </div>
      {message && <div className="run-message">{message}</div>}

      {preview && <div className="quick-import-preview">
        <div className="section-head compact-section-head"><div><h3>{preview.row_count} dòng hợp lệ</h3><p className="muted">Chưa có dữ liệu nào được ghi. Kiểm tra số dư dự kiến trước khi xác nhận.</p></div><span className="status-pill status-valid">Sẵn sàng</span></div>
        <div className="table-scroll"><table className="ranking quick-import-table">
          <thead><tr><th>Loại</th><th>Mã</th><th className="num">SL</th><th className="num">Giá / Số tiền</th><th>CTCK</th></tr></thead>
          <tbody>{preview.rows.map((row, index) => <tr key={`${row.event_type}-${row.symbol || 'cash'}-${index}`}>
            <td>{EVENT_LABELS[row.event_type] || row.event_type}</td><td><b>{row.symbol || '—'}</b></td>
            <td className="num">{row.quantity ? formatShares(row.quantity, locale) : '—'}</td>
            <td className="num">{row.price ? `${formatMoney(row.price, false, locale)} ₫/CP` : row.amount ? `${formatMoney(row.amount, false, locale)} ₫` : '—'}</td>
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
