import React, { useMemo } from 'react';
import { formatMoney } from '../lib/format.js';

function money(value, locale = 'vi') {
  return value == null || !Number.isFinite(Number(value)) ? '-' : `${formatMoney(value, false, locale)} ₫`;
}

export function dividendEventDate(event) {
  return event?.effective_event_date || event?.record_date || event?.ex_date || event?.announcement_date || event?.payment_date || null;
}

function eventYear(event) {
  const value = dividendEventDate(event);
  const year = Number(String(value || '').slice(0, 4));
  return Number.isInteger(year) && year >= 1900 && year <= 2200 ? year : null;
}

function eventLabel(event) {
  return event.dividend_type === 'CASH_DIVIDEND' ? 'Cổ tức tiền mặt' : 'Cổ tức cổ phiếu';
}

function eventValue(event, locale) {
  if (event.dividend_type === 'CASH_DIVIDEND') return money(event.cash_per_share, locale);
  return event.stock_ratio_percent != null && Number.isFinite(Number(event.stock_ratio_percent))
    ? `${Number(event.stock_ratio_percent).toFixed(2)}%`
    : '-';
}

function sourceName(event) {
  return String(event?.source || event?.provider || 'Không rõ nguồn').trim() || 'Không rõ nguồn';
}

function EventLeaf({ event, locale }) {
  return <article className="dividend-tree-event">
    <div className="dividend-tree-event-main">
      <div><span>Ngày sự kiện</span><strong>{dividendEventDate(event) || '-'}</strong></div>
      <div><span>Loại</span><strong>{eventLabel(event)}</strong></div>
      <div><span>{event.dividend_type === 'CASH_DIVIDEND' ? 'Tiền/CP' : 'Tỷ lệ'}</span><strong>{eventValue(event, locale)}</strong></div>
      <div><span>Thanh toán</span><strong>{event.payment_date || '-'}</strong></div>
    </div>
    <details className="dividend-tree-event-detail">
      <summary>Chi tiết sự kiện</summary>
      <div className="dividend-tree-detail-grid">
        <div><span>Ngày GDKHQ</span><b>{event.ex_date || '-'}</b></div>
        <div><span>Đăng ký cuối cùng</span><b>{event.record_date || '-'}</b></div>
        <div><span>Ngày công bố</span><b>{event.announcement_date || '-'}</b></div>
        <div><span>Nguồn dữ liệu</span><b>{sourceName(event)}</b></div>
      </div>
    </details>
  </article>;
}

function byDateDesc(a, b) {
  return String(dividendEventDate(b) || '').localeCompare(String(dividendEventDate(a) || ''));
}

function SourceGroups({ events, symbol, year, locale }) {
  const sources = [...new Set(events.map(sourceName))].sort((a, b) => a.localeCompare(b));
  return <div className="dividend-tree-sources">
    {sources.map(source => {
      const sourceEvents = events.filter(event => sourceName(event) === source).sort(byDateDesc);
      return <details className="dividend-tree-node dividend-tree-source" open key={`${symbol}-${year}-${source}`}>
        <summary>
          <span className="tree-caret" aria-hidden="true">›</span>
          <strong>Nguồn dữ liệu: {source}</strong>
          <span>{sourceEvents.length} sự kiện</span>
        </summary>
        <div className="dividend-tree-events">
          {sourceEvents.map((event, index) => <EventLeaf
            key={`${symbol}-${year}-${source}-${dividendEventDate(event)}-${event.dividend_type}-${event.source_event_id || index}`}
            event={event}
            locale={locale}
          />)}
        </div>
      </details>;
    })}
  </div>;
}

export default function DividendTree({ rows = [], locale = 'vi', root = 'symbol', openLatest = true }) {
  const prepared = useMemo(() => rows
    .filter(row => row && row.symbol)
    .map(row => ({
      symbol: String(row.symbol || '').toUpperCase(),
      events: [...(row.events || [])].sort(byDateDesc),
      error: row.error || null,
      loading: Boolean(row.loading),
    })), [rows]);

  if (root === 'year') {
    const all = prepared.flatMap(row => row.events.map(event => ({ ...event, symbol: row.symbol })));
    const years = [...new Set(all.map(eventYear).filter(Boolean))].sort((a, b) => b - a);
    return <div className="dividend-tree" role="tree">
      {years.map((year, yearIndex) => {
        const yearEvents = all.filter(event => eventYear(event) === year);
        const symbols = [...new Set(yearEvents.map(event => event.symbol))].sort();
        return <details className="dividend-tree-node dividend-tree-year" open={openLatest && yearIndex === 0} key={year}>
          <summary><span className="tree-caret" aria-hidden="true">›</span><strong>Năm {year}</strong><span>{yearEvents.length} sự kiện</span></summary>
          <div className="dividend-tree-children">
            {symbols.map(symbol => {
              const events = yearEvents.filter(event => event.symbol === symbol).sort(byDateDesc);
              return <details className="dividend-tree-node dividend-tree-symbol" open key={`${year}-${symbol}`}>
                <summary><span className="tree-caret" aria-hidden="true">›</span><strong>{symbol}</strong><span>{events.length} sự kiện</span></summary>
                <SourceGroups events={events} symbol={symbol} year={year} locale={locale} />
              </details>;
            })}
          </div>
        </details>;
      })}
    </div>;
  }

  return <div className="dividend-tree" role="tree">
    {prepared.map((row, symbolIndex) => {
      const years = [...new Set(row.events.map(eventYear).filter(Boolean))].sort((a, b) => b - a);
      return <details className="dividend-tree-node dividend-tree-symbol-root" open={openLatest && symbolIndex === 0} key={row.symbol}>
        <summary><span className="tree-caret" aria-hidden="true">›</span><strong>{row.symbol}</strong><span>{row.loading ? 'Đang tải…' : row.error ? 'Lỗi tải dữ liệu' : `${row.events.length} sự kiện`}</span></summary>
        <div className="dividend-tree-children">
          {row.error ? <div className="data-error-message compact-error" role="alert">{row.error}</div> : row.loading ? <div className="dividend-tree-placeholder">Đang tải dữ liệu…</div> : years.length === 0 ? <div className="empty-state compact-empty">Chưa tìm thấy sự kiện cổ tức cho {row.symbol}.</div> : years.map((year, yearIndex) => {
            const events = row.events.filter(event => eventYear(event) === year).sort(byDateDesc);
            return <details className="dividend-tree-node dividend-tree-year" open={openLatest && yearIndex === 0} key={`${row.symbol}-${year}`}>
              <summary><span className="tree-caret" aria-hidden="true">›</span><strong>Năm {year}</strong><span>{events.length} sự kiện</span></summary>
              <SourceGroups events={events} symbol={row.symbol} year={year} locale={locale} />
            </details>;
          })}
        </div>
      </details>;
    })}
  </div>;
}
