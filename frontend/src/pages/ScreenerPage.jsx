import React, { useEffect, useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import ValuationDetailOverlay from '../components/ValuationDetailOverlay.jsx';
import TcbsTokenPrompt from '../components/TcbsTokenPrompt.jsx';
import { crawlValuationHistory } from '../lib/api.js';
import { downloadScreenerAIExport } from '../lib/aiExport.js';
import '../valuation-page.css';
import '../screener-page.css';

const EXCHANGE_OPTIONS = [
  { id: 'ALL', label: 'Tất cả sàn' },
  { id: 'HOSE', label: 'HOSE' },
  { id: 'HNX', label: 'HNX' },
  { id: 'UPCOM', label: 'UPCOM' },
];

const MOS_OPTIONS = [
  { id: 'buffett_qualified', label: '🛡️ Đạt chuẩn Buffett (MOS ≥ 25%)' },
  { id: 'positive', label: '📈 Biên An Toàn Dương (MOS > 0%)' },
  { id: 'undervalued', label: '💎 Định giá Dưới Giá trị thực' },
  { id: 'all', label: '🌐 Tất cả cổ phiếu' },
];

const LIQUIDITY_OPTIONS = [
  { id: 20, label: '🔥 ≥ 20 Tỷ / ngày' },
  { id: 10, label: '⚡ ≥ 10 Tỷ / ngày' },
  { id: 5, label: '💧 ≥ 5 Tỷ / ngày' },
  { id: 1, label: '🌱 ≥ 1 Tỷ / ngày' },
  { id: 0, label: '🌐 Tất cả thanh khoản' },
];

const SCORE_OPTIONS = [
  { id: 0, label: 'Tất cả điểm số' },
  { id: 80, label: '≥ 80 Điểm (Hảo hạng)' },
  { id: 70, label: '≥ 70 Điểm (Đầu tư)' },
  { id: 60, label: '≥ 60 Điểm (Theo dõi)' },
];

const SORT_OPTIONS = [
  { id: 'mos', label: 'Biên An Toàn MOS (Cao → Thấp)' },
  { id: 'liquidity', label: 'Thanh khoản GTGD (Cao → Thấp)' },
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

  // Filters state - Default to Buffett Margin of Safety & >= 10B/day Liquidity
  const [mosFilter, setMosFilter] = useState('buffett_qualified');
  const [minLiquidity, setMinLiquidity] = useState(10);
  const [minScore, setMinScore] = useState(0);
  const [exchange, setExchange] = useState('ALL');
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('mos');
  const [exportingAI, setExportingAI] = useState(false);
  const [crawlingSymbol, setCrawlingSymbol] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [tokenPromptSymbol, setTokenPromptSymbol] = useState(null);
  const [tokenPromptError, setTokenPromptError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function fetchScreener() {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        if (mosFilter) params.set('mos_filter', mosFilter);
        if (minLiquidity > 0) params.set('min_liquidity', String(minLiquidity));
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
  }, [mosFilter, minLiquidity, minScore, exchange, search, sortBy, refreshKey]);

  const items = data?.items || [];
  const totalScreened = data?.total_screened || 0;
  const universeSize = data?.universe_size || 1523;
  const crawlEnabled = data?.crawl_enabled !== false;

  const exportScreenerCsv = () => {
    if (!items.length) return;
    const csvCell = (value) => {
      const str = value == null ? '' : String(value);
      return /[",\n]/.test(str) ? `"${str.replace(/"/g, '""')}"` : str;
    };
    const headers = [
      'Mã CP', 'Tên công ty', 'Sàn', 'Ngành', 'Thị giá (₫)', 'Giá trị Thực (₫)',
      'MOS (%)', 'MOS tham khảo (%)', 'Model Status', 'Req MOS (%)', 'Trạng thái định giá', 'Điểm Chất lượng', 'Hạng',
      'Archetype', 'P/E', 'P/B', 'ROE 5Y (%)', 'Thanh khoản 20D (tỷ/ngày)', 'Cảnh báo',
    ];
    const rows = items.map(it => [
      it.symbol, it.company_name, it.exchange, it.industry,
      it.current_price, it.intrinsic_value,
      it.margin_of_safety, it.diagnostic_mos, it.model_status, it.required_mos,
      it.valuation_status_vi || it.valuation_status,
      it.total_score, it.tier_vi || it.tier, it.archetype,
      it.pe, it.pb, it.avg_roe_5y, it.avg_turnover_20d_billion, it.valuation_warning,
    ]);
    const csv = '\uFEFF' + [headers, ...rows].map(r => r.map(csvCell).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `qport-screener-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const exportScreenerAi = async () => {
    if (!items.length || exportingAI) return;
    setExportingAI(true);
    try {
      await downloadScreenerAIExport(items);
    } catch (err) {
      console.error('Screener AI export failed:', err);
    } finally {
      setExportingAI(false);
    }
  };

  const handleCrawl = async (symbol) => {
    if (!symbol || crawlingSymbol) return;
    setCrawlingSymbol(symbol);
try {
        await crawlValuationHistory(symbol);
      } catch (err) {
        if (err?.code === 'TCBS_AUTH_REQUIRED') {
          setTokenPromptError(err?.message || 'Yêu cầu Bearer token TCBS.');
          setTokenPromptSymbol(symbol);
        } else if (err?.code === 'CRAWL_DISABLED_ON_VERCEL') {
          console.warn('Crawl disabled on Vercel:', err?.message);
        } else {
          console.error('Crawl TCBS failed:', symbol, err?.message || err);
        }
      } finally {
      setCrawlingSymbol(null);
      // Refetch screener so the refreshed model coverage is reflected.
      setRefreshKey(k => k + 1);
    }
  };

  // Feedback 31/08: chia kết quả bộ lọc thành 2 section.
  // Section 1: đạt chuẩn & đầy đủ dữ liệu định giá (có MOS + xác định được mô hình).
  // Section 2: đạt chuẩn nhưng thiếu dữ liệu định giá (không tính được MOS / chưa
  // xác định được mô hình / bị chặn chất lượng -> cảnh báo trên card).
  const fullyValued = useMemo(
    () => items.filter(it => it.model_status === 'MODEL_VERIFIED' && it.margin_of_safety != null),
    [items],
  );
  const section2 = useMemo(
    () => items.filter(it => !(it.model_status === 'MODEL_VERIFIED' && it.margin_of_safety != null)),
    [items],
  );

  const renderScreenerCard = (item, isMissingData) => {
    const tierClass = getTierClass(item);
    const hasMos = item.margin_of_safety != null;
    const isPosMos = item.is_positive_mos;
    return (
      <div
        key={item.symbol}
        className={`screener-card ${tierClass} ${isMissingData ? 'screener-card-missing-data' : ''}`}
        onClick={() => setSelectedSymbol(item.symbol)}
        style={{ cursor: 'pointer' }}
      >
        {isMissingData && (
          <div className="missing-data-badge" role="alert">
            <span className="missing-data-icon" aria-hidden="true">🕳️</span>
            <span>Thiếu dữ liệu định giá chi tiết</span>
          </div>
        )}
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

          {/* Prominent Margin of Safety Badge */}
          <div className={`score-badge ${tierClass}`}>
            <div className="score-number" style={{ color: isPosMos ? 'var(--retro-green, #2f6b4d)' : 'inherit' }}>
              {hasMos
                ? (item.margin_of_safety > 0 ? `+${item.margin_of_safety}%` : `${item.margin_of_safety}%`)
                : (isMissingData && item.diagnostic_mos != null
                    ? `${item.diagnostic_mos > 0 ? '+' : ''}${item.diagnostic_mos}%`
                    : `${item.total_score}/100`)}
            </div>
            <div className="score-label">
              {hasMos
                ? (item.is_buffett_qualified ? '🛡️ ĐẠT CHUẨN BUFFETT' : item.valuation_status_vi)
                : (isMissingData && item.diagnostic_mos != null
                    ? 'MOS tham khảo (chưa xác thực)'
                    : (item.model_status === 'MODEL_ESTIMATED' ? 'Mô hình Ước tính' : item.model_status === 'MODEL_INCOMPLETE' ? 'Thiếu dữ liệu model' : item.tier_vi))}
            </div>
          </div>
        </div>

        {item.valuation_warning && (
          <div className="valuation-warning-banner" role="alert">
            <span className="valuation-warning-icon">⚠️</span>
            <span>{item.valuation_warning}</span>
          </div>
        )}

        {isMissingData && item.valuation_gap && (
          <div className="missing-data-reason">
            <span className="missing-data-reason-label">{item.model_status === 'MODEL_ESTIMATED' ? 'Mô hình Ước tính' : item.model_status === 'MODEL_INCOMPLETE' ? 'Thiếu dữ liệu mô hình đặc thù' : item.model_status || 'Thiếu dữ liệu'}: </span>
            {item.valuation_gap}
          </div>
        )}
        {isMissingData && !item.valuation_gap && item.margin_of_safety == null && (
          <div className="missing-data-reason">
            Thiếu dữ liệu BCTC (lợi nhuận / số cổ phiếu) để tính Giá trị Thực và Biên An Toàn.
          </div>
        )}

        {/* Company Info */}
        <div className="card-company-block">
          <h3 className="card-company-name" title={item.company_name}>
            {item.company_name}
          </h3>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '4px', flexWrap: 'wrap', gap: '4px' }}>
            <span className="card-industry">{item.industry}</span>
            {item.intrinsic_value != null && (
              <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                Giá trị Thực: <strong style={{ color: 'var(--accent)' }}>{Math.round(item.intrinsic_value).toLocaleString('vi-VN')} ₫</strong>
              </span>
            )}
          </div>
        </div>

        {/* Key Metrics Strip */}
        <div className="card-metrics-grid">
<div className="metric-box">
                        <span className="metric-title">Biên an toàn (MOS)</span>
                        <span className={`metric-value ${isPosMos ? 'highlight-green' : ''}`}>
                          {hasMos
                            ? `${item.margin_of_safety > 0 ? '+' : ''}${item.margin_of_safety}%`
                            : (item.diagnostic_mos != null ? `${item.diagnostic_mos > 0 ? '+' : ''}${item.diagnostic_mos}%` : '—')}
                        </span>
                        {!hasMos && item.diagnostic_mos != null && (
                          <span className="metric-note">Tham khảo (chưa xác thực)</span>
                        )}
                      </div>
          <div className="metric-box">
            <span className="metric-title">Thanh khoản 20D</span>
            <span className="metric-value highlight-roe">
              {item.avg_turnover_20d_billion != null && item.avg_turnover_20d_billion > 0 ? `${item.avg_turnover_20d_billion.toFixed(1)} tỷ/ngày` : '—'}
            </span>
          </div>
          <div className="metric-box">
            <span className="metric-title">Sinh lời Vốn (ROE)</span>
            <span className="metric-value highlight-green">
              {item.avg_roe_5y !== null ? `${item.avg_roe_5y}%` : '—'}
            </span>
          </div>
          <div className="metric-box">
            <span className="metric-title">Điểm Chất lượng</span>
            <span className="metric-value">{item.total_score}/100</span>
          </div>
        </div>

        {/* Action Button */}
        <div className="card-actions" onClick={e => e.stopPropagation()}>
          {isMissingData && crawlEnabled && (
            <button
              type="button"
              className="btn-deep-dive btn-crawl-tcbs"
              onClick={() => handleCrawl(item.symbol)}
              disabled={crawlingSymbol != null}
              title="Crawl lịch sử BCTC (7–10 năm) từ TCBS để hoàn thiện mô hình định giá (cần TCBS_BEARER_TOKEN trên server)"
            >
              <span>{crawlingSymbol === item.symbol ? '⏳ Đang cập nhật…' : '⬇ Cập nhật dữ liệu TCBS'}</span>
            </button>
          )}
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
  };

  const countsByExchange = useMemo(() => {
    const counts = { HOSE: 0, HNX: 0, UPCOM: 0 };
    items.forEach(it => {
      if (counts[it.exchange] !== undefined) counts[it.exchange]++;
    });
    return counts;
  }, [items]);

  const getTierClass = (item) => {
    if (item.is_buffett_qualified) return 'tier-exceptional';
    if (item.is_positive_mos) return 'tier-investable';
    if (item.total_score >= 80) return 'tier-exceptional';
    if (item.total_score >= 70) return 'tier-investable';
    return 'tier-watch';
  };

  return (
    <div className="app-shell screener-page-shell">
      <AppNav active="screener" />

      <main className="screener-main-content">
        {/* Header Hero */}
        <section className="screener-hero">
          <div className="screener-hero-badge">
            <span className="sparkle-icon">✦</span>
            <span>BUFFETT RULE #1: NEVER LOSE MONEY</span>
          </div>
          <h1 className="screener-title">Bộ Lọc Cổ Phiếu Theo Biên An Toàn Buffett</h1>
          <p className="screener-subtitle">
            Sàng lọc toàn diện <strong>{universeSize} doanh nghiệp</strong> trên sàn chứng khoán Việt Nam: Ưu tiên mã có <strong>Thị giá thấp hơn Giá trị Thực</strong> và đạt <strong>Biên An Toàn (Margin of Safety)</strong> bảo vệ vốn theo nguyên tắc đầu tư giá trị cốt lõi.
          </p>

          {/* Quick Stats Pill */}
          <div className="screener-stats-strip">
            <div className="stat-pill highlight">
              <span className="stat-num">{totalScreened}</span>
              <span className="stat-label">mã đạt chuẩn biên an toàn</span>
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

            {/* Export CSV */}
            <button
              type="button"
              className="screener-export-btn"
              onClick={exportScreenerCsv}
              disabled={items.length === 0}
              title="Xuất danh sách cổ phiếu đang lọc ra file CSV"
            >
              <span aria-hidden="true">⬇</span> Xuất CSV
            </button>

            {/* Export AI (gồm data chi tiết overlay của tất cả mã được gợi ý) */}
            <button
              type="button"
              className="screener-export-btn screener-export-ai-btn"
              onClick={exportScreenerAi}
              disabled={items.length === 0 || exportingAI}
              title="Xuất báo cáo AI gồm định giá chi tiết (overlay) của tất cả mã được gợi ý"
            >
              <span aria-hidden="true">🤖</span> {exportingAI ? 'Đang xuất…' : 'Xuất AI'}
            </button>
          </div>

          <div className="toolbar-filter-row">
            {/* Buffett Margin of Safety Filter Tabs */}
            <div className="filter-group" style={{ flex: '1 1 100%' }}>
              <span className="filter-group-label" style={{ color: 'var(--accent)', fontWeight: '700' }}>
                🛡️ Tiêu chuẩn Biên An Toàn (Buffett MOS):
              </span>
              <div className="segmented-pills">
                {MOS_OPTIONS.map(opt => (
                  <button
                    key={opt.id}
                    type="button"
                    className={`segment-btn ${mosFilter === opt.id ? 'active' : ''}`}
                    onClick={() => setMosFilter(opt.id)}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Liquidity 20-Day Turnover Filter Tabs */}
            <div className="filter-group" style={{ flex: '1 1 100%' }}>
              <span className="filter-group-label" style={{ color: 'var(--retro-indigo, #2b4c7e)', fontWeight: '700' }}>
                ⚡ Thanh khoản GTGD Trung bình (20 phiên):
              </span>
              <div className="segmented-pills">
                {LIQUIDITY_OPTIONS.map(opt => (
                  <button
                    key={opt.id}
                    type="button"
                    className={`segment-btn ${minLiquidity === opt.id ? 'active' : ''}`}
                    onClick={() => setMinLiquidity(opt.id)}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

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

            {/* Quality Score Filter Tabs */}
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

        {/* Screener Results Area */}
        <section className="screener-results-section">
          {loading && (
            <div className="screener-loading-grid">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="screener-card skeleton-card">
                  <div className="skeleton-line" style={{ width: '40%', height: '24px' }} />
                  <div className="skeleton-line" style={{ width: '70%', height: '16px', marginTop: '12px' }} />
                  <div className="skeleton-line" style={{ width: '100%', height: '80px', marginTop: '16px' }} />
                </div>
              ))}
            </div>
          )}

          {!loading && error && (
            <div className="screener-error-box">
              <h3>Đã xảy ra lỗi khi tải bộ lọc</h3>
              <p>{error}</p>
              <button
                type="button"
                className="btn-retry"
                onClick={() => setMosFilter('buffett_qualified')}
              >
                Tải lại danh sách
              </button>
            </div>
          )}

          {!loading && !error && items.length === 0 && (
            <div className="screener-empty-box">
              <span className="empty-icon">📂</span>
              <h3>Không tìm thấy cổ phiếu thỏa mãn tiêu chí</h3>
              <p>Thử điều chỉnh tiêu chuẩn Biên An Toàn hoặc xóa từ khóa tìm kiếm.</p>
              <button
                type="button"
                className="reset-filters-btn"
                onClick={() => {
                  setSearch('');
                  setMosFilter('all');
                  setMinScore(0);
                  setExchange('ALL');
                }}
              >
                Xem toàn bộ cổ phiếu trên sàn
              </button>
            </div>
          )}

          {!loading && !error && items.length > 0 && (
            <>
              {fullyValued.length > 0 && (
                <div className="screener-section">
                  <div className="screener-section-head">
                    <h3>✅ Đạt chuẩn & Đầy đủ dữ liệu định giá</h3>
                    <span className="screener-section-count">{fullyValued.length} mã</span>
                  </div>
                  <div className="screener-grid">
                    {fullyValued.map(item => renderScreenerCard(item, false))}
                  </div>
                </div>
              )}

              {section2.length > 0 && (
                <div className="screener-section">
                  <div className="screener-section-head missing">
                    <h3>⚠️ Đạt chuẩn nhưng Thiếu dữ liệu định giá</h3>
                    <span className="screener-section-count">{section2.length} mã</span>
                    <p className="screener-section-note">
                      Các mã này đạt tiêu chí bộ lọc nhưng chưa thể định giá chi tiết do: Thiếu dữ liệu mô hình đặc thù (MODEL_INCOMPLETE), Mô hình Ước tính (giả định chưa có nguồn — MODEL_ESTIMATED), hoặc chưa xác định được bản chất kinh tế. Nhấn "Soi Định giá chi tiết" để xem dữ liệu cần bổ sung.
                    </p>
                  </div>
                  <div className="screener-grid">
                    {section2.map(item => renderScreenerCard(item, true))}
                  </div>
                </div>
              )}
            </>
          )}
        </section>

        {/* In-Place Valuation Detail Overlay (Modal) */}
        {selectedSymbol && (
          <ValuationDetailOverlay
            symbol={selectedSymbol}
            crawlEnabled={crawlEnabled}
            onClose={() => setSelectedSymbol(null)}
          />
        )}

        {/* TCBS Bearer token prompt on 401/403 crawl */}
        {tokenPromptSymbol && (
          <TcbsTokenPrompt
            symbol={tokenPromptSymbol}
            errorDetail={tokenPromptError}
            onClose={() => { setTokenPromptSymbol(null); setTokenPromptError(null); }}
            onSuccess={() => { setTokenPromptSymbol(null); setTokenPromptError(null); setRefreshKey(k => k + 1); }}
          />
        )}
      </main>
    </div>
  );
}
