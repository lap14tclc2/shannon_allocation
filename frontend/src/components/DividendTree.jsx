import React, { useMemo, useState } from 'react';
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
    <td className="col-date col-ex-date">
      <span className="mobile-label">GDKHQ:</span>
      <strong className="date-val">{eventDate}</strong>
      <span className={`dividend-pill-badge mobile-badge ${isCash ? 'badge-cash' : 'badge-stock'}`}>
        {isCash ? 'Tiền mặt' : 'Cổ phiếu'}
      </span>
    </td>
    <td className="col-desc">
      <div className="desc-cell">
        <span className={`dividend-pill-badge desktop-badge ${isCash ? 'badge-cash' : 'badge-stock'}`}>
          {isCash ? 'Tiền mặt' : 'Cổ phiếu'}
        </span>
        <span className="desc-text">{desc}</span>
      </div>
    </td>
    <td className="col-date col-pay-date">
      <span className="mobile-label">Thanh toán:</span>
      <span className="date-val">{payDate}</span>
    </td>
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

export default function DividendTree({ rows = [], locale = 'vi', root = 'symbol', openLatest = false }) {
  const prepared = useMemo(() => rows
    .filter(row => row && row.symbol)
    .map(row => ({
      symbol: String(row.symbol || '').toUpperCase(),
      events: [...(row.events || [])].sort(byDateDesc),
      error: row.error || null,
      loading: Boolean(row.loading),
    })), [rows]);

  const [expandedSymbols, setExpandedSymbols] = useState(() => {
    const initial = {};
    prepared.forEach((row, idx) => {
      // If openLatest is true, open the first one; otherwise all start collapsed for clean glance
      initial[row.symbol] = openLatest ? idx === 0 : false;
    });
    return initial;
  });

  const [filterQuery, setFilterQuery] = useState('');

  const filtered = useMemo(() => {
    const q = filterQuery.trim().toUpperCase();
    if (!q) return prepared;
    return prepared.filter(row => row.symbol.includes(q));
  }, [prepared, filterQuery]);

  function toggleSymbol(symbol) {
    setExpandedSymbols(prev => ({
      ...prev,
      [symbol]: !prev[symbol],
    }));
  }

  function expandAll() {
    const next = {};
    prepared.forEach(row => { next[row.symbol] = true; });
    setExpandedSymbols(next);
  }

  function collapseAll() {
    const next = {};
    prepared.forEach(row => { next[row.symbol] = false; });
    setExpandedSymbols(next);
  }

  if (root === 'year') {
    const all = prepared.flatMap(row => row.events.map(event => ({ ...event, symbol: row.symbol })));
    const years = [...new Set(all.map(eventYear).filter(Boolean))].sort((a, b) => b - a);

    return <div className="dividend-table-groups dividend-tree">
      {years.map((year, yearIndex) => {
        const yearEvents = all.filter(event => eventYear(event) === year);

        return <details className="dividend-symbol-section dividend-tree-node dividend-tree-year" key={year} open={yearIndex === 0}>
          <summary className="dividend-section-header dividend-accordion-summary">
            <div className="section-title-badge">
              <h3>Năm {year}</h3>
              <span className="event-count-tag">{yearEvents.length} sự kiện</span>
            </div>
            <span className="accordion-chevron" aria-hidden="true">▾</span>
          </summary>
          <DividendTable events={yearEvents} symbol={year} locale={locale} />
        </details>;
      })}
    </div>;
  }

  // Symbol Root - Collapsible Accordion Cards for each Stock
  return (
    <div className="dividend-tree-container">
      <div className="dividend-tree-toolbar">
        <div className="dividend-toolbar-search">
          <input
            type="text"
            className="dividend-search-input"
            value={filterQuery}
            onChange={e => setFilterQuery(e.target.value.toUpperCase())}
            placeholder="Lọc nhanh mã cổ phiếu (FPT, HPG...)"
          />
          {filterQuery && (
            <button
              type="button"
              className="btn-clear-filter"
              onClick={() => setFilterQuery('')}
              aria-label="Xóa lọc"
            >
              ✕
            </button>
          )}
        </div>
        <div className="dividend-toolbar-actions">
          <button type="button" className="btn-small btn-accordion-action" onClick={expandAll}>
            Mở rộng tất cả
          </button>
          <button type="button" className="btn-small btn-accordion-action" onClick={collapseAll}>
            Thu gọn tất cả
          </button>
        </div>
      </div>

      <div className="dividend-table-groups dividend-tree">
        {filtered.length === 0 ? (
          <div className="empty-state compact-empty">
            Không tìm thấy mã cổ tức phù hợp với "<strong>{filterQuery}</strong>".
          </div>
        ) : (
          filtered.map(row => {
            const isOpen = Boolean(expandedSymbols[row.symbol]);
            const latestEvent = row.events[0];
            const latestDate = latestEvent ? dividendEventDate(latestEvent) : null;
            const isCashLatest = latestEvent?.dividend_type === 'CASH_DIVIDEND';

            return (
              <div
                className={`dividend-symbol-section dividend-tree-node dividend-tree-symbol ${isOpen ? 'is-open' : 'is-collapsed'}`}
                key={row.symbol}
              >
                <div
                  className="dividend-section-header dividend-accordion-header"
                  onClick={() => toggleSymbol(row.symbol)}
                  role="button"
                  tabIndex={0}
                  aria-expanded={isOpen}
                  onKeyDown={e => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      toggleSymbol(row.symbol);
                    }
                  }}
                >
                  <div className="section-title-badge">
                    <div className="ticker-badge-cluster">
                      <span className="accordion-chevron-icon" aria-hidden="true">
                        {isOpen ? '▼' : '▶'}
                      </span>
                      <h3 className="stock-ticker-title">{row.symbol}</h3>
                      <span className="event-count-tag">{row.events.length} sự kiện</span>
                    </div>
                    <span className="accordion-toggle-hint mobile-toggle-hint">
                      {isOpen ? 'Thu gọn' : 'Chi tiết'}
                    </span>
                  </div>

                  <div className="dividend-header-right">
                    {latestEvent && (
                      <span className="latest-dividend-peek" title="Sự kiện cổ tức gần nhất">
                        Gần nhất: <strong>{latestDate}</strong> ({isCashLatest ? 'Tiền mặt' : 'Cổ phiếu'})
                      </span>
                    )}
                    {row.loading && <span className="loading-badge">Đang tải…</span>}
                    <span className="accordion-toggle-hint desktop-toggle-hint">
                      {isOpen ? 'Thu gọn' : 'Chi tiết'}
                    </span>
                  </div>
                </div>

                {isOpen && (
                  <div className="dividend-accordion-content">
                    <DividendTable events={row.events} symbol={row.symbol} locale={locale} />
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
