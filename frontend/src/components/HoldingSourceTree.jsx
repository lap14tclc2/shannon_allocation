import React from 'react';
import { formatMoney, formatShares, formatWeight } from '../lib/format.js';
import { BROKERS } from '../lib/brokers.js';

function money(value, locale) {
  return value == null || !Number.isFinite(Number(value)) ? '-' : `${formatMoney(value, false, locale)} ₫`;
}

function pct(value, digits = 2) {
  return value == null || !Number.isFinite(Number(value)) ? '-' : `${(Number(value) * 100).toFixed(digits)}%`;
}

function brokerName(code) {
  return BROKERS.find(item => item.code === code)?.name || code || 'Chưa gán';
}

function buyHref(book) {
  const params = new URLSearchParams({
    action: 'buy',
    symbol: book.symbol,
    broker: book.broker_code,
    account: book.account_id,
  });
  return `/transactions?${params.toString()}`;
}

function sellHref(book) {
  const params = new URLSearchParams({
    action: 'sell',
    symbol: book.symbol,
    broker: book.broker_code,
    account: book.account_id,
  });
  return `/transactions?${params.toString()}`;
}

export default function HoldingSourceTree({ positions = [], holdingBooks = [], locale = 'vi', loading = false, error = '' }) {
  return <div className="holding-source-tree" role="tree">
    {positions.map((position, index) => {
      const symbol = String(position.symbol || '').toUpperCase();
      const books = holdingBooks.filter(book => book.symbol === symbol);
      const pnl = position.unrealized_pnl == null ? null : Number(position.unrealized_pnl);
      return <details className="holding-source-symbol" open={index === 0} key={symbol}>
        <summary>
          <span className="tree-caret" aria-hidden="true">›</span>
          <div className="holding-source-symbol-name">
            <strong>{symbol}</strong>
            <span>{formatShares(position.shares, locale)} CP</span>
          </div>
          <div className="holding-source-symbol-value">
            <strong>{money(position.market_value, locale)}</strong>
            <span className={pnl == null ? '' : pnl >= 0 ? 'pos' : 'neg'}>{pnl == null ? '-' : `${pnl >= 0 ? '+' : ''}${money(pnl, locale)}`} · {pct(position.unrealized_return)}</span>
          </div>
          <span className="holding-source-weight">{formatWeight(position.weight)}</span>
        </summary>

        <div className="holding-source-children">
          <div className="holding-source-meta">
            <span>Giá vốn <b>{money(position.average_cost, locale)}</b></span>
            <span>Giá hiện tại <b>{money(position.price, locale)}</b></span>
            <span>{position.price_date ? `Giá ngày ${position.price_date}` : 'Giá chưa cập nhật'}</span>
          </div>

          {loading && books.length === 0 ? <div className="dividend-tree-placeholder">Đang xác định CTCK đang lưu ký…</div>
            : error && books.length === 0 ? <div className="data-error-message compact-error" role="alert">{error}</div>
              : books.length === 0 ? <div className="empty-state compact-empty">Chưa xác định được CTCK đang giữ {symbol}. Hãy kiểm tra CTCK trên giao dịch mua/nhập danh mục.</div>
                : <div className="holding-source-books">
                  {books.map(book => {
                    const assigned = book.broker_code !== 'UNASSIGNED';
                    const sourceValue = position.price == null ? null : Number(position.price) * Number(book.shares);
                    return <article className="holding-source-book" key={`${book.symbol}-${book.broker_code}-${book.account_id}`}>
                      <div className="holding-source-book-main">
                        <span className="holding-source-broker-label">CTCK đang lưu ký</span>
                        <strong>{brokerName(book.broker_code)}</strong>
                        <span>Tài khoản {book.account_id}</span>
                      </div>
                      <div className="holding-source-book-numbers">
                        <div><span>Số lượng tại CTCK</span><b>{formatShares(book.shares, locale)} CP</b></div>
                        <div><span>Giá trị ước tính</span><b>{money(sourceValue, locale)}</b></div>
                      </div>
                      <div className="holding-source-book-action">
                        {assigned
                          ? <>
                            <a className="btn-small" href={buyHref(book)}>Mua thêm cổ phiếu</a>
                            <a className="btn-small btn-sell" href={sellHref(book)}>Bán cổ phiếu</a>
                          </>
                          : <span className="status-pill">Cần gán CTCK trước khi mua/bán</span>}
                      </div>
                    </article>;
                  })}
                </div>}
        </div>
      </details>;
    })}
  </div>;
}
