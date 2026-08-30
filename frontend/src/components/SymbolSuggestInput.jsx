import React, { useState, useEffect, useRef, useMemo } from 'react';
import { lookupSecurities } from '../lib/api.js';

export default function SymbolSuggestInput({
  value = '',
  onChange,
  onSelectSecurity,
  placeholder = 'Tìm mã hoặc tên công ty (ví dụ: FPT, HPG, MBB...)',
  disabled = false,
  holdingSymbols = [],
  holdingBooks = [],
  ariaInvalid = false,
  id,
  name = 'symbol',
  autoFocus = false,
}) {
  const [query, setQuery] = useState(value || '');
  const [open, setOpen] = useState(false);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const containerRef = useRef(null);
  const inputRef = useRef(null);
  const debounceRef = useRef(null);

  const holdingSet = useMemo(() => new Set((holdingSymbols || []).map(s => String(s || '').toUpperCase())), [holdingSymbols]);

  // Sync external value
  useEffect(() => {
    setQuery(value || '');
  }, [value]);

  // Fetch suggestions when query changes
  useEffect(() => {
    if (!open) return;
    const cleanQuery = query.trim().toUpperCase();

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await lookupSecurities(cleanQuery, 25);
        if (res?.ok && Array.isArray(res.results)) {
          let list = res.results;
          // Sort holding symbols to top if no specific query or matching
          list.sort((a, b) => {
            const aHolding = holdingSet.has(a.symbol);
            const bHolding = holdingSet.has(b.symbol);
            if (aHolding && !bHolding) return -1;
            if (!aHolding && bHolding) return 1;
            return 0;
          });
          setResults(list);
        } else {
          setResults([]);
        }
      } catch {
        // Fallback to local holding symbols if API fails
        const fallback = (holdingSymbols || []).map(s => ({
          symbol: s,
          exchange: 'HOSE',
          company_name: 'Cổ phiếu trong danh mục',
        }));
        setResults(fallback);
      } finally {
        setLoading(false);
      }
    }, 150);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, open, holdingSet, holdingSymbols]);

  // Close when clicking or touching outside
  useEffect(() => {
    function onPointerDown(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener('pointerdown', onPointerDown);
    return () => document.removeEventListener('pointerdown', onPointerDown);
  }, []);

  function handleSelect(item) {
    const symbol = String(item?.symbol || '').toUpperCase();
    setQuery(symbol);
    setOpen(false);
    if (onChange) onChange(symbol);
    if (onSelectSecurity) onSelectSecurity(item);
  }

  function handleInputChange(e) {
    const val = e.target.value.replace(/[^a-zA-Z0-9\s]/g, '').toUpperCase();
    setQuery(val);
    setOpen(true);
    setActiveIndex(-1);
    if (onChange) onChange(val);
  }

  function handleKeyDown(e) {
    if (!open) {
      if (e.key === 'ArrowDown' || e.key === 'Enter') {
        setOpen(true);
        e.preventDefault();
      }
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex(prev => (prev < results.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex(prev => (prev > 0 ? prev - 1 : results.length - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (activeIndex >= 0 && activeIndex < results.length) {
        handleSelect(results[activeIndex]);
      } else if (query.trim()) {
        handleSelect({ symbol: query.trim().toUpperCase() });
      }
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  }

  return (
    <div className="symbol-suggest-container" ref={containerRef}>
      <div className="symbol-suggest-input-wrapper">
        <input
          ref={inputRef}
          type="text"
          id={id}
          name={name}
          className="symbol-suggest-input"
          value={query}
          onChange={handleInputChange}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="characters"
          spellCheck="false"
          aria-autocomplete="list"
          aria-expanded={open}
          aria-invalid={ariaInvalid}
          autoFocus={autoFocus}
        />
        {query && !disabled && (
          <button
            type="button"
            className="symbol-suggest-clear-btn"
            aria-label="Xóa mã"
            onClick={() => {
              setQuery('');
              if (onChange) onChange('');
              inputRef.current?.focus();
            }}
          >
            ✕
          </button>
        )}
      </div>

      {open && (
        <div className="symbol-suggest-dropdown" role="listbox">
          {loading && results.length === 0 ? (
            <div className="symbol-suggest-loading">Đang tìm kiếm mã chứng khoán…</div>
          ) : results.length === 0 ? (
            <div className="symbol-suggest-empty">
              <span>Không tìm thấy mã phù hợp với <strong>{query}</strong></span>
              {query.trim() && (
                <button
                  type="button"
                  className="symbol-suggest-custom-btn"
                  onClick={() => handleSelect({ symbol: query.trim().toUpperCase() })}
                >
                  Sử dụng mã <b>{query.trim().toUpperCase()}</b>
                </button>
              )}
            </div>
          ) : (
            <div className="symbol-suggest-list">
              {results.map((item, index) => {
                const isHolding = holdingSet.has(item.symbol);
                const isSelected = activeIndex === index;
                return (
                  <div
                    key={item.symbol}
                    role="option"
                    aria-selected={isSelected}
                    className={`symbol-suggest-item ${isSelected ? 'active' : ''} ${isHolding ? 'is-holding' : ''}`}
                    onPointerDown={() => handleSelect(item)}
                  >
                    <div className="symbol-item-main">
                      <strong className="symbol-item-ticker">{item.symbol}</strong>
                      <span className="symbol-item-exchange">{item.exchange || 'HOSE'}</span>
                      {isHolding && <span className="symbol-item-holding-tag">Đang nắm giữ</span>}
                    </div>
                    {item.company_name && (
                      <span className="symbol-item-company">{item.company_name}</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
