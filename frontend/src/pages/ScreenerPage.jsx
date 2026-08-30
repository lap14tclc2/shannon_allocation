import React, { useEffect, useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import ValuationDetailOverlay from '../components/ValuationDetailOverlay.jsx';
import '../valuation-page.css';
import '../screener-page.css';

const EXCHANGE_OPTIONS = [
  { id: 'ALL', label: 'Tất cả sàn' },
  { id: 'HOSE', label: 'HOSE' },
  { id: 'HNX', label: 'HNX' },
  { id: 'UPCOM', label: 'UPCOM' },
];

const SCORE_OPTIONS = [
  { id: 80, label: '≥ 80 Điểm (Hảo hạng)' },
  { id: 70, label: '≥ 70 Điểm (Đầu tư)' },
  { id: 60, label: '≥ 60 Điểm (Theo dõi)' },
  { id: 0, label: 'Tất cả điểm số' },
];

const SORT_OPTIONS = [
  { id: 'score', label: 'Điểm chất lượng (Cao → Thấp)' },
  { id: 'roe', label: 'ROE 5 năm (Cao → Thấp)' },
  { id: 'moat', label: 'Hào kinh tế Moat (Cao → Thấp)' },
  { id: 'symbol', label: 'Mã CP (A → Z)' },
];

export default function ScreenerPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedSymbol, setSelectedSymbol] = useState(null);

  // Filters state
  const [minScore, setMinScore] = useState(80);
  const [exchange, setExchange] = useState('ALL');
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('score');

  useEffect(() => {
    let cancelled = false;
    async function fetchScreener() {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        if (minScore > 0) params.set('min_score', String(minScore));
        if (exchange && exchange !== 'ALL') params.set('exchange', exchange);
        if (search.trim()) params.set('search', search.trim());
        if (sortBy) params.set('sort_by', sortBy);

        const res = await fetch(`/api/portfolio/screener?${params.toString()}`);
        if (!res.ok) {
          throw new Error(`Lỗi tải bộ lọc: HTTP ${res.status}`);
        }
        const json = await res.json();
        if (!cancelled) {
          setData(json);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Không thể kết nối máy chủ');
          setLoading(false);
        }
      }
    }

    const timer = setTimeout(fetchScreener, 150);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [minScore, exchange, search, sortBy]);

  const items = data?.items || [];
  const totalScreened = data?.total_screened || 0;
  const universeSize = data?.universe_size || 1523;

  const countsByExchange = useMemo(() => {
    const counts = { HOSE: 0, HNX: 0, UPCOM: 0 };
    items.forEach(it => {
      if (counts[it.exchange] !== undefined) counts[it.exchange]++;
    });
    return counts;
  }, [items]);

  const getTierClass = (score) => {
    if (score >= 80) return 'tier-exceptional';
    if (score >= 70) return 'tier-investable';
    if (score >= 60) return 'tier-watch';
    return 'tier-low';
  };

  return (
    <div className="app-shell screener-page-shell">
      <AppNav active="screener" />

      <main className="screener-main-content">
        {/* Header Hero */}
        <section className="screener-hero">
          <div className="screener-hero-badge">
            <span className="sparkle-icon">✦</span>
            <span>BUFFETT – MUNGER 100-POINT ENGINE</span>
          </div>
          <h1 className="screener-title">Bộ Lọc Doanh Nghiệp Chất Lượng Cao</h1>
          <p className="screener-subtitle">
            Sàng lọc <strong>{universeSize} mã</strong> toàn thị trường Việt Nam dựa trên 7 trụ cột: Độ dự đoán, Hào kinh tế (Moat), ROE chu kỳ, Sức mạnh tài chính & Hiệu quả phân bổ vốn.
          </p>

          {/* Quick Stats Pill */}
          <div className="screener-stats-strip">
            <div className="stat-pill highlight">
              <span className="stat-num">{totalScreened}</span>
              <span className="stat-label">doanh nghiệp thỏa điều kiện</span>
            </div>
            <div className="stat-pill">
              <span className="stat-dot dot-hose" />
              <span>HOSE: <strong>{countsByExchange.HOSE}</strong></span>
            </div>
            <div className="stat-pill">
              <span className="stat-dot dot-hnx" />
              <span>HNX: <strong>{countsByExchange.HNX}</strong></span>
            </div>
            <div className="stat-pill">
              <span className="stat-dot dot-upcom" />
              <span>UPCOM: <strong>{countsByExchange.UPCOM}</strong></span>
            </div>
          </div>
        </section>

        {/* Toolbar & Filters */}
        <section className="screener-toolbar-card">
          <div className="toolbar-top-row">
            {/* Search Input */}
            <div className="search-input-wrapper">
              <span className="search-icon" aria-hidden="true">🔍</span>
              <input
                type="text"
                className="screener-search-input"
                placeholder="Tìm mã cổ phiếu (VNM, FPT...), tên công ty, ngành nghề..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              {search && (
                <button
                  type="button"
                  className="search-clear-btn"
                  onClick={() => setSearch('')}
                  title="Xóa tìm kiếm"
                >
                  ✕
                </button>
              )}
            </div>

            {/* Sort Control */}
            <div className="sort-control-wrapper">
              <label htmlFor="screener-sort-select" className="sort-label">Sắp xếp:</label>
              <select
                id="screener-sort-select"
                className="screener-select"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
              >
                {SORT_OPTIONS.map(opt => (
                  <option key={opt.id} value={opt.id}>{opt.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="toolbar-filter-row">
            {/* Exchange Filter Tabs */}
            <div className="filter-group">
              <span className="filter-group-label">Sàn giao dịch:</span>
              <div className="segmented-pills">
                {EXCHANGE_OPTIONS.map(opt => (
                  <button
                    key={opt.id}
                    type="button"
                    className={`segment-btn ${exchange === opt.id ? 'active' : ''}`}
                    onClick={() => setExchange(opt.id)}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Score Filter Tabs */}
            <div className="filter-group">
              <span className="filter-group-label">Điểm Chất lượng:</span>
              <div className="segmented-pills">
                {SCORE_OPTIONS.map(opt => (
                  <button
                    key={opt.id}
                    type="button"
                    className={`segment-btn ${minScore === opt.id ? 'active' : ''}`}
                    onClick={() => setMinScore(opt.id)}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Results Grid */}
        <section className="screener-results-section">
          {loading && (
            <div className="screener-loading-state">
              <div className="spa-loading-spinner" />
              <p>Đang sàng lọc dữ liệu từ 1.523 mã chứng khoán...</p>
            </div>
          )}

          {error && (
            <div className="screener-error-state">
              <p className="error-title">⚠️ Đã xảy ra lỗi</p>
              <p className="error-desc">{error}</p>
            </div>
          )}

          {!loading && !error && items.length === 0 && (
            <div className="screener-empty-state">
              <div className="empty-icon">🔎</div>
              <h3>Không tìm thấy doanh nghiệp phù hợp</h3>
              <p>Thử điều chỉnh từ khóa tìm kiếm hoặc hạ ngưỡng điểm lọc.</p>
              <button
                type="button"
                className="reset-filters-btn"
                onClick={() => {
                  setSearch('');
                  setMinScore(80);
                  setExchange('ALL');
                }}
              >
                Đặt lại bộ lọc mặc định
              </button>
            </div>
          )}

          {!loading && !error && items.length > 0 && (
            <div className="screener-grid">
              {items.map((item) => {
                const tierClass = getTierClass(item.total_score);
                return (
                  <div
                    key={item.symbol}
                    className={`screener-card ${tierClass}`}
                    onClick={() => setSelectedSymbol(item.symbol)}
                    style={{ cursor: 'pointer' }}
                  >
                    {/* Card Header */}
                    <div className="card-header">
                      <div className="card-symbol-block">
                        <span className="card-symbol">{item.symbol}</span>
                        <span className={`exchange-badge badge-${item.exchange.toLowerCase()}`}>
                          {item.exchange}
                        </span>
                        {item.current_price != null && (
                          <span className="card-price-badge" style={{ fontSize: '0.88rem', fontWeight: '700', color: 'var(--text)', background: 'var(--surface-soft, var(--panel-2))', padding: '2px 8px', borderRadius: '4px', border: '1px solid var(--border)' }}>
                            {Math.round(item.current_price).toLocaleString('vi-VN')} ₫
                          </span>
                        )}
                      </div>
                      <div className={`score-badge ${tierClass}`}>
                        <div className="score-number">{item.total_score}</div>
                        <div className="score-label">/100 · {item.tier_vi}</div>
                      </div>
                    </div>

                    {/* Company Info */}
                    <div className="card-company-block">
                      <h3 className="card-company-name" title={item.company_name}>
                        {item.company_name}
                      </h3>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '4px' }}>
                        <span className="card-industry">{item.industry}</span>
                        {item.current_price != null && (
                          <span style={{ fontSize: '0.82rem', color: 'var(--muted, var(--text-secondary))' }}>
                            Thị giá: <strong style={{ color: 'var(--text)' }}>{Math.round(item.current_price).toLocaleString('vi-VN')} ₫</strong>
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Key Metrics Strip */}
                    <div className="card-metrics-grid">
                      <div className="metric-box">
                        <span className="metric-title">Sinh lời Vốn (ROE 5Y)</span>
                        <span className="metric-value highlight-green">
                          {item.avg_roe_5y !== null ? `${item.avg_roe_5y}%` : '—'}
                        </span>
                      </div>
                      <div className="metric-box">
                        <span className="metric-title">Hào kinh tế (Moat)</span>
                        <span className="metric-value">{item.moat_score}/20</span>
                      </div>
                      <div className="metric-box">
                        <span className="metric-title">Chất lượng Tiền</span>
                        <span className="metric-value">{item.cash_quality_score}/10</span>
                      </div>
                      <div className="metric-box">
                        <span className="metric-title">Phân bổ Vốn</span>
                        <span className="metric-value">{item.capital_allocation_score}/15</span>
                      </div>
                    </div>

                    {/* Action Button */}
                    <div className="card-actions" onClick={e => e.stopPropagation()}>
                      <button
                        type="button"
                        className="btn-deep-dive"
                        onClick={() => setSelectedSymbol(item.symbol)}
                        title={`Soi Định giá chi tiết ${item.symbol}`}
                      >
                        <span>Soi Định giá chi tiết</span>
                        <span className="arrow-icon">↗</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* In-Place Valuation Detail Overlay (Modal) */}
        {selectedSymbol && (
          <ValuationDetailOverlay
            symbol={selectedSymbol}
            onClose={() => setSelectedSymbol(null)}
          />
        )}
      </main>
    </div>
  );
}
