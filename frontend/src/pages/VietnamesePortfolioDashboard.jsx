import React, { useEffect, useMemo, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import AppNav from '../components/AppNav.jsx';
import DividendTree from '../components/DividendTree.jsx';
import HoldingSourceTree from '../components/HoldingSourceTree.jsx';
import { formatMoney } from '../lib/format.js';
import { deriveHoldingBooks } from '../lib/holdingBooks.js';
import { getDividendHistories, listPortfolioTransactions } from '../lib/api.js';
import { refreshDashboard, selectRefreshStatus } from '../lib/store.js';

function pct(value, digits = 2) {
  return value == null || !Number.isFinite(Number(value)) ? '-' : `${(Number(value) * 100).toFixed(digits)}%`;
}

function money(value, locale = 'vi') {
  return value == null || !Number.isFinite(Number(value)) ? '-' : `${formatMoney(value, false, locale)} ₫`;
}

function signedMoney(value, locale = 'vi') {
  if (value == null || !Number.isFinite(Number(value))) return '-';
  return `${Number(value) >= 0 ? '+' : ''}${money(value, locale)}`;
}

function Metric({ label, value, note, tone = '' }) {
  return <div className={`metric-card overview-metric ${tone}`}>
    <div className="metric-label">{label}</div>
    <div className="metric-value" data-sensitive="money">{value}</div>
    {note && <div className="metric-note">{note}</div>}
  </div>;
}

function currentVietnamYear() {
  return Number(new Intl.DateTimeFormat('en', { timeZone: 'Asia/Ho_Chi_Minh', year: 'numeric' }).format(new Date()));
}

function eventDate(event) {
  return event?.effective_event_date || event?.record_date || event?.ex_date || event?.announcement_date || event?.payment_date || null;
}

function eventYear(event) {
  const dateValue = eventDate(event);
  if (!dateValue) return null;
  const year = Number(String(dateValue).slice(0, 4));
  return Number.isInteger(year) && year >= 1900 ? year : null;
}

export default function VietnamesePortfolioDashboard({ dashboard = {}, locale = 'vi', dataLoading = false }) {
  const dispatch = useDispatch();
  const syncing = useSelector(selectRefreshStatus) === 'loading';
  const [message, setMessage] = useState('');
  const [query, setQuery] = useState('');
  const [dividends, setDividends] = useState([]);
  const [dividendLoading, setDividendLoading] = useState(false);
  const [holdingTransactions, setHoldingTransactions] = useState([]);
  const [holdingSourceLoading, setHoldingSourceLoading] = useState(false);
  const [holdingSourceError, setHoldingSourceError] = useState('');

  const portfolio = dashboard.portfolio || {};
  const portfolioContext = dashboard.portfolio_context || {};
  const positions = portfolio.positions || [];
  const performance = dashboard.performance_summary || {};
  const market = dashboard.market_data || {};
  const risk = dashboard.risk || {};
  const health = dashboard.health || {};
  const currentYear = currentVietnamYear();
  const holdingBooks = useMemo(() => deriveHoldingBooks(holdingTransactions), [holdingTransactions]);

  const visiblePositions = useMemo(() => {
    const q = query.trim().toUpperCase();
    return q ? positions.filter(row => String(row.symbol || '').toUpperCase().includes(q)) : positions;
  }, [positions, query]);

  const attentionItems = useMemo(() => {
    const items = [];
    const warnings = (health.flags || []).filter(flag => flag.level === 'WARNING');
    for (const flag of warnings.slice(0, 2)) items.push(flag.message);
    if (!warnings.length && risk.max_equity_weight != null && Number(risk.max_equity_weight) >= 0.40) {
      items.push(`Một mã đang chiếm ${pct(risk.max_equity_weight)} phần cổ phiếu của danh mục. Hãy kiểm tra mức tập trung này có còn phù hợp với kế hoạch đầu tư hay không.`);
    }
    if (market.status && !['VALID', 'READY', 'OK'].includes(String(market.status).toUpperCase())) {
      items.push('Dữ liệu giá hiện chưa đầy đủ hoặc chưa đồng bộ. Giá trị danh mục có thể chưa phản ánh phiên gần nhất.');
    }
    return items;
  }, [health, risk.max_equity_weight, market.status]);

  const latestDividendTreeRows = useMemo(() => dividends
    .map(item => {
      const validEvents = (item.result?.events || [])
        .map(event => ({ event, year: eventYear(event) }))
        .filter(row => row.year != null && row.year <= currentYear);
      const latestYear = validEvents.reduce(
        (latest, row) => latest == null || row.year > latest ? row.year : latest,
        null,
      );
      const events = latestYear == null
        ? []
        : validEvents
            .filter(row => row.year === latestYear)
            .map(row => row.event)
            .sort((a, b) => String(eventDate(b) || '').localeCompare(String(eventDate(a) || '')));
      return {
        symbol: item.symbol,
        events,
        error: item.error,
        loading: item.loading,
      };
    })
    .sort((a, b) => String(a.symbol).localeCompare(String(b.symbol))), [dividends, currentYear]);

  const dividendErrors = useMemo(() => dividends.filter(row => row.error), [dividends]);

  async function sync() {
    setMessage('');
    try {
      await dispatch(refreshDashboard()).unwrap();
      setMessage('Dữ liệu danh mục đã được cập nhật.');
    } catch (error) {
      setMessage(`Không thể cập nhật dữ liệu: ${error.message}`);
    }
  }

  async function loadDividends(refresh = false) {
    const symbols = positions.map(row => String(row.symbol || '').toUpperCase()).filter(Boolean);
    if (!symbols.length) return;
    setDividendLoading(true);
    setDividends(symbols.map(symbol => ({ symbol, result: null, error: null, loading: true })));
    try {
      await getDividendHistories(symbols, {
        refresh,
        concurrency: 6,
        onResult: completed => {
          setDividends(current => current.map(row => row.symbol === completed.symbol ? { ...completed, loading: false } : row));
        },
      });
    } finally {
      setDividendLoading(false);
    }
  }

  useEffect(() => {
    if (!positions.length) return undefined;
    let active = true;
    setHoldingSourceLoading(true);
    setHoldingSourceError('');
    listPortfolioTransactions()
      .then(rows => { if (active) setHoldingTransactions(rows || []); })
      .catch(error => { if (active) setHoldingSourceError(`Không thể xác định CTCK đang lưu ký: ${error.message}`); })
      .finally(() => { if (active) setHoldingSourceLoading(false); });
    return () => { active = false; };
  }, [positions.length]);

  useEffect(() => {
    if (positions.length) loadDividends(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [positions.map(row => row.symbol).join('|')]);

  const marketStatus = String(market.status || '').toUpperCase();
  const marketReady = !marketStatus || ['VALID', 'READY', 'OK'].includes(marketStatus);
  const hasCompleteValuation = !dataLoading && marketReady && positions.every(
    position => position.price != null && Number.isFinite(Number(position.price)),
  );
  const hasTotalPnl = hasCompleteValuation
    && portfolio.total_pnl != null
    && Number.isFinite(Number(portfolio.total_pnl));
  const totalPnl = hasTotalPnl ? Number(portfolio.total_pnl) : null;
  const totalPositive = totalPnl == null ? null : totalPnl >= 0;
  const dividendIncome = performance.net_dividend_income ?? performance.dividend_income ?? null;
  const hasCashRatio = portfolio.cash != null && portfolio.nav != null && Number(portfolio.nav) !== 0;

  return <div className="page investor-dashboard">
    <AppNav active="portfolio" locale={locale} />

    <header className="portfolio-hero investor-hero">
      <div className="hero-primary">
        <div className="eyebrow">{portfolioContext.name || 'Danh mục'} · Tổng tài sản</div>
        <h1 data-sensitive="money">{money(portfolio.nav, locale)}</h1>
        <div className={`hero-return ${totalPositive == null ? '' : totalPositive ? 'pos' : 'neg'}`}>
          <strong data-sensitive="money">{signedMoney(totalPnl, locale)}</strong>
          <span>{hasCompleteValuation
            ? <><span data-sensitive="pnl">{pct(portfolio.accounting_return)}</span> từ giá vốn và dòng tiền đã ghi nhận</>
            : 'Chờ cập nhật đủ dữ liệu giá để tính lãi/lỗ'}</span>
        </div>
        <div className="hero-meta">
          <span>{positions.length} mã cổ phiếu</span>
          <span>{dataLoading ? 'Đang tải dữ liệu giá…' : market.market_date ? `Dữ liệu giá đến ${market.market_date}` : 'Dữ liệu giá: chưa sẵn sàng'}</span>
        </div>
      </div>
      <div className="hero-actions">
        <a className="btn-primary" href="/transactions">+ Thêm giao dịch</a>
        <button className="btn-secondary" type="button" onClick={sync} disabled={syncing}>{syncing ? 'Đang cập nhật…' : '↻ Cập nhật dữ liệu'}</button>
      </div>
    </header>

    {message && <div className="run-message banner-message">{message}</div>}

    <div className="metric-grid portfolio-metrics overview-metrics investor-overview">
      <Metric label="Cổ phiếu" value={money(portfolio.equity_value, locale)} note={`${positions.length} mã đang nắm giữ`} />
      <Metric label="Tiền mặt" value={money(portfolio.cash, locale)} note={hasCashRatio ? `${pct(Number(portfolio.cash) / Number(portfolio.nav))} tổng tài sản` : undefined} />
      <Metric label="Tổng giá vốn" value={money(portfolio.cost_value, locale)} note="Giá vốn các cổ phiếu hiện có" />
      <Metric label="Cổ tức thực nhận" value={money(dividendIncome, locale)} note="Tiền mặt sau thuế đã ghi nhận" tone="income-metric" />
    </div>

    {/* Buy & Hold Discipline Health Score - Goal-Gradient & Zeigarnik Effect */}
    <section className="card portfolio-health-card">
      <div className="section-head">
        <div>
          <div className="eyebrow">Kỷ luật Buy & Hold</div>
          <h2>Đánh giá sức khỏe danh mục</h2>
        </div>
        <div className="health-score-badge">
          <span className="hanko-seal" title="Dấu triện kiểm tra">保全</span>
          <span className="health-score-ratio">
            <strong>{[
              positions.length >= 3,
              Number(portfolio.cash || 0) > 0,
              (risk.max_equity_weight == null || Number(risk.max_equity_weight) < 0.45),
              attentionItems.length === 0,
            ].filter(Boolean).length}</strong>/4 Tiêu chuẩn
          </span>
        </div>
      </div>
      <div className="health-checklist-grid">
        <div className={`health-check-item ${positions.length >= 3 ? 'passed' : 'pending'}`}>
          <span className="check-icon">{positions.length >= 3 ? '✓' : '○'}</span>
          <div>
            <b>Đa dạng hóa danh mục</b>
            <p>{positions.length >= 3 ? `Đã phân bổ trên ${positions.length} mã` : `Nên mở rộng từ 3-5 mã cốt lõi (hiện có ${positions.length})`}</p>
          </div>
        </div>
        <div className={`health-check-item ${Number(portfolio.cash || 0) > 0 ? 'passed' : 'pending'}`}>
          <span className="check-icon">{Number(portfolio.cash || 0) > 0 ? '✓' : '○'}</span>
          <div>
            <b>Dự phòng tiền mặt</b>
            <p>{hasCashRatio ? `${pct(Number(portfolio.cash) / Number(portfolio.nav))} tiền mặt bảo vệ vốn` : 'Nên duy trì tối thiểu 5-10% tiền mặt'}</p>
          </div>
        </div>
        <div className={`health-check-item ${(risk.max_equity_weight == null || Number(risk.max_equity_weight) < 0.45) ? 'passed' : 'pending'}`}>
          <span className="check-icon">{(risk.max_equity_weight == null || Number(risk.max_equity_weight) < 0.45) ? '✓' : '○'}</span>
          <div>
            <b>Kiểm soát tập trung vốn</b>
            <p>{risk.max_equity_weight == null ? 'Cân bằng tốt' : Number(risk.max_equity_weight) < 0.45 ? `Mã lớn nhất chiếm ${pct(risk.max_equity_weight)}` : `Mã lớn nhất chiếm ${pct(risk.max_equity_weight)} (Cần thận trọng)`}</p>
          </div>
        </div>
        <div className={`health-check-item ${attentionItems.length === 0 ? 'passed' : 'pending'}`}>
          <span className="check-icon">{attentionItems.length === 0 ? '✓' : '○'}</span>
          <div>
            <b>Đồng bộ & Bất biến sổ cái</b>
            <p>{attentionItems.length === 0 ? 'Dữ liệu sổ cái hoàn toàn khớp' : 'Có điểm cảnh báo cần kiểm tra'}</p>
          </div>
        </div>
      </div>
    </section>

    {attentionItems.length > 0 && <section className="card portfolio-assessment-card investor-attention-card">
      <div className="section-head">
        <div><div className="eyebrow">Cần chú ý</div><h2>Danh mục có điểm cần xem lại</h2></div>
        <a className="text-link" href="/risk">Xem phân tích →</a>
      </div>
      <div className="assessment-flags">
        {attentionItems.map((item, index) => <div className="assessment-flag warn-flag" key={index}><span aria-hidden="true">!</span><div><p>{item}</p></div></div>)}
      </div>
    </section>}

    <section className="card holdings-card investor-holdings-card">
      <div className="section-head holdings-head">
        <div>
          <div className="eyebrow">Danh mục hiện tại</div>
          <h2>Cổ phiếu đang nắm giữ</h2>
          <p className="muted">Mở từng mã để xem cổ phiếu đang nằm tại DNSE, TCBS hoặc CTCK nào. Khi bán, QPort chỉ dùng số cổ ở đúng CTCK và tài khoản đã chọn.</p>
        </div>
        {positions.length > 6 && <input className="search-input" value={query} onChange={event => setQuery(event.target.value)} placeholder="Tìm mã cổ phiếu…" aria-label="Tìm mã cổ phiếu" />}
      </div>

      {dataLoading && positions.length === 0 ? <div className="dashboard-loading-skeleton" role="status" aria-label="Đang tải danh sách cổ phiếu" /> : positions.length === 0 ? <div className="empty-state">
        <h3>Chưa có cổ phiếu trong danh mục</h3>
        <p>Hãy nhập danh mục hiện có hoặc ghi giao dịch mua đầu tiên.</p>
        <a className="btn-primary" href="/transactions">Nhập danh mục ban đầu</a>
      </div> : visiblePositions.length === 0 ? <div className="empty-state compact-empty">Không tìm thấy mã phù hợp.</div> : <HoldingSourceTree
        positions={visiblePositions}
        holdingBooks={holdingBooks}
        locale={locale}
        loading={holdingSourceLoading}
        error={holdingSourceError}
      />}
    </section>

    {positions.length > 0 && <section className="card dividend-card investor-dividend-card">
      <div className="section-head">
        <div>
          <div className="eyebrow">Cổ tức & quyền</div>
          <h2>Cổ tức gần nhất theo từng mã</h2>
          <p className="muted">Hiển thị các sự kiện cổ tức của năm mới nhất theo từng cổ phiếu đang nắm giữ.</p>
        </div>
        <div className="section-actions">
          <a className="text-link" href="/dividends">Xem toàn bộ lịch sử →</a>
          <button className="btn-secondary" type="button" onClick={() => loadDividends(true)} disabled={dividendLoading}>{dividendLoading ? 'Đang cập nhật…' : 'Cập nhật cổ tức'}</button>
        </div>
      </div>

      {dividendErrors.length > 0 && <div className="data-error-message" role="alert">
        Không thể tải dữ liệu cổ tức cho <b>{dividendErrors.map(row => row.symbol).join(', ')}</b>. Hãy thử cập nhật lại sau. Dữ liệu của các mã khác vẫn được giữ nguyên nếu tải thành công.
      </div>}

      {latestDividendTreeRows.length > 0 ? (
        <DividendTree rows={latestDividendTreeRows} locale={locale} root="symbol" openLatest />
      ) : dividendLoading ? <div className="dividend-tree-placeholder">Đang tải dữ liệu cổ tức…</div> : <div className="empty-state compact-empty">Chưa tìm thấy sự kiện cổ tức nào đến năm {currentYear} cho các mã hiện đang nắm giữ.</div>}
    </section>}
  </div>;
}
