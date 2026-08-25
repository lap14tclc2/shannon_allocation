import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { getStoredTheme, saveTheme } from '../lib/appearance.js';

const THEMES = [
  {
    id: 'retro',
    name: 'Retro Ledger',
    shortName: 'Retro',
    description: 'Sáng, ấm như giấy Washi với mực sumi và điểm nhấn đỏ son.',
    descriptionEn: 'Warm washi paper, sumi ink and a restrained cinnabar accent.',
  },
  {
    id: 'cyber',
    name: 'Cyber Fantasy',
    shortName: 'Cyber',
    description: 'Tối, sắc nét và giàu năng lượng cho dữ liệu phân tích.',
    descriptionEn: 'Dark, precise and energetic for analytical data.',
  },
];

export default function AppearanceControls({ locale = 'en' }) {
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const [open, setOpen] = useState(false);
  const [theme, setTheme] = useState(getStoredTheme);
  const [mounted, setMounted] = useState(false);
  const buttonRef = useRef(null);
  const panelRef = useRef(null);
  const currentTheme = THEMES.find(item => item.id === theme) || THEMES[0];

  useEffect(() => setMounted(true), []);

  function closeAndRestoreFocus() {
    setOpen(false);
    requestAnimationFrame(() => buttonRef.current?.focus());
  }

  useEffect(() => {
    if (!open || typeof document === 'undefined') return undefined;
    const onKey = event => {
      if (event.key === 'Escape') {
        event.stopPropagation();
        closeAndRestoreFocus();
      }
    };
    const onPointer = event => {
      if (panelRef.current?.contains(event.target) || buttonRef.current?.contains(event.target)) return;
      closeAndRestoreFocus();
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onPointer);
    document.body.classList.add('theme-sheet-open');
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onPointer);
      document.body.classList.remove('theme-sheet-open');
    };
  }, [open]);

  function selectTheme(value) {
    setTheme(saveTheme(value));
  }

  const picker = open ? <div className="appearance-overlay">
    <div ref={panelRef} className="appearance-popover" role="dialog" aria-modal="true" aria-label={text('Choose interface theme', 'Chọn giao diện')}>
      <div className="appearance-head">
        <div>
          <b>{text('Interface theme', 'Giao diện')}</b>
          <span>{text('Choose one complete QPort visual system', 'Chọn một phong cách hoàn chỉnh cho QPort')}</span>
        </div>
        <button type="button" className="appearance-close" onClick={closeAndRestoreFocus} aria-label={text('Close', 'Đóng')}>×</button>
      </div>

      <div className="theme-options" role="radiogroup" aria-label={text('Available themes', 'Các giao diện hiện có')}>
        {THEMES.map(item => {
          const selected = item.id === theme;
          return <button
            key={item.id}
            type="button"
            role="radio"
            aria-checked={selected}
            className={`theme-option ${selected ? 'active' : ''}`}
            onClick={() => selectTheme(item.id)}
          >
            <span className={`theme-preview theme-preview-${item.id}`} aria-hidden="true">
              <i className="theme-preview-nav" />
              <i className="theme-preview-card" />
              <i className="theme-preview-line" />
              <i className="theme-preview-accent" />
            </span>
            <span className="theme-option-copy">
              <strong>{item.name}</strong>
              <small>{locale === 'vi' ? item.description : item.descriptionEn}</small>
            </span>
            <span className="theme-option-check" aria-hidden="true">{selected ? '✓' : ''}</span>
          </button>;
        })}
      </div>

      <p className="appearance-note">{text(
        'Your choice is applied immediately and saved on this device.',
        'Lựa chọn được áp dụng ngay và lưu trên thiết bị này.'
      )}</p>
    </div>
    <button type="button" className="appearance-backdrop" aria-label={text('Close theme picker', 'Đóng bộ chọn giao diện')} onClick={closeAndRestoreFocus} tabIndex={-1} />
  </div> : null;

  return <div className="appearance-control">
    <button
      ref={buttonRef}
      type="button"
      className="appearance-toggle"
      aria-haspopup="dialog"
      aria-expanded={open}
      onClick={() => setOpen(value => !value)}
      title={text('Choose QPort theme', 'Chọn giao diện QPort')}
    >
      <span className={`theme-trigger-mark theme-trigger-${theme}`} aria-hidden="true"><i /><i /></span>
      <span className="theme-trigger-copy"><small>{text('Theme', 'Giao diện')}</small><strong>{currentTheme.shortName}</strong></span>
      <span className="theme-trigger-chevron" aria-hidden="true">⌄</span>
    </button>
    {mounted && typeof document !== 'undefined' ? createPortal(picker, document.body) : picker}
  </div>;
}