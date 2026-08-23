import React, { useEffect, useRef, useState } from 'react';
import {
  DEFAULT_APPEARANCE,
  getStoredAppearance,
  resetAppearance,
  saveAppearance,
} from '../lib/appearance.js';

const FIELDS = [
  ['background', 'Background', 'Nền'],
  ['text', 'Primary text', 'Chữ chính'],
  ['secondary', 'Secondary text', 'Chữ phụ'],
  ['muted', 'Muted text', 'Chữ mờ'],
  ['accent', 'Accent / links', 'Accent / link'],
  ['success', 'Positive / ready', 'Tăng / sẵn sàng'],
  ['warning', 'Warning / building', 'Cảnh báo / đang xây'],
  ['danger', 'Negative / error', 'Giảm / lỗi'],
  ['info', 'Information', 'Thông tin'],
];

function isHex(value) {
  return /^#[0-9a-f]{6}$/i.test(String(value || '').trim());
}

export default function AppearanceControls({ locale = 'en' }) {
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const [open, setOpen] = useState(false);
  const [palette, setPalette] = useState({ ...DEFAULT_APPEARANCE });
  const [drafts, setDrafts] = useState({ ...DEFAULT_APPEARANCE });
  const buttonRef = useRef(null);
  const panelRef = useRef(null);

  useEffect(() => {
    const current = getStoredAppearance() || { ...DEFAULT_APPEARANCE };
    setPalette(current);
    setDrafts(current);
  }, []);

  useEffect(() => {
    if (!open || typeof document === 'undefined') return undefined;
    const onKey = event => {
      if (event.key === 'Escape') setOpen(false);
    };
    const onPointer = event => {
      if (panelRef.current?.contains(event.target) || buttonRef.current?.contains(event.target)) return;
      setOpen(false);
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onPointer);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onPointer);
    };
  }, [open]);

  function updateColor(field, value) {
    if (!isHex(value)) return;
    const normalized = value.toLowerCase();
    const next = { ...palette, [field]: normalized };
    setPalette(next);
    setDrafts(current => ({ ...current, [field]: normalized }));
    saveAppearance(next);
  }

  function reset() {
    const next = resetAppearance();
    setPalette(next);
    setDrafts(next);
  }

  return <div className="appearance-control">
    <button
      ref={buttonRef}
      type="button"
      className="appearance-toggle"
      aria-haspopup="dialog"
      aria-expanded={open}
      onClick={() => setOpen(value => !value)}
      title={text('Customize QPort colors', 'Tùy chỉnh màu QPort')}
    >
      <span className="appearance-swatch" style={{ background: palette.accent }} aria-hidden="true" />
      <span>{text('colors', 'màu')}</span>
    </button>

    {open && <div ref={panelRef} className="appearance-popover" role="dialog" aria-label={text('Appearance colors', 'Màu giao diện')}>
      <div className="appearance-head">
        <div>
          <b>{text('Appearance', 'Giao diện')}</b>
          <span>{text('Saved automatically', 'Tự động lưu')}</span>
        </div>
        <button type="button" className="appearance-close" onClick={() => setOpen(false)} aria-label={text('Close', 'Đóng')}>×</button>
      </div>

      <p className="appearance-note">{text(
        'Choose the page background and semantic text colors. Cards, inputs and borders adapt automatically. Default is QPort dark.',
        'Chọn màu nền và màu chữ theo ngữ nghĩa. Card, input và border tự thích nghi. Mặc định là QPort dark.'
      )}</p>

      <div className="appearance-fields">
        {FIELDS.map(([field, en, vi]) => <label className="appearance-row" key={field}>
          <span>{text(en, vi)}</span>
          <span className="appearance-inputs">
            <input
              type="color"
              value={palette[field]}
              onChange={event => updateColor(field, event.target.value)}
              aria-label={text(`${en} color`, `Màu ${vi}`)}
            />
            <input
              className="appearance-hex"
              value={drafts[field]}
              maxLength={7}
              spellCheck="false"
              onChange={event => {
                const value = event.target.value;
                setDrafts(current => ({ ...current, [field]: value }));
                if (isHex(value)) updateColor(field, value);
              }}
              onBlur={() => {
                if (!isHex(drafts[field])) setDrafts(current => ({ ...current, [field]: palette[field] }));
              }}
              aria-label={text(`${en} hex value`, `Mã hex ${vi}`)}
            />
          </span>
        </label>)}
      </div>

      <div className="appearance-actions">
        <button type="button" className="btn-ghost appearance-reset" onClick={reset}>{text('Reset default dark', 'Khôi phục dark mặc định')}</button>
        <button type="button" className="btn-secondary" onClick={() => setOpen(false)}>{text('Done', 'Xong')}</button>
      </div>
    </div>}
  </div>;
}
