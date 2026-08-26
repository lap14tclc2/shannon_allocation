import React, { useEffect, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { changeAdminPassword, getCurrentUser, listUsers, removeUser } from '../lib/api.js';

export default function AdminPage({ locale = 'vi' }) {
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const [currentUser, setCurrentUser] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
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
      const result = await removeUser(user.id);
      setUsers(value => value.filter(item => item.id !== user.id));
      setMessage(text(
        `Removed ${user.username}. Related portfolio data was deleted.`,
        `Đã xóa ${user.username}. Dữ liệu danh mục liên quan đã được xóa.`
      ));
      return result;
    } catch (err) {
      setMessage(err.message);
    } finally {
      setRemovingId(null);
    }
  }

  async function updatePassword(event) {
    event.preventDefault();
    setMessage('');
    if (newPassword !== confirmPassword) {
      setMessage(text('New passwords do not match.', 'Password mới không khớp.'));
      return;
    }
    try {
      const result = await changeAdminPassword(currentPassword, newPassword);
      setMessage(result.message || text('Admin password updated.', 'Đã cập nhật password admin.'));
      setTimeout(() => window.location.assign('/login'), 600);
    } catch (err) {
      setMessage(err.message);
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

      {message && <div className="run-message banner-message">{message}</div>}

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
                <th>Username</th>
                <th>Role</th>
                <th>Ngày tạo</th>
                <th className="num">Thao tác</th>
              </tr></thead>
              <tbody>{users.map(user => (
                <tr key={user.id}>
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

        <section className="card admin-logs-card">
          <div className="eyebrow">Theo dõi hệ thống</div>
          <h2>System Logs</h2>
          <p className="muted">Xem request, lỗi runtime và audit log của tất cả user/portfolio.</p>
          <a className="btn-primary" href="/logs">Mở trang Logs</a>
        </section>

        <section className="card admin-password-card">
          <div className="eyebrow">Bảo mật admin</div>
          <h2>Đổi password admin</h2>
          <p className="muted">Khi đổi password, các session admin hiện tại sẽ bị đăng xuất.</p>
          <form className="admin-password-form" onSubmit={updatePassword}>
            <label><span>Password hiện tại</span><input type="password" value={currentPassword} onChange={e => setCurrentPassword(e.target.value)} required /></label>
            <label><span>Password mới</span><input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} minLength={6} maxLength={128} required /></label>
            <label><span>Xác nhận password mới</span><input type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} minLength={6} maxLength={128} required /></label>
            <button className="btn-primary" type="submit">Cập nhật password</button>
          </form>
        </section>
      </div>
    </div>
  );
}
