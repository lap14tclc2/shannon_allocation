import React, { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { formatNumber as num, pct } from '../lib/format.js';
import { chooseText } from '../i18n.js';

function Progress({ value, label }) {
  const bounded = Math.max(0, Math.min(1, Number(value || 0)));
  return <div className="evidence-progress" aria-label={label}>
    <div className="evidence-progress-track"><span style={{ width: `${bounded * 100}%` }} /></div>
    <b>{Math.round(bounded * 100)}%</b>
  </div>;
}

export default function PortfolioAssessmentEnhancer({ dashboard = {}, locale = 'en' }) {
  const [target, setTarget] = useState(null);
  const text = (en, vi) => chooseText(locale, en, vi);
  const risk = dashboard.risk || {};
  const perf = dashboard.performance_summary || {};
  const quality = risk.quality || {};
  const methodology = risk.methodology || {};
  const positions = dashboard.portfolio?.positions || [];
  const marketHistory = dashboard.market_data?.history || {};

  useEffect(() => {
    if (typeof document !== 'undefined') setTarget(document.querySelector('.portfolio-assessment-card'));
  }, []);

  const evidence = useMemo(() => {
    const coverage = Number(quality.coverage_weight || 0);
    const requested = Number(quality.requested_symbols ?? marketHistory.total_symbols ?? positions.length ?? 0);
    const eligible = Number(quality.eligible_symbols ?? marketHistory.ready_symbols ?? Math.max(0, requested - (quality.missing_symbols || []).length));
    const historyCount = Number(perf.official_snapshot_count || 0);
    const returnObs = Number(risk.return_observations || 0);
    const missing = quality.missing_symbols || marketHistory.symbols?.filter(row => !row.risk_ready).map(row => row.symbol) || [];
    const riskReady = coverage >= 0.90 && returnObs >= 20;
    const performanceReady = historyCount >= 20;
    const historyDepth = Math.min(1, historyCount / 252);
    const basicPerformanceDepth = Math.min(1, historyCount / 20);
    return { coverage, requested, eligible, historyCount, returnObs, missing, riskReady, performanceReady, historyDepth, basicPerformanceDepth };
  }, [quality, perf, risk, positions.length, marketHistory]);

  if (!target || positions.length === 0) return null;

  const building = !evidence.riskReady;

  return createPortal(
    <div className={`assessment-depth ${building ? 'assessment-depth-building' : ''}`} data-testid="portfolio-assessment-depth">
      <div className="assessment-depth-head">
        <div>
          <div className="eyebrow">{text('Evidence behind the assessment', 'Bằng chứng phía sau đánh giá')}</div>
          <h3>{text('Risk & performance context', 'Bối cảnh rủi ro & hiệu suất')}</h3>
        </div>
        <div className="assessment-readiness">
          <span className={`status-pill ${evidence.riskReady ? 'status-valid' : 'status-partial'}`}>{text('Risk', 'Rủi ro')} · {evidence.riskReady ? 'READY' : 'BUILDING'}</span>
          <span className={`status-pill ${evidence.performanceReady ? 'status-valid' : 'status-partial'}`}>{text('History', 'Lịch sử')} · {evidence.performanceReady ? 'READY' : 'BUILDING'}</span>
        </div>
      </div>

      {building ? <>
        <div className="assessment-building-grid">
          <section className="assessment-depth-block assessment-build-primary">
            <h4>{text('Market history is building', 'Lịch sử thị trường đang được xây dựng')}</h4>
            <p className="assessment-build-lead">{text(
              'QPort is collecting stored D1 history before showing volatility, correlation and tail-risk statistics. Missing metrics are hidden instead of displayed as rows of dashes.',
              'QPort đang thu thập lịch sử D1 trước khi hiển thị biến động, tương quan và tail risk. Các chỉ số chưa đủ dữ liệu được ẩn thay vì hiển thị hàng loạt dấu gạch.'
            )}</p>
            <div className="diag-row"><span>{text('Risk coverage', 'Độ phủ risk')}</span><b>{pct(evidence.coverage)} · {evidence.eligible}/{evidence.requested} {text('holdings', 'mã')}</b></div>
            <Progress value={evidence.coverage} label={text('Risk-history coverage', 'Độ phủ lịch sử risk')} />
            <div className="diag-row"><span>{text('Return observations', 'Quan sát lợi suất')}</span><b>{evidence.returnObs}</b></div>
            <div className="diag-row"><span>{text('Missing / short D1 history', 'D1 thiếu / chưa đủ')}</span><b>{evidence.missing.length ? evidence.missing.join(', ') : text('Backfill in progress', 'Đang backfill')}</b></div>
            <div className="diag-row"><span>{text('Risk model', 'Mô hình risk')}</span><b>{methodology.return_type || 'log_return'} · {methodology.annualization || 252}D</b></div>
          </section>

          <section className="assessment-depth-block">
            <h4>{text('Portfolio structure', 'Cấu trúc danh mục')}</h4>
            <div className="diag-row"><span>{text('Effective / actual positions', 'Vị thế hiệu dụng / thực tế')}</span><b>{num(risk.effective_positions)} / {risk.n_positions ?? positions.length}</b></div>
            <div className="diag-row"><span>{text('Effective-position ratio', 'Tỷ lệ vị thế hiệu dụng')}</span><b>{pct(risk.effective_position_ratio)}</b></div>
            <div className="diag-row"><span>{text('Equity HHI', 'HHI cổ phiếu')}</span><b>{num(risk.equity_hhi, 3)}</b></div>
            <div className="diag-row"><span>{text('Largest equity weight', 'Tỷ trọng lớn nhất')}</span><b>{pct(risk.max_equity_weight)}</b></div>
            <p className="muted">{text('These concentration metrics come from current holdings and can be shown before long D1 history is ready.', 'Các chỉ số tập trung này lấy từ holdings hiện tại nên có thể hiển thị trước khi lịch sử D1 dài hạn sẵn sàng.')}</p>
          </section>

          <section className="assessment-depth-block">
            <h4>{text('Performance history maturity', 'Độ trưởng thành lịch sử hiệu suất')}</h4>
            <div className="diag-row"><span>{text('Official daily snapshots', 'Snapshot ngày chính thức')}</span><b>{evidence.historyCount}</b></div>
            <div className="diag-row"><span>{text('Basic short-history target', 'Mốc lịch sử ngắn')}</span><b>{Math.min(evidence.historyCount, 20)}/20</b></div>
            <Progress value={evidence.basicPerformanceDepth} label={text('Basic performance readiness', 'Mức sẵn sàng performance cơ bản')} />
            <div className="diag-row"><span>{text('Full 1-year view', 'Khung đầy đủ 1 năm')}</span><b>{Math.min(evidence.historyCount, 252)}/252</b></div>
            <Progress value={evidence.historyDepth} label={text('One-year history readiness', 'Mức sẵn sàng lịch sử 1 năm')} />
            <div className="diag-row"><span>{text('Tracking range', 'Khoảng theo dõi')}</span><b>{perf.first_date || '-'} → {perf.latest_date || '-'}</b></div>
          </section>
        </div>
        <p className="assessment-depth-note muted">{text('BUILDING means QPort is waiting for enough stored evidence; it does not mean the calculation failed. Risk metrics appear automatically after the D1 backfill completes.', 'BUILDING nghĩa là QPort đang chờ đủ dữ liệu đã lưu; không có nghĩa phép tính bị lỗi. Các chỉ số risk sẽ tự xuất hiện sau khi D1 backfill hoàn tất.')}</p>
      </> : <>
        <div className="assessment-depth-grid">
          <section className="assessment-depth-block">
            <h4>{text('Data readiness & methodology', 'Dữ liệu & phương pháp')}</h4>
            <div className="diag-row"><span>{text('Risk coverage', 'Độ phủ risk')}</span><b>{pct(evidence.coverage)} · {evidence.eligible}/{evidence.requested}</b></div>
            <div className="diag-row"><span>{text('Portfolio return observations', 'Quan sát lợi suất danh mục')}</span><b>{evidence.returnObs}</b></div>
            <div className="diag-row"><span>{text('Official performance snapshots', 'Snapshot performance chính thức')}</span><b>{evidence.historyCount}</b></div>
            <div className="diag-row"><span>{text('Risk return model', 'Mô hình return risk')}</span><b>{methodology.return_type || 'log_return'} · {methodology.annualization || 252}D</b></div>
            <div className="diag-row"><span>{text('Covariance evidence', 'Bằng chứng covariance')}</span><b>{quality.min_periods ? `≥${quality.min_periods} ${text('overlapping observations', 'quan sát giao nhau')}` : text('Pairwise history', 'Lịch sử pairwise')}</b></div>
          </section>

          <section className="assessment-depth-block">
            <h4>{text('Diversification & concentration', 'Đa dạng hóa & tập trung')}</h4>
            <div className="diag-row"><span>{text('Effective / actual positions', 'Vị thế hiệu dụng / thực tế')}</span><b>{num(risk.effective_positions)} / {risk.n_positions ?? positions.length}</b></div>
            <div className="diag-row"><span>{text('Effective-position ratio', 'Tỷ lệ vị thế hiệu dụng')}</span><b>{pct(risk.effective_position_ratio)}</b></div>
            <div className="diag-row"><span>{text('Equity HHI', 'HHI cổ phiếu')}</span><b>{num(risk.equity_hhi, 3)}</b></div>
            <div className="diag-row"><span>{text('Largest equity weight', 'Tỷ trọng cổ phiếu lớn nhất')}</span><b>{pct(risk.max_equity_weight)}</b></div>
            <div className="diag-row"><span>{text('Diversification ratio', 'Tỷ lệ đa dạng hóa')}</span><b>{num(risk.diversification_ratio)}</b></div>
            <div className="diag-row"><span>{text('Largest risk contributor', 'Đóng góp risk lớn nhất')}</span><b>{risk.largest_risk_symbol || '-'} {pct(risk.largest_risk_contribution)}</b></div>
          </section>

          <section className="assessment-depth-block">
            <h4>{text('Market co-movement & volatility', 'Đồng biến & biến động')}</h4>
            <div className="diag-row"><span>{text('63D / 252D volatility', 'Biến động 63D / 252D')}</span><b>{pct(risk.volatility_63)} / {pct(risk.volatility_252)}</b></div>
            <div className="diag-row"><span>{text('Volatility regime ratio', 'Tỷ lệ regime biến động')}</span><b>{num(risk.volatility_ratio)}×</b></div>
            <div className="diag-row"><span>{text('Average correlation', 'Tương quan trung bình')}</span><b>{num(risk.average_correlation)}</b></div>
            <div className="diag-row"><span>{text('Maximum pair correlation', 'Tương quan cặp lớn nhất')}</span><b>{num(risk.max_correlation)}</b></div>
            <div className="diag-row"><span>{text('Downside volatility', 'Biến động phía giảm')}</span><b>{pct(risk.downside_volatility)}</b></div>
            <div className="diag-row"><span>{text('Positive-day ratio', 'Tỷ lệ ngày tăng')}</span><b>{pct(risk.positive_day_ratio)}</b></div>
          </section>

          <section className="assessment-depth-block">
            <h4>{text('Tail risk & tracked performance', 'Tail risk & hiệu suất đã theo dõi')}</h4>
            <div className="diag-row"><span>{text('Daily VaR / CVaR 95%', 'VaR / CVaR ngày 95%')}</span><b>{pct(risk.daily_var_95)} / {pct(risk.daily_cvar_95)}</b></div>
            <div className="diag-row"><span>{text('Worst observed risk day', 'Ngày risk xấu nhất')}</span><b>{pct(risk.max_daily_loss)}</b></div>
            <div className="diag-row"><span>{text('Since-inception TWR', 'TWR từ khi bắt đầu')}</span><b>{pct(perf.returns?.since_inception)}</b></div>
            <div className="diag-row"><span>{text('Current / max drawdown', 'Drawdown hiện tại / lớn nhất')}</span><b>{pct(perf.current_drawdown)} / {pct(perf.max_drawdown)}</b></div>
            <div className="diag-row"><span>{text('Best / worst tracked day', 'Ngày tốt / xấu nhất đã theo dõi')}</span><b>{pct(perf.best_day)} / {pct(perf.worst_day)}</b></div>
            <div className="diag-row"><span>{text('Performance history', 'Lịch sử performance')}</span><b>{perf.history_status || '-'} · {perf.first_date || '-'} → {perf.latest_date || '-'}</b></div>
          </section>
        </div>
        <p className="assessment-depth-note muted">{text('Interpret these diagnostics together. Concentration, correlation and tail loss can disagree; no single metric is used as a trading trigger. Historical VaR/CVaR describes the stored sample and is not a forecast.', 'Các chẩn đoán này phải được đọc cùng nhau. Tập trung, tương quan và tail loss có thể cho tín hiệu khác nhau; không chỉ số đơn lẻ nào được dùng làm trigger giao dịch. VaR/CVaR lịch sử mô tả mẫu đã lưu và không phải dự báo.')}</p>
      </>}
    </div>,
    target,
  );
}
