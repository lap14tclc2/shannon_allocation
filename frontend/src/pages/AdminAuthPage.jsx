import React, { useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { changeAdminPassword } from '../lib/api.js';
import { chooseText } from '../i18n.js';

export default function AdminAuthPage({ locale = 'vi' }) {
  const text = (en, vi) => chooseText(locale, en, vi);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  async function updatePassword(event) {
    event.preventDefault();
    setMessage('');
    if (newPassword !== confirmPassword) {
      setMessage(text('New passwords do not match.', 'Password mới không khớp.'));
      return;
    }
    setBusy(true);
    try {
      const result = await changeAdminPassword(currentPassword, newPassword);
      setMessage(result.message || text('Admin password updated. You will be redirected to login.', 'Đã cập nhật password admin. Bạn sẽ được chuyển tới trang đăng nhập.'));
      window.setTimeout(() => window.location.assign('/login'), 900);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <AppNav active="admin-auth" locale={locale} />
      <header className="page-header admin-header">
        <div>
          <div className="eyebrow">Bảo mật admin</div>
          <h1>Cập nhật xác thực</h1>
          <p className="muted">Đổi password quản trị. Sau khi cập nhật, các session admin hiện tại sẽ được đăng xuất.</p>
        </div>
      </header>

      {message && <div className="run-message banner-message" role="status">{message}</div>}

      <section className="card admin-password-card admin-auth-card">
        <div className="eyebrow">Mật khẩu quản trị</div>
        <h2>Đổi password admin</h2>
        <form className="admin-password-form" onSubmit={updatePassword}>
          <label><span>Password hiện tại</span><input type="password" autoComplete="current-password" value={currentPassword} onChange={event => setCurrentPassword(event.target.value)} required /></label>
          <label><span>Password mới</span><input type="password" autoComplete="new-password" value={newPassword} onChange={event => setNewPassword(event.target.value)} minLength={6} maxLength={128} required /></label>
          <label><span>Xác nhận password mới</span><input type="password" autoComplete="new-password" value={confirmPassword} onChange={event => setConfirmPassword(event.target.value)} minLength={6} maxLength={128} required /></label>
          <button className="btn-primary" type="submit" disabled={busy}>{busy ? 'Đang cập nhật…' : 'Cập nhật password'}</button>
        </form>
      </section>
    </div>
  );
}
