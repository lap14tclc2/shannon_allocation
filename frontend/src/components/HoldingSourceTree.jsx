import React, { useState } from 'react';
import ValuationDetailOverlay from './ValuationDetailOverlay.jsx';
import { formatShares, formatWeight, money, pct } from '../lib/format.js';
import { BROKERS } from '../lib/brokers.js';



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

export default function HoldingSourceTree({ positions = [], holdingBooks = [], locale = 'vi', loading = false, error = '', onEditPosition }) {
  const [selectedValuationSymbol, setSelectedValuationSymbol] = useState(null);

  return (
    <div className="holding-source-tree" role="tree">
      {positions.map((position, index) => {
        const symbol = String(position.symbol || '').toUpperCase();
        const books = holdingBooks.filter(book => book.symbol === symbol);
        const pnl = position.unrealized_pnl == null ? null : Number(position.unrealized_pnl);
        return <details className="holding-source-symbol" open={index === 0} key={symbol}>
          <summary>
            <span className="tree-caret" aria-hidden="true">›</span>
            <div className="holding-source-symbol-name">
              <strong>{symbol}</strong>
              <span><span data-sensitive="shares">{formatShares(position.shares, locale)}</span> CP</span>
            </div>
            <div className="holding-source-symbol-value">
              <strong data-sensitive="money">{money(position.market_value, locale)}</strong>
              <span className={pnl == null ? '' : pnl >= 0 ? 'pos' : 'neg'}><span data-sensitive="pnl">{pnl == null ? '-' : `${pnl >= 0 ? '+' : ''}${money(pnl, locale)}`}</span> · {pct(position.unrealized_return)}</span>
            </div>
            <span className="holding-source-weight">{formatWeight(position.weight)}</span>
          </summary>

          <div className="holding-source-children">
            <div className="holding-source-meta" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px' }}>
              <span>Giá vốn <b data-sensitive="money">{money(position.average_cost, locale)}</b></span>
              <span>Giá hiện tại <b data-sensitive="money">{money(position.price, locale)}</b></span>
              <span>{position.price_date ? `Giá ngày ${position.price_date}` : 'Giá chưa cập nhật'}</span>
              <button
                type="button"
                className="btn-small btn-view-detail"
                onClick={() => setSelectedValuationSymbol(symbol)}
                style={{ marginLeft: 'auto' }}
                title={`Soi giá chi tiết & định giá toàn diện ${symbol}`}
              >
                Soi giá chi tiết ↗
              </button>
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
                          <div><span>Số lượng tại CTCK</span><b><span data-sensitive="shares">{formatShares(book.shares, locale)}</span> CP</b></div>
                          <div><span>Giá trị ước tính</span><b data-sensitive="money">{money(sourceValue, locale)}</b></div>
                        </div>
                        <div className="holding-source-book-action">
                          {assigned
                            ? <>
                              <a className="btn-small" href={buyHref(book)}>Mua thêm cổ phiếu</a>
                              <a className="btn-small btn-sell" href={sellHref(book)}>Bán cổ phiếu</a>
                              {onEditPosition && (
                                <button
                                  type="button"
                                  className="btn-small btn-secondary"
                                  onClick={() => onEditPosition(symbol, book)}
                                  title={`Chỉnh sửa vị thế ${symbol}`}
                                >
                                  Chỉnh sửa
                                </button>
                              )}
                            </>
                            : <>
                              <span className="status-pill">Cần gán CTCK trước khi mua/bán</span>
                              {onEditPosition && (
                                <button
                                  type="button"
                                  className="btn-small btn-secondary"
                                  onClick={() => onEditPosition(symbol, book)}
                                >
                                  Chỉnh sửa
                                </button>
                              )}
                            </>}
                        </div>
                      </article>;
                    })}
                  </div>}
          </div>
        </details>;
      })}

      {selectedValuationSymbol && (
        <ValuationDetailOverlay
          symbol={selectedValuationSymbol}
          locale={locale}
          onClose={() => setSelectedValuationSymbol(null)}
        />
      )}
    </div>
  );
}
