import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { crawlValuationHistory } from '../lib/api.js';

/**
 * Popup nhập TCBS Bearer token khi crawl trả về 401/403 (TCBS_AUTH_REQUIRED).
 * Lưu token vào server rồi crawl lại, kèm section chi tiết lỗi.
 */
export default function TcbsTokenPrompt({ symbol, errorDetail, onClose, onSuccess }) {
  const [token, setToken] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState(null);

  const submit = async () => {
    if (!token.trim() || submitting) return;
    setSubmitting(true);
    setMessage(null);
    try {
      await crawlValuationHistory(symbol, token.trim());
      setMessage({ ok: true, text: 'Token đã lưu. Đang tải lại…' });
      onSuccess?.();
    } catch (err) {
      setMessage({ ok: false, text: err?.message || 'Crawl TCBS thất bại.' });
    } finally {
      setSubmitting(false);
    }
  };

  return createPortal(
    <div className="tcbs-token-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="tcbs-token-title">
      <div className="tcbs-token-modal" onClick={e => e.stopPropagation()}>
        <div className="tcbs-token-head">
          <b id="tcbs-token-title">🔑 Nhập TCBS Bearer Token — {symbol}</b>
          <button className="tcbs-token-close" type="button" onClick={onClose} aria-label="Đóng">✕</button>
        </div>

        <p className="tcbs-token-desc">
          Để crawl lịch sử BCTC (7–10 năm) từ TCBS, cần Bearer token từ phiên TCInvest:
          mở <code>tcinvest.tcbs.com.vn</code> → F12 → tab <b>Network</b> → lọc <code>apiextaws</code> →
          copy giá trị header <code>Authorization</code> (dạng <code>Bearer eyJ…</code>).
        </p>

        {errorDetail && (
          <div className="tcbs-token-error">
            <b>Chi tiết lỗi:</b>
            <pre>{errorDetail}</pre>
          </div>
        )}

        <input
          type="text"
          className="tcbs-token-input"
          placeholder="Bearer eyJhbGciOiJSUzI1NiIs..."
          value={token}
          onChange={e => setToken(e.target.value)}
          autoFocus
          spellCheck={false}
        />

        {message && (
          <div className={`tcbs-token-msg ${message.ok ? 'ok' : 'err'}`} role="status">{message.text}</div>
        )}

        <div className="tcbs-token-actions">
          <button className="btn-secondary" type="button" onClick={onClose} disabled={submitting}>Hủy</button>
          <button className="tcbs-token-submit" type="button" onClick={submit} disabled={submitting || !token.trim()}>
            {submitting ? 'Đang lưu & crawl…' : 'Lưu & thử lại'}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}