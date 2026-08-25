import React, { useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import {
  activatePortfolio,
  createPortfolio,
  removePortfolio,
  renamePortfolio,
} from '../lib/api.js';

function createdDate(value, locale = 'vi') {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10);
  return new Intl.DateTimeFormat(locale === 'vi' ? 'vi-VN' : 'en-US', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  }).format(date);
}

export default function PortfoliosPage({ registry = {}, locale = 'vi' }) {
  const [portfolios, setPortfolios] = useState(registry.portfolios || []);
  const [activeId, setActiveId] = useState(Number(registry.active_portfolio_id || 0));
  const [newName, setNewName] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editingName, setEditingName] = useState('');
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');
  const activePortfolio = useMemo(
    () => portfolios.find(item => Number(item.id) === Number(activeId)) || null,
    [portfolios, activeId],
  );

  async function create(event) {
    event.preventDefault();
    const name = newName.trim();
    if (!name) {
      setMessage('Hãy nhập tên danh mục.');
      return;
    }
    setBusy('create');
    setMessage('');
    try {
      const result = await createPortfolio(name);
      setPortfolios(current => [...current, result.portfolio]);
      setNewName('');
      setMessage(`Đã tạo “${result.portfolio.name}”. Danh mục mới có sổ giao dịch và dữ liệu hoàn toàn độc lập.`);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy('');
    }
  }

  function beginRename(item) {
    setEditingId(item.id);
    setEditingName(item.name);
    setMessage('');
  }

  async function saveRename(item) {
    const name = editingName.trim();
    if (!name || name === item.name) {
      setEditingId(null);
      return;
    }
    setBusy(`rename-${item.id}`);
    try {
      const result = await renamePortfolio(item.id, name);
      setPortfolios(current => current.map(row => row.id === item.id ? result.portfolio : row));
      setEditingId(null);
      setMessage('Đã đổi tên danh mục.');
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy('');
    }
  }

  async function openPortfolio(item) {
    if (Number(item.id) === Number(activeId)) {
      window.location.assign('/');
      return;
    }
    setBusy(`open-${item.id}`);
    setMessage('');
    try {
      await activatePortfolio(item.id);
      setActiveId(Number(item.id));
      window.location.assign('/');
    } catch (error) {
      setMessage(error.message);
      setBusy('');
    }
  }

  async function remove(item) {
    if (item.is_default) return;
    const confirmation = window.prompt(
      `Xóa “${item.name}” sẽ xóa vĩnh viễn holdings, cash, transactions, performance và analytics của riêng danh mục này. Các danh mục khác không bị ảnh hưởng.\n\nNhập chính xác: XOA DANH MUC`,
      '',
    );
    if (confirmation !== 'XOA DANH MUC') return;
    setBusy(`delete-${item.id}`);
    setMessage('');
    try {
      const result = await removePortfolio(item.id, confirmation);
      setPortfolios(current => current.filter(row => row.id !== item.id));
      setActiveId(Number(result.portfolio.next_active_portfolio_id || activeId));
      setMessage(`Đã xóa “${item.name}”.`);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy('');
    }
  }

  return <div className="page portfolio-manager-page">
    <AppNav active="portfolios" locale={locale} />

    <header className="portfolio-manager-hero">
      <div>
        <div className="eyebrow">Trung tâm tài sản</div>
        <h1>Danh mục của bạn</h1>
        <p>Chia tài sản theo mục tiêu, tài khoản hoặc chiến lược theo dõi. Mỗi danh mục có sổ kế toán độc lập và có thể chuyển đổi tức thì.</p>
      </div>
      <div className="portfolio-manager-stat">
        <span>Tổng số danh mục</span>
        <strong>{portfolios.length}</strong>
        <small>Đang xem: {activePortfolio?.name || '-'}</small>
      </div>
    </header>

    <main className="portfolio-manager-layout">
      <section className="portfolio-manager-main">
        <div className="section-head">
          <div>
            <h2>Không gian tài sản</h2>
            <p className="muted">Holdings, tiền mặt, giao dịch, hiệu quả và phân tích không bị trộn giữa các danh mục.</p>
          </div>
        </div>

        <div className="portfolio-card-grid">
          {portfolios.map(item => {
            const active = Number(item.id) === Number(activeId);
            const renaming = editingId === item.id;
            return <article className={`portfolio-space-card ${active ? 'active' : ''}`} key={item.id}>
              <div className="portfolio-space-card-top">
                <div className="portfolio-space-icon" aria-hidden="true">{item.is_default ? 'Q' : item.name.slice(0, 1).toUpperCase()}</div>
                <div className="portfolio-space-badges">
                  {active && <span className="portfolio-active-badge">Đang xem</span>}
                  {item.is_default && <span className="portfolio-default-badge">Mặc định</span>}
                </div>
              </div>

              {renaming ? <div className="portfolio-rename-row">
                <input
                  value={editingName}
                  onChange={event => setEditingName(event.target.value)}
                  maxLength={60}
                  autoFocus
                  onKeyDown={event => {
                    if (event.key === 'Enter') saveRename(item);
                    if (event.key === 'Escape') setEditingId(null);
                  }}
                />
                <button type="button" className="btn-small" onClick={() => saveRename(item)} disabled={busy === `rename-${item.id}`}>Lưu</button>
              </div> : <h3>{item.name}</h3>}

              <p>{item.is_default
                ? 'Chứa toàn bộ dữ liệu QPort đã có trước khi bật Multi-Portfolio.'
                : 'Một không gian độc lập cho holdings, cash, transactions, performance và analytics.'}</p>

              <dl className="portfolio-space-meta">
                <div><dt>Nguồn dữ liệu</dt><dd>Ledger riêng</dd></div>
                <div><dt>Ngày tạo</dt><dd>{createdDate(item.created_at, locale)}</dd></div>
              </dl>

              <div className="portfolio-space-actions">
                <button type="button" className={active ? 'btn-secondary' : 'btn-primary'} onClick={() => openPortfolio(item)} disabled={busy === `open-${item.id}`}>
                  {active ? 'Mở tổng quan' : busy === `open-${item.id}` ? 'Đang chuyển…' : 'Chuyển sang'}
                </button>
                <button type="button" className="btn-small" onClick={() => beginRename(item)} disabled={Boolean(busy)}>Đổi tên</button>
                {!item.is_default && <button type="button" className="danger-link" onClick={() => remove(item)} disabled={busy === `delete-${item.id}`}>
                  {busy === `delete-${item.id}` ? 'Đang xóa…' : 'Xóa'}
                </button>}
              </div>
            </article>;
          })}
        </div>
      </section>

      <aside className="portfolio-manager-side">
        <form className="card portfolio-create-card" onSubmit={create}>
          <div className="portfolio-create-icon" aria-hidden="true">＋</div>
          <h2>Tạo danh mục mới</h2>
          <p>Tạo một sổ tài sản trống. Bạn có thể nhập holdings ban đầu và tiền mặt sau khi chuyển sang danh mục mới.</p>
          <label>Tên danh mục
            <input
              value={newName}
              onChange={event => setNewName(event.target.value)}
              maxLength={60}
              placeholder="Ví dụ: Hưu trí dài hạn"
              autoComplete="off"
            />
          </label>
          <button className="btn-primary" type="submit" disabled={busy === 'create'}>
            {busy === 'create' ? 'Đang tạo…' : 'Tạo danh mục'}
          </button>
        </form>

        <section className="card portfolio-architecture-card">
          <span className="portfolio-architecture-kicker">Thiết kế an toàn</span>
          <h2>Sẵn sàng cho tổng hợp tài sản</h2>
          <p>Mỗi danh mục có định danh và schema riêng. Cấu trúc này cho phép xây dựng màn hình tổng hợp NAV nhiều danh mục sau này mà không làm mất ranh giới kế toán.</p>
          <ul>
            <li>Không trộn giao dịch hoặc tiền mặt</li>
            <li>Không dùng snapshot làm nguồn holdings</li>
            <li>Portfolio mặc định giữ nguyên dữ liệu cũ</li>
          </ul>
        </section>
      </aside>
    </main>

    {message && <div className="portfolio-manager-message" role="status">{message}</div>}
  </div>;
}
