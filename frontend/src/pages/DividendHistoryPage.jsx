import React, { useEffect, useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { getDividendHistory } from '../lib/api.js';
import { formatMoney } from '../lib/format.js';

function money(value, locale = 'vi') {
  return value == null || !Number.isFinite(Number(value)) ? '-' : `${formatMoney(value, false, locale)} ₫`;
}

function eventDate(event) {
  return event?.effective_event_date || event?.record_date || event?.ex_date || event?.announcement_date || event?.payment_date || '-';
}

function eventValue(event, locale) {
  if (event.dividend_type === 'CASH_DIVIDEND') return money(event.cash_per_share, locale);
  return event.stock_ratio_percent != null && Number.isFinite(Number(event.stock_ratio_percent))
    ? `${Number(event.stock_ratio_percent).toFixed(2)}%`
    : '-';
}

function eventLabel(event) {
  return event.dividend_type === 'CASH_DIVIDEND' ? 'Cổ tức tiền mặt' : 'Cổ tức cổ phiếu';
}

export default function DividendHistoryPage({ dashboard = {}, locale = 'vi' }) {
  const positions = dashboard.portfolio?.positions || [];
  const symbols = useMemo(
    () => positions.map(row => String(row.symbol || '').toUpperCase()).filter(Boolean),
    [positions],
  );
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  async function load(refresh = false) {
    if (!symbols.length) return;
    refresh ? setRefreshing(true) : setLoading(true);
    const loaded = [];
    for (let i = 0; i < symbols.length; i += 4) {
      const batch = symbols.slice(i, i + 4);
      const result = await Promise.all(batch.map(async symbol => {
        try {
          return { symbol, result: await getDividendHistory(symbol, { refresh }), error: null };
        } catch (error) {
          return { symbol, result: null, error: error.message || 'Không thể tải dữ liệu cổ tức.' };
        }
      }));
      loaded.push(...result);
      setRows([...loaded]);
    }
    setLoading(false);
    setRefreshing(false);
  }

  useEffect(() => {
    load(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbols.join('|')]);

  const totalEvents = rows.reduce((sum, row) => sum + Number(row.result?.events?.length || 0), 0);
  const failedSymbols = rows.filter(row => row.error).map(row => row.symbol);

  return <div className="page dividend-history-page">
    <AppNav active="dividends" locale={locale} />

    <header className="page-head">
      <div>
        <div className="eyebrow">Cổ tức & quyền</div>
        <h1>Lịch sử cổ tức</h1>
        <p className="muted">Lịch sử cổ tức của các mã hiện đang có trong danh mục. Dữ liệu được đọc từ cache trước và chỉ gọi nguồn ngoài khi cần làm mới.</p>
      </div>
      <button className="btn-secondary" type="button" onClick={() => load(true)} disabled={loading || refreshing || !symbols.length}>
        {refreshing ? 'Đang cập nhật…' : '↻ Cập nhật dữ liệu'}
      </button>
    </header>

    {failedSymbols.length > 0 && <div className="data-error-message" role="alert">
      Không thể tải lịch sử cổ tức cho <b>{failedSymbols.join(', ')}</b>. Các mã tải thành công vẫn được hiển thị bên dưới.
    </div>}

    {symbols.length === 0 ? <section className="card empty-state">
      <h2>Chưa có cổ phiếu trong danh mục</h2>
      <p>Hãy nhập danh mục trước khi xem lịch sử cổ tức.</p>
      <a className="btn-primary" href="/transactions">Nhập danh mục ban đầu</a>
    </section> : <>
      <div className="dividend-history-summary">
        <span><b>{symbols.length}</b> mã đang nắm giữ</span>
        <span><b>{loading && rows.length === 0 ? '-' : totalEvents}</b> sự kiện đã tải</span>
      </div>

      <div className="dividend-history-symbols">
        {symbols.map(symbol => {
          const row = rows.find(item => item.symbol === symbol);
          const events = row?.result?.events || [];
          const waiting = !row && loading;
          return <section className="card dividend-history-symbol" key={symbol}>
            <div className="section-head">
              <div>
                <div className="eyebrow">Mã cổ phiếu</div>
                <h2>{symbol}</h2>
                <p className="muted">{waiting ? 'Đang tải dữ liệu…' : row?.error ? 'Không thể tải dữ liệu.' : `${events.length} sự kiện đã ghi nhận`}</p>
              </div>
              <span className="status-pill">{waiting ? '-' : row?.result?.cache_hit ? 'CACHE' : row?.result ? 'ĐÃ TẢI' : '-'}</span>
            </div>

            {row?.error ? <div className="data-error-message compact-error" role="alert">{row.error}</div> : waiting ? <div className="dividend-history-placeholder">
              <div><span>Ngày</span><b>-</b></div>
              <div><span>Loại</span><b>-</b></div>
              <div><span>Giá trị</span><b>-</b></div>
              <div><span>Thanh toán</span><b>-</b></div>
            </div> : events.length === 0 ? <div className="empty-state compact-empty">Chưa tìm thấy sự kiện cổ tức cho {symbol}.</div> : <div className="dividend-history-events">
              {events.map((event, index) => <article className="dividend-history-event" key={`${symbol}-${eventDate(event)}-${event.dividend_type}-${event.source_event_id || index}`}>
                <div className="dividend-history-event-main">
                  <div><span>Ngày sự kiện</span><strong>{eventDate(event)}</strong></div>
                  <div><span>Loại</span><strong>{eventLabel(event)}</strong></div>
                  <div><span>{event.dividend_type === 'CASH_DIVIDEND' ? 'Tiền/CP' : 'Tỷ lệ'}</span><strong>{eventValue(event, locale)}</strong></div>
                  <div><span>Ngày thanh toán</span><strong>{event.payment_date || '-'}</strong></div>
                </div>
                <details>
                  <summary>Chi tiết</summary>
                  <div className="dividend-history-event-detail">
                    <div><span>Ngày GDKHQ</span><b>{event.ex_date || '-'}</b></div>
                    <div><span>Đăng ký cuối cùng</span><b>{event.record_date || '-'}</b></div>
                    <div><span>Ngày công bố</span><b>{event.announcement_date || '-'}</b></div>
                    <div><span>Nguồn</span><b>{event.source || '-'}</b></div>
                  </div>
                </details>
              </article>)}
            </div>}
          </section>;
        })}
      </div>
    </>}
  </div>;
}
