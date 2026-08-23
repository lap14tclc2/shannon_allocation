import React, { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { getPortfolioOperations } from '../lib/api.js';
import { formatMoney } from '../lib/format.js';

function finite(value) {
  const n = Number(value);
  return value == null || !Number.isFinite(n) ? null : n;
}

function pct(value, digits = 1) {
  const n = finite(value);
  return n == null ? '-' : `${(n * 100).toFixed(digits)}%`;
}

function num(value, digits = 2) {
  const n = finite(value);
  return n == null ? '-' : n.toFixed(digits);
}

function Pill({ tone = 'neutral', children }) {
  return <span className={`fm-pill fm-pill-${tone}`}>{children}</span>;
}

function ReviewRow({ label, value, tone = '' }) {
  return <div className="fm-review-row">
    <span>{label}</span>
    <b className={tone}>{value}</b>
  </div>;
}

function uniqueBrokerAccounts(operations = {}) {
  const keys = new Set();
  for (const lot of operations.tax_lots || []) {
    keys.add(`${String(lot.broker_code || 'UNASSIGNED').toUpperCase()}::${String(lot.account_id || 'PRIMARY').toUpperCase()}`);
  }
  return [...keys];
}

export default function FundManagerReview({ dashboard = {}, locale = 'en' }) {
  const [target, setTarget] = useState(null);
  const [operations, setOperations] = useState(null);
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const money = value => {
    const n = finite(value);
    return n == null ? '-' : `${formatMoney(n, false, locale)} VND`;
  };

  const portfolio = dashboard.portfolio || {};
  const positions = portfolio.positions || [];
  const risk = dashboard.risk || {};
  const perf = dashboard.performance_summary || {};
  const market = dashboard.market_data || {};
  const health = dashboard.health || {};
  const history = market.history || {};

  useEffect(() => {
    if (typeof document !== 'undefined') setTarget(document.querySelector('.page'));
  }, []);

  useEffect(() => {
    let active = true;
    if (!positions.length) return undefined;
    getPortfolioOperations()
      .then(result => { if (active) setOperations(result || {}); })
      .catch(() => { if (active) setOperations({}); });
    return () => { active = false; };
  }, [positions.length]);

  const review = useMemo(() => {
    const sorted = [...positions].sort((a, b) => Number(b.weight || 0) - Number(a.weight || 0));
    const top = sorted[0] || null;
    const topTwoWeight = sorted.slice(0, 2).reduce((sum, row) => sum + Number(row.weight || 0), 0);
    const coverage = finite(risk.quality?.coverage_weight) ?? 0;
    const returnObs = Number(risk.return_observations || 0);
    const snapshots = Number(perf.official_snapshot_count || 0);
    const riskReady = coverage >= 0.90 && returnObs >= 20;
    const performanceReady = snapshots >= 20;
    const warnings = (health.flags || []).filter(flag => flag.level === 'WARNING');
    const cashWeight = finite(portfolio.nav) && Number(portfolio.nav) > 0 ? Number(portfolio.cash || 0) / Number(portfolio.nav) : 0;
    const brokerAccounts = uniqueBrokerAccounts(operations || {});
    const opExceptions = operations?.exceptions || [];
    const grossDividend = finite(perf.dividend_income ?? portfolio.dividend_income) ?? 0;
    const cashDividendTax = finite(perf.cash_dividend_tax);
    const netDividend = finite(perf.net_dividend_income);
    const totalPnl = finite(portfolio.total_pnl);
    const accountingReturn = finite(portfolio.accounting_return);
    const twr = finite(perf.returns?.since_inception);
    const drawdown = finite(perf.current_drawdown);
    const maxDrawdown = finite(perf.max_drawdown);
    const largestWeight = finite(top?.weight) ?? 0;

    let state = 'STABLE';
    let tone = 'valid';
    if (!riskReady || !performanceReady) {
      state = 'EVIDENCE BUILDING';
      tone = 'building';
    } else if (warnings.length) {
      state = 'REVIEW';
      tone = 'warning';
    }

    const constructionTone = largestWeight >= 0.40 || topTwoWeight >= 0.75 ? 'warning' : largestWeight >= 0.30 ? 'building' : 'valid';
    const constructionLabel = largestWeight >= 0.40 || topTwoWeight >= 0.75
      ? text('Concentrated', 'Tập trung cao')
      : largestWeight >= 0.30
        ? text('Moderately concentrated', 'Tập trung vừa')
        : text('Broadly balanced', 'Tương đối cân bằng');

    const commentary = [];
    if (top) {
      commentary.push(text(
        `Portfolio construction is ${constructionLabel.toLowerCase()}: ${String(top.symbol || '').toUpperCase()} is the largest position at ${pct(largestWeight)}, while the two largest holdings represent ${pct(topTwoWeight)} of NAV. Effective positions are ${num(risk.effective_positions)} versus ${positions.length} actual holdings.`,
        `Cấu trúc danh mục đang ở trạng thái ${constructionLabel.toLowerCase()}: ${String(top.symbol || '').toUpperCase()} là vị thế lớn nhất với ${pct(largestWeight)}, còn hai vị thế lớn nhất chiếm ${pct(topTwoWeight)} NAV. Số vị thế hiệu dụng là ${num(risk.effective_positions)} so với ${positions.length} mã thực tế.`
      ));
    }

    if (!riskReady) {
      commentary.push(text(
        `Risk conclusions remain provisional because D1 coverage is ${pct(coverage)} with ${returnObs} usable return observations. Volatility, correlation and tail-loss statistics should not be treated as decision-grade until the backfill is complete.`,
        `Kết luận rủi ro hiện vẫn mang tính tạm thời vì độ phủ D1 mới đạt ${pct(coverage)} với ${returnObs} quan sát lợi suất sử dụng được. Không nên coi volatility, correlation và tail-loss là đủ chất lượng để ra quyết định trước khi backfill hoàn tất.`
      ));
    } else {
      commentary.push(text(
        `Risk evidence is usable: 252D volatility is ${pct(risk.volatility_252)}, average correlation is ${num(risk.average_correlation)}, daily CVaR 95% is ${pct(risk.daily_cvar_95)}, and the largest risk contributor is ${risk.largest_risk_symbol || '-'} at ${pct(risk.largest_risk_contribution)} of total modeled risk.`,
        `Bằng chứng rủi ro đã đủ dùng: volatility 252D là ${pct(risk.volatility_252)}, correlation trung bình ${num(risk.average_correlation)}, CVaR ngày 95% là ${pct(risk.daily_cvar_95)}, và mã đóng góp rủi ro lớn nhất là ${risk.largest_risk_symbol || '-'} với ${pct(risk.largest_risk_contribution)} tổng rủi ro mô hình.`
      ));
    }

    if (!performanceReady) {
      commentary.push(text(
        `Tracked performance is still immature with ${snapshots} official daily snapshots. Accounting P/L (${money(totalPnl)}) can be reported now, but TWR, drawdown persistence and consistency should gain weight only as the tracked history grows.`,
        `Lịch sử hiệu suất còn non với ${snapshots} snapshot ngày chính thức. Có thể báo cáo Accounting P/L (${money(totalPnl)}) ngay, nhưng TWR, độ bền drawdown và tính ổn định chỉ nên được coi trọng hơn khi lịch sử theo dõi dài lên.`
      ));
    } else {
      commentary.push(text(
        `Tracked performance is sufficiently established for short-history review: since-inception TWR is ${pct(twr)}, current drawdown is ${pct(drawdown)}, and maximum tracked drawdown is ${pct(maxDrawdown)}. These should be read alongside accounting return of ${pct(accountingReturn)} because external cash flows affect the two measures differently.`,
        `Lịch sử hiệu suất đã đủ cho review ngắn hạn: TWR từ khi theo dõi là ${pct(twr)}, drawdown hiện tại ${pct(drawdown)}, và max drawdown đã ghi nhận ${pct(maxDrawdown)}. Các số này nên đọc cùng accounting return ${pct(accountingReturn)} vì external cash flow ảnh hưởng hai thước đo khác nhau.`
      ));
    }

    commentary.push(text(
      `Liquidity is ${pct(cashWeight)} of NAV. Gross cash-dividend income recorded so far is ${money(grossDividend)}${netDividend != null ? `, with ${money(netDividend)} net after recorded withholding` : ''}${cashDividendTax != null ? ` and ${money(cashDividendTax)} cash-dividend tax` : ''}.`,
      `Thanh khoản tiền mặt đang chiếm ${pct(cashWeight)} NAV. Cổ tức tiền mặt gross đã ghi nhận là ${money(grossDividend)}${netDividend != null ? `, còn ${money(netDividend)} net sau khấu trừ đã ghi nhận` : ''}${cashDividendTax != null ? ` và ${money(cashDividendTax)} thuế cổ tức tiền mặt` : ''}.`
    ));

    const priorities = [];
    if (!riskReady) priorities.push(text('Complete D1 history before relying on covariance, volatility or CVaR.', 'Hoàn thiện lịch sử D1 trước khi dựa vào covariance, volatility hoặc CVaR.'));
    if (!performanceReady) priorities.push(text('Build at least 20 official snapshots for basic performance review and ~252 for a full-year view.', 'Tích lũy ít nhất 20 snapshot chính thức cho review performance cơ bản và khoảng 252 cho khung đầy đủ 1 năm.'));
    if (largestWeight >= 0.35 || topTwoWeight >= 0.70) priorities.push(text('Monitor concentration at both single-name and top-two level; review thesis changes rather than reacting to price alone.', 'Theo dõi concentration ở cả single-name và top-two; review thay đổi của investment thesis thay vì phản ứng chỉ theo giá.'));
    if (riskReady && finite(risk.largest_risk_contribution) != null && Number(risk.largest_risk_contribution) > 0.45) priorities.push(text('Investigate why one holding dominates modeled portfolio risk and whether that exposure is intentional.', 'Xác minh vì sao một mã chi phối phần lớn modeled risk và liệu exposure đó có chủ đích hay không.'));
    if (performanceReady && drawdown != null && drawdown <= -0.15) priorities.push(text('Review drawdown drivers and thesis integrity; do not convert the diagnostic into an automatic sell rule.', 'Review nguyên nhân drawdown và tính toàn vẹn của thesis; không biến chẩn đoán thành rule bán tự động.'));
    if (opExceptions.length) priorities.push(text(`Resolve ${opExceptions.length} operational/data exception${opExceptions.length === 1 ? '' : 's'} before treating the book as fully reconciled.`, `Xử lý ${opExceptions.length} exception vận hành/dữ liệu trước khi coi book là đã reconcile đầy đủ.`));
    if (!priorities.length) priorities.push(text('Maintain data freshness, ledger discipline and periodic thesis review; no portfolio-level exception currently requires escalation.', 'Duy trì độ mới dữ liệu, kỷ luật ledger và review thesis định kỳ; hiện chưa có exception cấp danh mục cần escalation.'));

    return {
      state, tone, constructionTone, constructionLabel, top, topTwoWeight, coverage, returnObs, snapshots,
      riskReady, performanceReady, warnings, cashWeight, brokerAccounts, opExceptions, grossDividend,
      cashDividendTax, netDividend, totalPnl, accountingReturn, twr, drawdown, maxDrawdown,
      commentary, priorities,
    };
  }, [positions, portfolio, risk, perf, market, health, history, operations, locale]);

  if (!target || !positions.length) return null;

  return createPortal(
    <section className="card fund-manager-review-card" data-testid="fund-manager-review">
      <div className="section-head fm-review-head">
        <div>
          <div className="eyebrow">{text('Professional portfolio review', 'Góc nhìn quản lý danh mục chuyên nghiệp')}</div>
          <h2>{text('Fund manager review', 'Nhận xét của nhà quản lý quỹ')}</h2>
          <p className="muted">{text(
            'A deterministic synthesis of portfolio construction, risk, performance, income, liquidity and operational evidence already stored in QPort. It does not create trades.',
            'Bản tổng hợp deterministic từ cấu trúc danh mục, risk, performance, income, liquidity và bằng chứng vận hành đã có trong QPort. Phần này không tạo giao dịch.'
          )}</p>
        </div>
        <div className="fm-review-state">
          <Pill tone={review.tone}>{review.state}</Pill>
          <span className="muted">{dashboard.today || market.market_date || '-'}</span>
        </div>
      </div>

      <div className="fm-executive-strip">
        <div>
          <span>{text('Construction', 'Cấu trúc')}</span>
          <b>{review.constructionLabel}</b>
          <Pill tone={review.constructionTone}>{positions.length} {text('holdings', 'mã')}</Pill>
        </div>
        <div>
          <span>{text('Risk evidence', 'Bằng chứng risk')}</span>
          <b>{review.riskReady ? text('Decision-grade', 'Đủ chất lượng review') : text('Building', 'Đang xây dựng')}</b>
          <Pill tone={review.riskReady ? 'valid' : 'building'}>{pct(review.coverage)} {text('coverage', 'độ phủ')}</Pill>
        </div>
        <div>
          <span>{text('Performance evidence', 'Bằng chứng performance')}</span>
          <b>{review.performanceReady ? text('Usable short history', 'Đủ lịch sử ngắn') : text('Immature', 'Chưa trưởng thành')}</b>
          <Pill tone={review.performanceReady ? 'valid' : 'building'}>{review.snapshots} {text('snapshots', 'snapshot')}</Pill>
        </div>
        <div>
          <span>{text('Control state', 'Trạng thái kiểm soát')}</span>
          <b>{review.opExceptions.length ? text('Exceptions open', 'Còn exception') : text('No open exception', 'Không có exception')}</b>
          <Pill tone={review.opExceptions.length ? 'warning' : 'valid'}>{review.opExceptions.length}</Pill>
        </div>
      </div>

      <div className="fm-review-grid">
        <section className="fm-review-block">
          <h3>{text('Portfolio construction', 'Cấu trúc danh mục')}</h3>
          <ReviewRow label={text('Largest holding', 'Vị thế lớn nhất')} value={review.top ? `${String(review.top.symbol || '').toUpperCase()} · ${pct(review.top.weight)}` : '-'} />
          <ReviewRow label={text('Top-two NAV weight', 'Tỷ trọng top-two NAV')} value={pct(review.topTwoWeight)} />
          <ReviewRow label={text('Effective / actual positions', 'Vị thế hiệu dụng / thực tế')} value={`${num(risk.effective_positions)} / ${positions.length}`} />
          <ReviewRow label={text('Equity HHI', 'HHI cổ phiếu')} value={num(risk.equity_hhi, 3)} />
          <ReviewRow label={text('Broker/account sources', 'Nguồn broker/account')} value={operations == null ? text('Loading…', 'Đang tải…') : String(review.brokerAccounts.length)} />
        </section>

        <section className="fm-review-block">
          <h3>{text('Risk discipline', 'Kỷ luật rủi ro')}</h3>
          <ReviewRow label={text('D1 risk coverage', 'Độ phủ D1 risk')} value={`${pct(review.coverage)} · ${history.ready_symbols ?? risk.quality?.eligible_symbols ?? 0}/${history.total_symbols ?? positions.length}`} />
          <ReviewRow label={text('252D volatility', 'Volatility 252D')} value={pct(risk.volatility_252)} />
          <ReviewRow label={text('Average correlation', 'Correlation trung bình')} value={num(risk.average_correlation)} />
          <ReviewRow label={text('Daily CVaR 95%', 'CVaR ngày 95%')} value={pct(risk.daily_cvar_95)} />
          <ReviewRow label={text('Largest risk contributor', 'Đóng góp risk lớn nhất')} value={`${risk.largest_risk_symbol || '-'} ${pct(risk.largest_risk_contribution)}`} />
        </section>

        <section className="fm-review-block">
          <h3>{text('Performance & income', 'Hiệu suất & thu nhập')}</h3>
          <ReviewRow label={text('Accounting P/L', 'Accounting P/L')} value={money(review.totalPnl)} tone={review.totalPnl != null ? (review.totalPnl >= 0 ? 'pos' : 'neg') : ''} />
          <ReviewRow label={text('Accounting return', 'Accounting return')} value={pct(review.accountingReturn)} />
          <ReviewRow label={text('Since-inception TWR', 'TWR từ khi theo dõi')} value={pct(review.twr)} />
          <ReviewRow label={text('Current / max drawdown', 'Drawdown hiện tại / max')} value={`${pct(review.drawdown)} / ${pct(review.maxDrawdown)}`} />
          <ReviewRow label={text('Gross cash dividends', 'Cổ tức tiền gross')} value={money(review.grossDividend)} />
        </section>

        <section className="fm-review-block">
          <h3>{text('Liquidity & controls', 'Thanh khoản & kiểm soát')}</h3>
          <ReviewRow label={text('Cash / NAV', 'Cash / NAV')} value={pct(review.cashWeight)} />
          <ReviewRow label={text('Market data', 'Dữ liệu thị trường')} value={`${market.status || '-'} · ${market.market_date || '-'}`} />
          <ReviewRow label={text('Return observations', 'Quan sát lợi suất')} value={String(review.returnObs)} />
          <ReviewRow label={text('Official snapshots', 'Snapshot chính thức')} value={String(review.snapshots)} />
          <ReviewRow label={text('Open operational exceptions', 'Exception vận hành đang mở')} value={String(review.opExceptions.length)} />
        </section>
      </div>

      <div className="fm-commentary">
        <h3>{text('Manager commentary', 'Nhận xét của nhà quản lý')}</h3>
        {review.commentary.map((paragraph, index) => <p key={index}>{paragraph}</p>)}
      </div>

      <div className="fm-priorities">
        <h3>{text('Monitoring priorities', 'Ưu tiên theo dõi')}</h3>
        <ol>{review.priorities.map((item, index) => <li key={index}>{item}</li>)}</ol>
      </div>

      <div className="section-foot fm-review-foot">
        <span className="muted">{text(
          'Professional-style portfolio oversight, not individualized investment advice. Evidence quality controls the confidence of each conclusion.',
          'Góc nhìn giám sát danh mục theo phong cách chuyên nghiệp, không phải tư vấn đầu tư cá nhân. Chất lượng dữ liệu quyết định độ tin cậy của từng kết luận.'
        )}</span>
        <a className="text-link" href="/performance">{text('Performance details →', 'Chi tiết hiệu suất →')}</a>
      </div>
    </section>,
    target,
  );
}
