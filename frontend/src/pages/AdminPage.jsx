import React, { useEffect, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { getCurrentUser, listUsers, removeUser } from '../lib/api.js';

export default function AdminPage({ locale = 'vi' }) {
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const [currentUser, setCurrentUser] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [removingId, setRemovingId] = useState(null);

  async function refreshUsers() {
    setLoading(true);
    try {
      const [me, result] = await Promise.all([getCurrentUser(), listUsers()]);
      setCurrentUser(me.user || null);
      setUsers(result.users || []);
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { refreshUsers(); }, []);

  async function remove(user) {
    if (!window.confirm(text(
      `Remove ${user.username} and permanently delete all portfolio data for this user?`,
      `Xóa ${user.username} và xóa vĩnh viễn toàn bộ dữ liệu danh mục của user này?`
    ))) return;
    setRemovingId(user.id);
    setMessage('');
    try {
      await removeUser(user.id);
      setUsers(value => value.filter(item => item.id !== user.id));
      setMessage(text(
        `Removed ${user.username}. Related portfolio data was deleted.`,
        `Đã xóa ${user.username}. Dữ liệu danh mục liên quan đã được xóa.`
      ));
    } catch (err) {
      setMessage(err.message);
    } finally {
      setRemovingId(null);
    }
  }

  return (
    <div className="page">
      <AppNav active="admin" locale={locale} />
      <header className="page-header admin-header">
        <div>
          <div className="eyebrow">Quản trị</div>
          <h1>User & truy cập</h1>
          <p className="muted">Admin có thể xem danh mục của từng user ở chế độ chỉ đọc. Mỗi user vẫn dùng một PostgreSQL schema riêng.</p>
        </div>
      </header>

      {message && <div className="run-message banner-message" role="status">{message}</div>}

      <div className="admin-grid">
        <section className="card admin-users-card">
          <div className="section-head">
            <div>
              <div className="eyebrow">Bảng user</div>
              <h2>User đã đăng ký</h2>
              <p className="muted">“Xem danh mục” là read-only. Xóa user vẫn xóa cả account, session và toàn bộ dữ liệu danh mục của user đó.</p>
            </div>
            <button className="btn-secondary" type="button" onClick={refreshUsers} disabled={loading}>
              {loading ? 'Đang tải…' : 'Làm mới'}
            </button>
          </div>

          <div className="table-scroll">
            <table className="ranking admin-user-table">
              <thead><tr>
                <th>#</th>
                <th>Username</th>
                <th>Role</th>
                <th>Ngày tạo</th>
                <th className="num">Thao tác</th>
              </tr></thead>
              <tbody>{users.map((user, index) => (
                <tr key={user.id}>
                  <td className="num">{index + 1}</td>
                  <td><b>{user.username}</b>{currentUser?.id === user.id && <span className="user-self">bạn</span>}</td>
                  <td><span className={`status-pill ${user.role === 'ADMIN' ? 'status-attention' : 'status-valid'}`}>{user.role}</span></td>
                  <td>{String(user.created_at || '').replace('T', ' ').slice(0, 19) || '-'}</td>
                  <td className="num">
                    {user.role === 'ADMIN' ? <span className="muted">Được bảo vệ</span> : <div className="admin-row-actions">
                      <a className="btn-secondary btn-small" href={`/admin/users/${Number(user.id)}`}>Xem danh mục</a>
                      <button className="btn-danger-small" type="button" onClick={() => remove(user)} disabled={removingId === user.id}>
                        {removingId === user.id ? 'Đang xóa…' : 'Xóa user + data'}
                      </button>
                    </div>}
                  </td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
