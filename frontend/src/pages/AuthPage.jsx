import React, { useState } from 'react';
import { loginUser, registerUser } from '../lib/api.js';

export default function AuthPage({ locale = 'en' }) {
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const [username, setUsername] = useState('');
  const [registerUsername, setRegisterUsername] = useState('');
  const [password, setPassword] = useState('');
  const [missingUser, setMissingUser] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');

  async function login(event) {
    event.preventDefault();
    setBusy(true);
    setMessage('');
    setMissingUser(false);
    try {
      const result = await loginUser(username, password);
      window.location.assign(result.user?.role === 'ADMIN' ? '/admin' : '/');
    } catch (err) {
      if (err.code === 'USER_NOT_REGISTERED') {
        setRegisterUsername(username.trim());
        setMissingUser(true);
        setMessage(text('This username is not registered yet.', 'Username này chưa được đăng ký.'));
      } else {
        setMessage(err.message);
      }
    } finally {
      setBusy(false);
    }
  }

  async function register(event) {
    event.preventDefault();
    setBusy(true);
    setMessage('');
    try {
      await registerUser(registerUsername);
      window.location.assign('/');
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <div className="auth-brand">
          <span className="brand-prompt" aria-hidden="true">$</span>
          <div><strong>qport</strong><small>/ buy & hold portfolio</small></div>
        </div>

        <div className="auth-copy">
          <div className="eyebrow">{text('Portfolio access', 'Truy cập danh mục')}</div>
          <h1>{text('Sign in with your username', 'Đăng nhập bằng username')}</h1>
          <p>{text(
            'Normal users only need a unique username. Admin requires a password.',
            'User thường chỉ cần username duy nhất. Admin cần thêm password.'
          )}</p>
        </div>

        <form className="auth-form" onSubmit={login}>
          <label>
            <span>{text('Username', 'Username')}</span>
            <input
              autoFocus
              autoComplete="username"
              value={username}
              onChange={e => { setUsername(e.target.value); setMissingUser(false); setMessage(''); }}
              placeholder={text('Enter username', 'Nhập username')}
              maxLength={32}
              required
            />
          </label>
          <label>
            <span>{text('Admin password', 'Password admin')} <small>{text('(admin only)', '(chỉ admin)')}</small></span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder={text('Leave empty for normal user', 'User thường để trống')}
            />
          </label>
          <button className="btn-primary auth-submit" type="submit" disabled={busy || !username.trim()}>
            {busy ? text('Signing in…', 'Đang đăng nhập…') : text('Sign in', 'Đăng nhập')}
          </button>
        </form>

        {message && <div className={`auth-message ${missingUser ? 'info' : 'error'}`}>{message}</div>}

        {missingUser && (
          <form className="register-panel register-panel-form" onSubmit={register}>
            <div className="register-copy">
              <strong>{text('New user?', 'User mới?')}</strong>
              <p>{text(
                'Choose the username to register. A fresh private portfolio database will be created for it.',
                'Chọn username để đăng ký. Hệ thống sẽ tạo một database danh mục riêng, sạch cho user này.'
              )}</p>
            </div>
            <label className="register-field">
              <span>{text('Register username', 'Username đăng ký')}</span>
              <input
                value={registerUsername}
                onChange={e => setRegisterUsername(e.target.value)}
                maxLength={32}
                required
              />
            </label>
            <button className="btn-secondary" type="submit" disabled={busy || !registerUsername.trim()}>
              {text('Register username', 'Đăng ký username')}
            </button>
          </form>
        )}

        <div className="auth-footnote">
          <span>{text('Default admin', 'Admin mặc định')}</span>
          <code>admin / abc123</code>
        </div>
      </section>
    </main>
  );
}
