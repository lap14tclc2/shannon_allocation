import React from 'react';
import AppNav from '../components/AppNav.jsx';
import { formatMoney, formatShares, formatWeight } from '../lib/format.js';

function money(value, locale = 'vi') {
  return value == null || !Number.isFinite(Number(value)) ? '-' : `${formatMoney(value, false, locale)} ₫`;
}

function pct(value, digits = 2) {
  return value == null || !Number.isFinite(Number(value)) ? '-' : `${(Number(value) * 100).toFixed(digits)}%`;
}

export default function AdminUserPortfolioPage({ payload = {}, locale = 'vi' }) {
  const user = payload.user || {};
  const dashboard = payload.dashboard || {};
  const portfolio = dashboard.portfolio || {};
  const positions = portfolio.positions || [];

  return <div className="page admin-user-portfolio-page">
    <AppNav active="admin" locale={locale} />

    <header className="page-head">
      <div>
        <div className="eyebrow">Quản trị · Chỉ xem</div>
        <h1>Danh mục của @{user.username || '-'}</h1>
        <p className="muted">Admin chỉ có quyền xem dữ liệu ở trang này. Mọi API tạo, sửa hoặc xóa giao dịch của user vẫn bị chặn.</p>
      </div>
      <a className="btn-secondary" href="/admin">← Quay lại danh sách user</a>
    </header>

    <div className="metric-grid portfolio-metrics overview-metrics investor-overview">
      <div className="metric-card"><div className="metric-label">Tổng tài sản</div><div className="metric-value">{money(portfolio.nav, locale)}</div></div>
      <div className="metric-card"><div className="metric-label">Cổ phiếu</div><div className="metric-value">{money(portfolio.equity_value, locale)}</div><div className="metric-note">{positions.length} mã</div></div>
      <div className="metric-card"><div className="metric-label">Tiền mặt</div><div className="metric-value">{money(portfolio.cash, locale)}</div></div>
      <div className="metric-card"><div className="metric-label">Lãi/lỗ</div><div className="metric-value">{money(portfolio.total_pnl, locale)}</div><div className="metric-note">{pct(portfolio.accounting_return)}</div></div>
    </div>

    <section className="card holdings-card investor-holdings-card">
      <div className="section-head">
        <div><div className="eyebrow">Danh mục hiện tại</div><h2>Cổ phiếu đang nắm giữ</h2></div>
        <span className="status-pill status-valid">CHỈ XEM</span>
      </div>
      {positions.length === 0 ? <div className="empty-state compact-empty">User này chưa có cổ phiếu trong danh mục.</div> : <div className="table-scroll">
        <table className="ranking portfolio-table portfolio-table-core">
          <thead><tr><th>Mã</th><th className="num">SL</th><th className="num">Giá vốn</th><th className="num">Giá hiện tại</th><th className="num">Giá trị</th><th className="num">Lãi/lỗ</th><th className="num">Tỷ trọng</th></tr></thead>
          <tbody>{positions.map(row => <tr key={String(row.symbol || '').toUpperCase()}>
            <td><b>{String(row.symbol || '').toUpperCase()}</b></td>
            <td className="num">{formatShares(row.shares, locale)}</td>
            <td className="num">{money(row.average_cost, locale)}</td>
            <td className="num">{money(row.price, locale)}</td>
            <td className="num">{money(row.market_value, locale)}</td>
            <td className={`num ${Number(row.unrealized_pnl || 0) >= 0 ? 'pos' : 'neg'}`}>{money(row.unrealized_pnl, locale)}</td>
            <td className="num">{formatWeight(row.weight)}</td>
          </tr>)}</tbody>
        </table>
      </div>}
    </section>
  </div>;
}
