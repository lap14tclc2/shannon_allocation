import React, { useEffect, useState } from 'react';
import { loginUser, registerUser } from '../lib/api.js';

function safeNextPath() {
  if (typeof window === 'undefined') return '/';
  const raw = new URLSearchParams(window.location.search).get('next') || '';
  if (!raw.startsWith('/') || raw.startsWith('//') || raw.startsWith('/login')) return '/';
  return raw;
}

export default function AuthPage() {
  const [username, setUsername] = useState('');
  const [registerUsername, setRegisterUsername] = useState('');
  const [password, setPassword] = useState('');
  const [missingUser, setMissingUser] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [nextPath, setNextPath] = useState('/');
  const [sessionExpired, setSessionExpired] = useState(false);
  const isAdmin = username.trim().toLowerCase() === 'admin';

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    setNextPath(safeNextPath());
    setSessionExpired(params.get('reason') === 'session_expired');
  }, []);

  async function login(event) {
    event.preventDefault();
    setBusy(true);
    setMessage('');
    setMissingUser(false);
    try {
      const result = await loginUser(username, isAdmin ? password : '');
      window.location.replace(result.user?.role === 'ADMIN' ? '/admin' : nextPath);
    } catch (error) {
      if (error.code === 'USER_NOT_REGISTERED') {
        setRegisterUsername(username.trim());
        setMissingUser(true);
        setMessage('Tên đăng nhập này chưa tồn tại. Bạn có thể tạo danh mục mới bên dưới.');
      } else {
        setMessage(error.message);
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
      window.location.replace(nextPath);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  return <main className="auth-shell">
    <section className="auth-card">
      <div className="auth-brand">
        <span className="brand-prompt" aria-hidden="true">$</span>
        <div><strong>qport</strong><small>/ quản lý danh mục cổ phiếu</small></div>
      </div>

      <div className="auth-copy">
        <div className="eyebrow">Danh mục của bạn</div>
        <h1>Đăng nhập vào QPort</h1>
        <p>Nhập tên tài khoản để mở danh mục đã lưu. Tài khoản quản trị cần thêm mật khẩu.</p>
      </div>

      {sessionExpired && <div className="auth-message info" role="status">Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại để tiếp tục.</div>}

      <form className="auth-form" onSubmit={login}>
        <label>
          <span>Tên đăng nhập</span>
          <input
            autoFocus
            autoComplete="username"
            value={username}
            onChange={event => { setUsername(event.target.value); setMissingUser(false); setMessage(''); if (event.target.value.trim().toLowerCase() !== 'admin') setPassword(''); }}
            placeholder="Nhập tên đăng nhập"
            maxLength={32}
            required
          />
        </label>
        {isAdmin && <label>
          <span>Mật khẩu quản trị</span>
          <input type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} placeholder="Nhập mật khẩu" required />
        </label>}
        <button className="btn-primary auth-submit" type="submit" disabled={busy || !username.trim() || (isAdmin && !password)}>{busy ? 'Đang đăng nhập…' : 'Đăng nhập'}</button>
      </form>

      {message && <div className={`auth-message ${missingUser ? 'info' : 'error'}`}>{message}</div>}

      {missingUser && <form className="register-panel register-panel-form" onSubmit={register}>
        <div className="register-copy"><strong>Tạo danh mục mới</strong><p>QPort sẽ tạo một không gian danh mục riêng cho tên đăng nhập này.</p></div>
        <label className="register-field"><span>Tên đăng nhập mới</span><input value={registerUsername} onChange={event => setRegisterUsername(event.target.value)} maxLength={32} required /></label>
        <button className="btn-secondary" type="submit" disabled={busy || !registerUsername.trim()}>Tạo danh mục</button>
      </form>}
    </section>
  </main>;
}
