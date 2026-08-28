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

function sourceName(event) {
  return String(event?.source || event?.provider || 'Không rõ nguồn').trim() || 'Không rõ nguồn';
}

function byDateDesc(a, b) {
  return String(dividendEventDate(b) || '').localeCompare(String(dividendEventDate(a) || ''));
}

export function formatDividendDescription(event, locale = 'vi') {
  const date = dividendEventDate(event);
  const year = date ? date.slice(0, 4) : '';
  const isCash = event.dividend_type === 'CASH_DIVIDEND';

  if (isCash) {
    const cashStr = event.cash_per_share != null && Number.isFinite(Number(event.cash_per_share))
      ? `${formatMoney(event.cash_per_share, false, locale)}đ/CP`
      : 'bằng tiền';
    return `Cổ tức ${year ? `năm ${year} ` : ''}bằng tiền, tỷ lệ ${cashStr}`;
  }

  const rawRatio = event.stock_ratio_percent != null
    ? Number(event.stock_ratio_percent)
    : (event.stock_ratio != null ? Number(event.stock_ratio) * 100.0 : null);

  let ratioDisplay = `${rawRatio ? rawRatio.toFixed(0) : ''}%`;
  if (rawRatio != null && Number.isFinite(rawRatio)) {
    if (Math.abs(rawRatio - 13) < 0.1) ratioDisplay = '100:13';
    else if (Math.abs(rawRatio - 15) < 0.1) ratioDisplay = '100:15';
    else if (Math.abs(rawRatio - 10) < 0.1) ratioDisplay = '10:1';
    else if (Math.abs(rawRatio - 20) < 0.1) ratioDisplay = '100:20';
    else if (Math.abs(rawRatio - 25) < 0.1) ratioDisplay = '100:25';
    else if (Math.abs(rawRatio - 30) < 0.1) ratioDisplay = '100:30';
    else if (Math.abs(rawRatio - 50) < 0.1) ratioDisplay = '100:50';
    else ratioDisplay = `${rawRatio.toFixed(1)}%`;
  }
  return `Cổ tức ${year ? `năm ${year} ` : ''}bằng cổ phiếu, tỷ lệ ${ratioDisplay}`;
}

export function EventLeaf({ event, locale }) {
  const isCash = event.dividend_type === 'CASH_DIVIDEND';
  const eventDate = dividendEventDate(event) || '-';
  const payDate = event.payment_date || '-';
  const desc = formatDividendDescription(event, locale);

  return <tr className={`dividend-table-row ${isCash ? 'row-cash' : 'row-stock'}`}>
    <td className="col-date col-ex-date"><strong>{eventDate}</strong></td>
    <td className="col-desc">
      <div className="desc-cell">
        <span className={`dividend-pill-badge ${isCash ? 'badge-cash' : 'badge-stock'}`}>
          {isCash ? 'Tiền mặt' : 'Cổ phiếu'}
        </span>
        <span className="desc-text">{desc}</span>
      </div>
    </td>
    <td className="col-date col-pay-date">{payDate}</td>
  </tr>;
}

export function SourceGroups({ events, symbol, year, locale }) {
  const sources = [...new Set(events.map(sourceName))].sort((a, b) => a.localeCompare(b));
  return <div className="dividend-accordion-sources dividend-tree-sources">
    {sources.map(source => {
      const sourceEvents = events.filter(event => sourceName(event) === source).sort(byDateDesc);
      return <details className="dividend-tree-node dividend-tree-source" open key={`${symbol}-${year}-${source}`}>
        <summary className="dividend-source-label">
          <span className="source-pill">Nguồn dữ liệu: <strong>{source}</strong></span>
          <span className="source-count">{sourceEvents.length} sự kiện</span>
        </summary>
        <div className="dividend-table-container">
          <table className="dividend-event-table">
            <thead>
              <tr>
                <th style={{ width: '160px' }}>Ngày sự kiện (GDKHQ)</th>
                <th>Chi tiết quyền & tỷ lệ thực hiện</th>
                <th style={{ width: '160px' }}>Ngày thanh toán</th>
              </tr>
            </thead>
            <tbody>
              {sourceEvents.map((event, index) => <EventLeaf
                key={`${symbol}-${year}-${source}-${dividendEventDate(event)}-${event.dividend_type}-${event.source_event_id || index}`}
                event={event}
                locale={locale}
              />)}
            </tbody>
          </table>
        </div>
      </details>;
    })}
  </div>;
}

export function DividendTable({ events = [], symbol = '', locale = 'vi' }) {
  const sorted = useMemo(() => [...events].sort(byDateDesc), [events]);
  if (!sorted.length) {
    return <div className="empty-state compact-empty">Chưa có lịch sử sự kiện cổ tức.</div>;
  }

  return <div className="dividend-table-wrapper">
    <table className="dividend-event-table">
      <thead>
        <tr>
          <th className="col-header-date">Ngày sự kiện (GDKHQ)</th>
          <th className="col-header-desc">Nội dung chi tiết cổ tức / Tỷ lệ</th>
          <th className="col-header-pay">Ngày thanh toán</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((event, index) => <EventLeaf
          key={`${symbol}-${dividendEventDate(event)}-${event.dividend_type}-${index}`}
          event={event}
          locale={locale}
        />)}
      </tbody>
    </table>
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

    return <div className="dividend-table-groups dividend-tree">
      {years.map((year, yearIndex) => {
        const yearEvents = all.filter(event => eventYear(event) === year);
        const isOpen = openLatest ? yearIndex === 0 : true;

        return <div className="dividend-symbol-section dividend-tree-node dividend-tree-year" key={year}>
          <div className="dividend-section-header">
            <div className="section-title-badge">
              <h3>Năm {year}</h3>
              <span className="event-count-tag">{yearEvents.length} sự kiện</span>
            </div>
          </div>
          <DividendTable events={yearEvents} symbol={year} locale={locale} />
        </div>;
      })}
    </div>;
  }

  // Symbol Root - Table list for each stock
  return <div className="dividend-table-groups dividend-tree">
    {prepared.map(row => {
      return <div className="dividend-symbol-section dividend-tree-node dividend-tree-symbol" key={row.symbol}>
        <div className="dividend-section-header">
          <div className="section-title-badge">
            <h3 className="stock-ticker-title">{row.symbol}</h3>
            <span className="event-count-tag">{row.events.length} sự kiện cổ tức</span>
          </div>
          {row.loading && <span className="loading-badge">Đang tải…</span>}
        </div>
        <DividendTable events={row.events} symbol={row.symbol} locale={locale} />
      </div>;
    })}
  </div>;
}

