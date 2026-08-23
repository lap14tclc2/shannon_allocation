import React, { useEffect, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { changeAdminPassword, getCurrentUser, listUsers, removeUser } from '../lib/api.js';

export default function AdminPage({ locale = 'en' }) {
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
      setTimeout(() => window.location.assign('/'), 600);
    } catch (err) {
      setMessage(err.message);
    }
  }

  return (
    <div className="page">
      <AppNav active="admin" locale={locale} />
      <header className="page-header admin-header">
        <div>
          <div className="eyebrow">{text('Administration', 'Quản trị')}</div>
          <h1>{text('Users & access', 'User & truy cập')}</h1>
          <p className="muted">{text(
            'Manage registered usernames and the admin password. Each user owns an isolated SQLite portfolio database.',
            'Quản lý username đã đăng ký và password admin. Mỗi user có một SQLite database danh mục riêng.'
          )}</p>
        </div>
      </header>

      {message && <div className="run-message banner-message">{message}</div>}

      <div className="admin-grid">
        <section className="card admin-users-card">
          <div className="section-head">
            <div>
              <div className="eyebrow">{text('User board', 'Bảng user')}</div>
              <h2>{text('Registered users', 'User đã đăng ký')}</h2>
              <p className="muted">{text(
                'Removing a user also removes all portfolio data and sessions belonging to that user.',
                'Xóa user sẽ đồng thời xóa toàn bộ portfolio data và session của user đó.'
              )}</p>
            </div>
            <button className="btn-secondary" type="button" onClick={refreshUsers} disabled={loading}>
              {loading ? text('Loading…', 'Đang tải…') : text('Refresh', 'Làm mới')}
            </button>
          </div>

          <div className="table-scroll">
            <table className="ranking admin-user-table">
              <thead><tr>
                <th>{text('Username', 'Username')}</th>
                <th>{text('Role', 'Role')}</th>
                <th>{text('Created', 'Ngày tạo')}</th>
                <th className="num">{text('Action', 'Thao tác')}</th>
              </tr></thead>
              <tbody>{users.map(user => (
                <tr key={user.id}>
                  <td><b>{user.username}</b>{currentUser?.id === user.id && <span className="user-self">{text('you', 'bạn')}</span>}</td>
                  <td><span className={`status-pill ${user.role === 'ADMIN' ? 'status-attention' : 'status-valid'}`}>{user.role}</span></td>
                  <td>{String(user.created_at || '').replace('T', ' ').slice(0, 19) || '-'}</td>
                  <td className="num">
                    {user.role === 'ADMIN' ? <span className="muted">{text('Protected', 'Được bảo vệ')}</span> : (
                      <button className="btn-danger-small" type="button" onClick={() => remove(user)} disabled={removingId === user.id}>
                        {removingId === user.id ? text('Removing…', 'Đang xóa…') : text('Remove user + data', 'Xóa user + data')}
                      </button>
                    )}
                  </td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </section>

        <section className="card admin-password-card">
          <div className="eyebrow">{text('Admin security', 'Bảo mật admin')}</div>
          <h2>{text('Update admin password', 'Đổi password admin')}</h2>
          <p className="muted">{text(
            'Use this form to change the admin password. Updating it signs out existing admin sessions.',
            'Dùng form này để đổi password admin. Khi đổi password, các session admin hiện tại sẽ bị đăng xuất.'
          )}</p>
          <form className="admin-password-form" onSubmit={updatePassword}>
            <label><span>{text('Current password', 'Password hiện tại')}</span><input type="password" value={currentPassword} onChange={e => setCurrentPassword(e.target.value)} required /></label>
            <label><span>{text('New password', 'Password mới')}</span><input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} minLength={6} maxLength={128} required /></label>
            <label><span>{text('Confirm new password', 'Xác nhận password mới')}</span><input type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} minLength={6} maxLength={128} required /></label>
            <button className="btn-primary" type="submit">{text('Update password', 'Cập nhật password')}</button>
          </form>
        </section>
      </div>
    </div>
  );
}
